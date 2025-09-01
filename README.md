MedNotes RAG
============

Small, fast, local Q&A + note-maker over your book using hybrid retrieval (dense + BM25), cross-encoder reranking, and a small local LLM via Ollama. Ships with a FastAPI backend and a React (Vite) UI.

Project Structure
-----------------
- `ingest.py`: PDF → pages → chunks → embeddings (LanceDB) + BM25.
- `query.py`: Hybrid retrieve (dense+bm25) → rerank → call Ollama.
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
- `ollama pull llama3.1:8b-instruct-q4_K_M`

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
- `POST /api/note` body `{ "topic": "..." }` → `{ "card": "..." }`.
- `GET /api/health` → `{ "status": "ok" }`.

Key Config (config.py)
----------------------
- Ingestion: `CHUNK_TOKENS`, `CHUNK_OVERLAP`.
- Retrieval: `DENSE_TOPK`, `BM25_TOPK`, `FUSION_TOPK`, `RERANK_TOPK`.
- Models: `EMBED_MODEL_NAME`, `RERANK_MODEL_NAME`, `OLLAMA_MODEL`.
- Generation: `MAX_TOKENS`.

Contributor Notes
-----------------
- Retrieval fusion is simple; consider RRF/weights.
- Reranker batch size and FP16 via `FlagReranker` in `query.py`.
- Prompts in `templates.py` — keep citations strict.
- UI lives under `web/src` (Vite + React + TS). Dev server proxies `/api`.

Troubleshooting
---------------
- Ollama not running: `brew install ollama && ollama serve & && ollama pull ...`.
- LanceDB FTS errors: we Pandas-filter for BM25 hits (no FTS needed).
- SSL warnings on macOS builds are harmless for local use.

See also: `README_quickstart.md` for the very short TL;DR.

