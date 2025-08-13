# LlamaIndex Agent Demo

Features:
- Product Q&A via SQL generation over `products` table (QueryEngineTool)
- Order Q&A via SQL generation over `orders` tables (QueryEngineTool)
- Purchase/After-sales answers from local docs under `docs/` (QueryEngineTool)
- Place orders into SQLite DB (FunctionTool)
- Request more info when user query is underspecified (FunctionTool)
- Per-user persistent memory across sessions

Setup:
- Python 3.10+.
- If venv creation is blocked, you can still run with system Python and `--break-system-packages` when installing.

Install:
1. python3 -m venv .venv && source .venv/bin/activate  # if available
2. pip install --upgrade pip
3. pip install -r requirements.txt  # add --break-system-packages if needed
4. cp .env.example .env  # optional if using OpenAI

Run:
- Initialize DB and start chat
```bash
python -m app.main --init-db --user alice@example.com
```

Examples:
- 查詢產品："查 SKU-1002 的價格與庫存"
- 查詢訂單："查詢 alice@example.com 最近訂單"
- 下單："幫我下單 SKU-1001 2個 給 alice@example.com"
- 售後："如何退貨？保固多久？"

Env Vars:
- `OPENAI_API_KEY` to use OpenAI; otherwise a mock LLM is used.
- `APP_DB_PATH` (default: `storage/app.db`)
- `APP_DOCS_DIR` (default: `docs/`)
