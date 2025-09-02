# Repository Guidelines

## Project Structure & Module Organization
- `ingest.py`: PDF → chunks → embeddings (LanceDB) + BM25 artifacts.
- `query.py`: Hybrid retrieval (dense+BM25) → RRF → rerank → MMR → call Ollama.
- `templates.py`: Prompt templates for QA and notes (disease/drug/procedure/general).
- `server.py`: FastAPI (`/api/*`) and static serving of `web/dist`.
- `config.py`: Central knobs (TOPKs, models, MAX_TOKENS, paths).
- `web/`: React + Vite UI (`web/src/*`). Data at `data/books/`; indices in `storage/`.

## Build, Test, and Development Commands
- Setup: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Ingest: `python ingest.py --pdf data/books/book1.pdf --book_id MyBook-1e`
- API (dev): `.venv/bin/uvicorn server:app --reload --port 8000`
- UI (dev): `cd web && npm install && npm run dev` (http://localhost:5173)
- Docker: `docker compose up -d` then `docker compose exec ollama ollama pull qwen2.5:7b-instruct`
- Smoke tests: `curl http://localhost:8000/api/health`; `curl -X POST :8000/api/qa -H 'content-type: application/json' -d '{"q":"What is DKA?"}'`
- Quick restart: `bash scripts/restart_backend.sh`

## Coding Style & Naming Conventions
- Python: PEP 8, 4‑space indent, type hints where practical, `snake_case` for vars/functions, `UPPER_SNAKE` for constants. Put all knobs in `config.py`; avoid hard‑coded model names/paths.
- Frontend: TypeScript + React functional components; `PascalCase` components, `camelCase` props; keep UI under `web/src`. Small, cohesive modules.
- Prompts/templates: keep citation format and compression rules intact; prefer additive edits in `templates.py`.

## Testing Guidelines
- No formal test suite yet. Add targeted unit tests if introducing complex logic; otherwise run smoke tests above.
- For retrieval changes, verify `/api/qa` with `{"debug": true}` and confirm contexts/citations.
- Coverage not enforced; keep tests fast and local.

## Commit & Pull Request Guidelines
- Use Conventional Commits style (e.g., `feat: add RRF fusion`, `fix: avoid blocking stream`).
- PRs: clear description, linked issue, steps to verify (commands/cURL), screenshots for UI, and note any config changes.

## Security & Configuration Tips
- Set `ADMIN_KEY` to enable admin endpoints; never commit secrets or PDFs. Generated data lives in `storage/`.
- Changing `EMBED_MODEL_NAME` requires re‑ingest; reranker/LLM swaps do not. `OLLAMA_MODEL` can be overridden via env.

## Deploy (Vercel + ngrok)
- Configure once in `deploy.env` (e.g., `NGROK_DOMAIN=flea-whole-loosely.ngrok-free.app`).
- Production: `./scripts/deploy_vercel_ui.sh production`.
- Preview: `./scripts/deploy_vercel_ui.sh preview`.
- Override API: `API_BASE_URL=https://api.example.com ./scripts/deploy_vercel_ui.sh production`.
