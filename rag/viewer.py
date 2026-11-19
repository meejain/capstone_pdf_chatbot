"""PDF page rendering for the viewer pane, including highlighting of a cited passage (PyMuPDF)."""
import re
from pathlib import Path

import pymupdf


def page_count(path: str | Path) -> int:
    with pymupdf.open(str(path)) as pdf:
        return pdf.page_count


def _candidate_snippets(text: str, limit: int = 14) -> list[str]:
    """Split a chunk into short line fragments that are likely to be found verbatim on the page."""
    out = []
    for line in re.split(r"\n+|(?<=[.;:])\s+", text):
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) >= 18:
            out.append(line[:70])
        if len(out) >= limit:
            break
    return out


def render_page(path: str | Path, page_no: int, zoom: float = 1.4, highlight: str | None = None) -> tuple[bytes, int]:
    """Render 1-based `page_no` to PNG. If `highlight` text is given, highlight its occurrences.
    Returns (png_bytes, number_of_highlighted_regions)."""
    with pymupdf.open(str(path)) as pdf:
        page_no = max(1, min(page_no, pdf.page_count))
        page = pdf[page_no - 1]
        found = 0
        if highlight:
            for snip in _candidate_snippets(highlight):
                quads = page.search_for(snip, quads=True)
                if quads:
                    annot = page.add_highlight_annot(quads)
                    annot.set_colors(stroke=(1.0, 0.86, 0.25))
                    annot.update()
                    found += len(quads)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), annots=True)
        return pix.tobytes("png"), found
