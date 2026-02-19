from fastapi import FastAPI
from app.api.routes import health
from app.api.routes import ingest

app = FastAPI(title="Enterprise Engineering Knowledge Copilot")

app.include_router(health.router)
app.include_router(ingest.router)