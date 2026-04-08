import os
import json
import base64
import time
from google import genai
from dotenv import load_dotenv
from app.services.key_manager import get_best_key, record_key_usage, mark_key_exhausted

load_dotenv()

GEMINI_MODEL = "gemini-2.5-flash"

PROMPT = """
You are a medical assistant.

Extract ONLY medications from this prescription image.

Return STRICT JSON in this format:
[
  {
    "name": "",
    "dosage": "",
    "frequency": "",
    "duration": "",
    "notes": ""
  }
]

Rules:
- Only include medicines
- Ignore all other text
- If any field is missing, use ""
- Return ONLY valid JSON
"""


def extract_medicine_data(image_bytes: bytes, source_name: str = "") -> list:
    # ── Smart key selection ───────────────────────────────────────────────
    api_key = get_best_key()
    if not api_key:
        print("  [OCR] All API keys exhausted")
        return []

    MAX_RETRIES  = 3
    RETRY_DELAYS = [5, 15, 30]

    for attempt in range(MAX_RETRIES):
        try:
            client = genai.Client(api_key=api_key)

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[{
                    "role": "user",
                    "parts": [
                        {"text": PROMPT},
                        {"inline_data": {
                            "mime_type": "image/jpeg",
                            "data": base64.b64encode(image_bytes).decode(),
                        }},
                    ],
                }],
            )

            # ── Success ───────────────────────────────────────────────────
            record_key_usage(api_key)  # ← track call

            text = (response.text or "").strip()
            if "```" in text:
                parts = text.split("```")
                text = parts[1] if len(parts) > 1 else parts[0]
            if text.lower().startswith("json"):
                text = text[4:].strip()

            data = json.loads(text)
            meds = data if isinstance(data, list) else []
            if source_name:
                for med in meds:
                    med["source"] = source_name
            return meds

        except Exception as e:
            err = str(e)
            is_429 = "429" in err or "quota" in err.lower() or "exhausted" in err.lower()
            is_503 = "503" in err or "UNAVAILABLE" in err

            if is_429:
                mark_key_exhausted(api_key)
                api_key = get_best_key()  # next key try karo
                if not api_key:
                    print("  [OCR] All API keys exhausted")
                    return []

            elif is_503 and attempt < MAX_RETRIES - 1:
                wait = RETRY_DELAYS[attempt]
                print(f"  [OCR] Attempt {attempt + 1} failed (503). Retrying in {wait}s...")
                time.sleep(wait)
                continue

            else:
                print(f"  [OCR] Error processing {source_name}: {err[:80]}")
                return []

    return []


def process_image_bytes_list(image_files: list[tuple[str, bytes]]) -> list:
    all_medicines = []
    for filename, image_bytes in image_files:
        print(f"📄 Processing: {filename}")
        meds = extract_medicine_data(image_bytes, source_name=filename)
        if not meds:
            print(f"  ⚠️ No medicines detected in {filename}")
            continue
        all_medicines.extend(meds)
    return all_medicines