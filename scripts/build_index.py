"""
Offline ingestion of the whole PDF corpus into the FAISS + BM25 knowledge base.
Run:  python scripts/build_index.py            (incremental - already indexed files are skipped)
      python scripts/build_index.py --rebuild  (delete index and rebuild from scratch)
"""
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from rag.knowledge_base import KnowledgeBase  # noqa: E402


def main():
    if "--rebuild" in sys.argv and config.INDEX_DIR.exists():
        shutil.rmtree(config.INDEX_DIR)
    pdfs = sorted(p for p in config.PDF_DIR.rglob("*.pdf"))
    print(f"Found {len(pdfs)} PDFs under {config.PDF_DIR}")
    t0 = time.time()
    kb = KnowledgeBase()
    print(f"Embedding model {config.EMBEDDINGS_MODEL} on {kb.device}")

    def progress(n, total, name, chunks, secs):
        print(f"[{n:>3}/{total}] {name[:70]:<70} {chunks:>5} chunks  {secs:5.1f}s", flush=True)

    stats = kb.add_pdfs(pdfs, progress=progress)
    print(f"\nIndexed {stats['files']} new files ({stats['pages']} pages, {stats['chunks']} chunks); "
          f"skipped {stats['skipped']}. Total chunks in KB: {len(kb.chunks)}. Took {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
