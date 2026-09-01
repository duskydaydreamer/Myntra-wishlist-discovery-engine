import json
from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)

def run_test():
    response = client.post(
        "/api/query",
        json={"query": "What are the top themes?"}
    )
    if response.status_code != 200:
        print(f"FAILED: Status {response.status_code}")
        print(response.json())
        return
        
    data = response.json()
    print("SUCCESS: Deterministic query executed.")
    print("--- API Response Metrics ---")
    print(f"query_type: {data.get('query_type')}")
    print(f"retrieval_mode: {data.get('retrieval_mode')}")
    print(f"numerator: {data.get('numerator')}")
    print(f"denominator: {data.get('denominator')}")
    print(f"evidence_count: {data.get('evidence_count')}")
    print(f"has_answer: {bool(data.get('answer'))}")
    print(f"dataset_scope_caveat: {data.get('dataset_scope_caveat')}")

if __name__ == "__main__":
    run_test()
