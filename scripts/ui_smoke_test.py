"""
Browser-level smoke test of the Streamlit app (requires the app running on :8501 and the LLM server).
Drives the real UI with Playwright: suggestion card, chat question + follow-up, citation jump, scope switch.
Run:  python scripts/ui_smoke_test.py [screenshot_dir]
"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"
SHOTS = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "deliverables" / "screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)


def wait_answer(page, n_before: int, timeout: float = 240):
    t0 = time.time()
    while time.time() - t0 < timeout:
        page.wait_for_timeout(1000)
        n = page.locator("[class*='st-key-answer_']").count()
        if n > n_before and page.locator(".st-key-streaming").count() == 0:
            page.wait_for_timeout(1500)
            return time.time() - t0
    raise TimeoutError("no answer rendered")


def ask(page, text: str):
    n = page.locator("[class*='st-key-answer_']").count()
    box = page.locator("[data-testid='stChatInputTextArea']")
    box.fill(text)
    box.press("Enter")
    return wait_answer(page, n)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 950})
        page.goto(URL, wait_until="networkidle")
        page.wait_for_selector(".st-key-card_summarize button", timeout=120_000)
        page.screenshot(path=SHOTS / "01_home.png")

        page.locator(".st-key-card_summarize button").click()
        secs = wait_answer(page, 0)
        page.screenshot(path=SHOTS / "02_summary.png")
        print(f"summary rendered in {secs:.1f}s; citations: {page.locator('[class*=st-key-cite_] button').count()}")

        page.locator("[class*='st-key-cite_'] button").first.click()
        page.wait_for_timeout(3000)
        page.screenshot(path=SHOTS / "03_citation_jump.png")
        print("highlight note visible:", page.locator(".hl-note").count() > 0)

        secs = ask(page, "How long is parental leave for non-birthing parents?")
        print(f"QA answered in {secs:.1f}s")
        secs = ask(page, "Can it be split into parts?")
        page.screenshot(path=SHOTS / "04_followup.png")
        last = page.locator("[class*='st-key-answer_']").last.inner_text()
        print(f"follow-up answered in {secs:.1f}s ->", last[:300].replace("\n", " "))

        page.locator("button:has-text('All documents')").click()
        page.wait_for_timeout(2500)
        secs = ask(page, "Compare Veridian's revenue and operating margin in Q1 and Q2 FY2026")
        page.screenshot(path=SHOTS / "05_all_docs_compare.png")
        print(f"cross-doc answered in {secs:.1f}s ->",
              page.locator("[class*='st-key-answer_']").last.inner_text()[:300].replace("\n", " "))
        browser.close()


if __name__ == "__main__":
    main()
