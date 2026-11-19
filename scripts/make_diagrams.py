"""Draws the architecture and query-workflow diagrams used in the presentation and approach document."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "deliverables" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

C = {"ui": "#FDE7EF", "ing": "#E7F1FD", "ret": "#EFE4FB", "llm": "#FFF4CC", "store": "#E6F6EC", "edge": "#555555"}


def box(ax, x, y, w, h, title, sub="", color="#fff", fs=11):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=color, ec="#9a9a9a", lw=1.2))
    ax.text(x + w / 2, y + h * (0.62 if sub else 0.5), title, ha="center", va="center", fontsize=fs, fontweight="bold", color="#222")
    if sub:
        ax.text(x + w / 2, y + h * 0.3, sub, ha="center", va="center", fontsize=fs - 2.5, color="#444")


def arrow(ax, p, q, text="", rad=0.0, color=C["edge"]):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=14, lw=1.4, color=color,
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((p[0] + q[0]) / 2, (p[1] + q[1]) / 2 + 0.12, text, ha="center", fontsize=8.5, color="#333", style="italic")


def architecture():
    fig, ax = plt.subplots(figsize=(16, 8.6))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 8.6)
    ax.axis("off")
    ax.text(8, 8.25, "AI-Powered PDF Chatbot - System Architecture", ha="center", fontsize=18, fontweight="bold", color="#0B5CAD")

    # lanes
    ax.add_patch(FancyBboxPatch((0.2, 5.3), 15.6, 2.5, boxstyle="round,pad=0.02", fc="#FAFCFF", ec="#c9d9ee", lw=1))
    ax.text(0.45, 7.55, "OFFLINE / UPLOAD-TIME INGESTION", fontsize=10, color="#0B5CAD", fontweight="bold")
    ax.add_patch(FancyBboxPatch((0.2, 0.3), 15.6, 4.7, boxstyle="round,pad=0.02", fc="#FFFBFD", ec="#f0c9da", lw=1))
    ax.text(0.45, 4.75, "ONLINE QUESTION ANSWERING (per chat message)", fontsize=10, color="#b0245f", fontweight="bold")

    # ingestion lane
    box(ax, 0.5, 5.7, 2.2, 1.5, "71 PDFs", "annual reports, papers,\npolicies, manuals + uploads", C["ing"])
    box(ax, 3.2, 5.7, 2.2, 1.5, "PyPDFLoader", "text per page\n+ metadata (title, page)", C["ing"])
    box(ax, 5.9, 5.7, 2.3, 1.5, "Recursive splitter", "1000 chars / 150 overlap\ntitle-prefixed chunks", C["ing"])
    box(ax, 8.7, 5.7, 2.4, 1.5, "gte-large embeddings", "1024-d, normalised\n(Apple MPS GPU)", C["ing"])
    box(ax, 11.6, 6.45, 2.0, 0.95, "FAISS index", "inner product = cosine", C["store"], fs=10)
    box(ax, 11.6, 5.55, 2.0, 0.8, "BM25 index", "keyword / exact terms", C["store"], fs=10)
    box(ax, 13.9, 5.7, 1.7, 1.5, "Manifest", "SHA-1 dedup,\nincremental adds", C["store"], fs=10)
    for a, b in [((2.7, 6.45), (3.2, 6.45)), ((5.4, 6.45), (5.9, 6.45)), ((8.2, 6.45), (8.7, 6.45)),
                 ((11.1, 6.6), (11.6, 6.9)), ((11.1, 6.3), (11.6, 5.95)), ((13.6, 6.45), (13.9, 6.45))]:
        arrow(ax, a, b)

    # query lane
    box(ax, 0.5, 2.9, 2.4, 1.5, "Streamlit UI", "Acrobat-style viewer +\nAsk AI Assistant panel", C["ui"])
    box(ax, 3.4, 2.9, 2.1, 1.5, "Intent router", "Q&A | summary | key\npoints | small talk", C["ret"])
    box(ax, 6.0, 2.9, 2.3, 1.5, "Query condenser", "LLM rewrites follow-ups\nusing chat history", C["ret"])
    box(ax, 8.8, 2.9, 2.5, 1.5, "Hybrid retriever", "FAISS top-30 + BM25 top-30\nRRF fusion, doc scope", C["ret"])
    box(ax, 11.8, 2.9, 2.0, 1.5, "Cross-encoder", "MiniLM re-rank\n20 -> top-k (6)", C["ret"])
    box(ax, 11.8, 0.6, 2.0, 1.5, "Self-correction", "low score -> LLM\nquery rewrite + retry", C["ret"])
    box(ax, 8.8, 0.6, 2.5, 1.5, "Grounded prompt", "numbered passages +\ncitation & refusal rules", C["llm"])
    box(ax, 6.0, 0.6, 2.3, 1.5, "LLM (local)", "Gemma-3-12B via LM Studio\nOpenAI-compatible API", C["llm"])
    box(ax, 3.4, 0.6, 2.1, 1.5, "Post-processing", "citation chips, follow-up\nquestions, feedback", C["ui"])
    box(ax, 0.5, 0.6, 2.4, 1.5, "Answer + page jump", "streamed answer, cited\npassage highlighted", C["ui"])
    for a, b in [((2.9, 3.65), (3.4, 3.65)), ((5.5, 3.65), (6.0, 3.65)), ((8.3, 3.65), (8.8, 3.65)),
                 ((11.3, 3.65), (11.8, 3.65)), ((12.8, 2.9), (12.8, 2.1)), ((11.8, 1.35), (11.3, 1.35)),
                 ((8.8, 1.35), (8.3, 1.35)), ((6.0, 1.35), (5.5, 1.35)), ((3.4, 1.35), (2.9, 1.35)),
                 ((1.7, 2.1), (1.7, 2.9))]:
        arrow(ax, a, b)
    arrow(ax, (12.6, 5.55), (10.4, 4.4), "vector + keyword search", rad=0.0, color="#2e8b57")
    arrow(ax, (4.45, 2.9), (8.8, 1.9), "summary actions: whole doc / multi-facet", rad=0.15, color="#b0245f")
    fig.savefig(OUT / "architecture.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def workflow():
    steps = [("1", "Upload / select PDF", C["ui"]), ("2", "Extract text\n(PyPDFLoader)", C["ing"]),
             ("3", "Chunk\n1000 / 150", C["ing"]), ("4", "Embed\ngte-large", C["ing"]), ("5", "Store\nFAISS + BM25", C["store"]),
             ("6", "Ask question\n(chat input)", C["ui"]), ("7", "Retrieve\nhybrid + re-rank", C["ret"]),
             ("8", "Grounded\nprompt", C["llm"]), ("9", "Generate\nGemma-3-12B", C["llm"]), ("10", "Display +\ncitations", C["ui"])]
    fig, ax = plt.subplots(figsize=(16, 3.2))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    w, gap = 1.35, 0.22
    for i, (n, t, c) in enumerate(steps):
        x = 0.2 + i * (w + gap)
        box(ax, x, 0.7, w, 1.7, t, "", c, fs=9.5)
        ax.text(x + 0.18, 2.22, n, fontsize=10, fontweight="bold", color="#b0245f")
        if i < len(steps) - 1:
            arrow(ax, (x + w, 1.55), (x + w + gap, 1.55))
    ax.text(8, 2.85, "End-to-end RAG workflow", ha="center", fontsize=15, fontweight="bold", color="#0B5CAD")
    ax.text(8, 0.25, "Steps 1-5 run once per document (ingestion) · steps 6-10 run per question, in ~3-10 s on a laptop",
            ha="center", fontsize=10, color="#555")
    fig.savefig(OUT / "workflow.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def corpus():
    import json
    man = json.loads((Path(__file__).resolve().parents[1] / "index" / "manifest.json").read_text())
    labels = {"financial": "Financial reports", "research": "Research papers", "government": "Gov. frameworks",
              "company": "Company docs"}
    cats = [k for k in labels if any(v["category"] == k for v in man.values())]
    vals = {m: [sum(v[m] for v in man.values() if v["category"] == k) for k in cats] for m in ("pages", "chunks")}
    fig, axes = plt.subplots(1, 2, figsize=(14, 3.2))
    for ax, (m, title) in zip(axes, [("pages", "Pages per collection"), ("chunks", "Chunks per collection")]):
        bars = ax.barh([labels[k] for k in cats], vals[m], color=["#0B5CAD", "#b42fd0", "#2e8b57", "#d6246e"])
        ax.set_title(title, fontsize=13, fontweight="bold", color="#333")
        ax.bar_label(bars, padding=4, fontsize=10)
        ax.spines[["top", "right"]].set_visible(False)
        ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(OUT / "corpus.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    architecture()
    workflow()
    corpus()
    print("Saved", list(OUT.glob("*.png")))
