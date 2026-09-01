from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routers import dashboard, evidence, themes, clusters, opportunities, query, unmet_needs, pipeline, knowledge_graph, meta

app = FastAPI(
    title="Myntra Discovery Pulse API",
    description="API for accessing Myntra Discovery Pulse qualitative dataset and AI synthesis",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "db_reachable": True, "chroma_reachable": True}

# Routers
api_router = APIRouter(prefix="/api")
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(evidence.router, prefix="/evidence", tags=["Evidence"])
api_router.include_router(themes.router, prefix="/themes", tags=["Themes"])
api_router.include_router(clusters.router, prefix="/clusters", tags=["Clusters"])
api_router.include_router(opportunities.router, prefix="/opportunities", tags=["Opportunities"])
api_router.include_router(query.router, prefix="/query", tags=["Query"])
api_router.include_router(unmet_needs.router, prefix="/unmet-needs", tags=["Unmet Needs"])
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["Pipeline"])
api_router.include_router(knowledge_graph.router, prefix="/knowledge-graph", tags=["Knowledge Graph"])
api_router.include_router(meta.router, prefix="/meta", tags=["Metadata"])

app.include_router(api_router)
