"""
Step 4-7 of the pipeline: embeddings -> FAISS vector store -> hybrid retrieval (dense + BM25, RRF fusion)
-> cross-encoder re-ranking.  Supports per-document scoping and incremental ingestion of uploaded PDFs.
"""
import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

import config

os.environ.setdefault("HF_HOME", str(config.HF_CACHE))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import faiss  # noqa: E402
from langchain_community.vectorstores import FAISS  # noqa: E402
from langchain_community.vectorstores.utils import DistanceStrategy  # noqa: E402
from langchain_core.documents import Document  # noqa: E402
from langchain_huggingface import HuggingFaceEmbeddings  # noqa: E402
from rank_bm25 import BM25Okapi  # noqa: E402

from rag.loader import chunk_documents, file_sha1, load_pdf  # noqa: E402

FAISS_DIR = config.INDEX_DIR / "faiss"
MANIFEST = config.INDEX_DIR / "manifest.json"
_TOKEN = re.compile(r"[a-z0-9]+(?:[.,][0-9]+)?")
_STOP = set("a an the of and or to in on for is are was were be by with as at from that this it its what which who how "
            "does do did can could should would will about into than then there their they them these those i we you".split())


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


@dataclass
class Hit:
    doc: Document
    rank_dense: int | None = None
    rank_bm25: int | None = None
    score_dense: float = 0.0
    rrf: float = 0.0
    rerank: float | None = None
    extra: dict = field(default_factory=dict)

    @property
    def score(self) -> float:
        return self.rerank if self.rerank is not None else self.rrf


class KnowledgeBase:
    def __init__(self, device: str | None = None):
        self.device = device or config.get_device()
        self.embeddings = HuggingFaceEmbeddings(
            model_name=config.EMBEDDINGS_MODEL,
            model_kwargs={"device": self.device},
            encode_kwargs={"normalize_embeddings": True, "batch_size": 64},  # normalised -> inner product == cosine
            cache_folder=str(config.HF_CACHE),
        )
        self._reranker = None
        self._lock = threading.Lock()
        self.vs: FAISS | None = None
        self.manifest: dict = {}
        self.chunks: list[Document] = []
        self.positions_by_source: dict[str, np.ndarray] = {}
        self.bm25: BM25Okapi | None = None
        if (FAISS_DIR / "index.faiss").exists():
            self.load()

    # ------------------------------------------------------------------ persistence
    def load(self):
        self.vs = FAISS.load_local(str(FAISS_DIR), self.embeddings, allow_dangerous_deserialization=True,
                                   distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT)
        self.manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
        self._rebuild_side_indexes()

    def save(self):
        config.INDEX_DIR.mkdir(parents=True, exist_ok=True)
        self.vs.save_local(str(FAISS_DIR))
        MANIFEST.write_text(json.dumps(self.manifest, indent=2))

    def _rebuild_side_indexes(self):
        ids = self.vs.index_to_docstore_id
        self.chunks = [self.vs.docstore.search(ids[i]) for i in range(len(ids))]
        by_src: dict[str, list[int]] = {}
        for i, d in enumerate(self.chunks):
            by_src.setdefault(d.metadata["source"], []).append(i)
        self.positions_by_source = {k: np.array(v, dtype="int64") for k, v in by_src.items()}
        self.bm25 = BM25Okapi([tokenize(d.page_content) for d in self.chunks])

    # ------------------------------------------------------------------ ingestion
    @property
    def is_ready(self) -> bool:
        return self.vs is not None and len(self.chunks) > 0

    def has_source(self, source: str) -> bool:
        return source in self.manifest

    def add_pdfs(self, paths: list[Path], progress=None, batch: int = 256) -> dict:
        """Ingest PDFs (skips files whose SHA1 is already indexed). Returns stats."""
        stats = {"files": 0, "pages": 0, "chunks": 0, "skipped": 0}
        known = {v["sha1"] for v in self.manifest.values()}
        with self._lock:
            for n, path in enumerate(paths, 1):
                path = Path(path)
                sha = file_sha1(path)
                if sha in known or path.name in self.manifest:
                    stats["skipped"] += 1
                    continue
                t0 = time.time()
                try:
                    pages = load_pdf(path)
                except Exception as e:  # never let one bad PDF break a batch ingestion
                    print(f"  ! could not read {path.name}: {e}")
                    stats["skipped"] += 1
                    continue
                chunks = chunk_documents(pages)
                if not chunks:
                    stats["skipped"] += 1
                    continue
                for i in range(0, len(chunks), batch):
                    part = chunks[i:i + batch]
                    if self.vs is None:
                        self.vs = FAISS.from_documents(part, self.embeddings,
                                                       distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT)
                    else:
                        self.vs.add_documents(part)
                first = pages[0].metadata if pages else {}
                self.manifest[path.name] = {
                    "title": first.get("title", path.stem), "category": first.get("category", "uploads"),
                    "path": str(path.relative_to(config.ROOT)) if path.is_relative_to(config.ROOT) else str(path),
                    "pages": first.get("total_pages", len(pages)), "chunks": len(chunks), "sha1": sha,
                    "added": time.strftime("%Y-%m-%d %H:%M"),
                }
                known.add(sha)
                stats["files"] += 1
                stats["pages"] += len(pages)
                stats["chunks"] += len(chunks)
                if progress:
                    progress(n, len(paths), path.name, len(chunks), time.time() - t0)
            if stats["files"]:
                self._rebuild_side_indexes()
                self.save()
        return stats

    def remove_source(self, source: str) -> bool:
        """Delete every chunk of one PDF from FAISS, BM25 and the manifest."""
        with self._lock:
            pos = self.positions_by_source.get(source)
            if pos is None:
                return False
            ids = [self.vs.index_to_docstore_id[int(i)] for i in pos]
            self.vs.delete(ids)
            self.manifest.pop(source, None)
            self._rebuild_side_indexes()
            self.save()
            return True

    # ------------------------------------------------------------------ retrieval
    def _scope_positions(self, sources: list[str] | None) -> np.ndarray | None:
        if not sources:
            return None
        arrs = [self.positions_by_source[s] for s in sources if s in self.positions_by_source]
        return np.concatenate(arrs) if arrs else np.array([], dtype="int64")

    def dense_search(self, query: str, n: int, positions: np.ndarray | None):
        q = np.array([self.embeddings.embed_query(query)], dtype="float32")
        n = min(n, len(self.chunks) if positions is None else len(positions))
        if n <= 0:
            return []
        if positions is None:
            scores, idx = self.vs.index.search(q, n)
        else:
            params = faiss.SearchParameters(sel=faiss.IDSelectorBatch(positions))
            scores, idx = self.vs.index.search(q, n, params=params)
        return [(int(i), float(s)) for i, s in zip(idx[0], scores[0]) if i >= 0]

    def bm25_search(self, query: str, n: int, positions: np.ndarray | None):
        scores = self.bm25.get_scores(tokenize(query))
        if positions is not None:
            mask = np.full(len(scores), -np.inf)
            mask[positions] = scores[positions]
            scores = mask
        top = np.argsort(-scores)[:n]
        return [(int(i), float(scores[i])) for i in top if np.isfinite(scores[i]) and scores[i] > 0]

    @property
    def reranker(self):
        if self._reranker is None:
            from sentence_transformers import CrossEncoder
            self._reranker = CrossEncoder(config.RERANKER_MODEL, device=self.device, cache_folder=str(config.HF_CACHE))
        return self._reranker

    def retrieve(self, query: str, sources: list[str] | None = None, k: int = None, hybrid: bool = True,
                 rerank: bool = True, extra_queries: list[str] | None = None) -> list[Hit]:
        """Hybrid retrieval with Reciprocal Rank Fusion, optional multi-query and cross-encoder re-ranking."""
        k = k or config.TOP_K
        positions = self._scope_positions(sources)
        if positions is not None and len(positions) == 0:
            return []
        hits: dict[int, Hit] = {}
        for q in [query] + list(extra_queries or []):
            for rank, (i, s) in enumerate(self.dense_search(q, config.CANDIDATES, positions)):
                h = hits.setdefault(i, Hit(self.chunks[i]))
                h.rank_dense = rank if h.rank_dense is None else min(h.rank_dense, rank)
                h.score_dense = max(h.score_dense, s)
                h.rrf += 1.0 / (config.RRF_K + rank + 1)
            if hybrid:
                for rank, (i, s) in enumerate(self.bm25_search(q, config.CANDIDATES, positions)):
                    h = hits.setdefault(i, Hit(self.chunks[i]))
                    h.rank_bm25 = rank if h.rank_bm25 is None else min(h.rank_bm25, rank)
                    h.rrf += 1.0 / (config.RRF_K + rank + 1)
        pool = sorted(hits.values(), key=lambda h: h.rrf, reverse=True)[:config.RERANK_POOL]
        if rerank and pool:
            scores = self.reranker.predict([(query, h.doc.metadata.get("text", h.doc.page_content)) for h in pool])
            for h, s in zip(pool, scores):
                h.rerank = float(s)
            pool.sort(key=lambda h: h.rerank, reverse=True)
        return pool[:k]

    def document_chunks(self, source: str) -> list[Document]:
        pos = self.positions_by_source.get(source, [])
        docs = [self.chunks[i] for i in pos]
        return sorted(docs, key=lambda d: (d.metadata["page"], d.metadata["chunk_id"]))

    def documents(self) -> dict:
        return self.manifest
