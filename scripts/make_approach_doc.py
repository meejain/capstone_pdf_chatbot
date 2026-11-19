"""Renders the Markdown deliverables to styled PDFs (Markdown -> HTML -> headless Chromium):
Approach_and_Design, How_to_Run_Locally and Submission_Highlights."""
from pathlib import Path

import re

import markdown
from playwright.sync_api import sync_playwright

D = Path(__file__).resolve().parents[1] / "deliverables"
CSS = """
body{font-family:'Helvetica Neue',Arial,sans-serif;font-size:11pt;color:#2c2c2c;line-height:1.45;margin:0}
h1{color:#0B5CAD;font-size:22pt;border-bottom:3px solid #d6246e;padding-bottom:6px}
h2{color:#0B5CAD;font-size:15pt;margin-top:20px} h3{color:#b0245f;font-size:12.5pt}
table{border-collapse:collapse;width:100%;margin:8px 0;font-size:9.5pt} th{background:#e7f1fd;text-align:left}
th,td{border:1px solid #c9d9ee;padding:5px 7px;vertical-align:top} code,pre{background:#f5f5f5;font-size:9pt}
pre{padding:8px;border-radius:6px;white-space:pre-wrap} img{max-width:100%} em{color:#555}
"""


DOCS = {"Approach_and_Design": "Approach &amp; Design", "How_to_Run_Locally": "How to Run Locally",
        "Submission_Highlights": "Submission Highlights"}


LIST_ITEM = re.compile(r"^( *)([*\-]|\d+\.) ")


def normalise_lists(md: str) -> str:
    """GitHub-style Markdown (2/3-space nesting, lists right after a paragraph) -> Python-Markdown friendly."""
    out, in_code, prev = [], False, ""
    for line in md.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
        m = None if in_code else LIST_ITEM.match(line)
        if m:
            indent = len(m.group(1))
            if indent:
                line = " " * (4 * -(-indent // 3)) + line.lstrip()
            elif prev.strip() and not LIST_ITEM.match(prev) and not prev.startswith("|"):
                out.append("")
        out.append(line)
        prev = line
    return "\n".join(out)


def render(name: str, label: str):
    md = normalise_lists((D / f"{name}.md").read_text())
    body = markdown.markdown(md, extensions=["tables", "fenced_code"])
    html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"
    tmp = D / f"_{name}.html"
    tmp.write_text(html)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(tmp.resolve().as_uri(), wait_until="networkidle")
        pg.pdf(path=str(D / f"{name}.pdf"), format="A4", print_background=True,
               margin={"top": "18mm", "bottom": "18mm", "left": "16mm", "right": "16mm"},
               display_header_footer=True, header_template="<span></span>",
               footer_template="<div style='font-size:8px;width:100%;text-align:center;color:#888'>"
                               f"AI-Powered PDF Chatbot - {label} · Meet Kumar Jain · <span class='pageNumber'></span></div>")
        b.close()
    tmp.unlink()
    print("Saved", D / f"{name}.pdf")


def main():
    for name, label in DOCS.items():
        render(name, label)


if __name__ == "__main__":
    main()
