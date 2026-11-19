"""Step 1-3 of the pipeline: load PDF -> extract & clean text per page -> chunk with overlap."""
import hashlib
import re
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config


def file_sha1(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def pretty_title(path: Path) -> str:
    name = path.stem
    m = re.match(r"(?i)adobe_adbe-10k-fy(\d\d)", name)
    if m:
        return f"Adobe Form 10-K FY20{m.group(1)}"
    m = re.match(r"(?i)google_(\d{4})-alphabet-annual-report", name)
    if m:
        return f"Alphabet (Google) Annual Report {m.group(1)}"
    m = re.match(r"(?i)google_goog-10-k-(\d{4})", name)
    if m:
        return f"Alphabet (Google) Form 10-K {m.group(1)}"
    m = re.match(r"(?i)microsoft_(\d{4})_annual_report", name)
    if m:
        return f"Microsoft Annual Report {m.group(1)}"
    name = re.sub(r"^arXiv_\d{4}\.\d{4,5}_", "", name)
    name = re.sub(r"^VS-[A-Z]+-\d{3}_", "", name)
    return name.replace("_", " ").replace("  ", " ").strip()


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)          # de-hyphenate line breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_pdf(path: Path) -> list[Document]:
    """Return one Document per non-empty page with source / page / category metadata (1-based page)."""
    path = Path(path)
    category = path.parent.name if path.parent.name in config.CATEGORY_LABELS else "uploads"
    try:
        pages = PyPDFLoader(str(path)).load()
    except Exception:  # malformed / unusual encryption -> fall back to PyMuPDF text extraction
        import pymupdf
        with pymupdf.open(str(path)) as pdf:
            pages = [Document(page_content=pg.get_text(), metadata={"page": i, "total_pages": pdf.page_count})
                     for i, pg in enumerate(pdf)]
    docs = []
    for p in pages:
        text = clean_text(p.page_content)
        if len(text) < 20:  # skip blank / image-only pages
            continue
        docs.append(Document(page_content=text, metadata={
            "source": path.name,
            "title": pretty_title(path),
            "category": category,
            "page": int(p.metadata.get("page", 0)) + 1,
            "total_pages": int(p.metadata.get("total_pages", len(pages))),
        }))
    return docs


def get_splitter(chunk_size: int = None, chunk_overlap: int = None) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or config.CHUNK_SIZE,
        chunk_overlap=chunk_overlap or config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def chunk_documents(pages: list[Document], chunk_size: int = None, chunk_overlap: int = None) -> list[Document]:
    chunks = get_splitter(chunk_size, chunk_overlap).split_documents(pages)
    for i, c in enumerate(chunks):
        c.metadata["chunk_id"] = f"{c.metadata['source']}::p{c.metadata['page']}::{i}"
        c.metadata["text"] = c.page_content.strip()
        # The indexed text is prefixed with the title so that both BM25 and the embedding know which
        # document a chunk belongs to (e.g. "Adobe 10-K FY23"), which matters for cross-document questions.
        c.page_content = f"[{c.metadata['title']}]\n{c.metadata['text']}"
    return chunks
