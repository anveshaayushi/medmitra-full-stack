import json
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from app.services.whatsapp_service import send_whatsapp_summary
from app.services.ocr_service      import extract_medicine_data
from app.services.analysis_service import analyze_medications

router = APIRouter()


# ── POST /api/analyze ─────────────────────────────────────────────────────────

@router.post("/analyze")
async def analyze_prescription(file: UploadFile = File(...)):
    file_bytes   = await file.read()
    filename     = file.filename or ""
    content_type = file.content_type or ""

    # JSON file upload
    if filename.endswith(".json") or content_type == "application/json":
        try:
            data = json.loads(file_bytes)
            if isinstance(data, list):
                meds         = data
                patient_name = "User"
            elif isinstance(data, dict):
                meds         = data.get("meds", [])
                patient_name = data.get("name", "User")
            else:
                meds         = []
                patient_name = "User"
        except Exception:
            meds         = []
            patient_name = "User"
    else:
        # Image upload — use ocr_service (ocr.py)
        meds         = extract_medicine_data(file_bytes, source_name=filename)
        patient_name = "User"

    print("EXTRACTED MEDS:", meds)
    # analysis_service (p2.py)
    return analyze_medications(meds, patient_name)


# ── POST /api/send-whatsapp ───────────────────────────────────────────────────

class WhatsAppRequest(BaseModel):
    phone_number:    str
    analysis_result: dict


@router.post("/send-whatsapp", tags=["WhatsApp"])
async def send_whatsapp(request: WhatsAppRequest):
    return send_whatsapp_summary(request.analysis_result, request.phone_number)