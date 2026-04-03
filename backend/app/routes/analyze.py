import json
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from app.services.prescriptionanalyser import (
    analyzeprescription,
    extract_meds_with_gemini,
    send_whatsapp_summary,
)

router = APIRouter()


# ── POST /api/analyze ─────────────────────────────────────────────────────────

@router.post("/analyze")
async def analyze_prescription(file: UploadFile = File(...)):
    file_bytes = await file.read()
    filename   = file.filename or ""
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
        # Image upload — use Gemini OCR
        meds         = extract_meds_with_gemini(file_bytes)
        patient_name = "User"

    print("EXTRACTED MEDS:", meds)
    return analyzeprescription({"meds": meds}, patient_name)


# ── POST /api/send-whatsapp ───────────────────────────────────────────────────

class WhatsAppRequest(BaseModel):
    phone_number:    str
    analysis_result: dict


@router.post("/send-whatsapp")
async def send_whatsapp(body: WhatsAppRequest):
    result = send_whatsapp_summary(body.analysis_result, body.phone_number)
    return result