from typing import List
# ← Change: import from the 3 separate service files instead of prescriptionanalyser
from app.services.ocr_service      import process_image_bytes_list
from app.services.analysis_service import analyze_medications


def analyze_multiple_images(image_files: List[bytes], patient_name: str = "User") -> dict:
    """
    Pipeline:
      1. ocr_service      → extract meds from each image (ocr.py)
      2. analysis_service → run full Gemini safety analysis (p2.py)
    WhatsApp is triggered separately via the /send-whatsapp route (twilio.py)
    """
    print(f"\n📦 Processing {len(image_files)} prescription(s)...")

    # Step 1 — OCR (ocr_service.py)
    # Build (filename, bytes) tuples for source tracking
    named_files = [
        (f"Prescription {idx + 1}", image_bytes)
        for idx, image_bytes in enumerate(image_files)
    ]
    all_meds = process_image_bytes_list(named_files)

    if not all_meds:
        return {
            "status":  "error",
            "message": "No medicines detected in any uploaded image",
        }

    print(f"\n🧠 Total medicines combined: {len(all_meds)}")

    # Step 2 — Analysis (analysis_service.py / p2.py)
    result = analyze_medications(all_meds, patient_name=patient_name)

    result["total_prescriptions"] = len(image_files)
    result["total_medicines"]     = len(all_meds)

    return result