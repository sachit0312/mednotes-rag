MedNotes RAG
============

Small, fast, local Q&A + note-maker over your book using hybrid retrieval (dense + BM25), cross-encoder reranking, and a small local LLM via Ollama. Ships with a FastAPI backend and a React (Vite) UI.

Project Structure
-----------------
- `ingest.py`: PDF → pages → chunks → embeddings (LanceDB) + BM25.
- `query.py`: Hybrid retrieve (dense+bm25) → RRF fuse → rerank → call Ollama (streaming supported).
- `templates.py`: System + QA + general `NOTE_CARD` templates.
- `config.py`: Paths and knobs (chunking, topK, model names).
- `server.py`: FastAPI (`/api/qa`, `/api/note`, `/api/health`) and static serving of `web/dist`.
- `web/`: React (Vite) UI (dev server proxies `/api` to FastAPI).
- `storage/`: LanceDB + BM25 artifacts; `data/books/`: your PDFs.

Quick Start (Dev)
-----------------
1) Python deps
- `python3 -m venv .venv && source .venv/bin/activate`
- `pip install -r requirements.txt`

2) Ollama
- `brew install ollama`
- `ollama serve &`
- Recommended model (configured by default): `ollama pull qwen2.5:7b-instruct`
  - Alternative: `ollama pull llama3.1:8b-instruct` (update `config.py: OLLAMA_MODEL`).

3) Ingest a PDF
- Put a file under `data/books/book1.pdf` (or pass a direct path).
- `python ingest.py --pdf data/books/book1.pdf --book_id MyBook-1e`

4) Run API and UI
- API: `.venv/bin/uvicorn server:app --reload --port 8000`
- UI: `cd web && npm install && npm run dev` → open http://localhost:5173

Production-style UI
-------------------
- `cd web && npm run build` then open http://localhost:8000 (served from `web/dist`).

API Endpoints
-------------
- `POST /api/qa` body `{ "q": "..." }` → `{ "answer": "..." }`.
- `POST /api/note` body `{ "topic": "...", "template": "disease|drug|procedure" }` → `{ "card": "..." }`.
- Optional params: `stream: true` to stream plain text; `debug: true` to include selected contexts (non-streamed only).
- `GET /api/health` → `{ "status": "ok" }`.

Key Config (config.py)
----------------------
- Ingestion: `CHUNK_TOKENS`, `CHUNK_OVERLAP`.
- Retrieval: `DENSE_TOPK`, `BM25_TOPK`, `FUSION_TOPK`, `RERANK_TOPK`, `RRF_K`.
- Models: `EMBED_MODEL_NAME`, `RERANK_MODEL_NAME`, `OLLAMA_MODEL` (default: Qwen2.5 7B Instruct).
- Generation: `MAX_TOKENS`.

 Contributor Notes
-----------------
- Retrieval fusion is simple; consider RRF/weights.
- Reranker batch size and FP16 via `FlagReranker` in `query.py`.
- Prompts in `templates.py` — keep citations strict. Specialized med-note templates added: Disease 1‑pager, Drug card, Procedure, with compression and retrieval‑ready rules.
- Retrieval now uses RRF; optional book filter via API/UI; server supports streaming responses.
- UI lives under `web/src` (Vite + React + TS). Dev server proxies `/api`.

Troubleshooting
---------------
- Ollama not running: `brew install ollama && ollama serve & && ollama pull ...`.
- LanceDB FTS errors: we Pandas-filter for BM25 hits (no FTS needed).
- SSL warnings on macOS builds are harmless for local use.

Contributors and agents: please read this README end‑to‑end before making changes. See also AGENTS.md for workflow notes.

Docker Compose (Deploy)
-----------------------
CPU‑only deployment using Docker Compose. No GPU required (slower than local GPU but works).

1) Provision a small VPS (e.g., 4 vCPU / 8–16 GB RAM). Install Docker and Compose.

2) Clone repo and build:

```bash
git clone https://github.com/you/mednotes-rag.git && cd mednotes-rag
docker compose build
```

3) Start services:

```bash
docker compose up -d
# Pull the model into Ollama
docker compose exec ollama ollama pull qwen2.5:7b-instruct
```

4) Ingest PDFs (copy your PDFs to `data/books/` first, then):

```bash
docker compose exec api python ingest.py --pdf data/books/book1.pdf --book_id Harrison-20e
```

5) Open the app: `http://<your-server-ip>:8000`

Optional: HTTPS with Caddy
--------------------------
Edit `Caddyfile` and replace `YOUR_DOMAIN` with your domain. Then enable the proxy service in `docker-compose.yml` (uncomment `caddy` service) and point DNS to the VPS. Caddy will issue TLS automatically.

Environment knobs
-----------------

Split Deploy (Vercel UI + Local ngrok API)
------------------------------------------
Keep API + Ollama on your laptop; deploy only the UI.

1) Run locally:
- `ollama serve & && ollama pull qwen2.5:7b-instruct`
- `.venv/bin/uvicorn server:app --reload --port 8000`
- `http://localhost:8000/api/health` should return ok.

2) Expose via ngrok:
- `brew install ngrok && ngrok config add-authtoken <TOKEN>`
- `ngrok http 8000` → copy the HTTPS forwarding URL.

3) Deploy UI to Vercel:
- Project root: `web`, build: `npm run build`, output: `web/dist`.
- Set env var `VITE_API_BASE_URL` to your ngrok URL.
- Deploy. The UI will call `${VITE_API_BASE_URL}/api/*`.

Helper script (optional):
- `./scripts/update_vercel_api_base.sh production` will read the current ngrok URL from `http://127.0.0.1:4040/api/tunnels`, update Vercel env `VITE_API_BASE_URL`, and deploy.
  - Prereqs: Vercel CLI logged in and linked in `web/`, ngrok running.
- `OLLAMA_BASE_URL` (set in compose): where API reaches Ollama. Defaults to `http://localhost:11434` for local dev; in Docker it points to `http://ollama:11434`.
- All other knobs live in `config.py`.
