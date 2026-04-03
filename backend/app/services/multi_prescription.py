from typing import List
from .prescriptionanalyser import (
    extract_meds_with_gemini,
    analyzeprescription
)


def analyze_multiple_images(image_files: List[bytes], patient_name="User"):
    """
    Combines multiple prescription images into ONE patient-level analysis
    """

    all_meds = []

    print(f"\n📦 Processing {len(image_files)} prescription(s)...")

    for idx, image_bytes in enumerate(image_files):
        print(f"\n📄 Processing Prescription {idx + 1}")

        meds = extract_meds_with_gemini(image_bytes)

        if not meds:
            print("  ⚠️ No medicines detected in this image")
            continue

        for m in meds:
            # Safety check
            if not isinstance(m, dict) or not m.get("name"):
                continue

            # Add source info (VERY useful for debugging + UI)
            m["source"] = f"Prescription {idx + 1}"

            all_meds.append(m)

    # ❌ No meds found at all
    if not all_meds:
        return {
            "status": "error",
            "message": "No medicines detected in any uploaded image"
        }

    print(f"\n🧠 Total medicines combined: {len(all_meds)}")

    # 🔥 SINGLE COMBINED ANALYSIS
    result = analyzeprescription(
        {"meds": all_meds},
        patientname=patient_name
    )

    # Optional: attach metadata
    result["total_prescriptions"] = len(image_files)
    result["total_medicines"] = len(all_meds)

    return result