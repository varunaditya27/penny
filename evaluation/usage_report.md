# Token Usage & Cost Report

**Hackathon Challenge:** HackerRank Orchestrate (Buy or Wait?)

## 1. Summary by Model

| Model Provider & Name | API Calls | Input Tokens | Output Tokens | Total Tokens | Estimated Cost (USD) |
|---|---|---|---|---|---|
| `openai/gpt-oss-20b` | 20 | 13,743 | 2,543 | 16,286 | $0.0018 |

## 2. Totals and Averages

- **Total API Calls**: 20
- **Total Input Tokens**: 13,743
- **Total Output Tokens**: 2,543
- **Total Combined Tokens**: 16,286
- **Average Tokens per Request** (250 requests): 65.1
- **Estimated Total Cost**: $0.0018
- **Estimated Cost per Request**: $0.00001

## 3. Notes on Token Efficiency & Caching
- Multimodal vision extractions for all 16 images are pre-extracted and cached in `code/cache/image_amounts.json`.
- Structured mutations from 215 multilingual messages are cached in `code/cache/message_mutations.json`.
- 100% of ledger math, currency conversions, 90-day daily balance simulation, and 6-tier ranking operate deterministically in Python with zero token overhead.