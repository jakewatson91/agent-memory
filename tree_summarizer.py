"""Hierarchical rollups for agent_memory.

Walks daily files into weekly summaries, weekly files into monthly summaries.
Each rollup is written to disk as Markdown AND indexed in LanceDB with
`level` set to "week" or "month" so semantic_search can surface them.

Usage:
    python tree_summarizer.py --level week              # current ISO week
    python tree_summarizer.py --level week --date 2026-05-11
    python tree_summarizer.py --level month             # current month
    python tree_summarizer.py --level month --date 2026-04-15
    python tree_summarizer.py --backfill                # all completed weeks + months
"""
import argparse
import os
import re
import sys
from datetime import date, datetime, timedelta
from glob import glob

from dotenv import load_dotenv
from openai import OpenAI

MEM_DIR = os.path.expanduser("~/agent_memory")
DAILY_DIR = os.path.join(MEM_DIR, "daily")
WEEKLY_DIR = os.path.join(MEM_DIR, "weekly")
MONTHLY_DIR = os.path.join(MEM_DIR, "monthly")
DB_PATH = os.path.join(MEM_DIR, ".lancedb")

load_dotenv(os.path.join(MEM_DIR, ".env"))

# Same provider memory_synthesis.py uses. Swap MODEL if the free tier flakes.
MODEL = "meta-llama/llama-3.3-70b-instruct"
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)


def _read(path: str) -> str:
    with open(path) as f:
        return f.read()


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def _iso_week_bounds(d: date) -> tuple[date, date, str]:
    """Return (monday, sunday, 'YYYY-WNN') for the ISO week containing d."""
    iso_year, iso_week, iso_weekday = d.isocalendar()
    monday = d - timedelta(days=iso_weekday - 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday, f"{iso_year}-W{iso_week:02d}"


def _month_bounds(d: date) -> tuple[date, date, str]:
    first = d.replace(day=1)
    if first.month == 12:
        next_first = first.replace(year=first.year + 1, month=1)
    else:
        next_first = first.replace(month=first.month + 1)
    last = next_first - timedelta(days=1)
    return first, last, f"{first.year}-{first.month:02d}"


def _collect_sources(level: str, start: date, end: date) -> list[tuple[str, str]]:
    """Return list of (path, content) for leaf or weekly files in [start, end]."""
    if level == "week":
        files = sorted(glob(os.path.join(DAILY_DIR, "*.md")))
        pattern = re.compile(r"(\d{4}-\d{2}-\d{2})\.md$")
        out = []
        for p in files:
            m = pattern.search(p)
            if not m:
                continue
            d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            if start <= d <= end:
                out.append((p, _read(p)))
        return out
    if level == "month":
        files = sorted(glob(os.path.join(WEEKLY_DIR, "*.md")))
        pattern = re.compile(r"(\d{4})-W(\d{2})\.md$")
        out = []
        for p in files:
            m = pattern.search(p)
            if not m:
                continue
            iso_year, iso_week = int(m.group(1)), int(m.group(2))
            monday = date.fromisocalendar(iso_year, iso_week, 1)
            if start <= monday <= end:
                out.append((p, _read(p)))
        return out
    raise ValueError(f"unknown level: {level}")


SYSTEM_WEEK = """You are summarizing one week of an engineer's working notes.

Input: several daily log files. Each entry inside a daily file is delimited by `### HH:MM:SS | project | title` and followed by bullet points.

Output: a Markdown rollup. For each *project* that appeared this week, emit one `## <project>` section. Inside each section, group related entries into 1-3 themes; each theme is a `### <theme title>` followed by 3-7 tight bullets capturing the substance — decisions made, lessons learned, patterns discovered, problems hit. Preserve technical specifics (function names, error messages, numeric results). Cite source dates inline as `(YYYY-MM-DD)` so the reader can find the original entry.

Hard rules:
- No em dashes.
- No preamble. Start with the first `## <project>` line.
- No vague summary statements. Every bullet must contain a specific fact.
- If a project had only one entry, keep it as one theme. Don't pad.
- Skip entries that are trivial (single-line status updates, "wrap-up" markers with no content).
"""

SYSTEM_MONTH = """You are summarizing one month of an engineer's working notes from weekly rollups.

Input: 1-5 weekly rollup files. Each contains `## <project>` sections with `### <theme>` subsections.

Output: a Markdown rollup organized as `## <project>` with `### <theme>` subsections, but at a higher altitude — group the weeks into the *2-4 most important threads per project* across the whole month. Each thread is a `### <thread title>` with 4-8 bullets that capture the arc (what was tried, what worked, what's settled, what's still open). Cite source weeks inline as `(YYYY-WNN)`.

Hard rules:
- No em dashes.
- No preamble.
- Every bullet must contain a specific fact.
- Skip projects that had no substantive activity.
"""


def _llm_rollup(system: str, user_payload: str) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_payload},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


def _index_rollup(md_text: str, source: str, level: str, when: datetime) -> int:
    """Index each `## <project>` block as a separate chunk in LanceDB.

    Returns number of chunks indexed.
    """
    # Lazy import to avoid the embedder load cost during dry runs.
    sys.path.insert(0, MEM_DIR)
    from mcp_server import _get_embedder, _get_table  # noqa: E402

    blocks = re.split(r"^(?=## )", md_text, flags=re.MULTILINE)
    blocks = [b.strip() for b in blocks if b.strip().startswith("## ")]
    if not blocks:
        # No project headers parsed — index the whole rollup as one chunk.
        blocks = [md_text.strip()]

    table = _get_table()
    embedder = _get_embedder()

    # Idempotent reindex: drop any prior chunks from this rollup source so the
    # LanceDB index always reflects the .md file on disk.
    escaped_source = source.replace("'", "''")
    try:
        table.delete(f"source = '{escaped_source}'")
    except Exception:
        pass

    rows = []
    for b in blocks:
        first_line = b.splitlines()[0] if b.splitlines() else ""
        proj_match = re.match(r"##\s+(.+)", first_line)
        project = proj_match.group(1).strip() if proj_match else "global"
        rows.append(
            {
                "vector": embedder.encode(b).tolist(),
                "text": b,
                "source": source,
                "project": project,
                "timestamp": when.isoformat(),
                "level": level,
                "parent": "",
            }
        )
    table.add(rows)
    return len(rows)


def _recently_written(path: str, seconds: int = 300) -> bool:
    """True if path was modified within the last `seconds`. Used to debounce
    burst regenerations when multiple terminals call /wrap back-to-back."""
    if not os.path.exists(path):
        return False
    return (datetime.now().timestamp() - os.path.getmtime(path)) < seconds


def rollup_week(target: date) -> str | None:
    monday, sunday, slug = _iso_week_bounds(target)
    out_path = os.path.join(WEEKLY_DIR, f"{slug}.md")
    if _recently_written(out_path):
        print(f"[week {slug}] regenerated <5min ago, skip (debounce)")
        return out_path
    sources = _collect_sources("week", monday, sunday)
    if not sources:
        print(f"[week {slug}] no daily files in {monday}..{sunday}, skip")
        return None

    payload = "\n\n".join(
        f"--- {os.path.basename(p)} ---\n{c}" for p, c in sources
    )
    header = f"# Week {slug} ({monday.isoformat()} to {sunday.isoformat()})\n\n"
    body = _llm_rollup(SYSTEM_WEEK, payload)
    md = header + body + "\n"
    _write(out_path, md)
    n = _index_rollup(body, f"weekly/{slug}.md", "week", datetime.combine(sunday, datetime.min.time()))
    print(f"[week {slug}] wrote {out_path}, indexed {n} chunks from {len(sources)} dailies")
    return out_path


def rollup_month(target: date) -> str | None:
    first, last, slug = _month_bounds(target)
    out_path = os.path.join(MONTHLY_DIR, f"{slug}.md")
    if _recently_written(out_path):
        print(f"[month {slug}] regenerated <5min ago, skip (debounce)")
        return out_path
    sources = _collect_sources("month", first, last)
    if not sources:
        print(f"[month {slug}] no weekly files in {first}..{last}, skip")
        return None

    payload = "\n\n".join(
        f"--- {os.path.basename(p)} ---\n{c}" for p, c in sources
    )
    header = f"# Month {slug} ({first.isoformat()} to {last.isoformat()})\n\n"
    body = _llm_rollup(SYSTEM_MONTH, payload)
    md = header + body + "\n"
    _write(out_path, md)
    n = _index_rollup(body, f"monthly/{slug}.md", "month", datetime.combine(last, datetime.min.time()))
    print(f"[month {slug}] wrote {out_path}, indexed {n} chunks from {len(sources)} weeklies")
    return out_path


def backfill() -> None:
    """Generate every completed week + month from existing daily/weekly files."""
    today = date.today()
    # Weeks: every ISO week that has at least one daily file and ended before today.
    daily_files = sorted(glob(os.path.join(DAILY_DIR, "*.md")))
    seen_weeks: set[tuple[int, int]] = set()
    for p in daily_files:
        m = re.search(r"(\d{4}-\d{2}-\d{2})\.md$", p)
        if not m:
            continue
        d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        iso_year, iso_week, _ = d.isocalendar()
        seen_weeks.add((iso_year, iso_week))
    for iso_year, iso_week in sorted(seen_weeks):
        monday = date.fromisocalendar(iso_year, iso_week, 1)
        rollup_week(monday)

    # Months: every month that now has a weekly file.
    weekly_files = sorted(glob(os.path.join(WEEKLY_DIR, "*.md")))
    seen_months: set[tuple[int, int]] = set()
    for p in weekly_files:
        m = re.search(r"(\d{4})-W(\d{2})\.md$", p)
        if not m:
            continue
        iso_year, iso_week = int(m.group(1)), int(m.group(2))
        monday = date.fromisocalendar(iso_year, iso_week, 1)
        seen_months.add((monday.year, monday.month))
    for y, mo in sorted(seen_months):
        rollup_month(date(y, mo, 15))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--level", choices=["week", "month"])
    p.add_argument("--date", help="YYYY-MM-DD; defaults to today")
    p.add_argument("--backfill", action="store_true")
    args = p.parse_args()

    if args.backfill:
        backfill()
        return
    if not args.level:
        p.error("--level or --backfill required")

    target = (
        datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    )
    if args.level == "week":
        rollup_week(target)
    else:
        rollup_month(target)


if __name__ == "__main__":
    main()
