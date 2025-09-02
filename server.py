from pathlib import Path
import os
import subprocess
import threading
import time
import requests
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import lancedb
from query import answer_qa, answer_note, answer_qa_stream, answer_note_stream
from config import LANCE_DIR, OLLAMA_MODEL, DATA_DIR
from typing import Dict, Any
from datetime import datetime

app = FastAPI(title="MedNotes RAG API", version="0.1.0")

# Provide a reasonable default admin key for local/dev unless overridden by env
os.environ.setdefault("ADMIN_KEY", "sachit loves astha")

# CORS for local dev / simple UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prefer production build if available, else fallback to raw /web
_dist = Path("web/dist")
WEB_DIR = _dist if _dist.exists() else Path("web")
WEB_DIR.mkdir(exist_ok=True)

# In-memory ingest jobs registry
INGEST_JOBS: Dict[str, Dict[str, Any]] = {}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/books")
def list_books():
    # List books solely from data/books/*.pdf
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        pdfs = sorted([p.stem for p in DATA_DIR.glob("*.pdf")])
        return {"books": pdfs}
    except Exception:
        return {"books": []}


# (Removed books_detail; keep a single source of truth via data/books)


def _book_exists(book_id: str) -> bool:
    try:
        db = lancedb.connect(str(LANCE_DIR))
        tbl = db.open_table("chunks")
        import pandas as pd  # type: ignore
        df = tbl.to_pandas(columns=["book_id"])  # reduce payload
        return any(df["book_id"] == book_id)
    except Exception:
        return False


def _update_job(book_id: str, **fields):
    job = INGEST_JOBS.get(book_id) or {"book_id": book_id}
    job.update(fields)
    job["updated_at"] = datetime.utcnow().isoformat()
    INGEST_JOBS[book_id] = job


def _run_ingest_job(book_id: str, pdf_path: Path):
    from ingest import extract_pages, chunk_pages, build_dense_index, build_bm25
    try:
        _update_job(book_id, status="ingesting", percent=10, message="saved_pdf", started_at=datetime.utcnow().isoformat())
        pages = list(extract_pages(pdf_path))
        _update_job(book_id, status="ingesting", percent=25, message="extracted_pages", pages=len(pages))
        rows = list(chunk_pages(pages, book_id))
        _update_job(book_id, status="ingesting", percent=45, message="chunked", chunks=len(rows))

        rows_for_dense = [dict(r) for r in rows]
        rows_for_bm25 = [dict(r) for r in rows]
        def cb_dense(frac: float):
            pct = 45 + int(30 * max(0.0, min(1.0, frac)))
            _update_job(book_id, status="ingesting", percent=pct, message="embedding")
        build_dense_index(rows_for_dense, progress_cb=cb_dense)
        _update_job(book_id, status="ingesting", percent=75, message="dense_index_built")
        def cb_bm25(frac: float):
            pct = 75 + int(20 * max(0.0, min(1.0, frac)))
            _update_job(book_id, status="ingesting", percent=pct, message="bm25")
        build_bm25(rows_for_bm25, progress_cb=cb_bm25)
        _update_job(book_id, status="complete", percent=100, message="done")
    except Exception as e:
        _update_job(book_id, status="error", percent=100, error=str(e))


@app.post("/api/ingest")
def api_ingest(request: Request, pdf: UploadFile = File(...), book_id: str = Form(...)):
    require_admin(request)
    if not book_id or not isinstance(book_id, str):
        raise HTTPException(status_code=400, detail="Missing 'book_id'")
    if _book_exists(book_id) or book_id in INGEST_JOBS:
        raise HTTPException(status_code=409, detail="book_id already exists or is being ingested")
    # Save uploaded file
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest = DATA_DIR / f"{book_id}.pdf"
    try:
        with dest.open("wb") as f:
            f.write(pdf.file.read())
    finally:
        try:
            pdf.file.close()
        except Exception:
            pass
    _update_job(book_id, status="queued", percent=5, message="uploaded", filename=str(dest))
    threading.Thread(target=_run_ingest_job, args=(book_id, dest), daemon=True).start()
    return {"status": "queued", "book_id": book_id}


@app.get("/api/ingest/jobs")
def api_ingest_jobs():
    # Only show active or failed jobs; hide completed to avoid clutter
    jobs = [j for j in INGEST_JOBS.values() if j.get("status") != "complete"]
    # most recent first
    jobs.sort(key=lambda j: j.get("updated_at", ""), reverse=True)
    return {"jobs": jobs}


@app.post("/api/qa")
def api_qa(payload: dict):
    q = (payload or {}).get("q")
    stream = bool((payload or {}).get("stream", False))
    books = (payload or {}).get("books")
    debug = bool((payload or {}).get("debug", False))
    if not q or not isinstance(q, str):
        raise HTTPException(status_code=400, detail="Missing 'q' string")
    # normalize books: allow comma-separated string or list
    if isinstance(books, str):
        books = [b.strip() for b in books.split(",") if b.strip()]
    if books and not isinstance(books, list):
        books = None
    try:
        if stream:
            gen = answer_qa_stream(q, books=books)
            return StreamingResponse(gen, media_type="text/plain; charset=utf-8")
        if debug:
            ans, rows = answer_qa(q, books=books, return_rows=True)
            ctx = [
                {
                    "id": r.get("id"),
                    "book_id": r.get("book_id"),
                    "page_start": r.get("page_start"),
                    "page_end": r.get("page_end"),
                    "score_dense": r.get("score_dense"),
                    "score_bm25": r.get("score_bm25"),
                    "score_rrf": r.get("score_rrf"),
                    "score_xenc": r.get("score_xenc"),
                    "dense": bool(r.get("contrib_dense")),
                    "bm25": bool(r.get("contrib_bm25")),
                }
                for r in rows
            ]
            return {"answer": ans, "contexts": ctx}
        ans = answer_qa(q, books=books)
        return {"answer": ans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/note")
def api_note(payload: dict):
    topic = (payload or {}).get("topic")
    template = (payload or {}).get("template") or "general"
    stream = bool((payload or {}).get("stream", False))
    books = (payload or {}).get("books")
    debug = bool((payload or {}).get("debug", False))
    if not topic or not isinstance(topic, str):
        raise HTTPException(status_code=400, detail="Missing 'topic' string")
    if isinstance(books, str):
        books = [b.strip() for b in books.split(",") if b.strip()]
    if books and not isinstance(books, list):
        books = None
    try:
        if stream:
            gen = answer_note_stream(topic, template=template, books=books)
            return StreamingResponse(gen, media_type="text/plain; charset=utf-8")
        if debug:
            ans, rows = answer_note(topic, template=template, books=books, return_rows=True)
            ctx = [
                {
                    "id": r.get("id"),
                    "book_id": r.get("book_id"),
                    "page_start": r.get("page_start"),
                    "page_end": r.get("page_end"),
                    "score_dense": r.get("score_dense"),
                    "score_bm25": r.get("score_bm25"),
                    "score_rrf": r.get("score_rrf"),
                    "score_xenc": r.get("score_xenc"),
                    "dense": bool(r.get("contrib_dense")),
                    "bm25": bool(r.get("contrib_bm25")),
                }
                for r in rows
            ]
            return {"card": ans, "contexts": ctx}
        ans = answer_note(topic, template=template, books=books)
        return {"card": ans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Ollama utilities and admin endpoints
@app.get("/api/ollama/health")
def ollama_health():
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        r = requests.get(f"{base}/api/version", timeout=5)
        r.raise_for_status()
        ver = r.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama unreachable: {e}")
    current_model = os.getenv("OLLAMA_MODEL", OLLAMA_MODEL)
    return {"base": base, "version": ver, "current_model": current_model}


@app.get("/api/ollama/models")
def ollama_models():
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        r = requests.get(f"{base}/api/tags", timeout=10)
        r.raise_for_status()
        data = r.json()
        models = [m.get("name") for m in data.get("models", []) if m.get("name")]
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Failed to list models: {e}")


@app.post("/api/ollama/set_model")
def set_ollama_model(request: Request, payload: dict):
    require_admin(request)
    model = (payload or {}).get("model")
    if not model or not isinstance(model, str):
        raise HTTPException(status_code=400, detail="Missing 'model' string")
    os.environ["OLLAMA_MODEL"] = model
    return {"status": "ok", "model": model}


def _background_restart_api():
    try:
        subprocess.Popen(["bash", "scripts/restart_backend.sh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


@app.post("/api/admin/restart_api")
def admin_restart_api(request: Request):
    require_admin(request)
    threading.Thread(target=_background_restart_api, daemon=True).start()
    return {"status": "restarting"}


def _background_restart_ollama():
    try:
        subprocess.Popen(["bash", "scripts/restart_ollama.sh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def require_admin(request: Request):
    expected = os.getenv("ADMIN_KEY")
    provided = request.headers.get("x-admin-key") or request.headers.get("X-Admin-Key")
    if not expected:
        raise HTTPException(status_code=503, detail="ADMIN_KEY not configured on server")
    if provided != expected:
        raise HTTPException(status_code=403, detail="Forbidden: invalid admin key")


@app.post("/api/admin/restart_ollama")
def admin_restart_ollama(request: Request):
    require_admin(request)
    threading.Thread(target=_background_restart_ollama, daemon=True).start()
    return {"status": "restarting"}


@app.get("/api/admin/validate")
def admin_validate(request: Request):
    require_admin(request)
    return {"status": "ok"}


@app.get("/api/ngrok/status")
def ngrok_status():
    api = os.getenv("NGROK_API_URL", "http://127.0.0.1:4040/api/tunnels")
    configured_domain = os.getenv("NGROK_DOMAIN")
    configured_url = None
    if configured_domain:
        configured_url = configured_domain if configured_domain.startswith("http") else f"https://{configured_domain}"
    out = {"running": False, "url": None, "configured": bool(configured_domain), "configured_url": configured_url, "error": None}
    try:
        r = requests.get(api, timeout=3)
        r.raise_for_status()
        data = r.json()
        tunnels = data.get("tunnels", [])
        https = next((t.get("public_url") for t in tunnels if t.get("proto") == "https"), None)
        if https:
            out.update({"running": True, "url": https})
        return out
    except Exception as e:
        out["error"] = f"unreachable: {e}"
        # Return 200 with running False so UI can show configured domain gracefully
        return out


def _background_restart_ngrok():
    try:
        subprocess.Popen(["bash", "scripts/restart_ngrok.sh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


@app.post("/api/admin/restart_ngrok")
def admin_restart_ngrok(request: Request):
    require_admin(request)
    threading.Thread(target=_background_restart_ngrok, daemon=True).start()
    return {"status": "restarting"}

# Mount static UI after ALL API routes to avoid intercepting /api/*
try:
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="ui")
except RuntimeError:
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
