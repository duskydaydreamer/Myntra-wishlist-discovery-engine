import os
import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROMA_PATH = os.environ.get("CHROMA_PATH", os.path.join(BASE_DIR, "data", "chroma"))

# Lazy loaded models - initialized on first request, not at startup
_embedding_model = None
_chroma_client = None
_collection = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            _embedding_model = SentenceTransformer('all-MiniLM-L6-v2', local_files_only=True)
        except Exception:
            _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model

def get_collection():
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = _chroma_client.get_or_create_collection("observation_embeddings")
    return _collection

def retrieve_semantic_evidence(query_text: str, eligible_ids: set, top_k: int = 20) -> list:
    """
    Given a query text and a set of eligible observation IDs (from SQLite filters),
    retrieve the top_k most semantically similar IDs from ChromaDB.
    """
    collection = get_collection()

    # 1. Embed query
    query_embedding = get_embedding_model().encode(query_text).tolist()
    
    # 2. Query ChromaDB for a large number of results (since we need to intersect with eligible_ids)
    max_results = min(10000, collection.count())
    if max_results == 0:
        return []
        
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=max_results
    )
    
    if not results or not results["ids"] or not results["ids"][0]:
        return []
        
    # 3. Filter against eligible_ids and keep order (which is sorted by distance/similarity)
    retrieved_ids = results["ids"][0]
    
    filtered_ids = []
    for obs_id in retrieved_ids:
        if obs_id in eligible_ids:
            filtered_ids.append(obs_id)
            if len(filtered_ids) >= top_k:
                break
                
    return filtered_ids
