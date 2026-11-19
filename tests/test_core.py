"""Fast unit tests (no LLM / embedding model needed).  Run:  python -m pytest tests -q"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.documents import Document  # noqa: E402

from rag.assistant import CITATION_RE, route, used_citations  # noqa: E402
from rag.knowledge_base import Hit, tokenize  # noqa: E402
from rag.loader import chunk_documents, clean_text, pretty_title  # noqa: E402


def _hit(n):
    return Hit(Document(page_content=f"chunk {n}", metadata={"source": f"d{n}.pdf", "title": f"Doc {n}", "page": n,
                                                            "text": f"chunk {n}"}))


def test_citations_single_and_grouped():
    hits = [_hit(i) for i in range(1, 6)]
    cites = used_citations("Revenue grew [3]. Margins [1, 5] and again [3][9].", hits)
    assert [c["n"] for c in cites] == [3, 1, 5]          # order of first use, de-duplicated, out-of-range ignored
    assert cites[0]["page"] == 3 and cites[0]["source"] == "d3.pdf"
    assert CITATION_RE.sub("X", "a [1, 2] b [4]") == "a X b X"


def test_router():
    assert route("hello!", None, True) == "smalltalk"
    assert route("Summarize this document", None, True) == "summarize"
    assert route("Summarize this document", None, False) == "qa"   # library scope -> retrieval Q&A
    assert route("How many leave days?", None, True) == "qa"
    assert route("anything", "takeaways", True) == "takeaways"


def test_loader_helpers():
    assert pretty_title(Path("Adobe_adbe-10k-fy23-final.pdf")) == "Adobe Form 10-K FY2023"
    assert pretty_title(Path("Microsoft_2024_Annual_Report.pdf")) == "Microsoft Annual Report 2024"
    assert pretty_title(Path("arXiv_2005.11401_RAG_-_Retrieval.pdf")) == "RAG - Retrieval.pdf".replace(".pdf", "")
    assert clean_text("retrie-\nval   works\n\n\n\nok") == "retrieval works\n\nok"


def test_chunking_metadata_and_title_prefix():
    page = Document(page_content="word " * 600, metadata={"source": "x.pdf", "title": "X Policy", "page": 2})
    chunks = chunk_documents([page], chunk_size=1000, chunk_overlap=150)
    assert len(chunks) >= 3
    assert all(c.page_content.startswith("[X Policy]\n") for c in chunks)
    assert all(len(c.metadata["text"]) <= 1000 and c.metadata["page"] == 2 for c in chunks)


def test_tokenize_keeps_numbers_drops_stopwords():
    assert tokenize("What is the SEV-1 response time of 15 minutes?") == ["sev", "1", "response", "time", "15", "minutes"]
