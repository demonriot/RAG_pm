from fastapi import FastAPI
from app.api.routes import health
from app.api.routes import ingest
from app.api.routes import retrieve
from app.api.routes.planning import router as planning_router
from app.api.routes.query import router as query_router
app = FastAPI(title="Enterprise Engineering Knowledge Copilot")

app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(retrieve.router)
app.include_router(planning_router)
app.include_router(query_router)