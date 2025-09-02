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
RRF_K = 60             # Reciprocal Rank Fusion constant
MMR_LAMBDA = 0.7       # 0..1, higher = more relevance, lower = more diversity

# models
EMBED_MODEL_NAME = "BAAI/bge-m3"
RERANK_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
# LLM served by Ollama
# Upgraded local default: Qwen2.5 14B Instruct (q4 quantization)
# Pull via: `ollama pull qwen2.5:14b-instruct-q4_K_M`
OLLAMA_MODEL = "qwen2.5:14b-instruct-q4_K_M"

# generation
MAX_TOKENS = 700

# term expansion
ENABLE_TERM_EXPANSION = True
TERMS_MAP_PATH = STORAGE_DIR / "terms.yaml"
