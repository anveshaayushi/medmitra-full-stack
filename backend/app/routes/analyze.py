from fastapi import APIRouter, UploadFile, File
from app.services.prescriptionanalyser import (
    analyzeprescription,
    extract_meds_with_gemini
)

router = APIRouter()


@router.post("/analyze")
async def analyze_prescription(file: UploadFile = File(...)):

    # 1. Read image
    image_bytes = await file.read()

    # 2. 🔥 Extract meds using Gemini
    meds = extract_meds_with_gemini(image_bytes)

    print("EXTRACTED MEDS:", meds)  # debug

    # 3. Pass to analyzer
    result = analyzeprescription(
        inputdata={"meds": meds},
        patientname="User"
    )

    return result