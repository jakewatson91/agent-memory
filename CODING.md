# CODING RULES
*These rules apply when writing, reviewing, or discussing code. Ignore for non-technical tasks.*

* **Clarity:** NO analogies. Explain in simple technical terms. ALWAYS give numerical examples when explaining a concept.
* **Architecture:** NEVER suggest implementing unscalable solutions (e.g., basic keyword matching instead of LLM understanding). ALWAYS prioritize a generalizable solution.
* **Refactoring:** ALWAYS give targeted fixes instead of the full rewritten script unless asked.
* **Naming:** The most annoying thing ever is changing a function or variable name based on a logic change. Like adding `model` to a `train_xgb` return and renaming the function to `train_xgb_with_model`. DO NOT do that. Just keep the original variable names.
* **Tone:** Keep it simple and concise. We're not building rocket ships. Don't be defensive unless it's necessary.
* **NEVER hardcode examples:** Never bake specific brand names, company names, vertical-specific phrases, customer emails, or product names into prompts, validators, blocklists, defaults, or filter rules. Those belong in config (workspace policy, source config, env, or DB), not in code. If a rule needs an example list, the *shape* of the list (a string array, a regex) lives in code; the *contents* live in config, defaulting to empty. Applies to every codebase, not just agent-crm. If a customer in a different vertical would need different values, it's config — full stop. Vertical-specific defaults are not defaults; "no default" is the default.
* **Setup-first design:** When building anything (a feature, a connector, a config knob, an integration), the first question is: *how does a new user set this up from scratch in their own environment?* If the answer involves "Jake has to do it manually" or "ask Jake for the API key" or "needs a code change per customer," the design is wrong — restructure until the setup path is plain, documented, and self-serve. Applies to every project meant to be forkable/multi-tenant. Acceptable setup steps: paste an API key, click a button, choose from a list, fill a form. Unacceptable: edit a TypeScript file, run a one-off script Jake wrote, contact us for access.
* **Use current models:** When recommending or picking an LLM model, never suggest one more than ~12 months old unless the project explicitly pins it for a known reason. Check the project's production code first (grep for `model:` strings) and match what's actually running. As of 2026-05, this rules out gpt-4o, gpt-4o-mini, Claude 3.5/3.7, GPT-4-turbo. Default to current-generation: Claude Opus 4.7 / Sonnet 4.6 / Haiku 4.5, GPT-5 family, DeepSeek v4, etc. If you don't know what's current, look it up before recommending. Don't anchor on training-data defaults.

## Default Architecture & Stack
When proposing architectures or scaffolding new projects, default to these tools unless explicitly instructed otherwise:
* **Frontend / Hosting:** Next.js deployed on Vercel
* **Database / Backend:** Supabase
* **Design:** Canva, draw.io
* **Agentic Tools:** Claude Cowork, Claude Code
* **Env Management:** uv, conda (for GPU training etc.)

## Active blockers
* **Anthropic API (as of 2026-05-09):** account returning "credit balance too low" despite $15.63 balance, Tier 2, $0/$10 monthly spent. Multiple fresh keys in Default workspace fail identically. Support ticket open. Do NOT propose direct Anthropic API usage for new work until cleared — use a different provider or wait. Remove this entry once resolved.
