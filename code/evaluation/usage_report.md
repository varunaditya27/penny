# Token Usage & Cost Report

**Hackathon Challenge:** HackerRank Orchestrate (Buy or Wait?)

## 1. Summary by Model

| Model Provider & Name | API Calls | Input Tokens | Output Tokens | Total Tokens | Estimated Cost (USD) |
|---|---|---|---|---|---|
| `openai/gpt-oss-20b` | 24 | 16,352 | 3,135 | 19,487 | $0.0022 |
| `qwen/qwen3.6-27b` | 16 | 24,192 | 816 | 25,008 | $0.0050 |

## 2. Totals and Averages

- **Total API Calls**: 40
- **Total Input Tokens**: 40,544
- **Total Output Tokens**: 3,951
- **Total Combined Tokens**: 44,495
- **Average Tokens per Request** (250 requests): 178.0
- **Estimated Total Cost**: $0.0072
- **Estimated Cost per Request**: $0.00003

## 3. Notes on Token Efficiency & Caching
- Multimodal vision extractions for all 16 images were performed with `qwen/qwen3.6-27b` on Groq and cached in `code/cache/image_amounts.json`.
- Structured mutations from 215 multilingual messages are cached in `code/cache/message_mutations.json`.
- 100% of ledger math, currency conversions, 90-day daily balance simulation, and 6-tier ranking operate deterministically in Python with zero token overhead.