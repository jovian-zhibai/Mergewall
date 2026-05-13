"""Example: Running CodeGuardian on sample code.

Two modes:
  - Demo mode (default): No API key needed, uses mock responses.
    Runs the full pipeline and produces a realistic report.

  - Live mode: Requires MiMo/OpenAI API key in environment.
    Set CODE_GUARDIAN_LIVE=1 to activate.

Usage:
    python examples/sample_review.py            # demo mode
    CODE_GUARDIAN_LIVE=1 python examples/sample_review.py  # live mode
"""

import os
import asyncio

from mergewall.graph.workflow import ReviewReport

SAMPLE_CODE = """
import sqlite3
import hashlib
import json
import os

API_SECRET = "sk-proj-abc123def456ghi789jkl"

def get_user(user_id):
    conn = sqlite3.connect("users.db")
    query = f"SELECT * FROM users WHERE id = {user_id}"
    result = conn.execute(query)
    user = result.fetchone()
    conn.close()
    return user

def authenticate(username, password):
    user = get_user_by_username(username)
    if user and user.password == hashlib.md5(password.encode()).hexdigest():
        return create_session(user.id)
    return None

def process_order(items):
    total = 0
    for item in items:
        product = db.query(f"SELECT price FROM products WHERE id = {item['id']}")
        total += product.price * item['quantity']
    return total

def load_config(path):
    data = open(path).read()
    config = json.loads(data)
    return config

def send_notification(user_id, message):
    # TODO: implement notification sending
    pass
"""


async def run_demo():
    """Demo mode — no API key needed."""
    from mergewall.demo import DemoReviewWorkflow

    print("=" * 60)
    print("  CodeGuardian Demo — Multi-Agent Code Review")
    print("  (No API key required)")
    print("=" * 60)
    print()

    demo = DemoReviewWorkflow()
    result = demo.run(code=SAMPLE_CODE, file_path="app.py")

    report = ReviewReport(result)
    print(report.to_markdown())

    print()
    print("-" * 60)
    print(f"Demo complete. {len(result.findings)} findings generated.")
    print(f"Simulated token usage: {result.token_usage:,} tokens")
    print()
    print("To run with MiMo: export LLM_API_KEY=your-key")
    print("  CODE_GUARDIAN_LIVE=1 python examples/sample_review.py")
    print("-" * 60)

    return result


async def run_live():
    """Live mode — requires LLM_API_KEY."""
    from mergewall.graph.workflow import CodeReviewWorkflow

    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        print("ERROR: LLM_API_KEY not set. Falling back to demo mode.\n")
        return await run_demo()

    print("Running live review with MiMo...")
    workflow = CodeReviewWorkflow()
    result = await workflow.run(code=SAMPLE_CODE, file_path="app.py")

    report = ReviewReport(result)
    print(report.to_markdown())

    return result


async def main():
    if os.getenv("CODE_GUARDIAN_LIVE") == "1":
        await run_live()
    else:
        await run_demo()


if __name__ == "__main__":
    asyncio.run(main())
