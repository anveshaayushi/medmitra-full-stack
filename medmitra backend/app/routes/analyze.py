from fastapi import APIRouter, File, UploadFile
from app.models.schemas import AnalysisResponse
from app.services.mock_service import get_mock_analysis

router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse, tags=["Analysis"])
async def analyze_prescription(
    file: UploadFile = File(default=None, description="Prescription image or PDF (not processed – mock mode)")
) -> AnalysisResponse:
    """
    Analyze a prescription and return structured medication data.

    **Note:** File processing / OCR is not implemented in this version.
    The endpoint always returns mock data that mirrors the exact structure
    expected by the Medmitra frontend.
    """
    # File is accepted but intentionally ignored – mock data is always returned.
    return await get_mock_analysis()
