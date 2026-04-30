# Memory Architecture

Last updated: 2026-04-30

The whole system in one page. If you're confused about where something lives or how updates flow, start here.

## Mental model

Three layers, three locations:

1. **Identity** — who Jake is, how Jake sounds, what Jake values. Loads every session automatically.
2. **Project state** — where each project stands, what's been tried, what's next. Lives in each project's repo.
3. **Cross-project lessons** — durable patterns worth remembering across projects. Stored in a vector log via MCP.

## File map

### Global identity (auto-loaded every session)

`~/.claude/CLAUDE.md` — entry point. Contains `@` imports for the files below. Claude Code reads this on every session start.

`~/agent_memory/` — source files imported by the entry point:
- `CONSTITUTION.md` — voice, tone, anti-AI rules, universal writing rules, operational bias
- `ME.md` — background, identity, active priorities
- `CODING.md` — technical stack defaults, code style rules

### Domain-specific (loaded when relevant)

`~/claude-cowork/CLAUDE.md` — imports `WRITING.md` when working in that folder
`~/claude-cowork/WRITING.md` — job-app-specific writing rules and examples

### Per-project state (in each repo)

`./CLAUDE.md` — project-specific stack, conventions, gotchas. Committed.
`./project_state.md` — current direction, decisions, learnings, next steps. Updated on `/wrap`.
`./progress_log.md` — append-only log of finished work. Updated on `/wrap`.

### Cross-project lessons

Daily log via the `append_daily_log` MCP tool. LanceDB vector store. Write durable lessons here in the moment, review monthly.

## Slash commands

Stored in `~/.claude/commands/`. Claude Code auto-discovers them.

- `/wrap` — end-of-session protocol: merge state, log completed work, capture cross-project lessons
- `/promote` — turn a session-level pattern into a global rule (proposes location and text, waits for confirmation)
- `/review_log` — review last 30 days of daily log entries and propose promotions
- `/audit_global` — flag stale or outdated content in global files

## Update flows

**In the moment:** when Claude does something annoying for the second time, type `/promote`. Claude proposes which file the rule belongs in and what to add. Confirm or refine.

**Monthly:** calendar reminder, first Sunday. Run `/review_log`. Promote durable patterns from the daily log into CONSTITUTION, CODING, or wherever they fit. ~10 minutes.

**Quarterly:** calendar reminder, first Sunday of quarter. Run `/audit_global`. Fix stale dates, retired projects, outdated stack defaults. ~15 minutes.

**Project init:** `init_project` (zsh function) scaf