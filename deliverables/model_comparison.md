# LLM comparison

Same corpus, same hybrid retrieval + re-ranking and the same grounded prompt - only the generator LLM changes. 33 ground-truth questions + 3 out-of-scope questions.

| Model | Answer accuracy | Answers cited | Out-of-scope refused | Avg latency |
|---|---|---|---|---|
| gemma-3-12b-it | 100% | 100% | 100% | 4.6 s |
| qwen2.5-7b-instruct | 100% | 97% | 100% | 2.0 s |
| llama-3.2-3b-instruct | 94% | 88% | 100% | 2.5 s |

## Per-question correctness

| # | Question | gemma-3-12b-it | qwen2.5-7b-instruct | llama-3.2-3b-instruct |
|---|---|---|---|---|
| 1 | How many days of paid annual leave do full-time employees get? | ✅ 8.3s | ✅ 4.9s | ✅ 1.9s |
| 2 | How many unused annual leave days can be carried forward? | ✅ 1.6s | ✅ 1.3s | ✅ 1.0s |
| 3 | How long is parental leave for non-birthing parents? | ✅ 4.8s | ✅ 1.9s | ✅ 2.0s |
| 4 | Which day is the company-wide anchor day for office attendance? | ✅ 4.8s | ✅ 1.1s | ✅ 1.6s |
| 5 | What setup stipend do fully remote employees receive? | ✅ 2.9s | ✅ 1.9s | ✅ 2.1s |
| 6 | Which flight class can I book for a 7 hour flight? | ✅ 4.1s | ✅ 2.2s | ✅ 2.4s |
| 7 | What is the maximum hotel rate per night in Tier 1 cities? | ✅ 2.7s | ✅ 0.7s | ✅ 1.5s |
| 8 | Within how many days must expense claims be submitted in Concur? | ✅ 3.3s | ✅ 1.7s | ✅ 2.1s |
| 9 | Up to what value can employees accept gifts without declaring them? | ✅ 3.9s | ✅ 1.5s | ✅ 2.1s |
| 10 | What is the minimum password length? | ✅ 5.1s | ✅ 2.1s | ✅ 2.3s |
| 11 | How quickly must critical vulnerabilities be patched? | ✅ 4.3s | ✅ 1.9s | ✅ 2.5s |
| 12 | How long is CCTV footage retained? | ✅ 2.7s | ✅ 1.3s | ✅ 2.2s |
| 13 | Who founded Veridian Systems? | ✅ 3.7s | ✅ 1.2s | ✅ 2.8s |
| 14 | How long is the probation period for new employees? | ✅ 2.1s | ✅ 0.7s | ✅ 1.0s |
| 15 | What is the 401(k) matching formula? | ✅ 4.0s | ✅ 1.7s | ✅ 3.2s |
| 16 | What is the response time for a SEV-1 security incident? | ✅ 3.6s | ✅ 1.4s | ✅ 2.7s |
| 17 | How many quotes are needed for a USD 50,000 purchase? | ✅ 4.6s | ✅ 1.2s | ✅ 2.6s |
| 18 | How often should the AeroBrew X1 be descaled? | ✅ 5.0s | ✅ 1.6s | ✅ 2.1s |
| 19 | What does error code E05 mean on the coffee machine? | ✅ 3.8s | ✅ 1.7s | ✅ 2.3s |
| 20 | How long does the SkyNote Pro 11 take to charge fully? | ✅ 3.7s | ✅ 1.6s | ✅ 2.6s |
| 21 | What is the MPPT voltage range of the SolarGrid inverter? | ✅ 4.8s | ✅ 1.4s | ✅ 2.2s |
| 22 | What is the API rate limit for the Enterprise plan? | ✅ 4.8s | ✅ 1.6s | ❌ 2.1s |
| 23 | What was Veridian's revenue in Q2 FY2026? | ✅ 4.0s | ✅ 1.3s | ✅ 2.3s |
| 24 | What was the Net Promoter Score in the 2025 customer survey? | ✅ 7.1s | ✅ 1.3s | ✅ 2.1s |
| 25 | When will API v2 be retired? | ✅ 2.0s | ✅ 1.3s | ✅ 1.6s |
| 26 | What is the recovery time objective for tier-1 services? | ✅ 3.8s | ✅ 1.1s | ✅ 1.8s |
| 27 | What is the P1 initial response time on the Premium support plan? | ✅ 4.0s | ✅ 1.2s | ❌ 1.8s |
| 28 | What are the four core functions of the NIST AI Risk Management Framework? | ✅ 4.6s | ✅ 3.8s | ✅ 4.6s |
| 29 | Which retriever does the original RAG paper use? | ✅ 6.8s | ✅ 4.0s | ✅ 5.5s |
| 30 | How many parallel attention heads does the base Transformer use? | ✅ 6.5s | ✅ 3.1s | ✅ 3.6s |
| 31 | What was Adobe's total revenue in fiscal year 2023? | ✅ 12.3s | ✅ 4.7s | ✅ 3.6s |
| 32 | What sliding window size does Mistral 7B use? | ✅ 7.8s | ✅ 4.0s | ✅ 6.9s |
| 33 | What is the Speak-Up Hotline and how can it be reached? | ✅ 4.7s | ✅ 2.3s | ✅ 2.5s |

## Out-of-scope answers

**What was Apple's revenue in fiscal 2023?**
* ✅ `gemma-3-12b-it`: "I couldn't find that in the selected document(s). The documents contain information about Adobe’s revenue, including Digital Media, Digital Experience, and Publishing and Advertisi"
* ✅ `qwen2.5-7b-instruct`: "I couldn't find that in the selected document(s). The provided documents are about Adobe Inc.'s financial performance and do not contain information on Apple's revenue. Related inf"
* ✅ `llama-3.2-3b-instruct`: "I couldn't find that in the selected document(s). The provided documents are related to Adobe Inc.'s financial reports for FY2024 and FY2023, but they do not mention Apple. However"

**What is the parental leave policy at Veridian's competitor, Contoso?**
* ✅ `gemma-3-12b-it`: "I couldn't find that in the selected document(s). The document details Veridian Systems Inc.'s employee leave policies, including annual leave, sick leave, parental leave, bereavem"
* ✅ `qwen2.5-7b-instruct`: "I couldn't find that in the selected document(s). The provided documents detail Veridian Systems Inc.'s employee leave policies but do not include information about a competitor na"
* ✅ `llama-3.2-3b-instruct`: "I couldn't find that in the selected document(s). \n\nRelated information available:\n- The document only provides information about Veridian Systems Inc.'s employee leave policy.\n- I"

**Who won the 2022 FIFA World Cup?**
* ✅ `gemma-3-12b-it`: "I couldn't find that in the selected document(s).\n\nThe documents discuss AI advancements, Google's mission, and challenges faced in 2022. They also mention Ronaldinho winning two F"
* ✅ `qwen2.5-7b-instruct`: "I couldn't find that in the selected document(s).\n\nThe provided documents discuss Google's and Microsoft's annual reports for 2022, focusing on AI advancements, company missions, a"
* ✅ `llama-3.2-3b-instruct`: "I couldn't find that in the selected document(s).\n\nHowever, I can provide some related information:\n\n* The 2022 FIFA World Cup was won by Argentina, who defeated France in the fina"

