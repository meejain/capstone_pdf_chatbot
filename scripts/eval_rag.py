"""
Evaluation harness.
  1. Retrieval: Hit@k / MRR over the whole 71-PDF library for 4 retriever configurations.
  2. End-to-end answers: grounded answer must contain the expected fact (scope = the expected document).
  3. Robustness: out-of-scope questions must be refused ("couldn't find").
Results are written to deliverables/evaluation_results.json and .md

Run:  python scripts/eval_rag.py            (retrieval + answers)
      python scripts/eval_rag.py --retrieval-only
      python scripts/eval_rag.py --models gemma-3-12b-it,qwen2.5-7b-instruct,llama-3.2-3b-instruct
             (LLM comparison: same retrieval, different generators -> deliverables/model_comparison.md)
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from rag.assistant import Assistant  # noqa: E402
from rag.knowledge_base import KnowledgeBase  # noqa: E402

# (question, expected source prefix, expected answer substrings - any of)
EVAL_SET = [
    ("How many days of paid annual leave do full-time employees get?", "VS-HR-001", ["24"]),
    ("How many unused annual leave days can be carried forward?", "VS-HR-001", ["10"]),
    ("How long is parental leave for non-birthing parents?", "VS-HR-001", ["12 weeks"]),
    ("Which day is the company-wide anchor day for office attendance?", "VS-HR-002", ["Tuesday"]),
    ("What setup stipend do fully remote employees receive?", "VS-HR-002", ["1,000", "1000"]),
    ("Which flight class can I book for a 7 hour flight?", "VS-FIN-003", ["premium economy"]),
    ("What is the maximum hotel rate per night in Tier 1 cities?", "VS-FIN-003", ["300"]),
    ("Within how many days must expense claims be submitted in Concur?", "VS-FIN-003", ["30"]),
    ("Up to what value can employees accept gifts without declaring them?", "VS-LGL-004", ["100"]),
    ("What is the minimum password length?", "VS-IT-005", ["14"]),
    ("How quickly must critical vulnerabilities be patched?", "VS-IT-005", ["72"]),
    ("How long is CCTV footage retained?", "VS-LGL-006", ["30 days"]),
    ("Who founded Veridian Systems?", "VS-HR-007", ["Raghunathan"]),
    ("How long is the probation period for new employees?", "VS-HR-007", ["90"]),
    ("What is the 401(k) matching formula?", "VS-HR-009", ["4%"]),
    ("What is the response time for a SEV-1 security incident?", "VS-IT-010", ["15 minutes"]),
    ("How many quotes are needed for a USD 50,000 purchase?", "VS-FIN-011", ["3", "three"]),
    ("How often should the AeroBrew X1 be descaled?", "AeroBrew", ["3 months", "three months"]),
    ("What does error code E05 mean on the coffee machine?", "AeroBrew", ["grinder"]),
    ("How long does the SkyNote Pro 11 take to charge fully?", "SkyNote", ["95"]),
    ("What is the MPPT voltage range of the SolarGrid inverter?", "SolarGrid", ["120"]),
    ("What is the API rate limit for the Enterprise plan?", "Veridian_Cloud_API", ["6,000", "6000"]),
    ("What was Veridian's revenue in Q2 FY2026?", "Veridian_QBR_Q2", ["438"]),
    ("What was the Net Promoter Score in the 2025 customer survey?", "Veridian_Customer_Satisfaction", ["47"]),
    ("When will API v2 be retired?", "Veridian_Product_Roadmap", ["30 September 2026", "September 30, 2026"]),
    ("What is the recovery time objective for tier-1 services?", "VS-OPS-022", ["1 hour", "one hour"]),
    ("What is the P1 initial response time on the Premium support plan?", "Veridian_Support_SLA", ["1 hour", "one hour"]),
    ("What are the four core functions of the NIST AI Risk Management Framework?", "NIST_AI_RMF", ["govern"]),
    ("Which retriever does the original RAG paper use?", "arXiv_2005.11401", ["DPR", "Dense Passage"]),
    ("How many parallel attention heads does the base Transformer use?", "arXiv_1706.03762", ["8", "eight"]),
    ("What was Adobe's total revenue in fiscal year 2023?", "Adobe_adbe-10k-fy23", ["19.41", "19,409", "19.4"]),
    ("What sliding window size does Mistral 7B use?", "arXiv_2310.06825", ["4096", "4,096"]),
    ("What is the Speak-Up Hotline and how can it be reached?", "VS-LGL-004", ["anonym", "24x7", "24/7"]),
]
OUT_OF_SCOPE = [
    ("What was Apple's revenue in fiscal 2023?", None),
    ("What is the parental leave policy at Veridian's competitor, Contoso?", "VS-HR-001"),
    ("Who won the 2022 FIFA World Cup?", None),
]
REFUSAL_MARKERS = ["couldn't find", "could not find", "not find", "no information", "does not contain", "doesn't contain",
                   "not mentioned", "not available", "do not have", "don't have", "not provided", "no mention"]

CONFIGS = {
    "Dense only (FAISS)": dict(hybrid=False, rerank=False),
    "Hybrid (FAISS + BM25, RRF)": dict(hybrid=True, rerank=False),
    "Dense + re-rank": dict(hybrid=False, rerank=True),
    "Hybrid + re-rank (default)": dict(hybrid=True, rerank=True),
}


def eval_retrieval(kb: KnowledgeBase, k: int = 6) -> dict:
    results = {}
    for name, cfg in CONFIGS.items():
        hits1 = hitsk = rr = 0.0
        t0 = time.time()
        for q, src, _ in EVAL_SET:
            ranked = kb.retrieve(q, sources=None, k=k, **cfg)
            ranks = [i for i, h in enumerate(ranked) if h.doc.metadata["source"].startswith(src)]
            if ranks:
                hitsk += 1
                rr += 1.0 / (ranks[0] + 1)
                hits1 += ranks[0] == 0
        n = len(EVAL_SET)
        results[name] = {"hit@1": round(hits1 / n, 3), f"hit@{k}": round(hitsk / n, 3), "mrr": round(rr / n, 3),
                         "avg_ms": int((time.time() - t0) * 1000 / n)}
        print(f"{name:<30} {results[name]}")
    return results


def eval_answers(kb: KnowledgeBase, model: str | None = None) -> dict:
    bot = Assistant(kb, model=model)
    rows, correct = [], 0
    for q, src, expected in EVAL_SET:
        source = next(s for s in kb.manifest if s.startswith(src))
        t0 = time.time()
        out = bot.answer(q, sources=[source])
        secs = time.time() - t0
        ok = any(e.lower() in out["answer"].lower() for e in expected)
        cited = bool(out["citations"])
        correct += ok
        rows.append({"question": q, "document": kb.manifest[source]["title"], "correct": ok, "cited": cited,
                     "seconds": round(secs, 1), "answer": out["answer"][:400]})
        print(f"{'✅' if ok else '❌'} {'📎' if cited else '  '} {secs:5.1f}s  {q}")
    refusals = []
    for q, src in OUT_OF_SCOPE:
        sources = [next(s for s in kb.manifest if s.startswith(src))] if src else None
        out = bot.answer(q, sources=sources)
        ok = any(m in out["answer"].lower() for m in REFUSAL_MARKERS)
        refusals.append({"question": q, "refused": ok, "answer": out["answer"][:300],
                         "self_correction": out["prepared"].trace.get("self_correction")})
        print(f"{'✅' if ok else '❌'} refusal  {q}")
    n = len(rows)
    return {"accuracy": round(correct / n, 3), "citation_rate": round(sum(r["cited"] for r in rows) / n, 3),
            "avg_seconds": round(sum(r["seconds"] for r in rows) / n, 1),
            "refusal_rate": round(sum(r["refused"] for r in refusals) / len(refusals), 3),
            "rows": rows, "refusals": refusals}


def to_markdown(res: dict) -> str:
    lines = ["# Evaluation results", "", f"Corpus: {res['corpus']['pdfs']} PDFs, {res['corpus']['pages']} pages, "
             f"{res['corpus']['chunks']} chunks. Questions: {len(EVAL_SET)} (+{len(OUT_OF_SCOPE)} out-of-scope).", "",
             "## Retrieval over the whole library", "", "| Configuration | Hit@1 | Hit@6 | MRR | Avg latency |",
             "|---|---|---|---|---|"]
    for name, r in res["retrieval"].items():
        lines.append(f"| {name} | {r['hit@1']:.0%} | {r['hit@6']:.0%} | {r['mrr']:.2f} | {r['avg_ms']} ms |")
    if "answers" in res:
        a = res["answers"]
        lines += ["", "## End-to-end answers (LLM: " + config.LLM_MODEL + ")", "",
                  f"* Answer accuracy (expected fact present): **{a['accuracy']:.0%}**",
                  f"* Answers with page citations: **{a['citation_rate']:.0%}**",
                  f"* Out-of-scope questions correctly refused: **{a['refusal_rate']:.0%}**",
                  f"* Average end-to-end latency: **{a['avg_seconds']} s**", "",
                  "| # | Question | Document | Correct | Cited | Time |", "|---|---|---|---|---|---|"]
        for i, r in enumerate(a["rows"], 1):
            lines.append(f"| {i} | {r['question']} | {r['document']} | {'✅' if r['correct'] else '❌'} | "
                         f"{'✅' if r['cited'] else '—'} | {r['seconds']}s |")
        lines += ["", "### Out-of-scope", ""]
        for r in a["refusals"]:
            lines.append(f"* {'✅' if r['refused'] else '❌'} *{r['question']}* → {r['answer'][:160]!r}")
    return "\n".join(lines) + "\n"


def compare_models(kb: KnowledgeBase, models: list[str]):
    out = config.ROOT / "deliverables"
    cache = out / "model_comparison.json"
    previous = json.loads(cache.read_text()) if cache.exists() and "--fresh" not in sys.argv else {}
    rows = {}
    for m in models:
        if m in previous:
            print(f"== Model: {m} (cached) ==")
            rows[m] = previous[m]
            continue
        print(f"== Model: {m} ==")
        rows[m] = eval_answers(kb, model=m)
    (out / "model_comparison.json").write_text(json.dumps(rows, indent=2))
    lines = ["# LLM comparison", "",
             "Same corpus, same hybrid retrieval + re-ranking and the same grounded prompt - only the generator LLM "
             f"changes. {len(EVAL_SET)} ground-truth questions + {len(OUT_OF_SCOPE)} out-of-scope questions.", "",
             "| Model | Answer accuracy | Answers cited | Out-of-scope refused | Avg latency |", "|---|---|---|---|---|"]
    for m, r in rows.items():
        lines.append(f"| {m} | {r['accuracy']:.0%} | {r['citation_rate']:.0%} | {r['refusal_rate']:.0%} | {r['avg_seconds']} s |")
    lines += ["", "## Per-question correctness", "", "| # | Question | " + " | ".join(models) + " |",
              "|---|---|" + "---|" * len(models)]
    for i, (q, _, _) in enumerate(EVAL_SET):
        cells = [("✅" if rows[m]["rows"][i]["correct"] else "❌") + f" {rows[m]['rows'][i]['seconds']}s" for m in models]
        lines.append(f"| {i + 1} | {q} | " + " | ".join(cells) + " |")
    lines += ["", "## Out-of-scope answers", ""]
    for j, (q, _) in enumerate(OUT_OF_SCOPE):
        lines.append(f"**{q}**")
        for m in models:
            r = rows[m]["refusals"][j]
            lines.append(f"* {'✅' if r['refused'] else '❌'} `{m}`: {r['answer'][:180]!r}")
        lines.append("")
    (out / "model_comparison.md").write_text("\n".join(lines) + "\n")
    print("Saved deliverables/model_comparison.{json,md}")


def main():
    kb = KnowledgeBase()
    if "--models" in sys.argv:
        compare_models(kb, sys.argv[sys.argv.index("--models") + 1].split(","))
        return
    res = {"corpus": {"pdfs": len(kb.manifest), "pages": sum(v["pages"] for v in kb.manifest.values()),
                      "chunks": len(kb.chunks)}}
    print("== Retrieval ==")
    res["retrieval"] = eval_retrieval(kb)
    if "--retrieval-only" not in sys.argv:
        print("== Answers ==")
        res["answers"] = eval_answers(kb)
    out = config.ROOT / "deliverables"
    out.mkdir(exist_ok=True)
    (out / "evaluation_results.json").write_text(json.dumps(res, indent=2))
    (out / "evaluation_results.md").write_text(to_markdown(res))
    print("\nSaved deliverables/evaluation_results.{json,md}")


if __name__ == "__main__":
    main()
