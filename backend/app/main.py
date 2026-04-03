from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import analyze, health
from app.routes.multi_prescription import router as multi_router

# ---------------------------------------------------------------------------
# App instance (CREATE FIRST)
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Medmitra – Prescription Intelligence System",
    description=(
        "FastAPI backend that parses prescriptions and returns structured "
        "medication data. Currently running in **mock mode** – all endpoints "
        "return realistic sample data without any OCR processing."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS – allow frontend
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers (ADD AFTER app is created)
# ---------------------------------------------------------------------------

app.include_router(health.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(multi_router, prefix="/api")   # ✅ YOUR NEW ROUTE

# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "Medmitra API is running. Visit /docs for the interactive API reference.",
        "docs": "/docs",
        "health": "/api/health",
        "analyze": "POST /api/analyze",
        "multi_analyze": "POST /api/analyze-multiple"
    }