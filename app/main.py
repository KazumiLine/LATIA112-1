import argparse
import os
from dotenv import load_dotenv

from app.db import init_db
from app.agent import build_user_agent


def run_chat(user_id: str):
    agent = build_user_agent(user_id)
    print("Type 'exit' to quit. Type 'help' for hints.")
    while True:
        try:
            user_input = input(f"[{user_id}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break
        if user_input.lower() == "help":
            print("Examples:\n- 產品有什麼？\n- 查詢 SKU-1002 的價格與庫存\n- 查詢 alice@example.com 的訂單\n- 我想下單：SKU-1001 2個，寄給 alice@example.com\n- 如何退貨？售後服務怎麼處理？")
            continue

        response = agent.chat(user_input)
        print(str(response))


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="LlamaIndex Agent CLI")
    parser.add_argument("--user", dest="user_id", default="guest", help="User ID or email for memory scoping")
    parser.add_argument("--init-db", dest="init_db_flag", action="store_true", help="Initialize database with sample data")

    args = parser.parse_args()

    if args.init_db_flag:
        init_db(seed=True)
        print("Database initialized and seeded.")

    run_chat(args.user_id)


if __name__ == "__main__":
    main()