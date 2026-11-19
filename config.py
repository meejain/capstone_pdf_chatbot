"""Central configuration. Every value can be overridden with an environment variable."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PDF_DIR = ROOT / "data" / "pdfs"
UPLOAD_DIR = PDF_DIR / "uploads"
INDEX_DIR = ROOT / "index"
HF_CACHE = Path(os.getenv("HF_CACHE", ROOT / ".hf_cache"))

# ---- LLM (OpenAI-compatible endpoint: LM Studio, Ollama, OpenAI, ...) -----------------------
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")   # Ollama: http://localhost:11434/v1
LLM_MODEL = os.getenv("LLM_MODEL", "gemma-3-12b-it")                     # Ollama: gemma3:12b
LLM_API_KEY = os.getenv("LLM_API_KEY", "lm-studio")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1200"))

# ---- Embeddings / re-ranking ----------------------------------------------------------------
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "thenlper/gte-large")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

# ---- Chunking & retrieval hyper-parameters --------------------------------------------------
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
TOP_K = int(os.getenv("TOP_K", "6"))
CANDIDATES = int(os.getenv("CANDIDATES", "30"))        # per retriever, before fusion
RERANK_POOL = int(os.getenv("RERANK_POOL", "20"))      # fused candidates sent to the cross-encoder
RRF_K = 60
# Cross-encoder logit below which a passage is treated as "not relevant" (triggers self-correction)
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "-4.0"))
SUMMARY_CHAR_BUDGET = int(os.getenv("SUMMARY_CHAR_BUDGET", "24000"))

CATEGORY_LABELS = {
    "company": "Company policies & manuals",
    "financial": "Financial annual reports",
    "research": "AI research papers",
    "government": "Government frameworks",
    "uploads": "My uploads",
}


def get_device() -> str:
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"
