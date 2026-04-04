import json
import os
import re
import time
from google import genai
from dotenv import load_dotenv
load_dotenv()

# ── Changes from original p2.py ───────────────────────────────────────────
# 1. Removed argparse / CLI entry point entirely
# 2. Removed file I/O (no reading/writing JSON files)
# 3. Exposed analyze_medications(meds: list, patient_name: str) -> dict
#    that the FastAPI service layer calls directly
# 4. Everything else (SYSTEM_PROMPT, patch, strip_fences) identical
# ──────────────────────────────────────────────────────────────────────────

GEMINI_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are a senior clinical pharmacist. You will receive a prescription as a JSON array.

Analyse it for:
  - Drug interactions (pair-wise AND 3-drug combos)
  - Duplicate therapy (same drug or same drug class prescribed twice)
  - Overdose / unsafe daily doses
  - Route-of-administration warnings (topical, IV, etc.)
  - Any other clinically significant risk

Return ONLY a valid JSON object. No markdown, no explanation outside the JSON.

Output schema — every key must always be present, use null for missing values:

{
  "status": "success",
  "patient_name": "<patient name>",
  "risk_score": {
    "score": <integer 0-10>,
    "label": "LOW RISK" | "MODERATE RISK" | "HIGH RISK",
    "high_alerts": <integer>,
    "medium_alerts": <integer>,
    "low_alerts": <integer>,
    "total_alert_count": <integer>
  },
  "clinical_alerts": [
    {
      "type": "contraindication" | "duplicate_therapy" | "class_duplicate" | "overdose" | "route_warning" | "interaction" | "patient_specific",
      "severity": "high" | "medium" | "low",
      "message": "<clear one-line description>",
      "mechanism": "<why it is dangerous, or null>",
      "recommendation": "<what to do instead, or null>",
      "drugs_involved": ["drug1", "drug2"]
    }
  ],
  "medication_summary": [
    {
      "canonical_name": "<generic drug name in lowercase>",
      "total_daily_dose_mg": <number or null>,
      "variants": [
        {
          "original_name": "<exactly as written in the prescription input>",
          "dose_mg": <number or null>,
          "freq_per_day": <number or null>,
          "duration": "<string or null>",
          "notes": "<string or null>",
          "route_note": "<route warning string or null>",
          "warning": "<low-confidence note, PRN note, or unresolved drug note — or null>"
        }
      ]
    }
  ]
}

Scoring rules:
  - Each HIGH alert   = 3 points
  - Each MEDIUM alert = 1 point
  - Cap total at 10
  - score 0-2  → label = "LOW RISK"
  - score 3-5  → label = "MODERATE RISK"
  - score 6-10 → label = "HIGH RISK"

Field rules:
  - freq_per_day: PRN / SOS / as-needed = 0, once daily = 1, BD = 2, TDS = 3, QID = 4, weekly = 0
  - total_daily_dose_mg = dose_mg x freq_per_day (set null if freq = 0 or dose unknown)
  - If you cannot identify a drug at all, still include it in medication_summary with
    canonical_name = the original name, and set warning = "Could not identify drug — verify manually"
  - medication_summary must be sorted alphabetically by canonical_name
  - clinical_alerts must be sorted: high first, then medium, then low
  - Never omit a key — use null instead
"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def _patch(result: dict, patient_name: str) -> dict:
    """Fill in any missing keys so the frontend never gets KeyError."""
    result.setdefault("status",       "success")
    result.setdefault("patient_name", patient_name.title())

    rs = result.setdefault("risk_score", {})
    rs.setdefault("score",             0)
    rs.setdefault("label",             "LOW RISK")
    rs.setdefault("high_alerts",       0)
    rs.setdefault("medium_alerts",     0)
    rs.setdefault("low_alerts",        0)
    rs.setdefault("total_alert_count", 0)

    for alert in result.get("clinical_alerts", []):
        alert.setdefault("type",           "")
        alert.setdefault("severity",       "low")
        alert.setdefault("message",        "")
        alert.setdefault("mechanism",      None)
        alert.setdefault("recommendation", None)
        alert.setdefault("drugs_involved", [])
        # ← Compatibility: frontend uses what_happens / what_to_do keys
        alert.setdefault("what_happens", alert.get("mechanism") or alert.get("message", ""))
        alert.setdefault("what_to_do",   alert.get("recommendation") or "Consult your doctor.")

    for med in result.get("medication_summary", []):
        med.setdefault("canonical_name",      "unknown")
        med.setdefault("total_daily_dose_mg", None)
        # Flatten variants into top-level fields for frontend compatibility
        variants = med.get("variants", [{}])
        first = variants[0] if variants else {}
        med.setdefault("original_name", first.get("original_name", med["canonical_name"]))
        med.setdefault("dose_mg",       first.get("dose_mg"))
        med.setdefault("freq_per_day",  first.get("freq_per_day"))
        med.setdefault("duration",      first.get("duration"))
        med.setdefault("notes",         first.get("notes"))
        for v in variants:
            v.setdefault("original_name", med["canonical_name"])
            v.setdefault("dose_mg",       None)
            v.setdefault("freq_per_day",  None)
            v.setdefault("duration",      None)
            v.setdefault("notes",         None)
            v.setdefault("route_note",    None)
            v.setdefault("warning",       None)

    return result


def analyze_medications(meds: list, patient_name: str = "User") -> dict:
    """
    Core analysis function.
    Takes a flat list of medication dicts and returns the full analysis dict.
    This is what multi_prescription.py service calls.
    """
    if not meds:
        return {
            "status":             "no_medications_found",
            "patient_name":       patient_name.title(),
            "risk_score":         {
                "score": 0, "label": "UNANALYZED",
                "high_alerts": 0, "medium_alerts": 0,
                "low_alerts": 0, "total_alert_count": 0,
            },
            "clinical_alerts":    [],
            "medication_summary": [],
        }

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment")

    client = genai.Client(api_key=api_key)

    # Warm-up ping (same as original p2.py)
    client.models.generate_content(model=GEMINI_MODEL, contents="reply: ok")
    time.sleep(1)

    prompt = f"Patient name: {patient_name}\n\nPrescription:\n{json.dumps(meds, indent=2)}"

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "system_instruction": SYSTEM_PROMPT,
            "temperature": 0.1,
        },
    )

    try:
        result = json.loads(_strip_fences(response.text))
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini returned invalid JSON: {e}\n\n{response.text[:400]}")

    return _patch(result, patient_name)