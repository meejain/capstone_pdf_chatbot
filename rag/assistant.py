"""
The assistant "brain": routing, question condensation, retrieval with self-correction, grounded prompt
construction (step 8) and post-processing of citations.  The UI calls `prepare()` and streams the LLM output.
"""
import json
import re
import time
from dataclasses import dataclass, field

from langchain_core.documents import Document

import config
from rag import llm
from rag.knowledge_base import Hit, KnowledgeBase

# --------------------------------------------------------------------------------------- prompts
QA_SYSTEM = """You are "AI Assistant", a helpful PDF assistant similar to Adobe Acrobat AI Assistant.
Answer the user's question using ONLY the numbered context passages taken from their PDF documents.

Rules:
1. Ground every statement in the passages and cite them inline with the passage number in square brackets, e.g. [1] or [2][4]. Put citations right after the sentence they support.
2. If the passages do not contain the answer, reply: "I couldn't find that in the selected document(s)." and then briefly say what related information is available. Never use outside knowledge and never guess numbers.
3. Be concise and well structured: start with a direct answer, then supporting detail as short bullet points. Bold key figures.
4. When comparing documents or years, use a small markdown table.
5. Do not mention "passages" or "context" - talk about "the document"."""

ACTION_PROMPTS = {
    "summarize": ("Summarize the key points of this document",
                  "Write a summary of the document. Start with a one-sentence overview in bold, then 5-8 bullet points "
                  "covering the most important facts, figures, rules or findings. Cite passages like [3]."),
    "standout": ("Identify what stands out in this document",
                 "Identify what stands out most in this document: the most important, surprising or noteworthy facts, "
                 "numbers, risks, obligations or decisions. Give 4-6 bullets, each starting with a short bold headline. "
                 "Cite passages like [3]."),
    "questions": ("Suggest questions to ask about this document",
                  "Suggest 5 insightful questions a reader could ask about this document. For each, give the question "
                  "in bold followed by a one-sentence answer from the document with a citation like [3]."),
    "takeaways": ("List the main takeaways from this document",
                  "List the 5-7 main takeaways from this document as a numbered list. Each item: a bold one-line "
                  "takeaway followed by a short explanation of why it matters. Cite passages like [3]."),
}

FACET_QUERIES = [
    "overview purpose scope introduction abstract summary",
    "key results findings figures metrics numbers",
    "conclusion recommendations outlook next steps",
    "risks challenges limitations obligations requirements",
]

CONDENSE_PROMPT = """Rewrite the user's latest follow-up message as a single standalone question that can be understood \
without the conversation. Resolve pronouns such as "it", "they", "that" and include the relevant names, documents, \
products or years from the conversation. If the message is already standalone, return it unchanged.
Return ONLY the rewritten question.

Conversation:
{history}

Follow-up message: {question}
Standalone question:"""

REWRITE_PROMPT = """A document search for the question below returned no relevant passages.
Rewrite it as a short, keyword-rich search query (max 15 words) using terms that would literally appear in a \
{doc_kind} document. Return ONLY the query.

Question: {question}
Search query:"""

FOLLOWUP_PROMPT = """Based on the question and answer below about a PDF document, suggest 3 short follow-up \
questions (max 12 words each) the user may want to ask next. They must be answerable from the same document.
Return ONLY a JSON list of strings.

Question: {question}
Answer: {answer}
JSON:"""

SMALLTALK_SYSTEM = """You are "AI Assistant", a friendly PDF assistant (similar to Adobe Acrobat AI Assistant) running \
locally. You help users understand PDF documents: summarise them, answer questions with page citations, identify key \
points and compare several documents. Reply briefly and invite the user to ask about the open document."""

SMALLTALK_RE = re.compile(r"^\s*(hi|hello|hey|hola|namaste|good (morning|afternoon|evening)|thanks|thank you|thx|"
                          r"who are you|what can you do|help)\b[\s!?.]*$", re.I)
SUMMARY_RE = re.compile(r"\b(summari[sz]e|summary|overview|tl;?dr|gist)\b", re.I)
CITATION_RE = re.compile(r"\[(\d{1,2}(?:\s*,\s*\d{1,2})*)\]")  # [3] or grouped [1, 5]


@dataclass
class Prepared:
    messages: list[dict]
    hits: list[Hit] = field(default_factory=list)
    intent: str = "qa"
    standalone: str = ""
    trace: dict = field(default_factory=dict)


def _fmt_history(history: list[dict], max_turns: int = 6) -> str:
    lines = []
    for m in history[-max_turns:]:
        content = re.sub(r"\s+", " ", m["content"])[:600]
        lines.append(f"{'User' if m['role'] == 'user' else 'Assistant'}: {content}")
    return "\n".join(lines)


def format_context(hits: list[Hit]) -> str:
    blocks = []
    for i, h in enumerate(hits, 1):
        md = h.doc.metadata
        blocks.append(f"[{i}] (Document: {md['title']}, page {md['page']})\n{md.get('text', h.doc.page_content)}")
    return "\n\n".join(blocks)


def route(question: str, action: str | None, single_doc: bool) -> str:
    if action:
        return action
    if SMALLTALK_RE.match(question):
        return "smalltalk"
    if single_doc and SUMMARY_RE.search(question) and len(question.split()) <= 12:
        return "summarize"
    return "qa"


class Assistant:
    def __init__(self, kb: KnowledgeBase, model: str | None = None):
        self.kb = kb
        self.model = model  # None -> config.LLM_MODEL at call time (what the UI selector changes)

    # ------------------------------------------------------------------ helpers
    def condense(self, question: str, history: list[dict]) -> str:
        if not history:
            return question
        out = llm.complete([{"role": "user", "content": CONDENSE_PROMPT.format(history=_fmt_history(history),
                                                                                question=question)}],
                           model=self.model, temperature=0.0, max_tokens=120)
        out = out.strip().strip('"').splitlines()[0] if out.strip() else question
        return out or question

    def _doc_kind(self, sources):
        if not sources:
            return "business or research"
        cats = {self.kb.manifest.get(s, {}).get("category", "") for s in sources}
        return {"financial": "financial annual report", "research": "research paper", "company": "company policy or manual",
                "government": "government framework"}.get(next(iter(cats)), "PDF")

    def retrieve(self, query: str, sources, settings: dict, trace: dict) -> list[Hit]:
        t0 = time.time()
        hits = self.kb.retrieve(query, sources=sources, k=settings.get("top_k", config.TOP_K),
                                hybrid=settings.get("hybrid", True), rerank=settings.get("rerank", True))
        trace["retrieval_ms"] = int((time.time() - t0) * 1000)
        best = hits[0].score if hits else float("-inf")
        trace["best_score"] = round(best, 3) if hits else None
        # Self-correction: if the best passage is not relevant, rewrite the query once and retry.
        if settings.get("rerank", True) and settings.get("self_correct", True) and best < config.RELEVANCE_THRESHOLD:
            rewritten = llm.complete([{"role": "user", "content": REWRITE_PROMPT.format(
                question=query, doc_kind=self._doc_kind(sources))}], model=self.model, temperature=0.0, max_tokens=60)
            rewritten = rewritten.strip().strip('"').splitlines()[0] if rewritten.strip() else query
            retry = self.kb.retrieve(query, sources=sources, k=settings.get("top_k", config.TOP_K),
                                     hybrid=settings.get("hybrid", True), rerank=True, extra_queries=[rewritten])
            trace["self_correction"] = {"rewritten_query": rewritten,
                                        "new_best_score": round(retry[0].score, 3) if retry else None}
            if retry and retry[0].score > best:
                hits, best = retry, retry[0].score
        trace["low_relevance"] = bool(settings.get("rerank", True) and best < config.RELEVANCE_THRESHOLD)
        return hits

    def document_context(self, source: str, action: str, settings: dict, trace: dict) -> list[Hit]:
        """Context for whole-document actions: the full text for short docs, multi-facet retrieval for long ones."""
        chunks = self.kb.document_chunks(source)
        total = sum(len(c.metadata.get("text", c.page_content)) for c in chunks)
        trace["doc_chars"] = total
        if total <= config.SUMMARY_CHAR_BUDGET:
            trace["strategy"] = "full document (stuffing)"
            return [Hit(c) for c in chunks]
        trace["strategy"] = "multi-facet retrieval (long document)"
        picked: dict[str, Hit] = {c.metadata["chunk_id"]: Hit(c) for c in chunks[:3]}  # title / abstract / intro
        queries = FACET_QUERIES + [ACTION_PROMPTS[action][0]]
        per_query = max(3, (config.SUMMARY_CHAR_BUDGET // config.CHUNK_SIZE - 3) // len(queries))
        for q in queries:
            for h in self.kb.retrieve(q, sources=[source], k=per_query, hybrid=True, rerank=settings.get("rerank", True)):
                picked.setdefault(h.doc.metadata["chunk_id"], h)
        hits = list(picked.values())
        hits.sort(key=lambda h: (h.doc.metadata["page"], h.doc.metadata["chunk_id"]))
        budget, out = config.SUMMARY_CHAR_BUDGET, []
        for h in hits:
            n = len(h.doc.metadata.get("text", h.doc.page_content))
            if budget - n < 0:
                break
            out.append(h)
            budget -= n
        return out

    # ------------------------------------------------------------------ main entry point
    def prepare(self, question: str, history: list[dict], sources: list[str] | None,
                action: str | None = None, settings: dict | None = None) -> Prepared:
        settings = settings or {}
        single = bool(sources) and len(sources) == 1
        intent = route(question, action, single)
        trace = {"intent": intent, "scope": sources if sources else "all documents"}

        if intent == "smalltalk":
            msgs = [{"role": "system", "content": SMALLTALK_SYSTEM}] + history[-4:] + [{"role": "user", "content": question}]
            return Prepared(msgs, [], intent, question, trace)

        if intent in ACTION_PROMPTS:
            if not single:
                sources = sources[:1] if sources else None
            if not sources:
                intent = "qa"
            else:
                hits = self.document_context(sources[0], intent, settings, trace)
                title = self.kb.manifest.get(sources[0], {}).get("title", sources[0])
                user = (f"Document: {title}\n\nContext passages:\n{format_context(hits)}\n\n"
                        f"Task: {ACTION_PROMPTS[intent][1]}")
                return Prepared([{"role": "system", "content": QA_SYSTEM}, {"role": "user", "content": user}],
                                hits, intent, ACTION_PROMPTS[intent][0], trace)

        t0 = time.time()
        standalone = self.condense(question, history) if settings.get("condense", True) else question
        trace["condense_ms"] = int((time.time() - t0) * 1000)
        trace["standalone_question"] = standalone
        hits = self.retrieve(standalone, sources, settings, trace)
        note = ""
        if trace.get("low_relevance"):
            note = ("\nNote: the search found only weakly related passages. If they do not answer the question, "
                    "say you couldn't find it in the selected document(s).")
        user = f"Context passages:\n{format_context(hits)}\n\nQuestion: {standalone}{note}"
        msgs = [{"role": "system", "content": QA_SYSTEM}]
        for m in history[-4:]:  # short conversational memory for tone / continuity
            msgs.append({"role": m["role"], "content": m["content"][:1500]})
        msgs.append({"role": "user", "content": user})
        return Prepared(msgs, hits, "qa", standalone, trace)

    def answer(self, question: str, history: list[dict] | None = None, sources: list[str] | None = None,
               action: str | None = None, settings: dict | None = None) -> dict:
        """Non-streaming convenience API (used by tests, evaluation and the CLI)."""
        t0 = time.time()
        prep = self.prepare(question, history or [], sources, action, settings)
        text = llm.complete(prep.messages, model=self.model)
        prep.trace["model"] = self.model or config.LLM_MODEL
        prep.trace["total_ms"] = int((time.time() - t0) * 1000)
        return {"answer": text, "citations": used_citations(text, prep.hits), "prepared": prep}

    def followups(self, question: str, answer: str) -> list[str]:
        try:
            raw = llm.complete([{"role": "user", "content": FOLLOWUP_PROMPT.format(question=question,
                                                                                    answer=answer[:1500])}],
                               model=self.model, temperature=0.3, max_tokens=150)
            raw = raw[raw.find("["): raw.rfind("]") + 1]
            items = [q.strip() for q in json.loads(raw) if isinstance(q, str) and q.strip()]
            return items[:3]
        except (ValueError, json.JSONDecodeError):
            return []


def used_citations(text: str, hits: list[Hit]) -> list[dict]:
    """Return the passages actually cited in the answer (in order of first citation)."""
    seen, out = set(), []
    numbers = [int(n) for m in CITATION_RE.finditer(text) for n in m.group(1).split(",")]
    for n in numbers:
        if 1 <= n <= len(hits) and n not in seen:
            seen.add(n)
            md = hits[n - 1].doc.metadata
            out.append({"n": n, "source": md["source"], "title": md["title"], "page": md["page"],
                        "text": md.get("text", hits[n - 1].doc.page_content), "score": hits[n - 1].score})
    return out


def doc_from_hit(h: Hit) -> Document:
    return h.doc
