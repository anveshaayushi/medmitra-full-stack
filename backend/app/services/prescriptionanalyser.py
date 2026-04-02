import os
import json
from itertools import combinations
from dotenv import load_dotenv

from google import genai
from google.genai import types

# ---------------- ENV ----------------
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ---------------- GEMINI OCR ----------------
def extract_meds_with_gemini(image_bytes):
    try:
        prompt = """
You are a medical AI assistant.

Extract ONLY medicines from this prescription image.

Return STRICT JSON:
[
  {"name": "", "dosage": "", "frequency": ""}
]

Ignore headings, instructions, and irrelevant text.
"""

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/jpeg"
                )
            ]
        )

        # -------- SAFE TEXT EXTRACTION --------
        text = ""

        try:
            if hasattr(response, "text") and response.text:
                text = response.text

            elif hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]

                if candidate.content and candidate.content.parts:
                    part = candidate.content.parts[0]

                    if hasattr(part, "text") and part.text:
                        text = part.text

        except Exception as e:
            print("Parsing error:", e)
            text = ""

        # -------- CLEAN --------
        text = text.strip()
        text = text.replace("```json", "").replace("```", "")

        print("GEMINI RAW:", text)

        # -------- PARSE --------
        try:
            return json.loads(text)
        except:
            return []

    except Exception as e:
        print("Gemini error:", e)
        return []


# ---------------- ANALYSIS LOGIC ----------------
KNOWN_INTERACTIONS = [
    ("ibuprofen", "aspirin", "high"),
    ("warfarin", "ibuprofen", "high"),
    ("sertraline", "tramadol", "high"),
    ("paracetamol", "ibuprofen", "moderate"),
]

def normalize(name):
    return name.lower().strip()

def analyze(raw_meds, patient_name):
    meds = [normalize(m["name"]) for m in raw_meds if m.get("name")]

    interactions = []

    for d1, d2 in combinations(meds, 2):
        for k1, k2, severity in KNOWN_INTERACTIONS:
            if {d1, d2} == {k1, k2}:
                interactions.append({
                    "drugs_involved": [d1, d2],
                    "severity": severity,
                    "message": f"{d1} and {d2} may interact"
                })

    return {
        "status": "success",
        "patient_name": patient_name,
        "risk_score": {
            "score": len(interactions),
            "label": "HIGH RISK" if len(interactions) > 2 else "MODERATE RISK" if interactions else "LOW RISK"
        },
        "clinical_alerts": interactions,
        "duplicate_alerts": [],
        "overdose_alerts": [],
        "medication_summary": raw_meds
    }


# ---------------- ENTRY FUNCTION ----------------
def analyzeprescription(inputdata, patientname="User"):
    meds = inputdata.get("meds", [])
    return analyze(meds, patientname)