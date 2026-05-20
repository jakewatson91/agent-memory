# Future development

Things considered and deliberately skipped. Each entry is enough to pick up where it was left.

## Auto-fetch loop (originally Phase 3)

**What it would do**: pull recent Gmail (and later Calendar, GitHub) on a cron, compress HTML to Markdown, index into a separate `autofetch_chunks` LanceDB table with a 7-day rolling TTL. Then `semantic_search(query, source_kind="autofetch")` answers "what's in my inbox about X" instantly without a live Gmail call.

**Why skipped (2026-05-19)**: I mostly use Claude for code, not inbox/calendar questions. Value-per-effort too low right now.

**What's already in place**:
- LanceDB schema for the main table supports it (separate table, not a column add).
- OpenRouter creds in `.env` for any LLM-side compression.
- `markdownify`, `google-auth`, `google-auth-oauthlib`, `google-api-python-client` installed in `.venv` (leftover from the build — uninstall with `pip uninstall ...` if you want a clean env, otherwise harmless).
- GCP project already created: `agent-memory-496913` (https://console.cloud.google.com/?project=agent-memory-496913). Enable Gmail API and create OAuth client inside this project, no need to make a new one.

**Design when we restart**:
- Direct Google OAuth, no Composio middleman.
- Separate `autofetch_chunks` table, not a column on `memory_chunks`. Keeps curated lessons separate from email noise.
- 7-day TTL purge on each run.
- Dedup by Gmail message ID.
- `semantic_search` gets `source_kind="memory"|"autofetch"|"all"` parameter.
- Setup: enable Gmail API → OAuth consent screen (External, Testing, add own email as test user) → Desktop OAuth client → drop JSON at `~/agent_memory/gmail_credentials.json` → run a `setup_gmail_auth.py` once → token saved at `~/agent_memory/.gmail_token.json`.
- Cron: `*/20 * * * *` running an `autofetch.py`.
- Gmail filter: `newer_than:1d -in:promotions -in:social -in:updates -in:forums`.

**Trigger to revisit**: when I find myself asking Claude "what's in my inbox" or "did X email me" more than once a week.

## Prompt-injection filter on ingested content (originally Phase 4)

**What it would do**: cheap Haiku gate over every auto-fetched chunk, scoring 0-1 for injection markers ("ignore previous", role hijacks, fake tool calls). Drop or quarantine scores >0.7. Regex pre-pass for the obvious cases.

**Why skipped**: only matters if auto-fetch is on. Phase 3 prerequisite.

**Trigger to revisit**: when Phase 3 starts.

## Misc

- `memory_synthesis.py` is still on disk but no longer cron'd. It had a couple bugs (`response.content[0].text` should be `response.choices[0].message.content`; reads non-existent `CURRENT.md`). If `CURRENT.md` is a pattern I want to revive (an LLM-maintained "what am I working on now" summary), fix those two bugs and re-enable. Otherwise delete the script.

- `cron_synthesis.log` is 1.2MB of crash dumps from the every-minute job. Safe to delete.
