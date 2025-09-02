import argparse, json, pickle, math, os
from typing import List, Dict, Optional, Iterable
import requests

import lancedb
from sentence_transformers import SentenceTransformer
from FlagEmbedding import FlagReranker
import numpy as np
import yaml

from config import (
    LANCE_DIR, BM25_PATH, EMBED_MODEL_NAME, RERANK_MODEL_NAME,
    DENSE_TOPK, BM25_TOPK, FUSION_TOPK, RERANK_TOPK, OLLAMA_MODEL, MAX_TOKENS, RRF_K,
    MMR_LAMBDA, ENABLE_TERM_EXPANSION, TERMS_MAP_PATH,
)
from templates import (
    SYSTEM_BASE,
    QA_TEMPLATE,
    NOTE_CARD,
    DISEASE_1PAGER,
    DRUG_CARD,
    PROCEDURE,
)

# Lazy global caches for models and term map
_EMBED_MODEL: Optional[SentenceTransformer] = None
_RERANKER: Optional[FlagReranker] = None
_TERMS_MAP: Optional[Dict[str, List[str]]] = None


def get_embed_model() -> SentenceTransformer:
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        _EMBED_MODEL = SentenceTransformer(EMBED_MODEL_NAME)
    return _EMBED_MODEL


def get_reranker() -> FlagReranker:
    global _RERANKER
    if _RERANKER is None:
        _RERANKER = FlagReranker(RERANK_MODEL_NAME, use_fp16=True)
    return _RERANKER


def load_terms_map() -> Dict[str, List[str]]:
    global _TERMS_MAP
    if _TERMS_MAP is None:
        try:
            with open(TERMS_MAP_PATH, "r") as f:
                data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            data = {}
        # normalize keys
        _TERMS_MAP = {str(k).lower(): [str(v).lower() for v in (vs or [])] for k, vs in data.items()}
    return _TERMS_MAP


def expanded_queries_for(q: str) -> List[str]:
    if not ENABLE_TERM_EXPANSION:
        return [q]
    ql = q.lower()
    mp = load_terms_map()
    expansions: List[str] = []
    for key, syns in mp.items():
        if key in ql:
            expansions.extend(syns[:2])
    expansions = expansions[:6]
    if not expansions:
        return [q]
    variants = [q]
    chunk: List[str] = []
    for i, term in enumerate(expansions):
        chunk.append(term)
        if (i + 1) % 2 == 0 or i == len(expansions) - 1:
            variants.append(f"{q} {', '.join(chunk)}")
            chunk = []
        if len(variants) >= 3:
            break
    return variants


def dense_search(query: str, books: Optional[List[str]] = None) -> List[Dict]:
    db = lancedb.connect(str(LANCE_DIR))
    tbl = db.open_table("chunks")
    embed = get_embed_model()
    qvec = embed.encode(query, normalize_embeddings=True).tolist()
    # lancedb similarity search
    rows = tbl.search(qvec).limit(DENSE_TOPK).to_list()
    for r in rows:
        r["score_dense"] = r.get("_distance", 0.0)
        r["contrib_dense"] = True
    if books:
        bset = set([b.strip() for b in books if b and b.strip()])
        rows = [r for r in rows if r.get("book_id") in bset]
    return rows


def bm25_search(query: str, books: Optional[List[str]] = None) -> List[Dict]:
    with open(BM25_PATH, "rb") as f:
        obj = pickle.load(f)
    bm25, ids = obj["bm25"], obj["ids"]
    variants = expanded_queries_for(query)
    db = lancedb.connect(str(LANCE_DIR))
    tbl = db.open_table("chunks")
    import pandas as pd  # type: ignore
    df = tbl.to_pandas()
    out_map: Dict[str, Dict] = {}
    for vq in variants:
        scores = bm25.get_scores(vq.lower().split())
        top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:BM25_TOPK]
        id_set = {ids[i] for i in top_idx}
        sub = df[df["id"].isin(list(id_set))].to_dict(orient="records")
        bm25_map = {ids[i]: scores[i] for i in top_idx}
        for r in sub:
            if books:
                bset = set([b.strip() for b in books if b and b.strip()])
                if r.get("book_id") not in bset:
                    continue
            rid = r["id"]
            score = bm25_map.get(rid, 0.0)
            cur = out_map.get(rid)
            if cur is None or score > cur.get("score_bm25", 0.0):
                rr = dict(r)
                rr["score_bm25"] = score
                rr["contrib_bm25"] = True
                out_map[rid] = rr
    return list(out_map.values())


def rrf_fuse(dense_rows: List[Dict], bm25_rows: List[Dict], k: int = RRF_K, limit: int = FUSION_TOPK) -> List[Dict]:
    # Compute 1-based ranks within each list
    r_dense = {r["id"]: i + 1 for i, r in enumerate(dense_rows)}
    r_bm25 = {r["id"]: i + 1 for i, r in enumerate(bm25_rows)}

    # Prefer dense row object if present; else bm25 row
    row_map: Dict[str, Dict] = {r["id"]: r for r in bm25_rows}
    row_map.update({r["id"]: r for r in dense_rows})

    scores: Dict[str, float] = {}
    for rid in set(list(r_dense.keys()) + list(r_bm25.keys())):
        s = 0.0
        if rid in r_dense:
            s += 1.0 / (k + r_dense[rid])
            row_map[rid]["contrib_dense"] = True
        if rid in r_bm25:
            s += 1.0 / (k + r_bm25[rid])
            row_map[rid]["contrib_bm25"] = True
        scores[rid] = s

    fused_ids = sorted(scores.keys(), key=lambda rid: scores[rid], reverse=True)[:limit]
    fused = [row_map[rid] for rid in fused_ids]
    for r in fused:
        r["score_rrf"] = scores[r["id"]]
    return fused


def hybrid_candidates(query: str, books: Optional[List[str]] = None) -> List[Dict]:
    a = dense_search(query, books=books)
    b = bm25_search(query, books=books)
    return rrf_fuse(a, b)


def rerank(query: str, cands: List[Dict]) -> List[Dict]:
    rr = get_reranker()
    pairs = [[query, r["text"]] for r in cands]
    scores = rr.compute_score(pairs, batch_size=16)
    for r, s in zip(cands, scores):
        r["score_xenc"] = float(s)
    cands.sort(key=lambda r: r["score_xenc"], reverse=True)
    return cands[:RERANK_TOPK]


def mmr_select(cands: List[Dict], k: Optional[int] = None, lam: float = MMR_LAMBDA) -> List[Dict]:
    if k is None:
        k = min(RERANK_TOPK, len(cands))
    if not cands or k <= 1 or lam is None:
        return cands[:k]
    # Require embeddings; if any missing, skip MMR
    embs = []
    for r in cands:
        e = r.get("embedding")
        if e is None:
            return cands[:k]
        embs.append(np.array(e, dtype=np.float32))
    embs = np.vstack(embs)
    norms = np.linalg.norm(embs, axis=1, keepdims=True) + 1e-8
    embs_n = embs / norms
    sim = embs_n @ embs_n.T
    rel = np.array([r.get("score_xenc", 0.0) for r in cands], dtype=np.float32)
    if rel.max() > rel.min():
        rel = (rel - rel.min()) / (rel.max() - rel.min())
    selected = []
    candidates = list(range(len(cands)))
    first = int(np.argmax(rel))
    selected.append(first)
    candidates.remove(first)
    while len(selected) < k and candidates:
        best_idx, best_val = None, -1e9
        for i in candidates:
            max_sim = sim[i, selected].max() if selected else 0.0
            score = lam * rel[i] - (1 - lam) * max_sim
            if score > best_val:
                best_val, best_idx = score, i
        selected.append(best_idx)
        candidates.remove(best_idx)
    return [cands[i] for i in selected]


def pack_context(rows: List[Dict]) -> str:
    blocks = []
    for r in rows:
        book = r.get("book_id")
        p0, p1 = r.get("page_start"), r.get("page_end")
        header = f"[source {book}:{p0}-{p1}]"
        blocks.append(f"{header}\n{r['text']}")
    return "\n\n".join(blocks)


def call_ollama(system: str, user: str) -> str:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    body = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {"num_predict": MAX_TOKENS},
        "stream": False,
    }
    r = requests.post(f"{base}/api/chat", json=body, timeout=600)
    r.raise_for_status()
    return r.json()["message"]["content"]


def call_ollama_stream(system: str, user: str) -> Iterable[str]:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    body = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {"num_predict": MAX_TOKENS},
        "stream": True,
    }
    with requests.post(f"{base}/api/chat", json=body, stream=True, timeout=600) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("done"):
                break
            msg = obj.get("message", {})
            chunk = msg.get("content", "")
            if chunk:
                yield chunk


def answer_qa(q: str, books: Optional[List[str]] = None, return_rows: bool = False):
    cands = hybrid_candidates(q, books=books)
    topk = rerank(q, cands)
    topk = mmr_select(topk)
    context = pack_context(topk)
    prompt = QA_TEMPLATE.format(question=q, context=context)
    ans = call_ollama(SYSTEM_BASE, prompt)
    return (ans, topk) if return_rows else ans


def answer_qa_stream(q: str, books: Optional[List[str]] = None) -> Iterable[str]:
    cands = hybrid_candidates(q, books=books)
    topk = rerank(q, cands)
    topk = mmr_select(topk)
    context = pack_context(topk)
    prompt = QA_TEMPLATE.format(question=q, context=context)
    return call_ollama_stream(SYSTEM_BASE, prompt)


def answer_note(topic: str, template: str = "general", books: Optional[List[str]] = None, return_rows: bool = False):
    # retrieve a bit broader for notes (add key terms expansion)
    seed_q = (
        f"{topic} definition overview key concepts mechanism pathophysiology clinical features diagnostics criteria "
        f"staging severity management treatment dosing contraindications complications monitoring guidelines differentials red flags scoring"
    )
    cands = hybrid_candidates(seed_q, books=books)
    topk = rerank(seed_q, cands)
    topk = mmr_select(topk)
    context = pack_context(topk)

    t = (template or "general").lower()
    if t == "disease":
        tmpl = DISEASE_1PAGER
    elif t == "drug":
        tmpl = DRUG_CARD
    elif t in ("procedure", "algorithm", "algo"):
        tmpl = PROCEDURE
    else:
        tmpl = NOTE_CARD

    prompt = tmpl.format(topic=topic, context=context)
    ans = call_ollama(SYSTEM_BASE, prompt)
    return (ans, topk) if return_rows else ans


def answer_note_stream(topic: str, template: str = "general", books: Optional[List[str]] = None) -> Iterable[str]:
    seed_q = (
        f"{topic} definition overview key concepts mechanism pathophysiology clinical features diagnostics criteria "
        f"staging severity management treatment dosing contraindications complications monitoring guidelines differentials red flags scoring"
    )
    cands = hybrid_candidates(seed_q, books=books)
    topk = rerank(seed_q, cands)
    topk = mmr_select(topk)
    context = pack_context(topk)

    t = (template or "general").lower()
    if t == "disease":
        tmpl = DISEASE_1PAGER
    elif t == "drug":
        tmpl = DRUG_CARD
    elif t in ("procedure", "algorithm", "algo"):
        tmpl = PROCEDURE
    else:
        tmpl = NOTE_CARD

    prompt = tmpl.format(topic=topic, context=context)
    return call_ollama_stream(SYSTEM_BASE, prompt)


def main():
    # Compatibility layer: support top-level --mode, --q, --topic
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--mode", choices=["qa", "note"], help=argparse.SUPPRESS)
    pre.add_argument("--q", help=argparse.SUPPRESS)
    pre.add_argument("--topic", help=argparse.SUPPRESS)
    pre.add_argument("--template", choices=["general", "disease", "drug", "procedure"], help=argparse.SUPPRESS)
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
            print(answer_note(pre_args.topic, template=pre_args.template or "general"))
            return

    # Default subcommand behavior
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)

    qa = sub.add_parser("qa")
    qa.add_argument("--q", required=True)

    note = sub.add_parser("note")
    note.add_argument("--topic", required=True)
    note.add_argument("--template", choices=["general", "disease", "drug", "procedure"], default="general")

    args = ap.parse_args(remaining)

    if args.mode == "qa":
        print(answer_qa(args.q))
    else:
        print(answer_note(args.topic, template=args.template))


if __name__ == "__main__":
    main()
