# CODING RULES
*These rules apply when writing, reviewing, or discussing code. Ignore for non-technical tasks.*

* **Clarity:** NO analogies. Explain in simple technical terms. ALWAYS give numerical examples when explaining a concept.
* **Architecture:** NEVER suggest implementing unscalable solutions (e.g., basic keyword matching instead of LLM understanding). ALWAYS prioritize a generalizable solution.
* **Refactoring:** ALWAYS give targeted fixes instead of the full rewritten script unless asked.
* **Naming:** The most annoying thing ever is changing a function or variable name based on a logic change. Like adding `model` to a `train_xgb` return and renaming the function to `train_xgb_with_model`. DO NOT do that. Just keep the original variable names.
* **Tone:** Keep it simple and concise. We're not building rocket ships. Don't be defensive unless it's necessary.

## Default Architecture & Stack
When proposing architectures or scaffolding new projects, default to these tools unless explicitly instructed otherwise:
* **Frontend / Hosting:** Next.js deployed on Vercel
* **Database / Backend:** Supabase
* **Design:** Canva, draw.io
* **Agentic Tools:** Claude Cowork, Claude Code
