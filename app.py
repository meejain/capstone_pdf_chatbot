"""
AI-Powered PDF Chatbot - an "Acrobat AI Assistant" style Streamlit application.

    streamlit run app.py

Left: PDF viewer (page rendering, navigation, zoom, cited-passage highlighting).
Right: "Ask AI Assistant" panel (suggestion cards, chat with memory, citations, follow-ups, multi-file scope).
"""
import html
import re
import time
from pathlib import Path

import streamlit as st

import config

st.set_page_config(page_title="AI Assistant - PDF Chatbot", page_icon="✦", layout="wide",
                   initial_sidebar_state="collapsed")

from rag import llm  # noqa: E402
from rag.assistant import ACTION_PROMPTS, CITATION_RE, Assistant, used_citations  # noqa: E402
from rag.knowledge_base import KnowledgeBase  # noqa: E402
from rag.viewer import page_count, render_page  # noqa: E402

CSS = Path(__file__).with_name("assets").joinpath("acrobat.css").read_text()
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

CATEGORY_ICON = {"company": "🏢", "financial": "📊", "research": "🔬", "government": "🏛️", "uploads": "📤"}
CARDS = [("summarize", "**Summarize** the key points of this document"),
         ("standout", "**Identify** what stands out in this doc"),
         ("questions", "**Suggest** questions to ask about this doc"),
         ("takeaways", "**List** the main takeaways from this document")]
DEFAULT_DOC = "VS-HR-001_Employee_Leave_Policy.pdf"


# ============================================================================== resources & state
@st.cache_resource(show_spinner="Loading embedding model and vector index ...")
def get_kb() -> KnowledgeBase:
    kb = KnowledgeBase()
    kb.retrieve("warm up", k=1)  # loads the cross-encoder once
    return kb


@st.cache_data(show_spinner=False, max_entries=64)
def cached_render(path: str, page: int, zoom: float, highlight: str | None):
    return render_page(path, page, zoom, highlight)


@st.cache_data(show_spinner=False)
def cached_page_count(path: str) -> int:
    return page_count(path)


kb = get_kb()
ss = st.session_state
ss.setdefault("chats", {})
ss.setdefault("show_assistant", True)
ss.setdefault("banner", True)
ss.setdefault("scope", "This document")
ss.setdefault("added_docs", [])
ss.setdefault("pending", None)
ss.setdefault("page", 1)
ss.setdefault("highlight", None)
ss.setdefault("processed_uploads", set())
ss.setdefault("model", config.LLM_MODEL)
ss.setdefault("compare", False)
ss.setdefault("compare_models", [])
ss.setdefault("settings", {"top_k": config.TOP_K, "hybrid": True, "rerank": True, "condense": True,
                           "self_correct": True, "followups": True, "trace": False})

assistant = Assistant(kb, model=ss.model)
docs = kb.documents()
if not docs:
    st.error("The knowledge base is empty. Run `python scripts/build_index.py` first, or use 'Add file to PDF Space' to upload a PDF.")
ordered = sorted(docs, key=lambda s: (list(config.CATEGORY_LABELS).index(docs[s]["category"])
                                      if docs[s]["category"] in config.CATEGORY_LABELS else 99, docs[s]["title"]))
if "doc" not in ss or ss.doc not in docs:
    ss.doc = DEFAULT_DOC if DEFAULT_DOC in docs else (ordered[0] if ordered else None)


def doc_path(source: str) -> Path:
    p = Path(docs[source]["path"])
    return p if p.is_absolute() else config.ROOT / p


def open_doc(source: str, page: int = 1, highlight: str | None = None):
    ss.doc, ss.page, ss.highlight = source, page, highlight


def scope_sources() -> list[str] | None:
    if ss.scope == "All documents":
        return None
    return [ss.doc] + [d for d in ss.added_docs if d != ss.doc and d in docs]


def chat_key() -> str:
    src = scope_sources()
    return "ALL" if src is None else "|".join(src)


def ingest_upload(files):
    new = [f for f in files if f.name not in ss.processed_uploads]
    if not new:
        return
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with st.status("Processing your PDF ...", expanded=True) as status:
        paths = []
        for f in new:
            p = config.UPLOAD_DIR / re.sub(r"[^\w.\- ]", "_", f.name)
            p.write_bytes(f.getbuffer())
            paths.append(p)
            ss.processed_uploads.add(f.name)
        st.write("📄 Extracting text with PyPDFLoader ...")
        st.write(f"✂️ Chunking (size {config.CHUNK_SIZE}, overlap {config.CHUNK_OVERLAP}) ...")
        st.write(f"🧠 Embedding with {config.EMBEDDINGS_MODEL} and indexing in FAISS + BM25 ...")
        t0 = time.time()
        stats = kb.add_pdfs(paths)
        label = (f"Indexed {stats['files']} file(s): {stats['pages']} pages, {stats['chunks']} chunks "
                 f"in {time.time() - t0:.1f}s")
        if not stats["files"]:
            label = "Already in the knowledge base - opening it"
        status.update(label=label, state="complete", expanded=False)
    names = [p.name for p in paths if p.name in kb.manifest]
    if names:
        open_doc(names[0])
        ss.added_docs = list(dict.fromkeys(ss.added_docs + names[1:]))
    st.rerun()


# ============================================================================== settings (in the "..." menu)
@st.cache_data(ttl=30, show_spinner=False)
def served_models() -> list[str]:
    return llm.list_models()


def chat_models() -> list[str]:
    return [m for m in served_models() if "embed" not in m.lower()]


def render_settings():
    st.markdown("**⚙️ Assistant settings**")
    if chat_models():
        st.caption(f"LLM server: {config.LLM_BASE_URL} · {len(chat_models())} chat model(s). "
                   "Pick the model (or compare models) under the scope selector.")
    else:
        st.error(f"LLM server not reachable at {config.LLM_BASE_URL}. Start LM Studio / Ollama.")
    s = ss.settings
    s["top_k"] = st.slider("Passages sent to the LLM (top-k)", 2, 12, s["top_k"], key="set_topk")
    s["hybrid"] = st.toggle("Hybrid search (dense + BM25, RRF)", s["hybrid"], key="set_hybrid")
    s["rerank"] = st.toggle("Cross-encoder re-ranking", s["rerank"], key="set_rerank")
    s["condense"] = st.toggle("Condense follow-ups with chat history", s["condense"], key="set_condense")
    s["self_correct"] = st.toggle("Self-correction (rewrite query on low relevance)", s["self_correct"],
                                  key="set_selfcorrect")
    s["followups"] = st.toggle("Suggest follow-up questions", s["followups"], key="set_followups")
    s["trace"] = st.toggle("Show retrieval trace", s["trace"], key="set_trace")
    st.markdown("**📚 Knowledge base**")
    by_cat = {}
    for d in docs.values():
        c = by_cat.setdefault(d["category"], [0, 0, 0])
        c[0] += 1
        c[1] += d["pages"]
        c[2] += d["chunks"]
    st.dataframe([{"Collection": config.CATEGORY_LABELS.get(k, k), "PDFs": v[0], "Pages": v[1], "Chunks": v[2]}
                  for k, v in by_cat.items()], hide_index=True, width="stretch")
    st.caption(f"{len(docs)} PDFs · {sum(v['pages'] for v in docs.values())} pages · {len(kb.chunks)} chunks · "
               f"embeddings: {config.EMBEDDINGS_MODEL} ({kb.device}) · vector DB: FAISS + BM25")


# ============================================================================== top bar
with st.container(key="topbar", horizontal=True, vertical_alignment="center"):
    with st.popover("Add file to PDF Space", icon=":material/note_add:", key="add_space"):
        up = st.file_uploader("Upload PDF(s)", type=["pdf"], accept_multiple_files=True, key="uploader_top")
        if up:
            ingest_upload(up)
    st.markdown("<div class='menu'><span>All tools</span><span class='active'>Read</span><span>Edit</span>"
                "<span>Convert</span><span>E-Sign</span></div>", unsafe_allow_html=True)
    st.space("stretch")
    st.markdown("<div class='find'>Find text, tools, or help &nbsp;🔍</div>", unsafe_allow_html=True)
    st.button("Share", key="share_btn")
    if st.button("Ask AI Assistant", key="ask_ai", icon=":material/auto_awesome:"):
        ss.show_assistant = not ss.show_assistant
        st.rerun()

if ss.banner and ss.doc:
    with st.container(key="banner", horizontal=True, vertical_alignment="center"):
        st.markdown("<div class='banner-text'>✦ &nbsp;Save time with a document summary using AI Assistant.</div>",
                    unsafe_allow_html=True)
        if st.button("View Summary", key="view_summary"):
            ss.show_assistant = True
            ss.scope = "This document"
            ss.pending = {"action": "summarize", "question": ACTION_PROMPTS["summarize"][0]}
            st.rerun()
        if st.button("✕", key="close_banner"):
            ss.banner = False
            st.rerun()

if not ss.doc:
    st.stop()

# ============================================================================== main layout
ratio = ([0.45, 0.55] if ss.compare else [0.6, 0.4]) if ss.show_assistant else [0.999, 0.001]
viewer_col, ai_col = st.columns(ratio, gap="small")

# ----------------------------------------------------------------------------- PDF viewer
with viewer_col:
    path = doc_path(ss.doc)
    n_pages = cached_page_count(str(path))
    with st.container(key="viewer_toolbar", horizontal=True, vertical_alignment="center"):
        sel = st.selectbox("Document", ordered, index=ordered.index(ss.doc), key=f"doc_select_{ss.doc}",
                           format_func=lambda s: f"{CATEGORY_ICON.get(docs[s]['category'], '📄')}  {docs[s]['title']}",
                           label_visibility="collapsed", width=430)
        if sel != ss.doc:
            open_doc(sel)
            st.rerun()
        if st.button("", icon=":material/chevron_left:", key="prev_page", disabled=ss.page <= 1):
            ss.page, ss.highlight = ss.page - 1, None
            st.rerun()
        st.markdown(f"<div class='pageno'>{ss.page} / {n_pages}</div>", unsafe_allow_html=True)
        if st.button("", icon=":material/chevron_right:", key="next_page", disabled=ss.page >= n_pages):
            ss.page, ss.highlight = ss.page + 1, None
            st.rerun()
        goto = st.number_input("Go to page", 1, n_pages, ss.page, key=f"goto_{ss.doc}_{ss.page}",
                               label_visibility="collapsed", width=90)
        if goto != ss.page:
            ss.page, ss.highlight = int(goto), None
            st.rerun()
        zoom = st.selectbox("Zoom", [1.0, 1.25, 1.5, 1.75, 2.0], index=2, key="zoom",
                            format_func=lambda z: f"{int(z * 100)}%", label_visibility="collapsed", width=95)
    png, found = cached_render(str(path), ss.page, zoom * 1.3, ss.highlight)
    with st.container(key="page_canvas", height=730, border=False):
        if ss.highlight:
            st.markdown(f"<div class='hl-note'>🔎 Showing cited passage on page {ss.page}"
                        f"{'' if found else ' (exact text could not be located - see source snippet)'}</div>",
                        unsafe_allow_html=True)
        st.image(png, width="stretch")

# ----------------------------------------------------------------------------- AI Assistant panel
def render_answer_html(text: str) -> str:
    return CITATION_RE.sub(lambda m: "".join(f"<span class='cite'>{n.strip()}</span>" for n in m.group(1).split(",")),
                           text)


def citation_chips(cites: list, key: str):
    cites = sorted(cites or [], key=lambda c: c["n"])
    if not cites:
        return
    with st.container(horizontal=True, key=f"cites_{key}"):
        for c in cites:
            label = f"{c['n']} · p.{c['page']}" + ("" if c["source"] == ss.doc else f" · {c['title'][:22]}")
            if st.button(label, key=f"cite_{key}_{c['n']}", help=f"{c['title']} - page {c['page']}"):
                open_doc(c["source"], c["page"], c["text"])
                st.rerun()


def show_comparison(i: int, m: dict):
    with st.container(key=f"answer_{i}"):
        st.markdown(f"<div class='ai-label'>✦ AI Assistant · model comparison</div>", unsafe_allow_html=True)
        st.caption("Same question, same retrieved passages - only the LLM differs.")
        cols = st.columns(len(m["variants"]), border=True)
        for j, (col, v) in enumerate(zip(cols, m["variants"])):
            with col:
                st.markdown(f"<div class='model-badge'>{html.escape(v['model'])}</div>", unsafe_allow_html=True)
                st.markdown(render_answer_html(v["content"]), unsafe_allow_html=True)
                citation_chips(v["citations"], f"{i}_{j}")
                st.caption(f"⏱ {v['elapsed']:.1f}s · 📎 {len(v['citations'])} citation(s) · "
                           f"{len(v['content'].split())} words")
                st.feedback("thumbs", key=f"fb_{chat_key()}_{i}_{j}")
        if ss.settings["trace"] and m.get("trace"):
            with st.expander("Retrieval trace"):
                st.json(m["trace"])


def show_message(i: int, m: dict):
    if m["role"] == "user":
        st.markdown(f"<div class='user-bubble'>{html.escape(m['content'])}</div>", unsafe_allow_html=True)
        return
    if m.get("variants"):
        show_comparison(i, m)
        return
    with st.container(key=f"answer_{i}"):
        st.markdown("<div class='ai-label'>✦ AI Assistant</div>", unsafe_allow_html=True)
        st.markdown(render_answer_html(m["content"]), unsafe_allow_html=True)
        cites = sorted(m.get("citations") or [], key=lambda c: c["n"])
        if cites:
            st.markdown("<div class='src-label'>Sources</div>", unsafe_allow_html=True)
            citation_chips(cites, str(i))
            with st.expander("View source passages"):
                for c in cites:
                    st.markdown(f"**[{c['n']}] {c['title']} - page {c['page']}**")
                    st.caption(c["text"][:700] + ("..." if len(c["text"]) > 700 else ""))
        with st.container(horizontal=True, vertical_alignment="center", key=f"meta_{i}"):
            st.feedback("thumbs", key=f"fb_{chat_key()}_{i}")
            if m.get("elapsed"):
                st.caption(f"{m['elapsed']:.1f}s · {m.get('intent', 'qa')} · {m.get('model', '')}")
        if ss.settings["trace"] and m.get("trace"):
            with st.expander("Retrieval trace"):
                st.json(m["trace"])
        if m.get("followups"):
            with st.container(key=f"fus_{i}", gap=None):
                for j, q in enumerate(m["followups"]):
                    if st.button(f"↳ {q}", key=f"fu_{i}_{j}", type="tertiary"):
                        ss.pending = {"question": q}
                        st.rerun()


def run_pending(chat: list, container):
    p = ss.pending
    ss.pending = None
    history = [{"role": m["role"], "content": m["content"]} for m in chat]
    chat.append({"role": "user", "content": p["question"]})
    with container:
        show_message(len(chat) - 1, chat[-1])
        with st.container(key="streaming"):
            st.markdown("<div class='ai-label'>✦ AI Assistant</div>", unsafe_allow_html=True)
            t0 = time.time()
            with st.spinner("Searching the document(s) ..." if not p.get("action") else "Reading the document ..."):
                prep = assistant.prepare(p["question"], history, scope_sources(), p.get("action"), ss.settings)
            models = ss.compare_models if ss.compare and len(ss.compare_models) >= 2 else []
            if models and prep.intent != "smalltalk":
                run_comparison(chat, prep, models, t0)
            try:
                text = st.write_stream(llm.stream(prep.messages, model=ss.model))
            except Exception as e:  # LLM server down etc.
                text = f"⚠️ The language model could not be reached ({e}). Check the LLM server (⋯ menu)."
            text = text if isinstance(text, str) else "".join(map(str, text))
            elapsed = time.time() - t0
            follow = []
            if ss.settings["followups"] and prep.intent != "smalltalk" and not text.startswith("⚠️"):
                with st.spinner("Suggesting follow-ups ..."):
                    follow = assistant.followups(prep.standalone or p["question"], text)
    prep.trace["total_s"] = round(elapsed, 2)
    prep.trace["passages"] = [f"{h.doc.metadata['title']} p.{h.doc.metadata['page']} (score {h.score:.2f})"
                              for h in prep.hits][:12]
    chat.append({"role": "assistant", "content": text, "citations": used_citations(text, prep.hits),
                 "followups": follow, "trace": prep.trace, "intent": prep.intent, "elapsed": elapsed,
                 "model": ss.model})
    st.rerun()


def run_comparison(chat: list, prep, models: list[str], t0: float):
    """Stream the same grounded prompt through several models, side by side."""
    variants = []
    cols = st.columns(len(models), border=True)
    for col, model in zip(cols, models):
        with col:
            st.markdown(f"<div class='model-badge'>{html.escape(model)}</div>", unsafe_allow_html=True)
            t1 = time.time()
            try:
                with st.spinner(f"{model} is answering ..."):
                    text = st.write_stream(llm.stream(prep.messages, model=model))
                text = text if isinstance(text, str) else "".join(map(str, text))
            except Exception as e:
                text = f"⚠️ {model} failed: {e}"
            variants.append({"model": model, "content": text, "citations": used_citations(text, prep.hits),
                             "elapsed": time.time() - t1})
    prep.trace["total_s"] = round(time.time() - t0, 2)
    prep.trace["passages"] = [f"{h.doc.metadata['title']} p.{h.doc.metadata['page']} (score {h.score:.2f})"
                              for h in prep.hits][:12]
    chat.append({"role": "assistant", "content": variants[0]["content"], "variants": variants,
                 "trace": prep.trace, "intent": prep.intent, "elapsed": time.time() - t0})
    st.rerun()


if ss.show_assistant:
    with ai_col, st.container(key="ai_panel"):
        with st.container(key="ai_header", horizontal=True, vertical_alignment="center"):
            if st.button("✕", key="close_ai"):
                ss.show_assistant = False
                st.rerun()
            online = bool(served_models())
            st.markdown("<div class='ai-title'>Ask AI Assistant <span class='shield'>🛡️</span></div>"
                        f"<div class='llm-status {'on' if online else 'off'}'>● "
                        f"{'Comparing ' + str(len(ss.compare_models)) + ' models' if ss.compare else ss.model}"
                        f"{' · local' if 'localhost' in config.LLM_BASE_URL else ''}</div>", unsafe_allow_html=True)
            st.space("stretch")
            with st.popover("Add files", icon=":material/add:", key="add_files"):
                st.caption("Ask questions across several PDFs at once.")
                others = [d for d in ordered if d != ss.doc]
                chosen = st.multiselect("Add documents from the library", others,
                                        default=[d for d in ss.added_docs if d in others],
                                        format_func=lambda s: docs[s]["title"], key="added_select")
                if chosen != ss.added_docs:
                    ss.added_docs = chosen
                    ss.scope = "This document"
                    st.rerun()
                up2 = st.file_uploader("...or upload new PDFs", type=["pdf"], accept_multiple_files=True,
                                       key="uploader_ai")
                if up2:
                    ingest_upload(up2)
            with st.popover("", icon=":material/more_horiz:", key="more_menu"):
                if st.button("🗑️ Clear this conversation", key="clear_chat"):
                    ss.chats.pop(chat_key(), None)
                    st.rerun()
                render_settings()

        n_extra = len([d for d in ss.added_docs if d != ss.doc])
        doc_label = "This document" if not n_extra else f"This document + {n_extra} file(s)"
        scope = st.segmented_control("Scope", ["This document", "All documents"], key=f"scope_{ss.scope}",
                                     default=ss.scope, format_func=lambda o: doc_label if o == "This document"
                                     else f"All documents ({len(docs)})", label_visibility="collapsed")
        if scope and scope != ss.scope:
            ss.scope = scope
            st.rerun()

        cms = chat_models()
        if cms:
            with st.container(key="model_row", horizontal=True, vertical_alignment="center"):
                if ss.model not in cms:
                    ss.model = config.LLM_MODEL if config.LLM_MODEL in cms else cms[0]
                picked = st.selectbox("Model", cms, index=cms.index(ss.model), key=f"model_pick_{ss.model}",
                                      label_visibility="collapsed", width=250, disabled=ss.compare,
                                      format_func=lambda m: f"🧠 {m}")
                if picked != ss.model:
                    ss.model = picked
                    st.rerun()
                cmp_on = st.toggle("Compare models", ss.compare, key="compare_toggle",
                                   help="Answer each question with 2-3 models side by side (same retrieved passages)")
                if cmp_on != ss.compare:
                    ss.compare = cmp_on
                    if cmp_on and len(ss.compare_models) < 2:
                        ss.compare_models = cms[:3]
                    st.rerun()
            if ss.compare:
                chosen_models = st.multiselect("Models to compare", cms, default=[m for m in ss.compare_models if m in cms],
                                               max_selections=3, key="compare_select", label_visibility="collapsed",
                                               placeholder="Pick 2-3 models to compare")
                if chosen_models != ss.compare_models:
                    ss.compare_models = chosen_models
                    st.rerun()
                if len(ss.compare_models) < 2:
                    st.caption("Select at least two models to compare.")

        chat = ss.chats.setdefault(chat_key(), [])
        box = st.container(key="chat_box", height=560, border=False, autoscroll=True)
        with box:
            if not chat and not ss.pending:
                st.markdown("<div class='hello'><div class='sparkle'>✦</div>Hi, how can I help you?</div>",
                            unsafe_allow_html=True)
                if ss.scope == "All documents":
                    st.caption("Searching across the whole PDF library. Try: *Compare Adobe's revenue in FY2023 "
                               "and FY2024* or *What does the RAG paper say about retrieval?*")
                for row in (CARDS[:2], CARDS[2:]):
                    c1, c2 = st.columns(2)
                    for col, (action, label) in zip((c1, c2), row):
                        if col.button(label, key=f"card_{action}", width="stretch"):
                            ss.scope = "This document"
                            ss.pending = {"action": action, "question": ACTION_PROMPTS[action][0]}
                            st.rerun()
            for i, m in enumerate(chat):
                show_message(i, m)

        question = st.chat_input("Ask a question about this document" if ss.scope == "This document"
                                 else "Ask a question across all documents", key="chat_input")
        if question:
            ss.pending = {"question": question}
        if ss.pending:
            run_pending(chat, box)
        st.markdown("<div class='disclaimer'>Your files are processed locally (FAISS + local LLM). "
                    "AI responses may be inaccurate - check the cited pages.</div>", unsafe_allow_html=True)
