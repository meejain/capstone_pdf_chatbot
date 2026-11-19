"""
Builds the public part of the PDF corpus:
  * copies the Session-2 annual reports (Adobe / Google / Microsoft)
  * downloads openly available arXiv research papers on LLMs, RAG and agents
  * downloads public-domain NIST publications
Run:  python scripts/download_corpus.py
"""
import shutil
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "data" / "pdfs"
SESSION2_DATASET = ROOT.parent / "session2" / "code" / "dataset"

ARXIV_PAPERS = {
    "2005.11401": "RAG - Retrieval-Augmented Generation for Knowledge-Intensive NLP",
    "1706.03762": "Attention Is All You Need",
    "1810.04805": "BERT - Pre-training of Deep Bidirectional Transformers",
    "2005.14165": "GPT-3 - Language Models are Few-Shot Learners",
    "2210.03629": "ReAct - Synergizing Reasoning and Acting",
    "2201.11903": "Chain-of-Thought Prompting",
    "2302.04761": "Toolformer",
    "2303.11366": "Reflexion",
    "2305.10601": "Tree of Thoughts",
    "2312.10997": "RAG for LLMs - A Survey",
    "2310.11511": "Self-RAG",
    "2401.15884": "Corrective RAG",
    "2212.10496": "HyDE - Precise Zero-Shot Dense Retrieval",
    "1908.10084": "Sentence-BERT",
    "1603.09320": "HNSW - Hierarchical Navigable Small World graphs",
    "1702.08734": "FAISS - Billion-scale similarity search with GPUs",
    "2004.04906": "DPR - Dense Passage Retrieval",
    "2307.03172": "Lost in the Middle",
    "2106.09685": "LoRA",
    "2203.02155": "InstructGPT",
    "2307.09288": "Llama 2",
    "2310.06825": "Mistral 7B",
    "2308.08155": "AutoGen",
    "2304.03442": "Generative Agents",
    "2309.15217": "RAGAS",
    "2306.05685": "Judging LLM-as-a-Judge",
    "2104.08663": "BEIR benchmark",
    "2404.16130": "GraphRAG - From Local to Global",
    "2203.11171": "Self-Consistency",
    "2112.09332": "WebGPT",
    "2305.14314": "QLoRA",
    "2401.18059": "RAPTOR",
    "2312.11805": "Gemini - Multimodal Models",
}

GOV_DOCS = {
    "NIST_AI_RMF_1.0.pdf": "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf",
    "NIST_Cybersecurity_Framework_2.0.pdf": "https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf",
    "NIST_GenAI_Profile_AI_600-1.pdf": "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf",
}

HEADERS = {"User-Agent": "Capstone-PDF-Chatbot/1.0 (educational project)"}


def safe_name(text: str) -> str:
    keep = "".join(c if c.isalnum() or c in " -_." else "" for c in text)
    return "_".join(keep.split())[:90]


def download(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 10_000:
        print(f"  = exists  {dest.name}")
        return True
    try:
        r = requests.get(url, headers=HEADERS, timeout=60)
        if r.status_code == 200 and r.content[:4] == b"%PDF":
            dest.write_bytes(r.content)
            print(f"  + {dest.name} ({len(r.content) // 1024} KB)")
            return True
        print(f"  ! {url} -> HTTP {r.status_code}")
    except requests.RequestException as e:
        print(f"  ! {url} -> {e}")
    return False


def main():
    fin = PDF_DIR / "financial"
    fin.mkdir(parents=True, exist_ok=True)
    print("Copying annual reports ...")
    for pdf in sorted(SESSION2_DATASET.rglob("*.pdf")):
        dest = fin / f"{pdf.parent.name.capitalize()}_{pdf.name}"
        if not dest.exists():
            shutil.copy2(pdf, dest)
        print(f"  = {dest.name}")

    research = PDF_DIR / "research"
    research.mkdir(parents=True, exist_ok=True)
    print("Downloading arXiv papers ...")
    ok = 0
    for arxiv_id, title in ARXIV_PAPERS.items():
        dest = research / f"arXiv_{arxiv_id}_{safe_name(title)}.pdf"
        existed = dest.exists()
        ok += download(f"https://arxiv.org/pdf/{arxiv_id}", dest)
        if not existed:
            time.sleep(3)  # be polite to arXiv

    gov = PDF_DIR / "government"
    gov.mkdir(parents=True, exist_ok=True)
    print("Downloading NIST publications ...")
    for name, url in GOV_DOCS.items():
        download(url, gov / name)

    total = len(list(PDF_DIR.rglob("*.pdf")))
    print(f"\nDone. arXiv ok={ok}/{len(ARXIV_PAPERS)}. Total PDFs in corpus: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
