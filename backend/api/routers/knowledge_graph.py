from fastapi import APIRouter
import json
import os

router = APIRouter()

@router.get("")
async def get_knowledge_graph():
    # Read the knowledge graph json generated in Phase 4
    # which is at data/phase4/knowledge_graph.json
    kg_path = os.path.join(os.getcwd(), "data", "phase4", "knowledge_graph.json")
    if os.path.exists(kg_path):
        with open(kg_path, "r") as f:
            return json.load(f)
    return {"nodes": [], "edges": []}
