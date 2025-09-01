import argparse, json, pickle, math
from typing import List, Dict
import requests

import lancedb
from sentence_transformers import SentenceTransformer
from FlagEmbedding import FlagReranker

from config import (
    LANCE_DIR, BM25_PATH, EMBED_MODEL_NAME, RERANK_MODEL_NAME,
    DENSE_TOPK, BM25_TOPK, FUSION_TOPK, RERANK_TOPK, OLLAMA_MODEL, MAX_TOKENS,
)
from templates import SYSTEM_BASE, QA_TEMPLATE, NOTE_CARD


def dense_search(query: str) -> List[Dict]:
    db = lancedb.connect(str(LANCE_DIR))
    tbl = db.open_table("chunks")
    embed = SentenceTransformer(EMBED_MODEL_NAME)
    qvec = embed.encode(query, normalize_embeddings=True).tolist()
    # lancedb similarity search
    rows = tbl.search(qvec).limit(DENSE_TOPK).to_list()
    for r in rows:
        r["score_dense"] = r.get("_distance", 0.0)
    return rows


def bm25_search(query: str) -> List[Dict]:
    with open(BM25_PATH, "rb") as f:
        obj = pickle.load(f)
    bm25, ids = obj["bm25"], obj["ids"]
    scores = bm25.get_scores(query.lower().split())
    top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:BM25_TOPK]
    # reconstruct minimal rows from LanceDB to get text/meta
    db = lancedb.connect(str(LANCE_DIR))
    tbl = db.open_table("chunks")
    id_set = [ids[i] for i in top_idx]
    # fallback: small table, load to pandas and filter by ids
    import pandas as pd  # type: ignore
    df = tbl.to_pandas()
    rows = df[df["id"].isin(id_set)].to_dict(orient="records")
    bm25_map = {ids[i]: scores[i] for i in top_idx}
    for r in rows:
        r["score_bm25"] = bm25_map.get(r["id"], 0.0)
    return rows


def hybrid_candidates(query: str) -> List[Dict]:
    a = dense_search(query)
    b = bm25_search(query)
    # union by id
    seen, fused = set(), []
    for row in sorted(a + b, key=lambda r: (r.get("score_bm25", 0.0) + (1 - r.get("_distance", 0.0))), reverse=True):
        rid = row["id"]
        if rid in seen:
            continue
        fused.append(row)
        seen.add(rid)
        if len(fused) >= FUSION_TOPK:
            break
    return fused


def rerank(query: str, cands: List[Dict]) -> List[Dict]:
    rr = FlagReranker(RERANK_MODEL_NAME, use_fp16=True)
    pairs = [[query, r["text"]] for r in cands]
    scores = rr.compute_score(pairs, batch_size=16)
    for r, s in zip(cands, scores):
        r["score_xenc"] = float(s)
    cands.sort(key=lambda r: r["score_xenc"], reverse=True)
    return cands[:RERANK_TOPK]


def pack_context(rows: List[Dict]) -> str:
    blocks = []
    for r in rows:
        book = r.get("book_id")
        p0, p1 = r.get("page_start"), r.get("page_end")
        header = f"[source {book}:{p0}-{p1}]"
        blocks.append(f"{header}\n{r['text']}")
    return "\n\n".join(blocks)


def call_ollama(system: str, user: str) -> str:
    body = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {"num_predict": MAX_TOKENS},
        "stream": False,
    }
    r = requests.post("http://localhost:11434/api/chat", json=body, timeout=600)
    r.raise_for_status()
    return r.json()["message"]["content"]


def answer_qa(q: str) -> str:
    cands = hybrid_candidates(q)
    topk = rerank(q, cands)
    context = pack_context(topk)
    prompt = QA_TEMPLATE.format(question=q, context=context)
    return call_ollama(SYSTEM_BASE, prompt)


def answer_note(topic: str) -> str:
    # retrieve a bit broader for notes (add key terms expansion)
    seed_q = (
        f"{topic} definition overview key concepts mechanism pathophysiology clinical features diagnostics criteria "
        f"staging severity management treatment dosing contraindications complications monitoring guidelines"
    )
    cands = hybrid_candidates(seed_q)
    topk = rerank(seed_q, cands)
    context = pack_context(topk)
    prompt = NOTE_CARD.format(topic=topic, context=context)
    return call_ollama(SYSTEM_BASE, prompt)


def main():
    # Compatibility layer: support top-level --mode, --q, --topic
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--mode", choices=["qa", "note"], help=argparse.SUPPRESS)
    pre.add_argument("--q", help=argparse.SUPPRESS)
    pre.add_argument("--topic", help=argparse.SUPPRESS)
    pre_args, remaining = pre.parse_known_args()

    if pre_args.mode:
        if pre_args.mode == "qa":
            if not pre_args.q:
                raise SystemExit("--q is required for --mode qa")
            print(answer_qa(pre_args.q))
            return
        else:
            if not pre_args.topic:
                raise SystemExit("--topic is required for --mode note")
            print(answer_note(pre_args.topic))
            return

    # Default subcommand behavior
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)

    qa = sub.add_parser("qa")
    qa.add_argument("--q", required=True)

    note = sub.add_parser("note")
    note.add_argument("--topic", required=True)

    args = ap.parse_args(remaining)

    if args.mode == "qa":
        print(answer_qa(args.q))
    else:
        print(answer_note(args.topic))


if __name__ == "__main__":
    main()
