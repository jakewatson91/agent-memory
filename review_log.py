"""Replacement for `claude -p /review_log` cron.

Reads the last 30 days of daily logs, asks an LLM to surface durable patterns
that look like promotion candidates for CONSTITUTION.md / ME.md / CODING.md,
and writes the report to `reports/review_log-YYYY-MM-DD.md`.
"""
import os
import re
from datetime import date, datetime, timedelta
from glob import glob

from dotenv import load_dotenv
from openai import OpenAI

MEM_DIR = os.path.expanduser("~/agent_memory")
DAILY_DIR = os.path.join(MEM_DIR, "daily")
REPORTS_DIR = os.path.join(MEM_DIR, "reports")
load_dotenv(os.path.join(MEM_DIR, ".env"))

MODEL = "anthropic/claude-haiku-4.5"
WINDOW_DAYS = 30

SYSTEM = """You review the last 30 days of Jake's daily logs and propose promotions to his global rule files.

A promotion candidate is a pattern that:
- Appears multiple times across different entries, OR
- Looks like a durable cross-project rule rather than a session-specific note.

For each candidate, output:
- **Rule**: one-sentence statement of the rule.
- **Belongs in**: CONSTITUTION.md (voice/identity/writing), CODING.md (technical/stack/style), or ME.md (background/priorities).
- **Evidence**: cite 2+ daily-log dates (YYYY-MM-DD) where the pattern showed up.
- **Proposed text**: the exact lines to insert, matching the destination file's existing style.

Hard rules:
- No em dashes.
- Do not write anything to the rule files yet. This is a proposal list only.
- Skip patterns that already appear in the global files — Jake will paste those file contents below for you to check against.
- If nothing qualifies, output "No promotion candidates this window."
"""


def main() -> None:
    today = date.today()
    cutoff = today - timedelta(days=WINDOW_DAYS)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    files = sorted(glob(os.path.join(DAILY_DIR, "*.md")))
    pattern = re.compile(r"(\d{4}-\d{2}-\d{2})\.md$")
    in_window = []
    for p in files:
        m = pattern.search(p)
        if not m:
            continue
        d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        if cutoff <= d <= today:
            with open(p) as fh:
                in_window.append((m.group(1), fh.read()))

    if not in_window:
        print(f"No daily logs in last {WINDOW_DAYS} days. Skipping.")
        return

    # Include current global file contents so the model can skip already-codified rules.
    globals_blob_parts = []
    for f in ("CONSTITUTION.md", "ME.md", "CODING.md"):
        path = os.path.join(MEM_DIR, f)
        if os.path.exists(path):
            with open(path) as fh:
                globals_blob_parts.append(f"--- CURRENT {f} ---\n{fh.read()}")
    globals_blob = "\n\n".join(globals_blob_parts)

    daily_blob = "\n\n".join(f"--- daily/{d}.md ---\n{c}" for d, c in in_window)
    payload = f"{globals_blob}\n\n{daily_blob}"

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

    out_path = os.path.join(REPORTS_DIR, f"review_log-{today.isoformat()}.md")
    with open(out_path, "w") as fh:
        fh.write(report + "\n")
    print(f"Wrote {out_path} ({len(in_window)} daily files reviewed)")


if __name__ == "__main__":
    main()
