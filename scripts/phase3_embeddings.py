import sqlite3
import json
import chromadb
from sentence_transformers import SentenceTransformer
import sys
import hashlib

def main():
    print("Loading model...")
    model_name = "all-MiniLM-L6-v2"
    model = SentenceTransformer(model_name)
    
    print("Connecting to DB and Chroma...")
    conn = sqlite3.connect("data/discovery_pulse.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    chroma_client = chromadb.PersistentClient(path="data/chroma")
    
    col_evidence = chroma_client.get_or_create_collection(
        name="evidence_quote_embeddings",
        metadata={"hnsw:space": "cosine"}
    )
    col_observation = chroma_client.get_or_create_collection(
        name="observation_embeddings",
        metadata={"hnsw:space": "cosine"}
    )
    
    print("Fetching valid canonical observations...")
    cursor.execute("SELECT * FROM observations")
    observations = cursor.fetchall()
    print(f"Found {len(observations)} observations.")
    
    existing_evidence = set(col_evidence.get()["ids"])
    existing_observation = set(col_observation.get()["ids"])
    
    evidence_docs = []
    evidence_ids = []
    evidence_metas = []
    
    observation_docs = []
    observation_ids = []
    observation_metas = []
    
    for row in observations:
        obs_dict = dict(row)
        obs_id = obs_dict["observation_id"]
        
        # 1. evidence_quote
        eq = obs_dict["evidence_quote"]
        if eq and obs_id not in existing_evidence:
            eq_hash = hashlib.sha256(eq.encode()).hexdigest()
            evidence_docs.append(eq)
            evidence_ids.append(obs_id)
            evidence_metas.append({
                "observation_id": obs_id,
                "source_record_id": obs_dict["source_record_id"],
                "input_hash": eq_hash,
                "model_version": model_name
            })
            
        # 2. observation
        if obs_id not in existing_observation:
            parts = [eq]
            for f in ["uncertainty", "information_needed", "workaround"]:
                val = obs_dict.get(f)
                if val and val != "unknown":
                    parts.append(val)
            
            obs_text = " ".join(parts)
            obs_hash = hashlib.sha256(obs_text.encode()).hexdigest()
            
            observation_docs.append(obs_text)
            observation_ids.append(obs_id)
            observation_metas.append({
                "observation_id": obs_id,
                "source_record_id": obs_dict["source_record_id"],
                "input_hash": obs_hash,
                "model_version": model_name
            })
            
    print(f"Need to embed {len(evidence_docs)} evidence quotes and {len(observation_docs)} observations.")
    
    batch_size = 32
    # Embed and add in batches
    if evidence_docs:
        print("Embedding evidence quotes...")
        for i in range(0, len(evidence_docs), batch_size):
            b_docs = evidence_docs[i:i+batch_size]
            b_ids = evidence_ids[i:i+batch_size]
            b_metas = evidence_metas[i:i+batch_size]
            
            b_embs = model.encode(b_docs).tolist()
            col_evidence.add(
                ids=b_ids,
                embeddings=b_embs,
                documents=b_docs,
                metadatas=b_metas
            )
            print(f"  Added {i+len(b_docs)}/{len(evidence_docs)} evidence embeddings")
            
    if observation_docs:
        print("Embedding observation texts...")
        for i in range(0, len(observation_docs), batch_size):
            b_docs = observation_docs[i:i+batch_size]
            b_ids = observation_ids[i:i+batch_size]
            b_metas = observation_metas[i:i+batch_size]
            
            b_embs = model.encode(b_docs).tolist()
            col_observation.add(
                ids=b_ids,
                embeddings=b_embs,
                documents=b_docs,
                metadatas=b_metas
            )
            print(f"  Added {i+len(b_docs)}/{len(observation_docs)} observation embeddings")
            
    print("Done generating embeddings.")
    
    # Sanity Check
    print("Performing Sanity Check...")
    queries = [
        "sizing / fit uncertainty",
        "quality concern",
        "comparison shopping",
        "review / trust uncertainty",
        "saved-product context / forgetting",
        "external-platform research"
    ]
    
    for q in queries:
        print(f"\nQUERY: '{q}'")
        res = col_observation.query(query_texts=[q], n_results=2)
        docs = res["documents"][0] if res["documents"] else []
        for d in docs:
            print(f"  - {d}")

if __name__ == "__main__":
    main()
