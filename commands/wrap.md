---
description: Session wrap-up — merge state, log completed work, capture cross-project lessons
---

Execute the wrap-up protocol:

1. Read `./project_state.md`. Merge new updates from this session, preserve historical context. Update heading to `Last Update: [current timestamp]`.
2. Move any newly-completed items from project_state.md into `./progress_log.md` (append, don't rewrite).
3. Call `append_daily_log` ONLY for durable cross-project lessons. Skip session recaps.

Output:
- **State:** [1-sentence summary of merge]
- **Completed:** [what moved to progress_log.md, or "none"]
- **Global Log:** [exact return string from append_daily_log, or "skipped — nothing durable"]
