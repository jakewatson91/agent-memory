---
description: Session wrap-up — merge state, log completed work, capture cross-project lessons
---

Execute the wrap-up protocol:

1. Read `./.claude/project_state.md`. Update with three rules in this priority order:
   - **ADD** any items observed in *this* session that are not already in the file.
   - **REMOVE / MOVE** items only when *this session produced positive evidence* the item is done, obsolete, or superseded. "I don't recognize this item" is NOT evidence — another terminal's wrap may have added it. Default to keep when in doubt.
   - **NEVER bulk-rewrite or reorder** the file. Edits should be visible as adds/removes against the prior content.

   Update the heading to `Last Update: [current timestamp]`.
2. For each item removed in step 1 because *this session completed it*, append to `./.claude/progress_log.md` (append, don't rewrite). Items removed because they're stale/obsolete (not completed) do not go to progress_log.
3. Call `append_daily_log` ONLY for durable cross-project lessons. Skip session recaps.
4. If step 3 wrote a log entry, refresh the current rollups so semantic_search stays in sync:
   ```bash
   cd ~/agent_memory && .venv/bin/python tree_summarizer.py --level week >> tree_summarizer.log 2>&1 && .venv/bin/python tree_summarizer.py --level month >> tree_summarizer.log 2>&1
   ```
   Skip this step if step 3 was skipped — nothing changed, no need to regenerate.
*if any of these files do not exist, create them.

Output:
- **State:** [1-sentence summary of merge]
- **Completed:** [what moved to progress_log.md, or "none"]
- **Global Log:** [exact return string from append_daily_log, or "skipped — nothing durable"]
- **Rollups:** [path of weekly + monthly files refreshed, or "skipped — no new log"]
