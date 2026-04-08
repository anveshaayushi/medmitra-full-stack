import json
import os
import re
import time
from itertools import combinations
from google import genai
from app.services.key_manager import get_best_key, record_key_usage, mark_key_exhausted

from dotenv import load_dotenv
load_dotenv()

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
  - total_daily_dose_mg = dose_mg x freq_per_day (null if unknown)
  - Sort medication_summary alphabetically, clinical_alerts high→medium→low
  - Never omit a key, use null instead
  - drugs_involved: always use the ORIGINAL name exactly as written in the prescription input (e.g. "ZERODOL MR" not "aceclofenac"). Never use generic names in drugs_involved.
  - mechanism and recommendation must be written in simple, plain English that a patient with no medical background can understand. Avoid medical jargon like "CYP1A2", "serotonergic", "hepatotoxicity", "contraindicated". Instead say things like "these two medicines together can slow your breathing dangerously" or "this combination can cause your stomach to bleed". Try to keep it short and to the point and informative(short doesn't mean to reduce information). recommendation must be a clear action like "Do not take both" or "Take them 2 hours apart" or "Tell your doctor immediately".
"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def _patch(result: dict, patient_name: str) -> dict:
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
        alert.setdefault("what_happens", alert.get("mechanism") or alert.get("message", ""))
        alert.setdefault("what_to_do",   alert.get("recommendation") or "Consult your doctor.")

    for med in result.get("medication_summary", []):
        med.setdefault("canonical_name",      "unknown")
        med.setdefault("total_daily_dose_mg", None)
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

    # ── Combo filter ──────────────────────────────────────────────────────
    # If a 3+ drug combo alert exists, remove individual 2-drug pair alerts
    # whose drugs are already fully covered inside that combo.
    # Better to show one combined alert than many redundant pair alerts.
    clinical_alerts = result.get("clinical_alerts", [])

    combo_covered_pairs = set()
    for alert in clinical_alerts:
        drugs = alert.get("drugs_involved") or []
        if len(drugs) >= 3:
            for pair in combinations(drugs, 2):
                combo_covered_pairs.add(tuple(sorted(pair)))

    result["clinical_alerts"] = [
        a for a in clinical_alerts
        if not (
            len(a.get("drugs_involved") or []) == 2
            and tuple(sorted(a.get("drugs_involved") or [])) in combo_covered_pairs
        )
    ]
    # ─────────────────────────────────────────────────────────────────────

    return result


def analyze_medications(meds: list, patient_name: str = "User") -> dict:
    if not meds:
        return {
            "status":             "no_medications_found",
            "patient_name":       patient_name.title(),
            "risk_score":         {"score": 0, "label": "UNANALYZED",
                                   "high_alerts": 0, "medium_alerts": 0,
                                   "low_alerts": 0, "total_alert_count": 0},
            "clinical_alerts":    [],
            "duplicate_alerts":   [],
            "overdose_alerts":    [],
            "medication_summary": [],
        }

    # ── Smart key selection ───────────────────────────────────────────────
    api_key = get_best_key()
    if not api_key:
        raise ValueError("All Gemini API keys exhausted for today. Try again tomorrow.")

    client = genai.Client(api_key=api_key)
    

    prompt = f"Patient name: {patient_name}\n\nPrescription:\n{json.dumps(meds, indent=2)}"

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={"system_instruction": SYSTEM_PROMPT, "temperature": 0.1},
        )
        record_key_usage(api_key)  # ← track successful call

    except Exception as e:
        err = str(e).lower()
        if "quota" in err or "429" in err or "limit" in err or "exhausted" in err:
            mark_key_exhausted(api_key)  # ← mark exhausted, retry with next key
            # Retry once with next key
            api_key = get_best_key()
            if not api_key:
                raise ValueError("All Gemini API keys exhausted for today.")
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={"system_instruction": SYSTEM_PROMPT, "temperature": 0.1},
            )
            record_key_usage(api_key)
        else:
            raise

    try:
        result = json.loads(_strip_fences(response.text))
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini returned invalid JSON: {e}\n\n{response.text[:400]}")

    return _patch(result, patient_name)