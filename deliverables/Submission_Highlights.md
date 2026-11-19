# AI-Powered PDF Chatbot — Submission Highlights

*Meet Kumar Jain · Capstone Case Study · Agentic AI Training (Batch 3, 2026)*

**Source code:** <https://github.com/meejain/capstone_pdf_chatbot>

**In one line:** a fully local, Adobe Acrobat-style *"Ask AI Assistant"* that lets you chat with a library of
**71 PDFs (about 2,330 pages)**, or any PDF you upload. Every answer is grounded in the documents, with **clickable
page citations that highlight the exact passage**.

---

## 1. Deliverables

| # | Deliverable (as required by the case study) | File |
|---|---|---|
| 1 | Working prototype of the AI chatbot | `app.py` + `rag/` (Streamlit app) — GitHub: https://github.com/meejain/capstone_pdf_chatbot |
| 2 | Presentation: system architecture and workflow (18 slides, with speaker notes) | `AI_PDF_Chatbot_Capstone.pptx` / `.pdf` |
| 3 | Brief explanation of approach, models, tools and techniques | `Approach_and_Design.pdf` / `.md` |
| 4 | Demo video (7 min 15 s, narrated) | `demo_video.mp4` — timed script: `demo_script.md` |
| + | How to run and test locally | `How_to_Run_Locally.pdf` / `.md` |
| + | Evaluation report and LLM comparison | `evaluation_results.md`, `model_comparison.md` |
| + | Screenshots of every feature | `screenshots/` |

The demo video shows everything the case study asks for:
- (a) the chatbot interacting with sample PDFs: a policy, a 10-K, a research paper and an uploaded PDF
- (b) example queries and responses
- (c) the key features and the end-to-end workflow

## 2. Key highlights

1. **Acrobat-like experience.** PDF viewer plus an *Ask AI Assistant* panel with suggestion cards:
   *Summarize*, *Identify what stands out*, *Suggest questions*, *List takeaways*.
2. **Verifiable answers.** Inline citation badges; clicking a source chip jumps to the page and **highlights the
   passage**.
3. **No hallucination by design.** If the answer is not in the document, the assistant says so. It refused
   100% of out-of-scope questions in testing.
4. **Advanced RAG, not naive RAG:**
   * hybrid search: dense **FAISS** plus keyword **BM25**, fused with Reciprocal Rank Fusion
   * **cross-encoder re-ranking**
   * **self-correcting** query rewrite when relevance is low
5. **Conversation memory.** Follow-ups like *"Can it be split?"* are rewritten into standalone questions.
6. **Search one document, several, or the whole library.** Cross-document comparisons, e.g. Adobe revenue FY2023 vs FY2024 across two 10-Ks.
7. **Upload any PDF.** It is indexed in seconds (SHA-1 de-duplication) and immediately searchable.
8. **Pluggable LLMs and side-by-side comparison.** A model picker plus a *Compare models* mode: 2–3 local models answer from
   the same retrieved passages.
9. **Fully local and private.** Gemma-3-12B served by LM Studio; embeddings computed on the Apple MPS GPU. No
   cloud calls.
10. **Measured, reproducible quality.** A ground-truth evaluation suite, a browser-level UI test, unit tests, and an
    automatically recorded demo video.

## 3. Results at a glance

**Retrieval over the whole 71-PDF library**, measured as how often the correct document is ranked first:

| Retriever | Hit@1 | Hit@6 | MRR |
|---|---|---|---|
| Dense only (FAISS) | 88% | 94% | 0.90 |
| **Hybrid + re-rank (default)** | **94%** | **97%** | **0.95** |

**End-to-end (33 ground-truth questions + 3 out-of-scope), Gemma-3-12B:**

| Answer accuracy | Answers with citations | Out-of-scope refused | Avg response time |
|---|---|---|---|
| **100%** | **100%** | **100%** | **4.7 s** |

**LLM comparison, with the same retrieval and prompt:**

| Model (local) | Accuracy | Cited | Refused | Latency |
|---|---|---|---|---|
| Gemma-3-12B (default) | 100% | 100% | 100% | 4.6 s |
| Qwen2.5-7B | 100% | 97% | 100% | 2.0 s |
| Llama-3.2-3B | 94% | 88% | 100% | 2.5 s |

*Finding:* smaller models mostly fail at **reading tables** (wrong row or column), even when they are given the
correct passage.

## 4. Architecture in brief

```
PDF -> PyPDFLoader -> clean -> Recursive chunks (1000/150) -> gte-large embeddings -> FAISS + BM25
Question -> intent router -> condense with chat history -> hybrid retrieval (RRF) -> cross-encoder re-rank
         -> [self-correct if low relevance] -> grounded prompt with numbered passages -> Gemma-3-12B
         -> streamed answer + citation chips + page highlight + follow-up suggestions
```

| Layer | Choice | Why |
|---|---|---|
| UI | Streamlit + custom CSS | Fast to build, chat elements, session state, Acrobat look |
| PDF loading | PyPDFLoader (+ PyMuPDF fallback) | Page-level metadata for citations; handles unusual PDFs |
| Chunking | Recursive, 1000 chars / 150 overlap | Keeps paragraphs and tables intact; fits the embedding window |
| Embeddings | `thenlper/gte-large` (1024-d) | High retrieval quality, open, local |
| Vector store | FAISS + BM25 | Exact search in under 20 ms; keyword matching for codes and numbers |
| Re-ranker | `ms-marco-MiniLM-L-6-v2` | Higher precision for about 60 ms; powers the relevance guardrail |
| LLM | Gemma-3-12B via LM Studio | Private, strong instruction following, 16k context |

## 5. Document corpus

| Collection | PDFs | Pages | Source |
|---|---|---|---|
| Financial annual reports | 12 | 1,226 | Adobe, Alphabet, Microsoft 10-K / annual reports FY2021–24 |
| AI research papers | 33 | 923 | Public arXiv papers (RAG, Transformer, ReAct, Self-RAG, FAISS, HNSW, …) |
| Government frameworks | 3 | 144 | NIST AI RMF 1.0, CSF 2.0, AI 600-1 (public domain) |
| Company policies & manuals | 23 | 47 | Synthetic "Veridian Systems" documents with known facts, used as ground truth |

## 6. Course concepts applied

* **Session 1:**
  * LLM client and system prompts
  * the Streamlit chat with history pattern
  * the tool / ReAct mindset, applied to the self-correction loop
* **Session 2:**
  * document loaders
  * chunking strategies
  * embeddings and cosine similarity
  * vector databases
  * the `do_rag()` pipeline
  * agentic RAG behaviours: query rewriting and reflection
* **Session 3 (Advanced RAG):**
  * chunk-size trade-offs
  * hybrid search
  * re-ranking
  * multi-query / multi-facet retrieval
  * condensing follow-ups with chat history

## 7. Try it in five minutes

```bash
git clone https://github.com/meejain/capstone_pdf_chatbot.git && cd capstone_pdf_chatbot
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python scripts/download_corpus.py && python scripts/build_index.py
~/.lmstudio/bin/lms load gemma-3-12b-it --context-length 16384
streamlit run app.py        # open http://localhost:8501
```

Then click **Summarize**, click a citation chip, and ask *"How long is parental leave for non-birthing
parents?"* The full checklist is in `How_to_Run_Locally.pdf`.

## 8. Next steps

* A LangGraph agent with tools (search, compare, summarise, web fallback) and checkpointed memory
* OCR and multimodal parsing for scanned PDFs, tables and charts
* RAGAS / LLM-as-a-judge evaluation of faithfulness at scale; per-user PDF spaces with authentication
