from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import lancedb
from query import answer_qa, answer_note, answer_qa_stream, answer_note_stream
from config import LANCE_DIR

app = FastAPI(title="MedNotes RAG API", version="0.1.0")

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


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/books")
def list_books():
    try:
        db = lancedb.connect(str(LANCE_DIR))
        tbl = db.open_table("chunks")
    except Exception:
        return {"books": []}
    try:
        df = tbl.to_pandas()
        books = sorted([b for b in df["book_id"].dropna().unique().tolist() if b])
        return {"books": books}
    except Exception:
        return {"books": []}


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

# Mount static UI at the end so API routes take precedence
try:
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="ui")
except RuntimeError:
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
