# MedNotes RAG MVP (local)

1. Install Ollama and pull the model:
   ```bash
   brew install ollama
   ollama serve &
   ollama pull llama3.1:8b-instruct-q4_K_M
   ```

2. Install Python deps:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Add your PDF to `data/books/`.
4. Ingest:

   ```bash
   python ingest.py --pdf data/books/book1.pdf --book_id Harrison-20e
   ```
5. Ask questions:

   ```bash
   python query.py --mode qa --q "First-line treatment for acute asthma exacerbation?"
   ```
6. Generate notes (general card):

   ```bash
   python query.py --mode note --topic "Asthma"
   ```

## FastAPI + UI

1) Run the API server:

```bash
.venv/bin/uvicorn server:app --reload --port 8000
```

2) React Dev UI (Vite):

```bash
cd web
npm install
npm run dev
```

- Open http://localhost:5173 (Vite proxies /api to http://localhost:8000)

3) Build static UI and serve via FastAPI (optional):

```bash
cd web
npm run build
```

- Then open http://localhost:8000/ (FastAPI serves from `web/dist`)

4) API endpoints:

- POST `/api/qa` with JSON `{ "q": "..." }`
- POST `/api/note` with JSON `{ "topic": "..." }`

## Tips

* If citations look weak, increase `RERANK_TOPK` to 10–12.
* Add more books by re-running `ingest.py` with new `--book_id`s; the table will append.
* Use unique `book_id`s (short slugs) so citations are readable.
* For scanned PDFs, consider OCR first (e.g., `ocrmypdf`) before ingesting.
