import os
import re
import lancedb
from sentence_transformers import SentenceTransformer

MEM_DIR = os.path.expanduser("~/agent_memory")
DB_PATH = os.path.join(MEM_DIR, ".lancedb")

db = lancedb.connect(DB_PATH)
embedder = SentenceTransformer("all-MiniLM-L6-v2")

table = db.open_table("memory_chunks")

daily_dir = os.path.join(MEM_DIR, "daily")
entry_pattern = re.compile(r"^### (\d{2}:\d{2}:\d{2}) \((.+?)\)\s*$")

total = 0
for filename in sorted(os.listdir(daily_dir)):
    if not filename.endswith(".md"):
        continue

    date_str = filename[:-3]  # strip .md
    filepath = os.path.join(daily_dir, filename)

    with open(filepath) as f:
        lines = f.readlines()

    current_time = None
    current_project = None
    current_lines = []

    def flush(time, project, body_lines, date, source):
        global total
        body = "".join(body_lines).strip()
        if not body:
            return
        timestamp = f"{date}T{time}"
        vector = embedder.encode(body).tolist()
        table.add([{
            "vector": vector,
            "text": body,
            "source": source,
            "project": project,
            "timestamp": timestamp,
        }])
        total += 1
        print(f"  indexed: {timestamp} ({project}) — {len(body)} chars")

    for line in lines:
        m = entry_pattern.match(line)
        if m:
            flush(current_time, current_project, current_lines, date_str, f"daily/{filename}")
            current_time = m.group(1)
            current_project = m.group(2)
            current_lines = []
        else:
            if current_time:
                current_lines.append(line)

    flush(current_time, current_project, current_lines, date_str, f"daily/{filename}")

print(f"\nDone. Indexed {total} entries.")
