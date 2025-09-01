import argparse, json, pickle
from pathlib import Path
import fitz  # PyMuPDF
from tqdm import tqdm

from sentence_transformers import SentenceTransformer
from llama_index.core.node_parser import SentenceSplitter
import lancedb
from config import (
    DATA_DIR, LANCE_DIR, CHUNK_JSONL, BM25_PATH,
    CHUNK_TOKENS, CHUNK_OVERLAP, EMBED_MODEL_NAME,
)
from rank_bm25 import BM25Okapi


def extract_pages(pdf_path: Path):
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text")
        yield i, text


def chunk_pages(pages, book_id: str):
    splitter = SentenceSplitter(chunk_size=CHUNK_TOKENS, chunk_overlap=CHUNK_OVERLAP)
    for page_num, text in pages:
        if not text or not text.strip():
            continue
        chunks = splitter.split_text(text)
        for idx, chunk in enumerate(chunks):
            yield {
                "id": f"{book_id}:p{page_num}:c{idx}",
                "text": chunk,
                "meta": {
                    "book_id": book_id,
                    "page_start": page_num,
                    "page_end": page_num,  # single-page chunks in MVP
                },
            }


def build_dense_index(rows):
    LANCE_DIR.mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(str(LANCE_DIR))
    try:
        tbl = db.open_table("chunks")
    except Exception:
        tbl = None

    model = SentenceTransformer(EMBED_MODEL_NAME)
    batch = []
    for r in tqdm(rows, desc="Embedding + upsert"):
        emb = model.encode(r["text"], normalize_embeddings=True).tolist()
        batch.append({"id": r["id"], "embedding": emb, "text": r["text"], **r["meta"]})
        if len(batch) >= 128:
            if tbl is None:
                tbl = db.create_table("chunks", data=batch)
            else:
                tbl.add(batch)
            batch = []
    if batch:
        if tbl is None:
            tbl = db.create_table("chunks", data=batch)
        else:
            tbl.add(batch)


def build_bm25(rows):
    # Persist raw chunks for transparency
    with open(CHUNK_JSONL, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    # Tokenize very simply (whitespace + lower)
    corpus, ids = [], []
    for r in rows:
        tokens = r["text"].lower().split()
        corpus.append(tokens)
        ids.append(r["id"])
    bm25 = BM25Okapi(corpus)
    with open(BM25_PATH, "wb") as f:
        pickle.dump({"bm25": bm25, "ids": ids}, f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=str, required=True)
    ap.add_argument("--book_id", type=str, required=True)
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    assert pdf_path.exists(), f"Missing PDF: {pdf_path}"

    # 1) extract + chunk
    pages = list(extract_pages(pdf_path))
    rows = list(chunk_pages(pages, args.book_id))

    # For reuse across dense & bm25
    rows_for_dense = [dict(r) for r in rows]
    rows_for_bm25 = [dict(r) for r in rows]

    # 2) dense index
    build_dense_index(rows_for_dense)

    # 3) bm25
    build_bm25(rows_for_bm25)

    print(f"Ingested {len(rows)} chunks from {pdf_path}")


if __name__ == "__main__":
    main()
