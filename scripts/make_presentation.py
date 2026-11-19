"""
Builds the capstone presentation from one content model into two formats:
  deliverables/AI_PDF_Chatbot_Capstone.pptx  (python-pptx, with speaker notes)
  deliverables/AI_PDF_Chatbot_Capstone.pdf   (reportlab, same slides)
Run after the evaluation and the demo recording (uses evaluation_results.json, figures/ and screenshots/).
"""
import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "deliverables"
FIG, SHOT = D / "figures", D / "screenshots"
BLUE, PINK, INK, GREY = (11, 92, 173), (214, 36, 110), (44, 44, 44), (110, 110, 110)
PRESENTER = "Meet Kumar Jain"
RES = json.loads((D / "evaluation_results.json").read_text())
A, R = RES["answers"], RES["retrieval"]
MC_PATH = D / "model_comparison.json"
MC = json.loads(MC_PATH.read_text()) if MC_PATH.exists() else {}


def model_slide():
    if len(MC) < 2:
        return []
    rows = [["LLM (same retrieval & prompt)", "Accuracy", "Cited", "Refused OOS", "Avg latency"]]
    for m, r in MC.items():
        rows.append([m, f"{r['accuracy']:.0%}", f"{r['citation_rate']:.0%}", f"{r['refusal_rate']:.0%}", f"{r['avg_seconds']} s"])
    best = max(MC, key=lambda m: (MC[m]["accuracy"], MC[m]["citation_rate"]))
    fastest = min(MC, key=lambda m: MC[m]["avg_seconds"])
    bullets = [f"Most accurate: {best} - chosen as the default generator",
               f"Fastest: {fastest} ({MC[fastest]['avg_seconds']} s avg) - good for quick look-ups on modest hardware",
               "Smaller models mostly fail on reading tables (wrong column / row) even with the right passage retrieved",
               "UI: pick any served model, or switch on 'Compare models' to see 2-3 answers side by side"]
    return [dict(title="LLM comparison: same RAG pipeline, different generators", table=rows, bullets=bullets,
                 below=SHOT / "10_model_compare.png",
                 notes="scripts/eval_rag.py --models ... ; the UI 'Compare models' toggle shows the same in the app.")]


def col_weights(rows):
    w = [max(len(str(r[j])) for r in rows) + 4 for j in range(len(rows[0]))]
    tot = sum(w)
    return [x / tot for x in w]


def shot(name):
    p = SHOT / f"{name}.png"
    return p if p.exists() else None


SLIDES = [
    dict(kind="title", title="AI-Powered PDF Chatbot", presenter=PRESENTER,
         subtitle="An Acrobat-style \"Ask AI Assistant\" built with Retrieval-Augmented Generation",
         footer="Capstone Case Study · Agentic AI Training (Batch 3, 2026)",
         notes="Introduce the project: a chatbot to interact with PDFs in natural language, modelled on Acrobat AI Assistant."),
    dict(title="Business problem & objective", bullets=[
        "Organisations produce large volumes of reports, manuals, research papers and policies",
        "Finding the right information manually is slow and error-prone - information overload",
        "Goal: a chatbot that understands PDF content and answers questions, explains and summarises",
        "Answers must be grounded in the document - verifiable, with page references, no hallucinations",
        "Constraints we set: runs fully locally (privacy), works on 50-100+ documents, familiar Acrobat-like UX"],
         image=shot("01_home"), notes="Problem statement from the case study; our additional constraints: privacy, scale, UX."),
    dict(title="Solution at a glance", bullets=[
        "Streamlit app with PDF viewer + Ask AI Assistant panel (suggestion cards, chat)",
        "RAG pipeline: PyPDFLoader → recursive chunks → gte-large → FAISS + BM25",
        "Hybrid retrieval + cross-encoder re-ranking + self-correcting query rewrite",
        "Local LLM: Gemma-3-12B via LM Studio (OpenAI-compatible API)",
        "Inline citations → click to jump to the page with the passage highlighted",
        "Conversation memory, follow-up suggestions, multi-document & library-wide scope, PDF upload"],
         image=shot("03_citation_highlight"), notes="Walk through the screenshot: citation chip → highlighted passage."),
    dict(title="End-to-end workflow", image=FIG / "workflow.png", image_pos="full", bullets=[
        "Steps 1-5 (ingestion) run once per document - offline for the library, in seconds for uploads",
        "Steps 6-10 run per question - typically 3-10 s on an Apple M3 Max laptop"],
         notes="This matches the 10-step workflow from the reference guide."),
    dict(title="System architecture", image=FIG / "architecture.png", image_pos="full",
         notes="Explain ingestion lane and online lane; modules have clean interfaces and can be swapped."),
    dict(title="Document corpus: 71 PDFs, ~2,330 pages, 9,834 chunks", table=[
        ["Collection", "PDFs", "Pages", "Examples", "Why"],
        ["Financial annual reports", "12", "1,226", "Adobe / Alphabet / Microsoft 10-K FY21-24", "Long, table-heavy, numeric"],
        ["AI research papers", "33", "923", "RAG, Transformer, ReAct, Self-RAG, FAISS, HNSW", "Dense technical text"],
        ["Government frameworks", "3", "144", "NIST AI RMF 1.0, CSF 2.0, AI 600-1", "Structured guidance"],
        ["Company policies & manuals", "23", "47", "Leave, travel, security, API guide, QBRs", "Known facts → ground truth"]],
         below=FIG / "corpus.png",
         bullets=["Public sources (arXiv, NIST) + Session-2 dataset + generated synthetic enterprise documents",
                  "Synthetic docs contain precise facts (e.g. '24 days annual leave') used as evaluation ground truth"],
         notes="Scripts: download_corpus.py and generate_synthetic_pdfs.py; mix of short and very long PDFs."),
    dict(title="Ingestion: loading & chunking", bullets=[
        "PyPDFLoader extracts text per page; PyMuPDF fallback for unusual/encrypted PDFs",
        "Cleaning: de-hyphenation, whitespace normalisation, blank-page filtering",
        "RecursiveCharacterTextSplitter - 1000 chars, 150 overlap, separators ¶ → line → sentence → word",
        "Why 1000/150? ~250 tokens fits gte-large's 512-token window and keeps tables/paragraphs intact; "
        "overlap preserves context across boundaries (Session 2 used 512/50 - too small for 10-K tables)",
        "Metadata per chunk: source, title, page, category, chunk_id → enables citations & per-document filtering",
        "Title prefix on each chunk ('[Adobe Form 10-K FY2024]') - helps cross-document questions",
        "Incremental ingestion with SHA-1 de-duplication; manifest.json"],
         notes="Justify chunk size with the Advanced RAG session: small = precise, large = context."),
    dict(title="Embeddings & vector store", bullets=[
        "Embedding model: thenlper/gte-large (1024-d, MTEB top-tier, open, runs on Apple MPS GPU)",
        "Vectors L2-normalised → inner product = cosine similarity (FAISS IndexFlatIP)",
        "FAISS: exact search over ~10k vectors in < 20 ms; persisted with save_local / load_local",
        "Per-document scoping with faiss IDSelectorBatch (search only the open PDF's vectors)",
        "BM25 (rank_bm25) keyword index alongside - catches exact terms, codes and numbers (e.g. 'E05', 'SEV-1')",
        "Alternatives considered: Chroma (Session 2), all-MiniLM-L6-v2 (faster, lower recall), HNSW (not needed at this scale)"],
         notes="Cosine vs Euclidean from the vector DB handout; HNSW unnecessary below ~1M vectors."),
    dict(title="Retrieval: hybrid search, re-ranking, self-correction", bullets=[
        "Dense top-30 (FAISS) + BM25 top-30 → Reciprocal Rank Fusion (k = 60)",
        "Top-20 fused candidates re-ranked by cross-encoder ms-marco-MiniLM-L-6-v2 → top-k = 6 to the LLM",
        "Query condensation: follow-ups rewritten with chat history into standalone questions",
        "Self-correction: best re-rank score < -4 → LLM rewrites the query (keywords) → retrieve again",
        "Still irrelevant → prompt instructs an explicit 'I couldn't find that' (no hallucination)",
        "Whole-document actions: full text if < 24k chars, else multi-facet retrieval (overview, results, risks, conclusions)"],
         image=shot("05_guardrail_trace"), notes="Agentic RAG behaviours from Session 2: query rewriting, reflection, retry."),
    dict(title="Generation: grounded prompting with Gemma-3-12B", bullets=[
        "Local LLM via LM Studio's OpenAI-compatible API (swap to Ollama / OpenAI with one env variable)",
        "16k context; temperature 0.1 for factual, repeatable answers; streamed to the UI",
        "System prompt rules: use ONLY numbered passages, cite [n] after each statement, refuse if absent, "
        "never guess numbers, tables for comparisons",
        "Passages are numbered with document title + page → citations map back to exact pages",
        "Intent router: Q&A / summarize / what stands out / suggested questions / takeaways / small-talk",
        "Follow-up question suggestions generated after each answer"],
         notes="Prompt engineering guide: grounding + explicit refusal behaviour."),
    dict(title="User experience (Acrobat-style)", bullets=[
        "Top bar, summary banner ('View Summary'), PDF viewer with zoom & page navigation",
        "Ask AI Assistant panel: 4 suggestion cards, chat with memory, gradient input box",
        "Citation badges + source chips → jump & highlight; 'View source passages' expander",
        "Scopes: this document · + added files · all documents (PDF Space)",
        "Upload PDFs; settings & knowledge-base stats in the ⋯ menu; 👍/👎 feedback"],
         image=shot("02_summary"), notes="Show the summary screenshot."),
    dict(title="Demo highlights", images=[shot("04_followup_memory"), shot("07_all_documents")], bullets=[
        "Left: follow-up 'Can it be split into parts?' resolved via conversation memory",
        "Right: cross-document comparison of Adobe revenue FY2023 vs FY2024 (two 10-Ks cited)"],
         notes="See the demo video for the full walk-through."),
    dict(title="Evaluation results", table=[["Retriever (whole library)", "Hit@1", "Hit@6", "MRR"]] +
         [[k, f"{v['hit@1']:.0%}", f"{v['hit@6']:.0%}", f"{v['mrr']:.2f}"] for k, v in R.items()],
         kpis=[(f"{A['accuracy']:.0%}", "answer accuracy"), (f"{A['citation_rate']:.0%}", "answers cited"),
               (f"{A['refusal_rate']:.0%}", "out-of-scope refused"), (f"{A['avg_seconds']} s", "avg. latency")],
         bullets=["33 ground-truth questions across all 4 collections + 3 out-of-scope questions (Apple, Contoso, FIFA)",
                  "Hybrid + re-rank improves Hit@1 over dense-only search; re-ranker also powers the relevance guardrail"],
         notes="scripts/eval_rag.py - reproducible; results in deliverables/evaluation_results.md"),
    *model_slide(),
    dict(title="Design choices & justification", table=[
        ["Component", "Choice", "Alternatives", "Why"],
        ["UI", "Streamlit + custom CSS", "Gradio, React", "Fast to build, chat elements, session state"],
        ["Loader", "PyPDFLoader (+PyMuPDF)", "Unstructured, OCR", "Text PDFs, page metadata, robust fallback"],
        ["Chunking", "Recursive 1000/150", "Semantic, fixed 512", "Keeps paragraphs/tables; fits embedding window"],
        ["Embeddings", "gte-large", "MiniLM, nomic, OpenAI", "High recall, local, free"],
        ["Vector DB", "FAISS (+BM25)", "Chroma, pgvector", "Fast exact search, ID filtering, simple persistence"],
        ["Re-ranker", "MiniLM cross-encoder", "bge-reranker, none", "+precision for ~60 ms"],
        ["LLM", "Gemma-3-12B local", "GPT-4o, Llama 3", "Private, good instruction following, 16k ctx"]],
         notes="Case study asks to justify model/tool choices."),
    dict(title="Challenges & lessons learned", bullets=[
        "Encrypted / complex PDFs (AES, form XObjects) → cryptography dependency + PyMuPDF fallback",
        "Long 10-Ks: generic summaries need multi-facet retrieval instead of the first pages only",
        "Dense search misses exact codes & numbers → BM25 hybrid; cross-doc questions → title-prefixed chunks",
        "Small default LLM context (4k) truncated prompts → load with 16k context",
        "Evaluation needs ground truth → synthetic enterprise documents with known facts",
        "UI fidelity in Streamlit: keyed containers + CSS for an Acrobat-like layout"],
         notes="Honest discussion of issues hit during the build."),
    dict(title="Future enhancements", bullets=[
        "OCR + table/figure extraction (multimodal LLM) for scanned PDFs and charts",
        "LangGraph agent with tools (search, summarise, compare, web fallback) and checkpointed memory",
        "RAGAS / LLM-as-a-judge evaluation for faithfulness and answer relevance at scale",
        "Parent-document retrieval and semantic chunking; HNSW / IVF index for millions of chunks",
        "Authentication, per-user PDF spaces, export answers to Word, streaming voice input"],
         notes="Ties to sessions 3-5: LangGraph, MCP, evaluation."),
    dict(kind="title", title="Thank you", presenter=PRESENTER, subtitle="Demo video · Approach document · Source code (streamlit run app.py)",
         footer="Questions?", notes="Close and take questions."),
]


# ============================================================================ PPTX renderer
def rgb(c):
    return RGBColor(*c)


def add_text(slide, x, y, w, h, text, size=18, bold=False, color=INK, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = align
    p.font.size, p.font.bold, p.font.color.rgb = Pt(size), bold, rgb(color)
    return tb


def add_bullets(slide, x, y, w, h, bullets, size=17):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, b in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = "•  " + b
        p.font.size = Pt(size)
        p.font.color.rgb = rgb(INK)
        p.space_after = Pt(8)


def add_picture_fit(slide, path, x, y, w, h):
    from PIL import Image
    iw, ih = Image.open(path).size
    scale = min(w / iw, h / ih)
    pw, ph = int(iw * scale), int(ih * scale)
    slide.shapes.add_picture(str(path), x + (w - pw) // 2, y + (h - ph) // 2, pw, ph)


def add_table(slide, x, y, w, rows, size=13):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), x, y, w, Inches(0.5) * len(rows))
    t = shape.table
    for j, frac in enumerate(col_weights(rows)):
        t.columns[j].width = Emu(int(w * frac))
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = t.cell(r, c)
            cell.text = str(val)
            para = cell.text_frame.paragraphs[0]
            para.font.size = Pt(size)
            para.font.bold = r == 0
            para.font.color.rgb = rgb(INK)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(0xE7, 0xF1, 0xFD) if r == 0 else RGBColor(0xFF, 0xFF, 0xFF)
    return shape


def build_pptx(path):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    SW, SH = prs.slide_width, prs.slide_height
    blank = prs.slide_layouts[6]
    for i, s in enumerate(SLIDES, 1):
        sl = prs.slides.add_slide(blank)
        bar = sl.shapes.add_shape(1, 0, 0, SW, Inches(0.12))
        bar.fill.solid()
        bar.fill.fore_color.rgb = rgb(PINK)
        bar.line.fill.background()
        if s.get("kind") == "title":
            add_text(sl, Inches(0.8), Inches(2.3), SW - Inches(1.6), Inches(1.2), s["title"], 54, True, BLUE, PP_ALIGN.CENTER)
            add_text(sl, Inches(0.8), Inches(3.6), SW - Inches(1.6), Inches(0.8), s["subtitle"], 24, False, INK, PP_ALIGN.CENTER)
            add_text(sl, Inches(0.8), Inches(4.6), SW - Inches(1.6), Inches(0.6), s["footer"], 16, False, GREY, PP_ALIGN.CENTER)
            if s.get("presenter"):
                line = sl.shapes.add_shape(1, SW // 2 - Inches(0.5), Inches(5.45), Inches(1.0), Inches(0.05))
                line.fill.solid()
                line.fill.fore_color.rgb = rgb(PINK)
                line.line.fill.background()
                tb = sl.shapes.add_textbox(Inches(0.8), Inches(5.6), SW - Inches(1.6), Inches(0.7))
                p = tb.text_frame.paragraphs[0]
                p.alignment = PP_ALIGN.CENTER
                r1 = p.add_run()
                r1.text = "Presented by  "
                r1.font.size, r1.font.color.rgb = Pt(20), rgb(GREY)
                r2 = p.add_run()
                r2.text = s["presenter"]
                r2.font.size, r2.font.bold, r2.font.color.rgb = Pt(26), True, rgb(BLUE)
        else:
            add_text(sl, Inches(0.5), Inches(0.3), SW - Inches(1), Inches(0.8), s["title"], 30, True, BLUE)
            top = Inches(1.25)
            body_h = SH - top - Inches(0.6)
            if s.get("image_pos") == "full" and s.get("image"):
                h_img = body_h - (Inches(0.9) if s.get("bullets") else 0)
                add_picture_fit(sl, s["image"], Inches(0.4), top, SW - Inches(0.8), h_img)
                if s.get("bullets"):
                    add_bullets(sl, Inches(0.6), top + h_img + Inches(0.05), SW - Inches(1.2), Inches(0.9), s["bullets"], 15)
            elif s.get("images"):
                imgs = [p for p in s["images"] if p]
                wcol = (SW - Inches(1.2)) // max(1, len(imgs))
                for j, p in enumerate(imgs):
                    add_picture_fit(sl, p, Inches(0.5) + wcol * j, top, wcol - Inches(0.2), body_h - Inches(1.1))
                add_bullets(sl, Inches(0.6), SH - Inches(1.5), SW - Inches(1.2), Inches(1.0), s["bullets"], 15)
            elif s.get("table"):
                tshape = add_table(sl, Inches(0.5), top, SW - Inches(1), s["table"], 16 if len(s["table"][0]) <= 4 else 14)
                y = top + Inches(0.5) * len(s["table"]) + Inches(0.3)
                if s.get("kpis"):
                    kw = (SW - Inches(1)) // len(s["kpis"])
                    for j, (v, t) in enumerate(s["kpis"]):
                        bx = sl.shapes.add_shape(5, Inches(0.5) + kw * j + Inches(0.1), y, kw - Inches(0.2), Inches(1.2))
                        bx.fill.solid()
                        bx.fill.fore_color.rgb = RGBColor(0xFA, 0xF5, 0xFF)
                        bx.line.color.rgb = RGBColor(0xE2, 0xC7, 0xF7)
                        tf = bx.text_frame
                        tf.text = v
                        tf.paragraphs[0].font.size, tf.paragraphs[0].font.bold = Pt(32), True
                        tf.paragraphs[0].font.color.rgb = RGBColor(0x6C, 0x2B, 0xB5)
                        p2 = tf.add_paragraph()
                        p2.text = t
                        p2.font.size = Pt(14)
                        p2.font.color.rgb = rgb(INK)
                        for p in tf.paragraphs:
                            p.alignment = PP_ALIGN.CENTER
                    y += Inches(1.45)
                if s.get("bullets"):
                    add_bullets(sl, Inches(0.6), y, SW - Inches(1.2), Inches(1.0), s["bullets"], 15)
                    y += Inches(1.0)
                if s.get("below") and Path(s["below"]).exists():
                    add_picture_fit(sl, s["below"], Inches(0.5), y, SW - Inches(1), SH - y - Inches(0.5))
                del tshape
            elif s.get("image"):
                add_bullets(sl, Inches(0.5), top, Inches(6.3), body_h, s["bullets"], 16)
                add_picture_fit(sl, s["image"], Inches(7.0), top, SW - Inches(7.4), body_h)
            else:
                add_bullets(sl, Inches(0.6), top, SW - Inches(1.2), body_h, s["bullets"], 18)
        add_text(sl, Inches(0.5), SH - Inches(0.45), Inches(8), Inches(0.3), "AI-Powered PDF Chatbot · Capstone", 10, False, GREY)
        add_text(sl, SW - Inches(1.3), SH - Inches(0.45), Inches(0.8), Inches(0.3), str(i), 10, False, GREY, PP_ALIGN.RIGHT)
        sl.notes_slide.notes_text_frame.text = s.get("notes", "")
    prs.save(path)


# ============================================================================ PDF renderer
def build_pdf(path):
    PW, PH = 1333, 750
    c = rl_canvas.Canvas(str(path), pagesize=(PW, PH))
    col = lambda t: colors.Color(*(v / 255 for v in t))  # noqa: E731

    def wrap(text, font, size, width):
        words, lines, cur = text.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if c.stringWidth(t, font, size) > width:
                lines.append(cur)
                cur = w
            else:
                cur = t
        return lines + [cur]

    def bullets(items, x, y, width, size=17):
        for b in items:
            for k, line in enumerate(wrap(b, "Helvetica", size, width - 22)):
                c.setFont("Helvetica", size)
                c.setFillColor(col(INK))
                if k == 0:
                    c.setFillColor(col(PINK))
                    c.drawString(x, y, "•")
                    c.setFillColor(col(INK))
                c.drawString(x + 22, y, line)
                y -= size * 1.35
            y -= 7
        return y

    def image(p, x, y, w, h):
        ir = ImageReader(str(p))
        iw, ih = ir.getSize()
        sc = min(w / iw, h / ih)
        c.drawImage(ir, x + (w - iw * sc) / 2, y + (h - ih * sc) / 2, iw * sc, ih * sc)

    def table(rows, x, y, width, size=13):
        ws = [width * f for f in col_weights(rows)]
        rh = 40
        for r, row in enumerate(rows):
            c.setFillColor(col((231, 241, 253)) if r == 0 else colors.white)
            c.setStrokeColor(col((184, 199, 219)))
            c.rect(x, y - rh, width, rh, fill=1, stroke=1)
            cx = x
            for j, v in enumerate(row):
                c.setFillColor(col(INK))
                font = "Helvetica-Bold" if r == 0 else "Helvetica"
                fs = size
                while c.stringWidth(str(v), font, fs) > ws[j] - 12 and fs > 9:
                    fs -= 0.5
                c.setFont(font, fs)
                c.drawString(cx + 6, y - rh + 14, str(v))
                cx += ws[j]
            y -= rh
        return y

    for i, s in enumerate(SLIDES, 1):
        c.setFillColor(col(PINK))
        c.rect(0, PH - 12, PW, 12, fill=1, stroke=0)
        if s.get("kind") == "title":
            c.setFillColor(col(BLUE))
            c.setFont("Helvetica-Bold", 56)
            c.drawCentredString(PW / 2, PH / 2 + 50, s["title"])
            c.setFillColor(col(INK))
            c.setFont("Helvetica", 24)
            c.drawCentredString(PW / 2, PH / 2 - 5, s["subtitle"])
            c.setFillColor(col(GREY))
            c.setFont("Helvetica", 16)
            c.drawCentredString(PW / 2, PH / 2 - 50, s["footer"])
            if s.get("presenter"):
                c.setFillColor(col(PINK))
                c.roundRect(PW / 2 - 45, PH / 2 - 98, 90, 4, 2, fill=1, stroke=0)
                t1, t2 = "Presented by  ", s["presenter"]
                w1, w2 = c.stringWidth(t1, "Helvetica", 20), c.stringWidth(t2, "Helvetica-Bold", 26)
                x = (PW - w1 - w2) / 2
                c.setFillColor(col(GREY))
                c.setFont("Helvetica", 20)
                c.drawString(x, PH / 2 - 135, t1)
                c.setFillColor(col(BLUE))
                c.setFont("Helvetica-Bold", 26)
                c.drawString(x + w1, PH / 2 - 135, t2)
        else:
            c.setFillColor(col(BLUE))
            c.setFont("Helvetica-Bold", 30)
            c.drawString(50, PH - 70, s["title"])
            top = PH - 110
            if s.get("image_pos") == "full" and s.get("image"):
                hb = 80 if s.get("bullets") else 0
                image(s["image"], 40, 60 + hb, PW - 80, top - 60 - hb)
                if s.get("bullets"):
                    bullets(s["bullets"], 60, 60 + hb - 18, PW - 120, 15)
            elif s.get("images"):
                imgs = [p for p in s["images"] if p]
                wcol = (PW - 100) / max(1, len(imgs))
                for j, p in enumerate(imgs):
                    image(p, 50 + wcol * j, 150, wcol - 20, top - 150)
                bullets(s["bullets"], 60, 120, PW - 120, 15)
            elif s.get("table"):
                y = table(s["table"], 50, top, PW - 100, 17 if len(s["table"][0]) <= 4 else 15) - 25
                if s.get("kpis"):
                    kw = (PW - 100) / len(s["kpis"])
                    for j, (v, t) in enumerate(s["kpis"]):
                        x = 50 + kw * j + 10
                        c.setFillColor(col((250, 245, 255)))
                        c.setStrokeColor(col((226, 199, 247)))
                        c.roundRect(x, y - 110, kw - 20, 110, 12, fill=1, stroke=1)
                        c.setFillColor(col((108, 43, 181)))
                        c.setFont("Helvetica-Bold", 34)
                        c.drawCentredString(x + (kw - 20) / 2, y - 55, v)
                        c.setFillColor(col(INK))
                        c.setFont("Helvetica", 15)
                        c.drawCentredString(x + (kw - 20) / 2, y - 85, t)
                    y -= 140
                if s.get("bullets"):
                    y = bullets(s["bullets"], 60, y - 10, PW - 120, 15)
                if s.get("below") and Path(s["below"]).exists():
                    image(s["below"], 50, 40, PW - 100, y - 50)
            elif s.get("image"):
                bullets(s["bullets"], 50, top - 10, 620, 16)
                image(s["image"], 700, 60, PW - 740, top - 60)
            else:
                bullets(s["bullets"], 60, top - 10, PW - 120, 18)
        c.setFillColor(col(GREY))
        c.setFont("Helvetica", 10)
        c.drawString(50, 20, "AI-Powered PDF Chatbot · Capstone")
        c.drawRightString(PW - 50, 20, str(i))
        c.showPage()
    c.save()


if __name__ == "__main__":
    build_pptx(D / "AI_PDF_Chatbot_Capstone.pptx")
    build_pdf(D / "AI_PDF_Chatbot_Capstone.pdf")
    print("Saved", D / "AI_PDF_Chatbot_Capstone.pptx", "and .pdf")
