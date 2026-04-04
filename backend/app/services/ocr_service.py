import os
import json
import base64
from google import genai
from dotenv import load_dotenv
load_dotenv()

GEMINI_MODEL = "gemini-2.5-flash"

# ── Changes from original ocr.py ──────────────────────────────────────────
# 1. Removed top-level script block (folder_path / process_folder call)
# 2. extract_medicine_data() now accepts bytes directly (not a file path)
#    so FastAPI can pass uploaded file bytes without saving to disk
# 3. client is created lazily inside the function (safe for import)
# ──────────────────────────────────────────────────────────────────────────

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
    """
    Extract medications from raw image bytes using Gemini vision.
    Returns a list of medication dicts.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("  [OCR] GEMINI_API_KEY not set")
        return []

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"text": PROMPT},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                # ← Change: encode bytes directly instead of reading file
                                "data": base64.b64encode(image_bytes).decode(),
                            }
                        },
                    ],
                }
            ],
        )

        text = response.text
        if not text:
            return []

        text = text.strip()

        # Clean markdown fences (same as original)
        if "```" in text:
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else parts[0]

        if text.lower().startswith("json"):
            text = text[4:].strip()

        data = json.loads(text)
        meds = data if isinstance(data, list) else []

        # Add source tracking (same as original process_folder)
        if source_name:
            for med in meds:
                med["source"] = source_name

        return meds

    except Exception as e:
        print(f"  [OCR] Error processing {source_name}: {e}")
        return []


def process_image_bytes_list(image_files: list[tuple[str, bytes]]) -> list:
    """
    Process a list of (filename, bytes) tuples.
    Equivalent to original process_folder() but works on in-memory bytes.
    image_files: [(filename, bytes), ...]
    """
    all_medicines = []

    for filename, image_bytes in image_files:
        print(f"📄 Processing: {filename}")
        meds = extract_medicine_data(image_bytes, source_name=filename)

        if not meds:
            print(f"  ⚠️ No medicines detected in {filename}")
            continue

        all_medicines.extend(meds)

    return all_medicines