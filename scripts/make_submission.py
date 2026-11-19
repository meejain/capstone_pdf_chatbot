"""
Builds the upload-ready submission (portal limit: max 5 files, 50 MB each) into
../Capstone_Submission_MeetKumarJain/:

  1. MeetKumarJain_AI_PDF_Chatbot_Presentation.pptx            - architecture & workflow deck
  2. MeetKumarJain_AI_PDF_Chatbot_Approach_and_Design.pdf       - approach, models, tools, techniques
  3. MeetKumarJain_AI_PDF_Chatbot_Demo_Video.mp4                - 7-min narrated demo
  4. MeetKumarJain_AI_PDF_Chatbot_Highlights_and_How_to_Run.pdf - highlights + run/test guide (merged)
  5. MeetKumarJain_AI_PDF_Chatbot_Source_Code.zip               - working prototype (+ docs, results, sample PDFs)

Run after `python scripts/make_approach_doc.py` (which renders the PDFs):
     python scripts/make_submission.py
"""
import shutil
import zipfile
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "deliverables"
OUT = ROOT.parent / "Capstone_Submission_MeetKumarJain"
PREFIX = "MeetKumarJain_AI_PDF_Chatbot"
LIMIT_MB = 50

ZIP_INCLUDE = ["README.md", "requirements.txt", ".gitignore", "app.py", "config.py", ".streamlit", "assets", "rag",
               "scripts", "tests", "deliverables", "data/pdfs/company", "data/pdfs/financial",
               "data/pdfs/government"]
ZIP_EXCLUDE_NAMES = {"__pycache__", ".DS_Store", ".pytest_cache", "demo_video.mp4"}


def merge_pdfs(parts: list[Path], out: Path, title: str):
    merged = pymupdf.open()
    toc = []
    for part in parts:
        with pymupdf.open(str(part)) as src:
            toc.append([1, part.stem.replace("_", " "), merged.page_count + 1])
            merged.insert_pdf(src)
    merged.set_toc(toc)
    merged.set_metadata({"title": title, "author": "Meet Kumar Jain"})
    merged.save(str(out), garbage=3, deflate=True)


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
    OUT.mkdir(parents=True)

    shutil.copy2(D / "AI_PDF_Chatbot_Capstone.pptx", OUT / f"{PREFIX}_Presentation.pptx")
    shutil.copy2(D / "Approach_and_Design.pdf", OUT / f"{PREFIX}_Approach_and_Design.pdf")
    shutil.copy2(D / "demo_video.mp4", OUT / f"{PREFIX}_Demo_Video.mp4")
    merge_pdfs([D / "Submission_Highlights.pdf", D / "How_to_Run_Locally.pdf"],
               OUT / f"{PREFIX}_Highlights_and_How_to_Run.pdf",
               "AI-Powered PDF Chatbot - Submission Highlights & How to Run")
    build_zip(OUT / f"{PREFIX}_Source_Code.zip")

    print(f"Upload folder: {OUT}")
    uploads = sorted(OUT.iterdir())
    for p in uploads:
        mb = p.stat().st_size / 1e6
        print(f"  {'OK ' if mb < LIMIT_MB else 'TOO BIG'} {mb:6.1f} MB  {p.name}")
    assert len(uploads) == 5 and all(p.is_file() and p.stat().st_size < LIMIT_MB * 1e6 for p in uploads)


if __name__ == "__main__":
    main()
