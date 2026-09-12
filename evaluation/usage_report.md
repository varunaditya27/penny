# Token Usage & Cost Report

**Hackathon Challenge:** HackerRank Orchestrate (Buy or Wait?)

## 1. Summary by Model

| Model Provider & Name | API Calls | Input Tokens | Output Tokens | Total Tokens | Estimated Cost (USD) |
|---|---|---|---|---|---|
| `llama-3.3-70b-versatile` | 0 | 0 | 0 | 0 | $0.0000 |
| `openai/gpt-oss-20b` | 0 | 0 | 0 | 0 | $0.0000 |
| `qwen/qwen3.6-27b` | 0 | 0 | 0 | 0 | $0.0000 |

## 2. Totals and Averages

- **Total API Calls**: 0
- **Total Input Tokens**: 0
- **Total Output Tokens**: 0
- **Total Combined Tokens**: 0
- **Average Tokens per Request** (250 requests): 0.0
- **Estimated Total Cost**: $0.0000
- **Estimated Cost per Request**: $0.00000

## 3. Notes on Token Efficiency & Caching
- Multimodal vision extractions for all 16 images are pre-extracted and cached in `code/cache/image_amounts.json`.
- Structured mutations from 215 multilingual messages are cached in `code/cache/message_mutations.json`.
- 100% of ledger math, currency conversions, 90-day daily balance simulation, and 6-tier ranking operate deterministically in Python with zero token overhead.