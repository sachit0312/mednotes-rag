from pathlib import Path

# paths
DATA_DIR = Path("data/books")
STORAGE_DIR = Path("storage")
LANCE_DIR = STORAGE_DIR / "lancedb"
CHUNK_JSONL = STORAGE_DIR / "chunks.jsonl"
BM25_PATH = STORAGE_DIR / "bm25.pkl"

# ingestion
CHUNK_TOKENS = 800     # ~800-token target
CHUNK_OVERLAP = 120

# retrieval
DENSE_TOPK = 150
BM25_TOPK = 150
FUSION_TOPK = 200      # union cap before rerank
RERANK_TOPK = 8        # final context set size

# models
EMBED_MODEL_NAME = "BAAI/bge-m3"
RERANK_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
OLLAMA_MODEL = "llama3.1:8b-instruct-q4_K_M"

# generation
MAX_TOKENS = 700

