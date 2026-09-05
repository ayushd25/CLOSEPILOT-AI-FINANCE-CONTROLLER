import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.api.reconciliation import router as reconciliation_router
from app.api.cases import router as cases_router
from app.api.audit import router as audit_router
from app.api.evaluation import router as evaluation_router
from app.api.synthetic import router as synthetic_router
from app.api.agent import router as agent_router
from app.api.policy import router as policy_router
from app.api.forecast import router as forecast_router
from app.api.tax_lines import router as tax_lines_router
from app.config import settings
from app.db import Database
from app.db.indexes import ensure_indexes

logger = logging.getLogger("closepilot")

request_id_middleware_enabled = app_state = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    Database.connect()
    await ensure_indexes()
    logger.info("In-memory store initialized")
    yield
    await Database.close()


app = FastAPI(
    title="ClosePilot API",
    version="1.0.0",
    description="Autonomous Finance Controller",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")] if settings.CORS_ORIGINS else []
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(reconciliation_router)
app.include_router(cases_router)
app.include_router(audit_router)
app.include_router(evaluation_router)
app.include_router(synthetic_router)
app.include_router(agent_router)
app.include_router(policy_router)
app.include_router(forecast_router)
app.include_router(tax_lines_router)
