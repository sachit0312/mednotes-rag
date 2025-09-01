from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from query import answer_qa, answer_note

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


@app.post("/api/qa")
def api_qa(payload: dict):
    q = (payload or {}).get("q")
    if not q or not isinstance(q, str):
        raise HTTPException(status_code=400, detail="Missing 'q' string")
    try:
        ans = answer_qa(q)
        return {"answer": ans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/note")
def api_note(payload: dict):
    topic = (payload or {}).get("topic")
    if not topic or not isinstance(topic, str):
        raise HTTPException(status_code=400, detail="Missing 'topic' string")
    try:
        ans = answer_note(topic)
        return {"card": ans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static UI at the end so API routes take precedence
try:
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="ui")
except RuntimeError:
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
