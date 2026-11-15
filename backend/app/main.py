from contextlib import asynccontextmanager
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.telemetry import tracer
from app.services.seed_service import ensure_enterprise_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        await ensure_enterprise_seed(db)
    yield


app = FastAPI(
    title="NEXUS — AI-Native Business Operations Platform",
    description=(
        "Multi-tenant Enterprise AI Command Center powered by the official Model Context Protocol (MCP) "
        "and LangGraph stateful orchestration."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def telemetry_and_security_headers_middleware(request: Request, call_next):
    start_ts = time.perf_counter()
    with tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.route", request.url.path)
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_ts) * 1000, 2)
        span.set_attribute("http.status_code", response.status_code)
        span.set_attribute("http.duration_ms", duration_ms)
        response.headers["X-Process-Time-Ms"] = str(duration_ms)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "mcp_protocol": "2025-11-25",
    }


app.include_router(api_router, prefix=settings.API_V1_PREFIX)

