AGENTS GUIDE
============

Read this before you start making changes to the repo.

1) Start by reading README.md end‑to‑end
- Understand purpose, architecture, config knobs, and how to run (local, Docker, split deploy).
- Skim the API and UI sections to know how users interact with the system.

2) Scope and principles
- Keep changes minimal, targeted, and consistent with the existing style.
- Prefer improving root causes over patching symptoms.
- Don’t refactor broadly unless asked; avoid unrelated changes.

3) Retrieval‑Augmented Generation (RAG) intent
- Answers must come from provided context; keep strict citations `[book:page-page]`.
- Prioritize exam‑relevant content (definitions, ddx, first/best test, red flags) and compressed outputs.
- Use the provided note templates (disease/drug/procedure/general) and enforce one‑fact‑per‑line when applicable.

4) Config and performance
- Tuning should go through `config.py` (TOPKs, RRF, MMR, models, MAX_TOKENS).
- Model changes: embeddings require re‑ingest; reranker/LLM do not.
- Respect streaming behavior and avoid blocking calls in request paths.

5) Local dev checklists
- Ensure Ollama is running with the configured model (default: Qwen2.5 7B Instruct).
- Ingest at least one PDF before testing queries.
- Run API: `uvicorn server:app --reload --port 8000`; UI: `web` via Vite or served statically from FastAPI.

6) Deploy patterns
- Docker Compose (API + Ollama), optional Caddy for HTTPS.
- Split deploy: UI (Vercel) + local/API (ngrok or Cloudflare Tunnel). UI uses `VITE_API_BASE_URL`.

7) For agentic tooling (if applicable)
- Share brief preambles for tool actions; group related steps.
- Keep an explicit, concise plan (e.g., Inventory → Modify X → Validate) and update it as you proceed.
- Prefer ripgrep (`rg`) for search, patch files via apply‑patch tooling; avoid destructive commands.

8) Validation and safety
- If tests exist, run those most relevant to your change; otherwise, smoke‑test endpoints and UI flows.
- Don’t commit secrets; don’t add licenses/headers unless requested.
- Mention any limitations or next steps succinctly in your handoff.

9) Git etiquette
- Commit early, commit clearly. Prefer small, focused commits per feature or fix.
- Write a meaningful subject line (imperative mood), e.g., "feat: add RRF fusion and streaming".
- Add a concise body listing what changed and why when the diff is non‑trivial.
- After completing a feature, push your commit(s) so others can pick up immediately.
- Avoid committing generated artifacts or secrets; respect .gitignore unless explicitly force‑adding docs.
