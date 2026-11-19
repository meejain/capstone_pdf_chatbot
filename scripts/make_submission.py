"""
Builds the upload-ready submission (portal limit: max 5 files, 50 MB each) into
../Capstone_Submission_MeetKumarJain/:

  1. MeetKumarJain_AI_PDF_Chatbot_Presentation.pptx       - architecture & workflow deck
  2. MeetKumarJain_AI_PDF_Chatbot_Approach_and_Design.docx  - approach, models, tools, techniques
  3. MeetKumarJain_AI_PDF_Chatbot_Demo_Video.mp4            - 7-min narrated demo
  4. MeetKumarJain_AI_PDF_Chatbot_Highlights_and_How_to_Run.docx
  5. MeetKumarJain_AI_PDF_Chatbot_Source_Code.zip           - working prototype (+ docs, results, sample PDFs)

PDF versions of the documents are placed in a "PDF_versions" sub-folder in case the portal accepts PDFs.
Run:  python scripts/make_submission.py
"""
import shutil
import zipfile
from pathlib import Path

import pypandoc
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "deliverables"
OUT = ROOT.parent / "Capstone_Submission_MeetKumarJain"
PREFIX = "MeetKumarJain_AI_PDF_Chatbot"
LIMIT_MB = 50
PAGE_BREAK = '\n\n```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```\n\n'

ZIP_INCLUDE = ["README.md", "requirements.txt", ".gitignore", "app.py", "config.py", ".streamlit", "assets", "rag",
               "scripts", "tests", "deliverables", "data/pdfs/company", "data/pdfs/financial",
               "data/pdfs/government"]
ZIP_EXCLUDE_NAMES = {"__pycache__", ".DS_Store", ".pytest_cache", "demo_video.mp4"}


def style_tables(path: Path):
    """Pandoc tables have no borders - add a light grid, shaded bold header and compact font."""
    doc = Document(str(path))
    for table in doc.tables:
        tbl_pr = table._tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            el = OxmlElement(f"w:{edge}")
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), "4")
            el.set(qn("w:color"), "B8C7DB")
            borders.append(el)
        tbl_pr.append(borders)
        for r, row in enumerate(table.rows):
            for cell in row.cells:
                if r == 0:
                    shd = OxmlElement("w:shd")
                    shd.set(qn("w:val"), "clear")
                    shd.set(qn("w:fill"), "E7F1FD")
                    cell._tc.get_or_add_tcPr().append(shd)
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(9.5)
                        if r == 0:
                            run.bold = True
    doc.save(str(path))


def to_docx(markdown: str, out: Path, title: str):
    pypandoc.convert_text(markdown, "docx", format="gfm+raw_attribute", outputfile=str(out),
                          extra_args=[f"--resource-path={D}", f"--metadata=title:{title}",
                                      "--metadata=author:Meet Kumar Jain"])
    style_tables(out)


def build_zip(out: Path):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for item in ZIP_INCLUDE:
            p = ROOT / item
            files = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file())
            for f in files:
                if any(part in ZIP_EXCLUDE_NAMES for part in f.relative_to(ROOT).parts):
                    continue
                z.write(f, Path("capstone_pdf_chatbot") / f.relative_to(ROOT))


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "PDF_versions").mkdir(parents=True)

    shutil.copy2(D / "AI_PDF_Chatbot_Capstone.pptx", OUT / f"{PREFIX}_Presentation.pptx")
    shutil.copy2(D / "demo_video.mp4", OUT / f"{PREFIX}_Demo_Video.mp4")
    # strip the H1 (pandoc renders the metadata title instead)
    approach = (D / "Approach_and_Design.md").read_text().split("\n", 1)[1]
    to_docx(approach, OUT / f"{PREFIX}_Approach_and_Design.docx",
            "AI-Powered PDF Chatbot — Approach, Models, Tools & Techniques")
    highlights = (D / "Submission_Highlights.md").read_text().split("\n", 1)[1]
    howto = (D / "How_to_Run_Locally.md").read_text().split("\n", 1)[1]
    combined = (highlights + PAGE_BREAK + "# How to Run Locally\n" + howto)
    to_docx(combined, OUT / f"{PREFIX}_Highlights_and_How_to_Run.docx",
            "AI-Powered PDF Chatbot — Submission Highlights & How to Run")
    build_zip(OUT / f"{PREFIX}_Source_Code.zip")

    for name in ["AI_PDF_Chatbot_Capstone.pdf", "Approach_and_Design.pdf", "Submission_Highlights.pdf",
                 "How_to_Run_Locally.pdf"]:
        shutil.copy2(D / name, OUT / "PDF_versions" / f"{PREFIX}_{name.replace('AI_PDF_Chatbot_', '')}")

    print(f"Upload folder: {OUT}")
    uploads = sorted(p for p in OUT.iterdir() if p.is_file())
    for p in uploads:
        mb = p.stat().st_size / 1e6
        print(f"  {'OK ' if mb < LIMIT_MB else 'TOO BIG'} {mb:6.1f} MB  {p.name}")
    assert len(uploads) <= 5 and all(p.stat().st_size < LIMIT_MB * 1e6 for p in uploads)
    for p in sorted((OUT / "PDF_versions").iterdir()):
        print(f"  (alt) {p.stat().st_size / 1e6:6.1f} MB  PDF_versions/{p.name}")


if __name__ == "__main__":
    main()
