# Token Usage & Cost Report

**Hackathon Challenge:** HackerRank Orchestrate (Buy or Wait?)

## 1. Summary by Model

| Model Provider & Name | API Calls | Input Tokens | Output Tokens | Total Tokens | Estimated Cost (USD) |
|---|---|---|---|---|---|
| `qwen/qwen3.6-27b` | 16 | 24,192 | 816 | 25,008 | $0.0050 |

## 2. Totals and Averages

- **Total API Calls**: 16
- **Total Input Tokens**: 24,192
- **Total Output Tokens**: 816
- **Total Combined Tokens**: 25,008
- **Average Tokens per Request** (250 requests): 100.0
- **Estimated Total Cost**: $0.0050
- **Estimated Cost per Request**: $0.00002

## 3. Notes on Token Efficiency & Caching
- Multimodal vision extractions for all 16 images were performed with `qwen/qwen3.6-27b` on Groq and cached in `code/cache/image_amounts.json`.
- Structured mutations from 215 multilingual messages are cached in `code/cache/message_mutations.json`.
- 100% of ledger math, currency conversions, 90-day daily balance simulation, and 6-tier ranking operate deterministically in Python with zero token overhead.