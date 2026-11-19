"""
Records the narrated demo video (5-10 min) by driving the real application in a browser.

  * Playwright drives the Streamlit app (visible cursor, typed questions, live LLM answers) and records video
  * macOS `say` generates the narration for every scene; ffmpeg mixes it at the scene start times
  * on-screen captions + full-screen slides (architecture, evaluation) are injected into the page
  * key frames are saved as screenshots for the presentation

Prerequisites: app running on http://localhost:8501, LLM server running, `playwright install chromium`.
Run:  python scripts/record_demo.py
Output: deliverables/demo_video.mp4, deliverables/demo_script.md, deliverables/screenshots/*.png
"""
import base64
import json
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DELIV = ROOT / "deliverables"
SHOTS = DELIV / "screenshots"
URL = "http://localhost:8501"
VOICE, RATE = "Samantha", 178
PRESENTER = "Meet Kumar Jain"
W, H = 1600, 950
CAPSTONE_PDF = ROOT.parent / "Capstone Case Study" / "1792044795273_Capstone Case Study.pdf"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

INJECT = """
(() => {
  if (window.__demoInjected) return; window.__demoInjected = true;
  const css = document.createElement('style');
  css.textContent = `
    #demo-cursor{position:fixed;z-index:2147483647;width:22px;height:22px;pointer-events:none;left:0;top:0;
      transition:transform .05s linear}
    #demo-cursor svg{filter:drop-shadow(0 1px 2px rgba(0,0,0,.5))}
    .demo-ripple{position:fixed;z-index:2147483646;width:34px;height:34px;margin:-17px 0 0 -17px;border-radius:50%;
      border:3px solid #d6246e;pointer-events:none;animation:rip .6s ease-out forwards}
    @keyframes rip{from{transform:scale(.3);opacity:1}to{transform:scale(1.6);opacity:0}}
    #demo-caption{position:fixed;z-index:2147483645;left:24px;bottom:22px;max-width:56vw;background:rgba(18,18,18,.82);
      color:#fff;font:600 17px/1.35 'Source Sans 3','Segoe UI',sans-serif;padding:10px 16px;border-radius:10px;
      display:none;box-shadow:0 4px 18px rgba(0,0,0,.3)}
    #demo-caption b{color:#ff8fc0}
    #demo-overlay{position:fixed;inset:0;z-index:2147483640;background:#fff;display:none;align-items:center;
      justify-content:center;flex-direction:column;font-family:'Source Sans 3','Segoe UI',sans-serif}`;
  document.head.appendChild(css);
  const cur = document.createElement('div'); cur.id = 'demo-cursor';
  cur.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24"><path d="M3 2l7 19 2.6-7.6L20 11z" fill="#111" stroke="#fff" stroke-width="1.5"/></svg>';
  document.body.appendChild(cur);
  const cap = document.createElement('div'); cap.id = 'demo-caption'; document.body.appendChild(cap);
  const ov = document.createElement('div'); ov.id = 'demo-overlay'; document.body.appendChild(ov);
  document.addEventListener('mousemove', e => { cur.style.transform = `translate(${e.clientX}px, ${e.clientY}px)`; }, true);
  document.addEventListener('mousedown', e => { const r = document.createElement('div'); r.className = 'demo-ripple';
    r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px'; document.body.appendChild(r);
    setTimeout(() => r.remove(), 700); }, true);
})();
"""


def b64img(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def slide_title() -> str:
    return f"""<div style="text-align:center">
      <div style="font-size:30px;color:#d6246e;font-weight:700;letter-spacing:.5px">✦ CAPSTONE CASE STUDY</div>
      <div style="font-size:64px;font-weight:800;color:#0B5CAD;margin:18px 0">AI-Powered PDF Chatbot</div>
      <div style="font-size:26px;color:#333">An Acrobat-style "Ask AI Assistant" built with Retrieval-Augmented Generation</div>
      <div style="font-size:20px;color:#666;margin-top:34px">PyPDFLoader · Recursive chunking · gte-large embeddings · FAISS + BM25 ·
      Cross-encoder re-ranking · Gemma-3-12B (local, LM Studio) · LangChain · Streamlit</div>
      <div style="width:90px;height:4px;background:#d6246e;border-radius:2px;margin:46px auto 26px"></div>
      <div style="font-size:26px;color:#666">Presented by <b style="font-size:36px;color:#0B5CAD;margin-left:8px">{PRESENTER}</b></div></div>"""


def slide_image(path: Path, title: str) -> str:
    return (f"<div style='font-size:34px;font-weight:800;color:#0B5CAD;margin-bottom:14px'>{title}</div>"
            f"<img src='{b64img(path)}' style='max-width:92vw;max-height:80vh;box-shadow:0 2px 14px rgba(0,0,0,.15)'>")


def slide_eval(res: dict) -> str:
    rows = "".join(f"<tr><td>{k}</td><td>{v['hit@1']:.0%}</td><td>{v['hit@6']:.0%}</td><td>{v['mrr']:.2f}</td></tr>"
                   for k, v in res["retrieval"].items())
    a = res.get("answers", {})
    cards = "".join(f"<div style='background:#faf5ff;border:2px solid #e2c7f7;border-radius:14px;padding:18px 26px;"
                    f"text-align:center'><div style='font-size:44px;font-weight:800;color:#6c2bb5'>{v}</div>"
                    f"<div style='font-size:18px;color:#444'>{t}</div></div>"
                    for v, t in [(f"{a.get('accuracy', 0):.0%}", "answer accuracy"),
                                 (f"{a.get('citation_rate', 0):.0%}", "answers with citations"),
                                 (f"{a.get('refusal_rate', 0):.0%}", "out-of-scope refused"),
                                 (f"{a.get('avg_seconds', 0)} s", "avg. response time")])
    return f"""<div style='font-size:34px;font-weight:800;color:#0B5CAD;margin-bottom:6px'>Evaluation: 33 ground-truth questions + 3 out-of-scope</div>
      <div style='font-size:19px;color:#555;margin-bottom:18px'>Retrieval over the whole library ({res['corpus']['pdfs']} PDFs, {res['corpus']['pages']} pages, {res['corpus']['chunks']} chunks)</div>
      <table style='border-collapse:collapse;font-size:22px;margin-bottom:28px' cellpadding='10'>
      <tr style='background:#e7f1fd;font-weight:700'><td>Retriever configuration</td><td>Hit@1</td><td>Hit@6</td><td>MRR</td></tr>{rows}</table>
      <div style='display:flex;gap:22px'>{cards}</div>{slide_models()}"""


def slide_end() -> str:
    return """<div style="text-align:center"><div style="font-size:58px;font-weight:800;color:#0B5CAD">Thank you</div>
      <div style="font-size:24px;color:#333;margin-top:18px">Working prototype · Architecture deck · Approach document · Evaluation report</div>
      <div style="font-size:20px;color:#666;margin-top:26px">Run it: <code>streamlit run app.py</code> &nbsp;·&nbsp; fully local &amp; private</div>
      <div style="width:90px;height:4px;background:#d6246e;border-radius:2px;margin:40px auto 24px"></div>
      <div style="font-size:24px;color:#666">Source code: <b style="font-size:30px;color:#0B5CAD">github.com/meejain/capstone_pdf_chatbot</b></div>
      <div style="font-size:22px;color:#666;margin-top:14px">Presented by <b style="color:#2c2c2c">""" + PRESENTER + """</b></div></div>"""


def model_sentence() -> str:
    path = DELIV / "model_comparison.json"
    if not path.exists():
        return ""
    mc = json.loads(path.read_text())
    spoken = {"gemma-3-12b-it": "Gemma 3 twelve B", "qwen2.5-7b-instruct": "Qwen 2.5 seven B",
              "llama-3.2-3b-instruct": "Llama 3.2 three B"}
    parts = [f"{spoken.get(m, m)} is {r['accuracy']:.0%} accurate in {r['avg_seconds']} seconds" for m, r in mc.items()]
    return "Comparing local models with the same pipeline: " + "; ".join(parts) + "."


def slide_models() -> str:
    path = DELIV / "model_comparison.json"
    if not path.exists():
        return ""
    rows = "".join(f"<tr><td>{m}</td><td>{r['accuracy']:.0%}</td><td>{r['citation_rate']:.0%}</td>"
                   f"<td>{r['refusal_rate']:.0%}</td><td>{r['avg_seconds']} s</td></tr>"
                   for m, r in json.loads(path.read_text()).items())
    return ("<div style='font-size:22px;color:#555;margin:22px 0 8px'>LLM comparison (same retrieval &amp; prompt)</div>"
            "<table style='border-collapse:collapse;font-size:20px' cellpadding='8'><tr style='background:#efe4fb;"
            "font-weight:700'><td>Model</td><td>Accuracy</td><td>Cited</td><td>Refused OOS</td><td>Latency</td></tr>"
            f"{rows}</table>")


class Demo:
    def __init__(self, page, tmp: Path):
        self.page, self.tmp = page, tmp
        self.t0 = time.time()
        self.audio: list[tuple[float, Path]] = []
        self.script: list[tuple[str, str]] = []

    # ---------- helpers
    def inject(self):
        self.page.evaluate(INJECT)

    def caption(self, text: str | None):
        self.inject()
        self.page.evaluate("t => { const c = document.getElementById('demo-caption'); "
                           "if (!t) { c.style.display='none'; return; } c.innerHTML = t; c.style.display='block'; }", text)

    def overlay(self, html: str | None):
        self.inject()
        self.page.evaluate("h => { const o = document.getElementById('demo-overlay'); "
                           "if (!h) { o.style.display='none'; return; } o.innerHTML = h; o.style.display='flex'; "
                           "document.getElementById('demo-caption').style.display='none'; }", html)

    def move_to(self, locator, steps: int = 28):
        t = time.time()
        box = locator.bounding_box()
        if box:
            self.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=steps)
            self.page.wait_for_timeout(250)
        if time.time() - t > 5:
            print(f"   ~ slow move_to {time.time() - t:.1f}s", flush=True)

    def click(self, locator):
        locator.scroll_into_view_if_needed(timeout=10_000)
        self.move_to(locator)
        locator.click()
        self.page.wait_for_timeout(600)

    def answers(self) -> int:
        return self.page.locator("[class*='st-key-answer_']:visible").count()

    def wait_answer(self, before: int, timeout: float = 300):
        t = time.time()
        while time.time() - t < timeout:
            self.page.wait_for_timeout(800)
            if self.answers() > before and self.page.locator(".st-key-streaming").count() == 0:
                self.page.wait_for_timeout(1200)
                self.inject()
                return
        raise TimeoutError("answer did not render")

    def ask(self, text: str):
        before = self.answers()
        box = self.page.locator("[data-testid='stChatInputTextArea']")
        self.click(box)
        box.press_sequentially(text, delay=38)
        self.page.wait_for_timeout(400)
        box.press("Enter")
        self.wait_answer(before)

    def scroll_chat(self, where: str = "top", ms: int = 2500):
        self.page.evaluate("""([w, ms]) => { const el = document.querySelector('.st-key-chat_box');
            if (!el) return; const target = w === 'top' ? 0 : el.scrollHeight;
            el.scrollTo({top: target, behavior: 'smooth'}); }""", [where, ms])
        self.page.wait_for_timeout(ms)

    def select_doc(self, title: str):
        sel = self.page.locator("[class*='st-key-doc_select_'] input[role='combobox']").first
        self.click(sel)
        self.page.keyboard.press("Meta+A")
        self.page.keyboard.type(title, delay=45)
        self.page.wait_for_timeout(700)
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(3500)
        self.inject()

    def shot(self, name: str):
        self.page.screenshot(path=str(SHOTS / f"{name}.png"))

    # ---------- scene runner
    def scene(self, name: str, narration: str, caption: str | None, action=None, min_pad: float = 0.8):
        wav = self.tmp / f"{len(self.audio):02d}_{name}.wav"
        subprocess.run(["say", "-v", VOICE, "-r", str(RATE), "-o", str(wav), "--file-format=WAVE",
                        "--data-format=LEI16@22050", narration], check=True)
        with wave.open(str(wav)) as w:
            dur = w.getnframes() / w.getframerate()
        start = time.time() - self.t0
        self.audio.append((start, wav))
        self.script.append((f"{int(start // 60)}:{int(start % 60):02d}", f"**{name}** - {narration}"))
        if caption is not None:
            self.caption(caption)
        if action:
            try:
                action()
            except Exception as e:  # keep recording; log the problem
                print(f"   ! scene '{name}' action failed: {str(e).splitlines()[0]}", flush=True)
                self.page.keyboard.press("Escape")
        remaining = dur + min_pad - (time.time() - self.t0 - start)
        if remaining > 0:
            self.page.wait_for_timeout(int(remaining * 1000))
        print(f"[{start:6.1f}s] {name:<22} narration {dur:4.1f}s, scene {time.time() - self.t0 - start:5.1f}s", flush=True)


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    res = json.loads((DELIV / "evaluation_results.json").read_text())
    a = res.get("answers", {})
    r = res["retrieval"]
    dense, best = r["Dense only (FAISS)"]["hit@1"], r["Hybrid + re-rank (default)"]["hit@1"]
    tmp = Path(tempfile.mkdtemp(prefix="demo_"))
    upload = tmp / "Capstone_Case_Study_AI_Powered_PDF_Chatbot.pdf"
    shutil.copy(CAPSTONE_PDF, upload)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": W, "height": H}, record_video_dir=str(tmp),
                                  record_video_size={"width": W, "height": H})
        ctx.add_init_script(INJECT.replace("(() => {", "window.addEventListener('DOMContentLoaded', () => {", 1)
                            .rsplit("})();", 1)[0] + "});")
        page = ctx.new_page()
        page.set_default_timeout(10_000)
        d = Demo(page, tmp)
        page.goto(URL, wait_until="networkidle")
        page.wait_for_selector(".st-key-card_summarize button", timeout=180_000)
        d.inject()
        d.overlay(slide_title())

        # ---------------------------------------------------------------- 1. intro + architecture
        d.scene("Introduction",
                "Welcome! This is the capstone demo of our A.I.-powered PDF chatbot: a retrieval-augmented assistant "
                "inspired by the Adobe Acrobat A.I. Assistant. It lets you chat with a library of seventy-one PDF "
                "documents, or with any PDF you upload, and every answer is grounded in the documents, with clickable "
                "page citations. Everything runs locally on a laptop, so documents never leave the machine.", None)
        d.overlay(slide_image(DELIV / "figures" / "workflow.png", "End-to-end workflow"))
        d.scene("Workflow",
                "The workflow follows the classic RAG pattern. A PDF is loaded and its text extracted, split into "
                "overlapping chunks, embedded into vectors, and stored in a vector database. At question time, the most "
                "relevant chunks are retrieved, combined with the question into a grounded prompt, and a large language "
                "model generates the answer, which is displayed in the chat interface.", None)
        d.overlay(slide_image(DELIV / "figures" / "architecture.png", "System architecture"))
        d.scene("Architecture",
                "Here is the architecture in more detail. Offline, PDFs are loaded with PyPDF Loader and split by a "
                "recursive character splitter into chunks of one thousand characters with one hundred and fifty "
                "characters of overlap. Chunks are embedded with the G.T.E. large sentence-embedding model and stored in "
                "a FAISS index, next to a B.M. twenty-five keyword index. Online, an intent router separates questions "
                "from whole-document actions. Follow-up questions are condensed using the chat history. A hybrid "
                "retriever fuses vector and keyword results with reciprocal rank fusion, and a cross-encoder re-ranks "
                "them. If relevance is low, a self-correction step rewrites the query and retries. Finally, Gemma 3, "
                "a twelve-billion-parameter model served locally by LM Studio, writes the answer with citations.", None)
        d.overlay(None)

        # ---------------------------------------------------------------- 2. UI tour
        def tour():
            d.move_to(page.locator(".st-key-page_canvas"))
            page.wait_for_timeout(1500)
            d.move_to(page.locator(".st-key-viewer_toolbar"))
            sel = page.locator("[class*='st-key-doc_select_'] button[aria-label='Open']").first
            d.click(sel)
            page.wait_for_timeout(4500)
            page.keyboard.press("Escape")
            d.move_to(page.locator(".st-key-ai_header"))
            page.wait_for_timeout(1200)
            d.move_to(page.locator(".st-key-card_summarize"))
            d.shot("01_home")
        d.scene("User interface",
                "This is the application. Just like Acrobat, the PDF viewer is on the left, with document selection, "
                "page navigation and zoom. The library contains company policies and product manuals, Adobe, Google and "
                "Microsoft annual reports, A.I. research papers, and NIST frameworks: more than two thousand three "
                "hundred pages in total. On the right is the Ask A.I. Assistant panel, with the familiar suggestion cards.",
                "<b>UI tour</b> · PDF viewer (left) · Ask AI Assistant panel (right) · 71-PDF library", tour)

        # ---------------------------------------------------------------- 3. summary
        def summarize():
            before = d.answers()
            d.click(page.locator(".st-key-card_summarize button"))
            d.wait_answer(before)
            d.scroll_chat("top", 1500)
            d.shot("02_summary")
            d.scroll_chat("bottom", 2500)
        d.scene("One-click summary",
                "Let's open the Employee Leave Policy, and click Summarize. For a short document like this, the "
                "assistant reads the entire text; for long documents, it gathers representative passages with "
                "several focused searches. The answer streams in token by token. Notice the small numbered badges: "
                "every statement is linked to the passage it came from.",
                "<b>Summarize</b> card · whole-document context · streamed answer with citations", summarize)

        def cite():
            chips = page.locator("[class*='st-key-cite_'] button:visible")
            d.click(chips.nth(1) if chips.count() > 1 else chips.first)
            page.wait_for_timeout(2500)
            d.inject()
            d.move_to(page.locator(".st-key-page_canvas img"))
            d.shot("03_citation_highlight")
        d.scene("Citations",
                "Clicking a source chip jumps the viewer to the cited page and highlights the exact passage in yellow, "
                "so the reader can verify the answer in seconds. This traceability is the key difference from a "
                "generic chatbot.", "<b>Citation chip</b> → jump to page + highlight the passage", cite)

        # ---------------------------------------------------------------- 4. QA + follow-up (memory)
        d.scene("Question answering",
                "Now a specific question: how long is parental leave for non-birthing parents? The hybrid retriever "
                "and re-ranker find the right paragraph, and the model answers precisely, with a citation.",
                "<b>Q&amp;A</b> · hybrid retrieval (FAISS + BM25) · cross-encoder re-ranking",
                lambda: d.ask("How long is parental leave for non-birthing parents?"))

        def follow():
            d.ask("Can it be split into parts?")
            d.shot("04_followup_memory")
        d.scene("Conversation memory",
                "And a follow-up that only makes sense in context: can it be split into parts? Before searching, the "
                "assistant uses the chat history to rewrite this into a standalone question, so it knows that 'it' means "
                "parental leave for non-birthing parents.",
                "<b>Follow-up</b> · chat history condensed into a standalone question", follow)

        # ---------------------------------------------------------------- 5. guardrail / self-correction
        def guard():
            d.click(page.locator(".st-key-more_menu button").first)
            page.wait_for_timeout(1200)
            d.click(page.locator("[data-testid='stPopoverBody'] label:has-text('Show retrieval trace')"))
            page.wait_for_timeout(1500)
            page.keyboard.press("Escape")
            page.wait_for_timeout(800)
            d.ask("What was Apple's revenue in 2023?")
            exp = page.locator("[class*='st-key-answer_']:visible").last.locator("summary:has-text('Retrieval trace')")
            d.click(exp)
            page.wait_for_timeout(1500)
            d.scroll_chat("bottom", 1500)
            d.shot("05_guardrail_trace")
        d.scene("Hallucination guard",
                "What happens when the answer is not in the document? I'll switch on the retrieval trace, and ask about "
                "Apple's revenue. The re-ranker reports very low relevance, so the self-correction step rewrites the "
                "query and searches again. Still nothing relevant, so instead of hallucinating, the assistant clearly "
                "says it couldn't find the information. The trace shows every step: the standalone question, the scores, "
                "and the rewritten query.", "<b>Guardrail</b> · low relevance → query rewrite → honest \"not found\"", guard)

        # ---------------------------------------------------------------- 6. long financial document
        def adobe():
            d.select_doc("Adobe Form 10-K FY2024")
            d.ask("What was Adobe's total revenue in fiscal 2024 and how did Digital Media perform?")
            d.shot("06_adobe_10k")
        d.scene("Long annual report",
                "Long documents work just as well. This is Adobe's fiscal 2024 Form 10-K, more than one hundred pages. "
                "I'll ask for total revenue and the performance of the Digital Media segment. The answer combines "
                "figures from different sections of the report, each with its page number.",
                "<b>Annual report</b> · Adobe Form 10-K FY2024 · figures with page citations", adobe)

        # ---------------------------------------------------------------- 7. all documents
        def all_docs():
            d.click(page.locator("button:has-text('All documents')").first)
            page.wait_for_timeout(2500)
            d.ask("Compare Adobe's total revenue in fiscal 2023 and fiscal 2024")
            d.shot("07_all_documents")
        d.scene("Search across all PDFs",
                "Switching the scope to All documents turns the assistant into a research tool across the whole library, "
                "like an Acrobat PDF Space. Here it compares revenue across two different annual reports, and the "
                "citation chips show which report each figure came from.",
                "<b>Scope: All documents</b> · cross-document comparison", all_docs)

        # ---------------------------------------------------------------- 8. research paper
        def paper():
            d.select_doc("RAG - Retrieval-Augmented Generation")
            d.click(page.locator("button:has-text('This document')").first)
            page.wait_for_timeout(2500)
            d.inject()
            before = d.answers()
            d.click(page.locator(".st-key-card_standout button"))
            d.wait_answer(before)
            d.scroll_chat("top", 1500)
            d.shot("08_research_paper")
            d.scroll_chat("bottom", 2500)
        d.scene("Research papers",
                "The same works for research papers. Here is the original retrieval-augmented generation paper from "
                "twenty twenty. Identify what stands out picks out the key contributions and results, and as always, "
                "each point is cited.", "<b>Identify what stands out</b> · research paper", paper)

        # ---------------------------------------------------------------- 8b. model comparison
        def compare():
            d.select_doc("Veridian Support SLA")
            d.click(page.locator(".st-key-compare_toggle label").first)
            page.wait_for_timeout(2500)
            d.inject()
            d.move_to(page.locator(".st-key-compare_select"))
            page.wait_for_timeout(1200)
            d.ask("What is the P1 initial response time on the Premium support plan? Answer briefly.")
            d.shot("12_model_compare_demo")
            page.wait_for_timeout(3000)
            d.click(page.locator(".st-key-compare_toggle label").first)
            page.wait_for_timeout(2500)
            d.inject()
        d.scene("Compare models",
                "The language model is pluggable. A model picker lists every model served by LM Studio, and the "
                "Compare models switch answers the same question with several models side by side, using exactly the "
                "same retrieved passages. Here Gemma 3 twelve B, Llama 3.2 three B and Qwen 2.5 seven B answer a "
                "question about the support SLA. You can compare correctness, citations, length and latency at a "
                "glance: Qwen is the fastest, while the small Llama model is noticeably less precise.",
                "<b>Compare models</b> · same passages, different LLMs · latency & citations per model", compare)

        # ---------------------------------------------------------------- 9. upload
        def up():
            d.click(page.locator(".st-key-add_space button").first)
            page.wait_for_timeout(1200)
            page.locator("input[type=file]").first.set_input_files(str(upload))
            t = time.time()
            while time.time() - t < 120:
                page.wait_for_timeout(1000)
                if "Capstone" in page.locator("[class*='st-key-doc_select_'] input").first.input_value(timeout=5000):
                    break
            page.wait_for_timeout(2500)
            page.keyboard.press("Escape")
            d.inject()
            d.ask("What deliverables must participants submit?")
            d.shot("09_upload_capstone")
        d.scene("Upload your own PDF",
                "Users can also bring their own documents. I'll upload the capstone case study P.D.F. itself. It is "
                "extracted, chunked, embedded and indexed in a few seconds, and immediately becomes available for "
                "questions. Let's ask what deliverables the participants must submit.",
                "<b>Upload</b> → PyPDFLoader → chunk → embed → index → ask", up)

        # ---------------------------------------------------------------- 10. evaluation + close
        d.overlay(slide_eval(res))
        d.scene("Evaluation",
                f"To justify our design choices, we evaluated the system on thirty-three ground-truth questions. Over the "
                f"whole library, dense vector search alone ranks the correct document first {dense:.0%} of the time. "
                f"Adding B.M. twenty-five and cross-encoder re-ranking raises this to {best:.0%}. End to end, "
                f"{a.get('accuracy', 0):.0%} of answers contain the correct fact, {a.get('citation_rate', 0):.0%} include "
                f"citations, and {a.get('refusal_rate', 0):.0%} of the out-of-scope questions are correctly refused. "
                f"{model_sentence()}", None)
        d.overlay(slide_end())
        d.scene("Closing",
                "To summarize: a fully local and private PDF chatbot, built with LangChain, FAISS, sentence "
                "transformers, Streamlit and Gemma 3, with an Acrobat-style interface, hybrid retrieval, re-ranking, "
                "conversation memory, self-correction and verifiable citations. Thank you for watching!", None, min_pad=2.0)

        video = Path(page.video.path())
        ctx.close()
        browser.close()

    # ---------------------------------------------------------------- mux narration + video
    out = DELIV / "demo_video.mp4"
    trim = max(0.0, d.audio[0][0] - 0.9)  # drop the app-loading screen before the title slide
    cmd = [FFMPEG, "-y", "-ss", f"{trim:.2f}", "-i", str(video)]
    for _, wav in d.audio:
        cmd += ["-i", str(wav)]
    delays = "".join(f"[{i + 1}:a]adelay={int((s - trim) * 1000)}|{int((s - trim) * 1000)}[a{i}];"
                     for i, (s, _) in enumerate(d.audio))
    mix = delays + "".join(f"[a{i}]" for i in range(len(d.audio))) + f"amix=inputs={len(d.audio)}:normalize=0[aout]"
    cmd += ["-filter_complex", mix, "-map", "0:v", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium",
            "-crf", "24", "-pix_fmt", "yuv420p", "-r", "25", "-c:a", "aac", "-b:a", "128k", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    lines = ["# Demo video script", "", f"Video: `demo_video.mp4` (recorded automatically by `scripts/record_demo.py`)", "",
             "| Time | Scene & narration |", "|---|---|"]
    def shifted(t):
        m, sec = map(int, t.split(":"))
        v = max(0, int(m * 60 + sec - trim))
        return f"{v // 60}:{v % 60:02d}"
    lines += [f"| {shifted(t)} | {txt} |" for t, txt in d.script]
    (DELIV / "demo_script.md").write_text("\n".join(lines) + "\n")
    print("Saved", out)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
