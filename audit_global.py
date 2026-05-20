"""Replacement for `claude -p /audit_global` cron.

Reads the three global rule files, asks an LLM to flag stale or outdated
content, and writes the report to `reports/audit_global-YYYY-MM-DD.md`.
No Claude CLI, no OAuth, no expiry surface.
"""
import os
from datetime import date
from dotenv import load_dotenv
from openai import OpenAI

MEM_DIR = os.path.expanduser("~/agent_memory")
REPORTS_DIR = os.path.join(MEM_DIR, "reports")
load_dotenv(os.path.join(MEM_DIR, ".env"))

MODEL = "anthropic/claude-haiku-4.5"
TARGET_FILES = ["CONSTITUTION.md", "ME.md", "CODING.md"]

SYSTEM = """You audit Jake's global rule files for stale or outdated content. For each file, flag:
- Dates or timeframes that have passed.
- Project references that may no longer be active.
- Stack or tool defaults that look outdated.
- Rules that contradict patterns observed in his recent work.

Do not edit anything. Produce a report of what to look at.

Output format:
# Audit YYYY-MM-DD

## CONSTITUTION.md
- (finding) — quote the line, explain why it looks stale.

## ME.md
- ...

## CODING.md
- ...

If a file has nothing to flag, write "Nothing stale." under that heading. No preamble, no em dashes, no vague claims.
"""


def main() -> None:
    today = date.today().isoformat()
    os.makedirs(REPORTS_DIR, exist_ok=True)

    payload_parts = [f"Today is {today}.\n"]
    for f in TARGET_FILES:
        path = os.path.join(MEM_DIR, f)
        if not os.path.exists(path):
            payload_parts.append(f"--- {f} ---\n(file missing)\n")
            continue
        with open(path) as fh:
            payload_parts.append(f"--- {f} ---\n{fh.read()}\n")
    payload = "\n".join(payload_parts)

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": payload},
        ],
        temperature=0.2,
    )
    report = resp.choices[0].message.content.strip()

    out_path = os.path.join(REPORTS_DIR, f"audit_global-{today}.md")
    with open(out_path, "w") as fh:
        fh.write(report + "\n")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
