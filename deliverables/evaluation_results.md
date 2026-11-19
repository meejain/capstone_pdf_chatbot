# Evaluation results

Corpus: 71 PDFs, 2340 pages, 9834 chunks. Questions: 33 (+3 out-of-scope).

## Retrieval over the whole library

| Configuration | Hit@1 | Hit@6 | MRR | Avg latency |
|---|---|---|---|---|
| Dense only (FAISS) | 88% | 94% | 0.90 | 18 ms |
| Hybrid (FAISS + BM25, RRF) | 88% | 94% | 0.90 | 25 ms |
| Dense + re-rank | 91% | 94% | 0.92 | 114 ms |
| Hybrid + re-rank (default) | 94% | 97% | 0.95 | 57 ms |

## End-to-end answers (LLM: gemma-3-12b-it)

* Answer accuracy (expected fact present): **100%**
* Answers with page citations: **100%**
* Out-of-scope questions correctly refused: **100%**
* Average end-to-end latency: **4.7 s**

| # | Question | Document | Correct | Cited | Time |
|---|---|---|---|---|---|
| 1 | How many days of paid annual leave do full-time employees get? | Employee Leave Policy | ✅ | ✅ | 5.6s |
| 2 | How many unused annual leave days can be carried forward? | Employee Leave Policy | ✅ | ✅ | 1.5s |
| 3 | How long is parental leave for non-birthing parents? | Employee Leave Policy | ✅ | ✅ | 4.7s |
| 4 | Which day is the company-wide anchor day for office attendance? | Remote and Hybrid Work Policy | ✅ | ✅ | 4.6s |
| 5 | What setup stipend do fully remote employees receive? | Remote and Hybrid Work Policy | ✅ | ✅ | 3.0s |
| 6 | Which flight class can I book for a 7 hour flight? | Travel and Expense Policy | ✅ | ✅ | 4.1s |
| 7 | What is the maximum hotel rate per night in Tier 1 cities? | Travel and Expense Policy | ✅ | ✅ | 2.9s |
| 8 | Within how many days must expense claims be submitted in Concur? | Travel and Expense Policy | ✅ | ✅ | 3.2s |
| 9 | Up to what value can employees accept gifts without declaring them? | Code of Business Conduct | ✅ | ✅ | 3.7s |
| 10 | What is the minimum password length? | Information Security Policy | ✅ | ✅ | 4.6s |
| 11 | How quickly must critical vulnerabilities be patched? | Information Security Policy | ✅ | ✅ | 4.1s |
| 12 | How long is CCTV footage retained? | Data Privacy and Retention Policy | ✅ | ✅ | 2.4s |
| 13 | Who founded Veridian Systems? | Employee Onboarding Handbook | ✅ | ✅ | 3.6s |
| 14 | How long is the probation period for new employees? | Employee Onboarding Handbook | ✅ | ✅ | 2.0s |
| 15 | What is the 401(k) matching formula? | Employee Benefits Guide 2026 | ✅ | ✅ | 3.9s |
| 16 | What is the response time for a SEV-1 security incident? | Incident Response Runbook | ✅ | ✅ | 3.6s |
| 17 | How many quotes are needed for a USD 50,000 purchase? | Procurement and Vendor Management Policy | ✅ | ✅ | 4.6s |
| 18 | How often should the AeroBrew X1 be descaled? | AeroBrew X1 Smart Coffee Machine User Manual | ✅ | ✅ | 5.0s |
| 19 | What does error code E05 mean on the coffee machine? | AeroBrew X1 Smart Coffee Machine User Manual | ✅ | ✅ | 3.9s |
| 20 | How long does the SkyNote Pro 11 take to charge fully? | SkyNote Pro 11 Tablet Quick Start Guide | ✅ | ✅ | 3.9s |
| 21 | What is the MPPT voltage range of the SolarGrid inverter? | SolarGrid 5kW Hybrid Inverter Installation Manual | ✅ | ✅ | 4.9s |
| 22 | What is the API rate limit for the Enterprise plan? | Veridian Cloud API Developer Guide v3 | ✅ | ✅ | 4.9s |
| 23 | What was Veridian's revenue in Q2 FY2026? | Veridian QBR Q2 FY2026 | ✅ | ✅ | 4.1s |
| 24 | What was the Net Promoter Score in the 2025 customer survey? | Veridian Customer Satisfaction Survey 2025 | ✅ | ✅ | 7.4s |
| 25 | When will API v2 be retired? | Veridian Product Roadmap 2026 | ✅ | ✅ | 2.1s |
| 26 | What is the recovery time objective for tier-1 services? | Business Continuity and Disaster Recovery Plan | ✅ | ✅ | 4.0s |
| 27 | What is the P1 initial response time on the Premium support plan? | Veridian Support SLA and Escalation Guide | ✅ | ✅ | 3.4s |
| 28 | What are the four core functions of the NIST AI Risk Management Framework? | NIST AI RMF 1.0 | ✅ | ✅ | 4.9s |
| 29 | Which retriever does the original RAG paper use? | RAG - Retrieval-Augmented Generation for Knowledge-Intensive NLP | ✅ | ✅ | 7.1s |
| 30 | How many parallel attention heads does the base Transformer use? | Attention Is All You Need | ✅ | ✅ | 6.4s |
| 31 | What was Adobe's total revenue in fiscal year 2023? | Adobe Form 10-K FY2023 | ✅ | ✅ | 11.7s |
| 32 | What sliding window size does Mistral 7B use? | Mistral 7B | ✅ | ✅ | 16.1s |
| 33 | What is the Speak-Up Hotline and how can it be reached? | Code of Business Conduct | ✅ | ✅ | 4.4s |

### Out-of-scope

* ✅ *What was Apple's revenue in fiscal 2023?* → "I couldn't find that in the selected document(s). The documents contain information about Adobe’s revenue, including Digital Media, Digital Experience, and Publ"
* ✅ *What is the parental leave policy at Veridian's competitor, Contoso?* → "I couldn't find that in the selected document(s). The documents detail Veridian Systems Inc.'s employee leave policies, including annual leave, sick leave, pare"
* ✅ *Who won the 2022 FIFA World Cup?* → "I couldn't find that in the selected document(s).\n\nThe documents discuss AI advancements, Google's mission, and challenges faced in 2022. They also mention Rona"
