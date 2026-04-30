import os
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from sentence_transformers import SentenceTransformer
import lancedb
from lancedb.pydantic import LanceModel, Vector

# Directories
MEM_DIR = os.path.expanduser("~/agent_memory")
DB_PATH = os.path.join(MEM_DIR, ".lancedb")

mcp = FastMCP("Agent Memory")
try:
    embedder = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
except Exception:
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
db = lancedb.connect(DB_PATH)


# 1. Define the explicit schema
class MemorySchema(LanceModel):
    vector: Vector(384)
    text: str
    source: str
    project: str
    timestamp: str


def get_or_create_table():
    try:
        table = db.open_table("memory_chunks")
        if "project" not in table.schema.names:
            print("Schema mismatch detected. Dropping old table...")
            db.drop_table("memory_chunks")
            return db.create_table("memory_chunks", schema=MemorySchema)
        return table
    except Exception:
        return db.create_table("memory_chunks", schema=MemorySchema)


table = get_or_create_table()


@mcp.tool()
def read_global_context() -> str:
    """Read md files"""
    files = ["CONSTITUTION.md", "ME.md", "STYLE.md", "CODING.md", "CURRENT.md"]
    context = []
    for f in files:
        path = os.path.join(MEM_DIR, f)
        if os.path.exists(path):
            with open(path, "r") as file:
                context.append(f"--- {f} ---\n{file.read()}")
    return "\n\n".join(context)


@mcp.tool()
def append_daily_log(log_entry: str, project: str = "global") -> str:
    """Append a log to today's daily file and index it for semantic search.

    Expected format: title line followed by bullet points.
    Example:
      Credit Risk Model Decision
      - Abandoned TabICL architecture
      - Baseline XGBoost: 0.8614 AUC
      - Next: hyperparameter optimization
    """
    today = datetime.now().strftime("%Y-%m-%d")
    file_path = os.path.join(MEM_DIR, "daily", f"{today}.md")
    timestamp = datetime.now().strftime("%H:%M:%S")

    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # 1. Write to flat file with standardized format
    with open(file_path, "a") as f:
        f.write(f"\n### {timestamp} | {project} | {log_entry}\n")

    # 2. Add to LanceDB vector index
    vector = embedder.encode(log_entry).tolist()
    table.add(
        [
            {
                "vector": vector,
                "text": log_entry,
                "source": f"daily/{today}.md",
                "timestamp": datetime.now().isoformat(),
                "project": project,
            }
        ]
    )

    return f"Logged and indexed {len(log_entry)} characters."


@mcp.tool()
def semantic_search(query: str, limit: int = 3, project: str = "global") -> str:
    """Search global memory by meaning. Returns top matching file chunks."""
    query_vector = embedder.encode(query).tolist()

    # Compares query vector against database, filters by project, returns top 10
    results = (
        table.search(query_vector).where(f"project = '{project}'").limit(10).to_list()
    )

    if not results:
        return "No relevant memories found."

    # Sorts the 10 results by ISO timestamp descending (newest first)
    results.sort(key=lambda x: x["timestamp"], reverse=True)

    # Truncates to the requested limit
    results = results[:limit]

    formatted_results = []
    for res in results:
        formatted_results.append(f"Source: {res['source']}\nText: {res['text']}\n")

    return "\n\n".join(formatted_results)


if __name__ == "__main__":
    mcp.run()
