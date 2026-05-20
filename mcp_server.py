import os
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Directories
MEM_DIR = os.path.expanduser("~/agent_memory")
DB_PATH = os.path.join(MEM_DIR, ".lancedb")

mcp = FastMCP("Agent Memory")


# Heavy imports + initialization are deferred so the MCP handshake completes
# quickly (Claude Code's default startup timeout is ~5s; loading the
# SentenceTransformer model + LanceDB took ~8.5s and was timing out before
# tools could register). The model + DB only matter for the indexed-write and
# semantic-search paths; read_global_context never touches them.
_embedder = None
_db = None
_table = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        try:
            _embedder = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
        except Exception:
            _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _get_table():
    """Open or create the memory_chunks table. Lazy because the LanceDB
    connection + schema check adds ~1s, and most sessions never call the
    indexed paths."""
    global _db, _table
    if _table is not None:
        return _table

    import lancedb
    from lancedb.pydantic import LanceModel, Vector

    class MemorySchema(LanceModel):
        vector: Vector(384)
        text: str
        source: str
        project: str
        timestamp: str
        level: str  # "leaf" | "week" | "month"
        parent: str  # source path of the rollup that subsumes this chunk; "" for leaves

    if _db is None:
        _db = lancedb.connect(DB_PATH)

    try:
        table = _db.open_table("memory_chunks")
        if "level" not in table.schema.names:
            # Bring legacy tables up to current schema without losing rows.
            table.add_columns({"level": "'leaf'", "parent": "''"})
    except Exception:
        table = _db.create_table("memory_chunks", schema=MemorySchema)

    _table = table
    return _table


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

    # 2. Add to LanceDB vector index (lazy init the heavy bits on first call)
    vector = _get_embedder().encode(log_entry).tolist()
    _get_table().add(
        [
            {
                "vector": vector,
                "text": log_entry,
                "source": f"daily/{today}.md",
                "timestamp": datetime.now().isoformat(),
                "project": project,
                "level": "leaf",
                "parent": "",
            }
        ]
    )

    return f"Logged and indexed {len(log_entry)} characters."


@mcp.tool()
def semantic_search(
    query: str,
    limit: int = 3,
    project: str = "global",
    level: str = "any",
) -> str:
    """Search memory by meaning across leaf/week/month rollups.

    Args:
        query: free-text query.
        limit: number of results to return (default 3).
        project: project name to filter on, or "any" to search across all projects.
        level: "leaf" | "week" | "month" | "any" (default "any"). Use "week"/"month"
            for broad questions ("what happened this month"), "leaf" for specific
            ones ("what was the exact error message").
    """
    query_vector = _get_embedder().encode(query).tolist()

    clauses = []
    if project != "any":
        clauses.append(f"project = '{project}'")
    if level != "any":
        clauses.append(f"level = '{level}'")
    where = " AND ".join(clauses) if clauses else None

    q = _get_table().search(query_vector)
    if where:
        q = q.where(where)
    results = q.limit(20).to_list()

    if not results:
        return "No relevant memories found."

    results.sort(key=lambda x: x["timestamp"], reverse=True)
    results = results[:limit]

    formatted = []
    for res in results:
        tag = f"[{res.get('level', 'leaf')}]"
        formatted.append(
            f"{tag} Source: {res['source']}\nProject: {res['project']}\nText: {res['text']}\n"
        )
    return "\n\n".join(formatted)


if __name__ == "__main__":
    mcp.run()
