import hashlib
from typing import Dict, List, Optional, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class Deduplicator:
    def __init__(self, near_duplicate_similarity: float = 0.92, model_name: str = 'all-MiniLM-L6-v2'):
        self.near_duplicate_similarity = near_duplicate_similarity
        self.model = SentenceTransformer(model_name)
        
        # In-memory stores for current run deduplication
        # hash -> raw_record_id
        self.seen_hashes: Dict[str, str] = {}
        
        # source -> List[Tuple[raw_record_id, embedding]]
        self.source_embeddings: Dict[str, List[Tuple[str, np.ndarray]]] = {}

    def get_hash(self, text: str) -> str:
        # Lowercase and whitespace-normalized
        normalized = " ".join(text.lower().split())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def check_duplicate(self, raw_record_id: str, text: str, source: str) -> Tuple[bool, Optional[str]]:
        """
        Returns (is_duplicate, duplicate_of_id)
        """
        if not text:
            return False, None
            
        # 1. Exact match check
        text_hash = self.get_hash(text)
        if text_hash in self.seen_hashes:
            return True, self.seen_hashes[text_hash]
            
        # 2. Near-duplicate check
        # Generate embedding
        embedding = self.model.encode([text])[0]
        
        if source not in self.source_embeddings:
            self.source_embeddings[source] = []
            
        source_records = self.source_embeddings[source]
        
        if source_records:
            # Extract just the embeddings to compute similarity
            existing_embeddings = np.array([emb for _, emb in source_records])
            similarities = cosine_similarity([embedding], existing_embeddings)[0]
            
            max_sim_idx = np.argmax(similarities)
            max_sim = similarities[max_sim_idx]
            
            if max_sim >= self.near_duplicate_similarity:
                return True, source_records[max_sim_idx][0]
                
        # Not a duplicate, add to stores
        self.seen_hashes[text_hash] = raw_record_id
        self.source_embeddings[source].append((raw_record_id, embedding))
        
        return False, None
