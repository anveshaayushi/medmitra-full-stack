from fastapi import APIRouter
from app.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Check that the Medmitra API is up and running."""
    return HealthResponse(
        status="ok",
        service="Medmitra – Prescription Intelligence System",
        version="1.0.0",
    )
