# AI-Powered PDF Chatbot — How to Run Locally

*Prepared by Meet Kumar Jain · Capstone Case Study · Agentic AI Training (Batch 3, 2026)*

This guide walks you through running the chatbot on your own machine and testing its main features. The
setup is done once. The test checklist after that takes about **five minutes**.

Everything runs **locally**: the PDFs, embeddings, vector index and the language model (served by LM Studio)
never leave the machine.

---

## 1. Prerequisites

| Requirement | Details |
|---|---|
| Computer | macOS on Apple Silicon (tested on an M3 Max with 48 GB) or Windows/Linux with 16 GB+ RAM |
| Python | 3.11 or 3.12 |
| LM Studio | <https://lmstudio.ai> - provides the local LLM through an OpenAI-compatible API on port 1234 |
| Disk space | About 15 GB: the LLM (8 GB), the embedding model (1.3 GB), the PDF corpus and the index |
| Optional | Ollama or an OpenAI-compatible API instead of LM Studio (see step 7) |

## 2. One-time setup

Get the code from GitHub, or unzip the submitted source-code archive:

```bash
git clone https://github.com/meejain/capstone_pdf_chatbot.git
cd capstone_pdf_chatbot
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium          # only needed for the automated UI test
```

Build the document library and the search index. The arXiv papers and the index are not in the repository,
so run these once:

```bash
python scripts/download_corpus.py         # copies the annual reports, downloads arXiv papers + NIST frameworks
python scripts/generate_synthetic_pdfs.py # creates the 23 "Veridian Systems" company documents
python scripts/build_index.py             # text extraction -> chunking -> embeddings -> FAISS + BM25 (about 6 min)
```

## 3. Start the language model (LM Studio)

The LM Studio desktop app must be installed. The commands below use its command-line tool `lms`.

```bash
~/.lmstudio/bin/lms server start
~/.lmstudio/bin/lms load gemma-3-12b-it --context-length 16384
~/.lmstudio/bin/lms ps                # should list the model with CONTEXT 16384
```

For the **Compare models** feature, also download and load the two smaller models:

```bash
~/.lmstudio/bin/lms get qwen2.5-7b-instruct
~/.lmstudio/bin/lms get llama-3.2-3b-instruct
~/.lmstudio/bin/lms load qwen2.5-7b-instruct   --context-length 16384
~/.lmstudio/bin/lms load llama-3.2-3b-instruct --context-length 16384
```

> Always load models with `--context-length 16384`. The default (4k) is too small for whole-document summaries.

## 4. Run the application

```bash
cd capstone_pdf_chatbot
source .venv/bin/activate
streamlit run app.py
```

Open **<http://localhost:8501>** in a browser. The first load takes about 20–30 seconds while the embedding
model and the vector index are loaded. A green **"● gemma-3-12b-it · local"** badge in the *Ask AI Assistant*
panel means the language model is connected.

### The screen at a glance

* **Top bar:** *Add file to PDF Space* (upload), *Share*, and *Ask AI Assistant* (shows or hides the panel).
* **Left:** the PDF viewer, with document picker, page navigation and zoom.
* **Right:** the *Ask AI Assistant* panel, with these parts:
  * scope (*This document* / *All documents*)
  * model picker and *Compare models* switch
  * four suggestion cards
  * the chat box
* **⋯ menu (top right of the panel):** search settings, retrieval trace, knowledge-base statistics, and *Clear conversation*.

## 5. Five-minute test checklist

| # | What to do | What you should see |
|---|---|---|
| 1 | With **Employee Leave Policy** open, click the **Summarize** card | A bullet summary with small purple citation badges |
| 2 | Click a source chip below the answer, e.g. **2 · p.2** | The viewer jumps to page 2 and highlights the cited passage in yellow |
| 3 | Ask: *"How long is parental leave for non-birthing parents?"* | **12 weeks**, with a citation |
| 4 | Follow up: *"Can it be split into parts?"* | Yes, in up to two blocks. The follow-up is understood from the conversation |
| 5 | Ask: *"What was Apple's revenue in 2023?"* | *"I couldn't find that…"*, with no invented answer. Turn on ⋯ → **Show retrieval trace** to see the automatic query rewrite |
| 6 | Open **Travel and Expense Reimbursement Policy** and ask: *"Which flight class for a 7 hour flight, and the hotel limit in London?"* | Premium economy; USD 300 per night |
| 7 | Open **Adobe Form 10-K FY2024** and ask: *"What was total revenue in fiscal 2024?"* | **$21,505 million**, with page citations |
| 8 | Switch the scope to **All documents** and ask: *"Compare Adobe's total revenue in fiscal 2023 and 2024"* | $19,409M vs $21,505M, with citation chips from both annual reports |
| 9 | Turn on **Compare models** and ask any question | Two or three answers side by side, each with time taken and citation count |
| 10 | Use **Add file to PDF Space** to upload any PDF and ask about it | The PDF is indexed in seconds, opens in the viewer, and can be queried |

## 6. Automated tests (optional, with the app running)

```bash
python -m pytest tests -q                    # 5 unit tests, under 1 second
python scripts/ui_smoke_test.py              # drives the real UI in a browser, about 2 minutes
python scripts/eval_rag.py --retrieval-only  # retrieval benchmark, about 30 seconds
python scripts/eval_rag.py                   # full 36-question evaluation, about 4 minutes
python scripts/eval_rag.py --models gemma-3-12b-it,qwen2.5-7b-instruct,llama-3.2-3b-instruct   # LLM comparison
```

Results are written to `deliverables/evaluation_results.md` and `deliverables/model_comparison.md`.

## 7. Using a different LLM server (optional)

The app talks to any OpenAI-compatible endpoint. For example, with **Ollama**:

```bash
ollama pull gemma3:12b
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_MODEL=gemma3:12b
streamlit run app.py
```

Other settings, such as chunk size, top-k and the embedding model, can be changed with environment variables
(see `config.py` and the README).

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| `Port 8501 is not available` | Run `streamlit run app.py --server.port 8502`, or stop the old process (`lsof -ti tcp:8501`, then `kill <PID>`) |
| Red LLM badge / "model could not be reached" | LM Studio's server is not running. Repeat step 3 |
| Summaries cut off, or "context length" errors | Reload the model with `--context-length 16384` |
| "The knowledge base is empty" | Run `python scripts/build_index.py` |
| First answer is slow | The re-ranker and LLM warm up on the first query. Later answers take about 3–10 s |
| Long tests stop when the Mac is unattended | Prefix the command with `caffeinate -dimsu` so the Mac doesn't sleep |
