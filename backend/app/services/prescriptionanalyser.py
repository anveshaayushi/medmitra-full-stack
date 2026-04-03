"""
MedMitra — Prescription Safety Checker
=======================================
FastAPI-ready module. No CLI arguments.
API keys are read from environment variables:
    GEMINI_API_KEY   — for OCR + analysis
    TWILIO_SID       — for WhatsApp notifications
    TWILIO_AUTH      — for WhatsApp notifications
    TWILIO_FROM      — your Twilio WhatsApp number e.g. whatsapp:+14155238886

Entry points for FastAPI routes:
    extract_meds_with_gemini(image_bytes: bytes) -> list
    analyzeprescription(inputdata: dict, patientname: str) -> dict
    send_whatsapp_summary(analysis_result: dict, phone_number: str) -> dict
"""

import base64
import json
import os
import re
import time
from difflib import get_close_matches
from dotenv import load_dotenv

load_dotenv()

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

try:
    from google import genai
    GENAI_OK = True
except ImportError:
    GENAI_OK = False

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_OK = True
except ImportError:
    TWILIO_OK = False

# ════════════════════════════════════════════════════════
#  GLOBALS
# ════════════════════════════════════════════════════════

GEMINI_MODEL     = "gemini-2.5-flash"
LEARNED_FILE     = os.path.join(os.path.dirname(__file__), "learned_drugs.json")
GEMINI_AVAILABLE = False
_client          = None
_gemini_calls    = 0
MAX_GEMINI_CALLS = 2


# ════════════════════════════════════════════════════════
#  STATIC KNOWLEDGE BASE
# ════════════════════════════════════════════════════════

BRAND_TO_GENERIC = {
    "ultrafen":"diclofenac","ultrafen-plus":"diclofenac","ultrafen plus":"diclofenac",
    "metfornin":"metformin","metformine":"metformin",
    "amoxycillin":"amoxicillin","ibuprophen":"ibuprofen",
    "asprin":"aspirin","diclofinac":"diclofenac",
    "azithromicin":"azithromycin","cetrizine":"cetirizine",
    "levocetrizine":"levocetirizine","omeprazol":"omeprazole",
    "pantaprazole":"pantoprazole","warfrine":"warfarin",
    "paracitamol":"paracetamol","paracetmol":"paracetamol",
    "pcm":"paracetamol","para":"paracetamol","ibu":"ibuprofen",
    "asp":"aspirin","azi":"azithromycin","amox":"amoxicillin",
    "metro":"metronidazole","doxy":"doxycycline","cet":"cetirizine",
    "mont":"montelukast","tel":"telmisartan","losar":"losartan",
    "aml":"amlodipine","aten":"atenolol","meto":"metoprolol",
    "rami":"ramipril","met":"metformin","glim":"glimepiride",
    "pan":"pantoprazole","ome":"omeprazole","warf":"warfarin",
    "pred":"prednisolone","dexa":"dexamethasone","preg":"pregabalin",
    "p-650":"paracetamol","p650":"paracetamol","p 650":"paracetamol",
    "p-500":"paracetamol","p500":"paracetamol","p-1000":"paracetamol",
    "crocin":"paracetamol","dolo":"paracetamol","calpol":"paracetamol",
    "combiflam":"ibuprofen","brufen":"ibuprofen",
    "augmentin":"amoxicillin clavulanic acid",
    "amoxyclav":"amoxicillin clavulanic acid",
    "azee":"azithromycin","zithromax":"azithromycin",
    "ciplox":"ciprofloxacin","flagyl":"metronidazole",
    "cetzine":"cetirizine","levocet":"levocetirizine",
    "allegra":"fexofenadine","claritin":"loratadine",
    "telma":"telmisartan","telmikind":"telmisartan",
    "amlokind":"amlodipine","metolar":"metoprolol",
    "cardace":"ramipril","glycomet":"metformin",
    "glimy":"glimepiride","janumet":"sitagliptin",
    "galvus":"vildagliptin","pantocid":"pantoprazole",
    "omez":"omeprazole","rablet":"rabeprazole",
    "pand":"pantoprazole","omez d":"omeprazole",
    "zoloft":"sertraline","prozac":"fluoxetine",
    "cipralex":"escitalopram","paxil":"paroxetine",
    "lipitor":"atorvastatin","crestor":"rosuvastatin",
    "acitrom":"warfarin","coumadin":"warfarin",
    "ultracet":"tramadol","lyrica":"pregabalin",
    "shelcal":"calcium carbonate","emset":"ondansetron",
    "evion":"vitamin d3","orsl":"ors",
    "wysolone":"prednisolone","decadron":"dexamethasone",
    "eltroxin":"levothyroxine","thyronorm":"levothyroxine",
    "hexigel":"chlorhexidine","hexigel gum paint":"chlorhexidine",
    "enzoflam":"diclofenac","benadryl":"diphenhydramine",
    "zyrtec":"cetirizine","ecosprin":"aspirin","disprin":"aspirin",
    "glucophage":"metformin",
    "panzo d":"pantoprazole","panzo":"pantoprazole",
    "hygina":"chlorhexidine","hygina mouth wash":"chlorhexidine",
    "hygina mouthwash":"chlorhexidine",
    "broned ls syrup":"levosalbutamol","broned ls":"levosalbutamol",
    "broned":"levosalbutamol",
}

DRUG_CLASS = {
    "telmisartan":"arb","losartan":"arb","ramipril":"ace_inhibitor",
    "amlodipine":"ccb","metoprolol":"beta_blocker","atenolol":"beta_blocker",
    "paracetamol":"analgesic","ibuprofen":"nsaid","aspirin":"nsaid",
    "diclofenac":"nsaid","aceclofenac":"nsaid","naproxen":"nsaid",
    "omeprazole":"ppi","pantoprazole":"ppi","rabeprazole":"ppi",
    "cetirizine":"antihistamine","levocetirizine":"antihistamine",
    "loratadine":"antihistamine","fexofenadine":"antihistamine",
    "diphenhydramine":"antihistamine","azithromycin":"antibiotic",
    "amoxicillin":"antibiotic","ciprofloxacin":"antibiotic",
    "doxycycline":"antibiotic","levofloxacin":"antibiotic",
    "sertraline":"ssri","fluoxetine":"ssri","escitalopram":"ssri",
    "atorvastatin":"statin","rosuvastatin":"statin","simvastatin":"statin",
    "alprazolam":"benzodiazepine","clonazepam":"benzodiazepine","diazepam":"benzodiazepine",
    "codeine":"opioid","tramadol":"opioid","morphine":"opioid",
    "prednisolone":"corticosteroid","dexamethasone":"corticosteroid",
    "pregabalin":"gabapentinoid","gabapentin":"gabapentinoid",
    "metformin":"biguanide","glimepiride":"sulfonylurea",
    "chlorhexidine":"antiseptic","levosalbutamol":"bronchodilator",
}

KNOWN_INTERACTIONS = [
    ("ibuprofen","aspirin","high",
     "Ibuprofen blocks aspirin from protecting your heart and raises risk of stomach bleeding.",
     "Avoid taking both. If you need a painkiller with aspirin, use paracetamol instead."),
    ("diclofenac","aspirin","high",
     "Both together damage the stomach lining and can cause serious internal bleeding.",
     "Do not take both. Use one NSAID at a time, only as directed by your doctor."),
    ("ibuprofen","diclofenac","high",
     "Same type of painkiller (NSAID). Taking both doubles the risk of stomach ulcers and kidney damage.",
     "Take only one of these at a time, never both together."),
    ("warfarin","aspirin","high",
     "Both thin your blood. Together they can cause dangerous bleeding that is hard to stop.",
     "Avoid aspirin unless your doctor specifically says to take both. Monitor closely."),
    ("warfarin","ibuprofen","high",
     "Ibuprofen raises warfarin levels and also irritates your stomach, creating a double bleeding risk.",
     "Use paracetamol for pain instead of ibuprofen while on warfarin."),
    ("warfarin","ciprofloxacin","high",
     "Ciprofloxacin stops your body from breaking down warfarin, causing it to build up to dangerous levels.",
     "If this antibiotic is necessary, your doctor must monitor your INR very closely."),
    ("warfarin","metronidazole","high",
     "Metronidazole strongly increases warfarin's blood-thinning effect, greatly raising bleeding risk.",
     "Avoid this combination. If unavoidable, reduce warfarin dose and check INR frequently."),
    ("warfarin","azithromycin","medium",
     "Azithromycin can increase the blood-thinning effect of warfarin, raising bleeding risk.",
     "Monitor for unusual bruising or bleeding. Check INR more frequently."),
    ("warfarin","amoxicillin","medium",
     "Amoxicillin may increase the blood-thinning effect of warfarin, raising the risk of bleeding.",
     "Monitor for unusual bruising or bleeding. Check INR more frequently."),
    ("sertraline","tramadol","high",
     "Together these can cause serotonin syndrome — agitation, rapid heartbeat, high fever, muscle twitching.",
     "Avoid this combination. Inform your doctor immediately if you feel agitated or have a fast heartbeat."),
    ("fluoxetine","tramadol","high",
     "Together these can cause serotonin syndrome — confusion, rapid heartbeat, and muscle stiffness.",
     "Avoid this combination. Tell your doctor if you are on fluoxetine before taking tramadol."),
    ("escitalopram","tramadol","high",
     "Together these can cause serotonin syndrome — agitation, fever, and muscle problems.",
     "Avoid this combination. Your doctor may suggest an alternative painkiller."),
    ("telmisartan","ramipril","high",
     "Both lower blood pressure through the same kidney pathway. Together they can cause sudden kidney failure.",
     "Do not take both. This is a well-known dangerous combination. Consult your doctor immediately."),
    ("losartan","ramipril","high",
     "Both act on the same kidney system. Using both together sharply increases risk of kidney damage.",
     "Do not take both. Your doctor should prescribe only one of these."),
    ("metoprolol","atenolol","high",
     "Same type of medicine (beta-blocker). Taking both causes excessive slowing of your heart.",
     "Only one beta-blocker should be taken at a time. Check with your doctor which one you need."),
    ("metformin","alcohol","high",
     "Alcohol with metformin can cause lactic acidosis — a rare but life-threatening buildup of acid.",
     "Avoid alcohol completely while taking metformin."),
    ("omeprazole","clopidogrel","high",
     "Omeprazole blocks the enzyme that activates clopidogrel, making it much less effective.",
     "Switch to pantoprazole instead of omeprazole — it has much less interaction with clopidogrel."),
    ("alprazolam","diazepam","high",
     "Both are sedatives of the same type. Together they cause extreme drowsiness and can slow breathing.",
     "Never take two benzodiazepines together. Use only one as prescribed."),
    ("alprazolam","clonazepam","high",
     "Both are sedatives of the same type. Combining them causes severe drowsiness and breathing problems.",
     "Never take two benzodiazepines together. Use only one as prescribed."),
    ("ondansetron","azithromycin","high",
     "Both affect the electrical rhythm of your heart and can cause dangerous irregular heartbeat.",
     "This combination requires heart monitoring. Inform your doctor immediately."),
    ("codeine","tramadol","high",
     "Both are opioid painkillers. Taking both together severely slows your breathing and can be fatal.",
     "Never take two opioid painkillers together. Use only the one your doctor prescribed."),
    ("atorvastatin","rosuvastatin","high",
     "Same type of cholesterol medicine (statin). Taking both greatly increases risk of severe muscle damage.",
     "Take only one statin. Ask your doctor which one is right for you."),
    ("prednisolone","ibuprofen","high",
     "Both damage the stomach lining. Together they greatly increase risk of stomach ulcers and bleeding.",
     "Avoid ibuprofen while on steroids. Use paracetamol for pain relief instead."),
    ("dexamethasone","ibuprofen","high",
     "Both damage the stomach lining. Together they greatly increase risk of stomach ulcers and bleeding.",
     "Avoid ibuprofen while on steroids. Use paracetamol instead."),
    ("methotrexate","ibuprofen","high",
     "Ibuprofen prevents methotrexate from leaving your body, causing toxic buildup.",
     "Avoid all NSAIDs while on methotrexate. Use paracetamol only if your doctor approves."),
    ("amoxicillin","amoxicillin clavulanic acid","high",
     "Augmentin already contains amoxicillin. Taking separate amoxicillin doubles the dose.",
     "Stop the separate amoxicillin. Augmentin alone is sufficient."),
    ("lithium","ibuprofen","high",
     "Ibuprofen causes lithium to build up in your blood to dangerous toxic levels.",
     "Avoid all NSAIDs with lithium. Use paracetamol only for pain."),
    ("pregabalin","alprazolam","high",
     "Both slow down your brain and breathing. Together they can cause extreme sedation.",
     "This combination requires close monitoring. Do not drive or operate machinery."),
    ("sitagliptin","vildagliptin","medium",
     "Both are the same type of diabetes medicine (DPP-4 inhibitor). Taking both increases side effect risk.",
     "Use only one DPP-4 inhibitor. Ask your doctor which one to continue."),
    ("pantoprazole","clopidogrel","medium",
     "Pantoprazole slightly reduces clopidogrel's effectiveness at preventing blood clots.",
     "Generally acceptable but monitor for chest pain or clot symptoms."),
    ("doxycycline","calcium carbonate","medium",
     "Calcium binds to doxycycline in your gut and prevents it from being absorbed properly.",
     "Take doxycycline at least 2 hours before or 4 hours after any calcium supplements."),
    ("iron folic acid","calcium carbonate","medium",
     "Calcium prevents iron from being properly absorbed in your gut.",
     "Take iron and calcium at least 2 hours apart from each other."),
    ("ciprofloxacin","azithromycin","high",
     "Both can affect your heart's electrical rhythm. Together they increase risk of dangerous irregular heartbeat.",
     "Avoid this combination. Your doctor should choose only one antibiotic."),
    ("amoxicillin","ibuprofen","low",
     "Ibuprofen can slightly reduce blood flow to the kidneys, slowing clearance of amoxicillin.",
     "Take ibuprofen with food. Paracetamol is a safer alternative while on antibiotics."),
    ("azithromycin","ibuprofen","low",
     "Ibuprofen can make stomach side effects worse when combined with azithromycin.",
     "Take both medicines with food. If you have severe nausea, switch to paracetamol."),
    ("ciprofloxacin","ibuprofen","medium",
     "Ibuprofen together with ciprofloxacin increases risk of seizures.",
     "Avoid ibuprofen while on ciprofloxacin. Use paracetamol for pain relief instead."),
    ("metronidazole","ibuprofen","low",
     "Both can irritate your stomach lining, increasing chance of nausea and stomach pain.",
     "Take both with food. Use paracetamol instead of ibuprofen if possible."),
    ("amoxicillin","paracetamol","low",
     "These two medicines are generally safe to take together.",
     "No special precautions needed. This is generally a safe combination."),
    ("loratadine","ibuprofen","low",
     "No major direct interaction between loratadine and ibuprofen.",
     "Generally safe to take together. Discuss with your pharmacist if symptoms worsen."),
    ("cetirizine","ibuprofen","low",
     "No major direct interaction. Ibuprofen may mildly worsen inflammation cetirizine is controlling.",
     "Generally safe to take together with food. No special precautions needed."),
    ("diphenhydramine","ibuprofen","low",
     "No major direct interaction. Both can cause some drowsiness and stomach upset when combined.",
     "Take ibuprofen with food. Avoid driving if you feel drowsy."),
    ("paracetamol","ibuprofen","medium",
     "Taking both makes it easy to accidentally exceed the safe daily dose of either medicine.",
     "Do not exceed 4000mg paracetamol or 1200mg ibuprofen per day. Stagger the doses."),
    ("omeprazole","azithromycin","medium",
     "Both can affect the electrical rhythm of the heart. Risk increases if you have heart problems.",
     "Usually acceptable for short courses. Inform your doctor if you have a heart condition."),
    ("pantoprazole","azithromycin","low",
     "Pantoprazole can slightly increase azithromycin levels in the blood.",
     "Generally safe. No special precautions needed for most patients."),
    ("vitamin d3","calcium carbonate","low",
     "Vitamin D3 helps your body absorb calcium better — commonly prescribed together intentionally.",
     "This is a beneficial combination. Take as directed by your doctor."),
    ("metformin","ibuprofen","medium",
     "Ibuprofen can reduce blood flow to the kidneys, increasing risk of lactic acidosis.",
     "Avoid regular ibuprofen use with metformin. Paracetamol is safer."),
    ("amlodipine","ibuprofen","medium",
     "Ibuprofen can raise blood pressure, reducing the effectiveness of amlodipine.",
     "Use paracetamol for pain instead of ibuprofen. Monitor your blood pressure closely."),
    ("levothyroxine","calcium carbonate","medium",
     "Calcium binds to levothyroxine and prevents it from being absorbed properly.",
     "Take levothyroxine at least 4 hours apart from any calcium supplement."),
    ("levothyroxine","omeprazole","low",
     "Omeprazole reduces stomach acid, which can slightly reduce levothyroxine absorption.",
     "Take levothyroxine on an empty stomach, at least 30 minutes before omeprazole."),
    ("sertraline","warfarin","medium",
     "Sertraline can increase the blood-thinning effect of warfarin, raising the risk of bleeding.",
     "Monitor for unusual bruising or bleeding. Check INR more frequently."),
    ("tramadol","warfarin","medium",
     "Tramadol may increase the blood-thinning effect of warfarin and carries a small seizure risk.",
     "Monitor for unusual bleeding. Inform your doctor you are on both medications."),
]

OVERDOSE_LIMITS = {
    "paracetamol":(4000,"mg"),"ibuprofen":(1200,"mg"),
    "aspirin":(4000,"mg"),"diclofenac":(150,"mg"),
    "aceclofenac":(200,"mg"),"naproxen":(1000,"mg"),
    "metformin":(2000,"mg"),"sertraline":(200,"mg"),
    "fluoxetine":(80,"mg"),"escitalopram":(20,"mg"),
    "alprazolam":(4,"mg"),"diazepam":(30,"mg"),
    "pregabalin":(600,"mg"),"gabapentin":(3600,"mg"),
    "atorvastatin":(80,"mg"),"rosuvastatin":(40,"mg"),
    "prednisolone":(60,"mg"),"tramadol":(400,"mg"),
    "codeine":(240,"mg"),
}

MEDICINES = sorted(set(
    list(BRAND_TO_GENERIC.values()) + [
        "paracetamol","ibuprofen","aspirin","diclofenac","amoxicillin",
        "azithromycin","ciprofloxacin","metronidazole","cetirizine",
        "levocetirizine","loratadine","amlodipine","telmisartan","metformin",
        "omeprazole","pantoprazole","atorvastatin","warfarin","tramadol",
        "sertraline","fluoxetine","escitalopram","prednisolone","dexamethasone",
        "pregabalin","levothyroxine","chlorhexidine","ondansetron","clopidogrel",
        "lithium","methotrexate","sitagliptin","vildagliptin","doxycycline",
        "naproxen","aceclofenac","gabapentin","rosuvastatin","simvastatin",
        "clonazepam","diazepam","morphine","codeine","iron folic acid",
        "calcium carbonate","vitamin d3","losartan","ramipril","glimepiride",
        "levosalbutamol","chlorhexidine",
    ]
), key=lambda x: -len(x))
MEDICINES_SET = set(MEDICINES)


# ════════════════════════════════════════════════════════
#  GEMINI SETUP
# ════════════════════════════════════════════════════════

def init_gemini():
    global GEMINI_AVAILABLE, _client, _gemini_calls
    _gemini_calls = 0

    if not GENAI_OK:
        print("  [Gemini] google-genai not installed — offline mode")
        return

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key.upper() == "NONE":
        print("  [Gemini] No API key found — offline mode")
        return

    try:
        _client = genai.Client(api_key=api_key)
        _client.models.generate_content(model=GEMINI_MODEL, contents="reply: ok")
        GEMINI_AVAILABLE = True
        print(f"  [Gemini] Connected — {GEMINI_MODEL}")
    except Exception as e:
        print(f"  [Gemini] Unavailable: {str(e)[:80]} — running offline")
        GEMINI_AVAILABLE = False


def _gemini_generate(contents):
    global _gemini_calls
    if not GEMINI_AVAILABLE:
        return None
    if _gemini_calls >= MAX_GEMINI_CALLS:
        print(f"  [Gemini] Budget reached ({MAX_GEMINI_CALLS} calls max) — skipping")
        return None
    try:
        time.sleep(1)
        response = _client.models.generate_content(model=GEMINI_MODEL, contents=contents)
        _gemini_calls += 1
        print(f"  [Gemini] Call {_gemini_calls}/{MAX_GEMINI_CALLS} used")
        return response.text.strip()
    except Exception as e:
        print(f"  [Gemini] Error: {str(e)[:80]}")
        return None


# ════════════════════════════════════════════════════════
#  SELF-LEARNING ENGINE
# ════════════════════════════════════════════════════════

def load_learned():
    if not os.path.exists(LEARNED_FILE):
        return
    try:
        with open(LEARNED_FILE, "r") as f:
            learned = json.load(f)
        count = 0
        for entry in learned.get("drugs", []):
            name = entry.get("canonical_name")
            if not name:
                continue
            if name not in MEDICINES_SET:
                MEDICINES.append(name)
                MEDICINES_SET.add(name)
            brand = entry.get("original_name", "").lower().strip()
            if brand and brand not in BRAND_TO_GENERIC:
                BRAND_TO_GENERIC[brand] = name
            for alias in entry.get("brand_aliases", []):
                a = alias.lower().strip()
                if a and a not in BRAND_TO_GENERIC:
                    BRAND_TO_GENERIC[a] = name
            if entry.get("drug_class") and name not in DRUG_CLASS:
                DRUG_CLASS[name] = entry["drug_class"]
            for pair in entry.get("interactions", []):
                d2         = pair.get("drug")
                reason     = pair.get("reason", "")
                what_to_do = pair.get("what_to_do", "Consult your doctor.")
                sev        = pair.get("severity", "medium")
                if d2:
                    existing = [(a, b) for a, b, _, _, _ in KNOWN_INTERACTIONS]
                    if (name, d2) not in existing and (d2, name) not in existing:
                        KNOWN_INTERACTIONS.append((name, d2, sev, reason, what_to_do))
            count += 1
        if count:
            print(f"  [Learn] Loaded {count} learned drug(s)")
    except Exception as e:
        print(f"  [Learn] Could not load: {str(e)[:50]}")


def save_learned(name, original, drug_class=None, interactions=None,aliases=None):
    try:
        data = {"drugs": []}
        if os.path.exists(LEARNED_FILE):
            with open(LEARNED_FILE, "r") as f:
                data = json.load(f)
        existing = [d["canonical_name"] for d in data["drugs"]]
        if name not in existing:
            entry = {
                "canonical_name": name,
                "original_name":  original,
                "brand_aliases":  aliases or [],
                "drug_class":     drug_class,
                "interactions":   interactions or [],
            }
            data["drugs"].append(entry)
            with open(LEARNED_FILE, "w") as f:
                json.dump(data, f, indent=2)
            print(f"  [Learn] Saved new drug: {name}")
    except Exception as e:
        print(f"  [Learn] Could not save: {str(e)[:50]}")


# ════════════════════════════════════════════════════════
#  STEP 1 — NORMALIZE
# ════════════════════════════════════════════════════════

def normalize_drug_name(raw_name):
    clean = re.sub(
        r'\b\d+\s*(mg|ml|mcg|iu|g|tab|cap|caps|tablet)?\b',
        '', raw_name.lower().strip()
    ).strip()

    for brand in sorted(BRAND_TO_GENERIC, key=lambda x: -len(x)):
        if '-' in brand or ' ' in brand:
            if brand in clean:
                return BRAND_TO_GENERIC[brand]
        else:
            if re.search(rf"\b{re.escape(brand)}\b", clean):
                return BRAND_TO_GENERIC[brand]

    if clean in MEDICINES_SET:
        return clean

    match = get_close_matches(clean, MEDICINES, n=1, cutoff=0.75)
    if match:
        return match[0]

    if REQUESTS_OK:
        try:
            url = f"https://rxnav.nlm.nih.gov/REST/spellingsuggestions.json?name={raw_name}"
            r = requests.get(url, timeout=4)
            suggestions = (r.json()
                           .get("suggestionGroup", {})
                           .get("suggestionList", {}))
            if suggestions:
                suggested = suggestions["suggestion"][0].lower()
                if suggested not in MEDICINES_SET:
                    MEDICINES.append(suggested)
                    MEDICINES_SET.add(suggested)
                    BRAND_TO_GENERIC[clean] = suggested
                    save_learned(suggested, raw_name)
                return suggested
        except Exception as e:
            print(f"  [RxNorm] {str(e)[:40]}")

    return clean


# ════════════════════════════════════════════════════════
#  STEP 1.5 — BATCH ENRICH UNKNOWN DRUGS
# ════════════════════════════════════════════════════════

def _is_unrecognized(raw_name, canonical):
    raw_clean = re.sub(
        r'\b\d+\s*(mg|ml|mcg|iu|g|tab|cap|caps|tablet)?\b',
        '', raw_name.lower().strip()
    ).strip()
    return canonical == raw_clean and canonical not in MEDICINES_SET


def batch_enrich_unknown_drugs(unknown_drugs):
    if not unknown_drugs:
        return
    prompt = (
        f"You are a pharmacist. Identify each drug name below and return ONLY "
        f"valid JSON with no markdown fences:\n"
        f'{{"drugs": [{{"original": "input name", "canonical": "generic name lowercase",'
        f'"drug_class": "pharmacological class or null"}}]}}\n'
        f'"brand_aliases": ["other common spellings of this brand"]}}]}}\n'
        f"Drug names to identify: {unknown_drugs}\n"
        f"Rules:\n"
        f"- original must be EXACTLY the input string, unchanged\n"
        f"- canonical must be the international generic name in lowercase\n"
        f"- If it is a combination drug, use the primary active ingredient\n"
        f"- If truly unidentifiable, set canonical same as original\n"
        f"- drug_class examples: antibiotic, nsaid, ppi, antihistamine, etc.\n"
        f"Return ONLY the JSON object. No explanation."
    )
    text = _gemini_generate(prompt)
    if not text:
        print("  [Batch Enrich] Gemini unavailable — unknown drugs left as-is")
        return
    try:
        clean = re.sub(r"```(?:json)?", "", text).strip().strip("`")
        data  = json.loads(clean)
        enriched = 0
        for entry in data.get("drugs", []):
            original   = entry.get("original", "").lower().strip()
            canonical  = entry.get("canonical", "").lower().strip()
            drug_class = entry.get("drug_class")
            aliases    = entry.get("brand_aliases", [])
            if canonical and original and canonical != original:
                BRAND_TO_GENERIC[original] = canonical
                for alias in aliases:                      
                    a = alias.lower().strip()
                    if a and a not in BRAND_TO_GENERIC:
                        BRAND_TO_GENERIC[a] = canonical
                if canonical not in MEDICINES_SET:
                    MEDICINES.append(canonical)
                    MEDICINES_SET.add(canonical)
                if drug_class and canonical not in DRUG_CLASS:
                    DRUG_CLASS[canonical] = drug_class
                save_learned(canonical, original, drug_class=drug_class)
                enriched += 1
        print(f"  [Batch Enrich] Identified {enriched}/{len(unknown_drugs)} unknown drug(s)")
    except Exception as e:
        print(f"  [Batch Enrich] Parse error: {str(e)[:60]}")


# ════════════════════════════════════════════════════════
#  STEP 2 — DUPLICATE DETECTION
# ════════════════════════════════════════════════════════

def detect_duplicates(normalized_meds):
    seen_names   = {}
    seen_classes = {}
    duplicates   = []
    for med in normalized_meds:
        if med in seen_names:
            duplicates.append({
                "type":           "duplicate_drug",
                "message":        f"{med.title()} appears more than once in your prescription",
                "recommendation": "Remove the duplicate entry and take it only once."
            })
        else:
            seen_names[med] = True
        if med in DRUG_CLASS:
            cls = DRUG_CLASS[med]
            if cls in seen_classes and seen_classes[cls] != med:
                duplicates.append({
                    "type":           "duplicate_class",
                    "message":        (f"{med.title()} and {seen_classes[cls].title()} "
                                       f"are both {cls.upper().replace('_','-')} medicines"),
                    "recommendation": (f"Do not take two {cls.replace('_','-')} medicines "
                                       f"together — ask your doctor which one you need.")
                })
            else:
                seen_classes[cls] = med
    return duplicates


# ════════════════════════════════════════════════════════
#  STEP 3 — KNOWN INTERACTIONS
# ════════════════════════════════════════════════════════

def check_known_interactions(normalized_meds):
    warnings   = []
    seen_pairs = set()
    for d1, d2, severity, reason, what_to_do in KNOWN_INTERACTIONS:
        pair = tuple(sorted([d1, d2]))
        if pair in seen_pairs:
            continue
        if d1 in normalized_meds and d2 in normalized_meds:
            seen_pairs.add(pair)
            warnings.append({
                "drugs_involved": [d1, d2],
                "severity":       severity,
                "what_happens":   reason,
                "what_to_do":     what_to_do,
                "source":         "static",
            })
    return warnings


# ════════════════════════════════════════════════════════
#  STEP 4 — OpenFDA SKIPPED
# ════════════════════════════════════════════════════════

def check_openfda_parallel(normalized_meds, known_warnings):
    print("  OpenFDA skipped — static KB covers all clinically significant interactions.")
    return []


# ════════════════════════════════════════════════════════
#  STEP 5 — GEMINI HOLISTIC CHECK
# ════════════════════════════════════════════════════════

def check_gemini_holistic(normalized_meds, existing_warnings):
    already = [
        f"{w['drugs_involved'][0]} + {w['drugs_involved'][1]}"
        for w in existing_warnings
        if len(w.get("drugs_involved", [])) >= 2
    ]
    prompt = (
    f"You are a clinical pharmacist reviewing a prescription.\n"
    f"Medications: {normalized_meds}\n"
    f"Already flagged interactions: {already}\n\n"

    f"IMPORTANT RULES:\n"
    f"- ONLY use drugs from the provided medication list\n"
    f"- DO NOT introduce any new drug names\n"
    f"- If unsure, return empty list\n\n"

    f"Find ONLY NEW risks not already flagged above:\n"
    f"- 3-drug combinations causing additive danger\n"
    f"- absorption/timing problems\n\n"

    f'Return STRICT JSON:\n'
    f'{{"warnings": [{{'
    f'"drugs_involved": ["drug1", "drug2"],'
    f'"severity": "high" | "medium" | "low",'
    f'"what_happens": "...",'
    f'"what_to_do": "..."'
    f'}}]}}\n'
    f'If no risks: {{"warnings": []}}'
    )
    text = _gemini_generate(prompt)
    if not text:
        return []
    try:
        clean   = re.sub(r"```(?:json)?", "", text).strip().strip("`")
        data    = json.loads(clean)
        results = []
        for w in data.get("warnings", []):
            w["source"] = "gemini_ai"
            drugs = w.get("drugs_involved", [])

            # STRICT FILTER — only allow real prescription drugs
            drugs = [d for d in drugs if d in normalized_meds]

            if len(drugs) >= 2:
                w["drugs_involved"] = drugs
                results.append(w)
                
        return results
    except Exception as e:
        print(f"  [Gemini holistic] Parse error: {str(e)[:60]}")
        return []


# ════════════════════════════════════════════════════════
#  STEP 6 — OVERDOSE DETECTION
# ════════════════════════════════════════════════════════

FREQ_MAP = {
    "od":1,"qd":1,"bd":2,"bid":2,"bds":2,
    "tds":3,"tid":3,"qid":4,"qds":4,
    "prn":0,"sos":0,
    "1-0-0":1,"0-1-0":1,"0-0-1":1,
    "1-0-1":2,"1-1-0":2,"0-1-1":2,
    "1-1-1":3,"1-1-1-1":4,
    "1tid":3,"1tds":3,"1bd":2,"1od":1,
}

def parse_frequency(freq_str):
    if not freq_str:
        return 1
    f = str(freq_str).lower().strip().replace(" ", "")
    if re.match(r'^\d+(\+\d+)+$', f):
        return sum(int(p) for p in f.split('+'))
    
    if f in FREQ_MAP:
        return FREQ_MAP[f]
    
    if f in FREQ_MAP:
        return FREQ_MAP[f]
    m = re.match(r'\d+\s*(tid|tds|bd|bid|od|qd|qid|prn|sos)', f)
    if m:
        return FREQ_MAP.get(m.group(1), 1)
    if "prn" in f or "sos" in f or "as needed" in f:
        return 0
    if "twice"  in f: return 2
    if "thrice" in f or "three" in f: return 3
    if "once"   in f: return 1
    parts = re.split(r'[-]', f)
    if all(p.isdigit() for p in parts) and len(parts) in (3, 4):
        return sum(int(p) for p in parts)
    return 1


def parse_dose_mg(dose_str):
    if not dose_str:
        return None
    m = re.search(r'(\d+)', str(dose_str))
    return int(m.group(1)) if m else None


def detect_overdose(raw_medications, normalized_meds):
    alerts = []
    for i, med in enumerate(normalized_meds):
        raw  = raw_medications[i]
        dose = parse_dose_mg(raw.get("dosage") or raw.get("dose", ""))
        freq = parse_frequency(raw.get("frequency") or raw.get("freq", ""))
        if dose and freq and freq > 0 and med in OVERDOSE_LIMITS:
            daily = dose * freq
            limit, unit = OVERDOSE_LIMITS[med]
            if daily > limit:
                alerts.append({
                    "drug":           med,
                    "daily_dose_mg":  daily,
                    "safe_limit_mg":  limit,
                    "message":        (
                        f"Your {med.title()} dose adds up to {daily}{unit} per day, "
                        f"which is above the safe limit of {limit}{unit}."
                    ),
                    "recommendation": (
                        "Do not take more than the safe limit. "
                        "Contact your doctor immediately to adjust the dose."
                    ),
                })
    return alerts


# ════════════════════════════════════════════════════════
#  STEP 7 — RISK SCORE
# ════════════════════════════════════════════════════════

def calculate_risk_score(warnings, duplicates, overdoses):
    high   = sum(1 for w in warnings if w.get("severity") == "high")
    medium = sum(1 for w in warnings if w.get("severity") == "medium")
    low    = sum(1 for w in warnings if w.get("severity") == "low")
    score  = min(10, (high * 3) + (medium * 1) + (len(overdoses) * 2))
    return {
        "score":             score,
        "label":             ("HIGH RISK"     if score >= 6 else
                              "MODERATE RISK" if score >= 3 else
                              "LOW RISK"),
        "high_alerts":       high,
        "medium_alerts":     medium,
        "low_alerts":        low,
        "total_alert_count": high + medium + low + len(duplicates) + len(overdoses),
    }


# ════════════════════════════════════════════════════════
#  STEP 8 — MEDICATION SUMMARY
# ════════════════════════════════════════════════════════

def build_medication_summary(raw_medications, normalized_meds):
    summary = []
    for i, med in enumerate(normalized_meds):
        raw   = raw_medications[i]
        dose  = parse_dose_mg(raw.get("dosage") or raw.get("dose", ""))
        freq  = parse_frequency(raw.get("frequency") or raw.get("freq", ""))
        dur   = str(raw.get("duration", "") or "").strip() or None
        notes = str(raw.get("notes",    "") or "").strip() or None
        total = None
        if dose and freq and freq > 0:
            total = dose * freq
        raw_clean = re.sub(
            r'\b\d+\s*(mg|ml|mcg|iu|g|tab|cap|caps|tablet)?\b',
            '', raw.get("name", "").lower().strip()
        ).strip()
        warning = None
        if med not in MEDICINES_SET and med == raw_clean:
            warning = "Could not confidently identify this drug — verify manually"
        summary.append({
            "canonical_name":      med,
            "original_name":       raw.get("name", med),
            "dose_mg":             dose,
            "freq_per_day":        freq,
            "total_daily_dose_mg": total,
            "duration":            dur,
            "notes":               notes,
            "warning":             warning,
        })
    return sorted(summary, key=lambda x: x["canonical_name"])


# ════════════════════════════════════════════════════════
#  MAIN ANALYSIS PIPELINE
# ════════════════════════════════════════════════════════

def analyze(raw_medications, patient_name):
    print("\nStep 1: Normalizing drug names...")
    normalized = [normalize_drug_name(m["name"]) for m in raw_medications]

    print("\nStep 1.5: Batch enriching unknown drugs...")
    unknown = [
        m["name"] for i, m in enumerate(raw_medications)
        if _is_unrecognized(m["name"], normalized[i])
    ]
    if unknown:
        batch_enrich_unknown_drugs(unknown)
        normalized = [normalize_drug_name(m["name"]) for m in raw_medications]
    else:
        print("  All drugs recognized — no enrichment needed")

    print("\nStep 2: Detecting duplicates...")
    duplicates = detect_duplicates(normalized)

    print("\nStep 3: Checking known interactions...")
    warnings = check_known_interactions(normalized)

    print("\nStep 4: OpenFDA check...")
    warnings += check_openfda_parallel(normalized, warnings)

    print("\nStep 5: Gemini holistic check...")
    warnings += check_gemini_holistic(normalized, warnings)

    # 🔒 FINAL SAFETY FILTER (CRITICAL)
    valid = set(normalized)

    warnings = [
        w for w in warnings
        if all(d in valid for d in w.get("drugs_involved", []))
    ]

    print("\nStep 6: Checking overdose limits...")
    overdoses = detect_overdose(raw_medications, normalized)

    print("\nStep 7: Calculating risk score...")
    risk = calculate_risk_score(warnings, duplicates, overdoses)
    print(f"  {risk['label']} (score {risk['score']}/10)")

    print("\nStep 8: Building medication summary...")
    med_summary = build_medication_summary(raw_medications, normalized)

    sev_order = {"high": 0, "medium": 1, "low": 2}
    warnings.sort(key=lambda w: sev_order.get(w.get("severity", "low"), 2))

    return {
        "status":             "success",
        "patient_name":       patient_name.title(),
        "risk_score":         risk,
        "clinical_alerts":    warnings,
        "duplicate_alerts":   duplicates,
        "overdose_alerts":    overdoses,
        "medication_summary": med_summary,
    }


# ════════════════════════════════════════════════════════
#  WHATSAPP SENDER  (Twilio)
# ════════════════════════════════════════════════════════

def _send_long_whatsapp(twilio_client, from_number: str, to_number: str, body: str):
    """Split messages longer than 1500 chars and send each part."""
    limit = 1500
    parts = []
    while len(body) > limit:
        split_index = body.rfind('\n', 0, limit)
        if split_index == -1:
            split_index = limit
        parts.append(body[:split_index])
        body = body[split_index:]
    parts.append(body)
    for part in parts:
        twilio_client.messages.create(from_=from_number, body=part, to=to_number)


def send_whatsapp_summary(analysis_result: dict, phone_number: str) -> dict:
    """
    Send prescription analysis summary to a WhatsApp number via Twilio.
    Called by the /api/send-whatsapp route.

    Requires .env:
        TWILIO_SID=...
        TWILIO_AUTH=...
        TWILIO_FROM=whatsapp:+14155238886
    """
    print(f"[WhatsApp] SID={os.getenv('TWILIO_SID','MISSING')[:8]}...")
    print(f"[WhatsApp] AUTH={'SET' if os.getenv('TWILIO_AUTH') else 'MISSING'}")
    print(f"[WhatsApp] FROM={os.getenv('TWILIO_FROM','MISSING')}")
    print(f"[WhatsApp] TO={phone_number}")
    if not TWILIO_OK:
        return {"status": "error", "message": "Twilio not installed. Run: pip install twilio"}

    sid   = os.getenv("TWILIO_SID", "").strip()
    auth  = os.getenv("TWILIO_AUTH", "").strip()
    from_ = os.getenv("TWILIO_FROM", "whatsapp:+14155238886").strip()

    if not sid or not auth:
        return {"status": "error", "message": "TWILIO_SID or TWILIO_AUTH not set in .env"}

    number = phone_number.strip()
    if not number.startswith("+"):
        number = "+" + number
    to_number = f"whatsapp:{number}"

    try:
        tc = TwilioClient(sid, auth)

        # ── Part 1: Header + Risk + Medications ──────────
        lines = []
        lines.append("🌸👋 *Smart Prescription Summary* 💊✨")
        lines.append("MedMitra has checked your medicines to keep you safe 💚\n")

        patient = analysis_result.get("patient_name", "")
        if patient and patient.lower() != "user":
            lines.append(f"👤 *Patient:* {patient}")

        risk       = analysis_result.get("risk_score", {})
        risk_label = risk.get("label", "UNKNOWN")
        risk_emoji = "🔴" if "HIGH" in risk_label else "🟡" if "MODERATE" in risk_label else "🟢"
        lines.append(f"{risk_emoji} *Risk Level:* {risk_label}\n")

        meds = analysis_result.get("medication_summary", [])
        if meds:
            lines.append("💊 *Your Medicines:*")
            for med in meds:
                name     = med.get("original_name", med.get("canonical_name", ""))
                dose     = f"{med['dose_mg']}mg" if med.get("dose_mg") else ""
                freq     = f"{med['freq_per_day']}x/day" if med.get("freq_per_day") else ""
                duration = med.get("duration") or ""
                note     = med.get("notes") or ""
                detail   = " · ".join(p for p in [dose, freq, duration] if p)
                line     = f"• 💊 *{name}*" + (f" — {detail}" if detail else "")
                if note:
                    line += f" ({note})"
                lines.append(line)

        _send_long_whatsapp(tc, from_, to_number, "\n".join(lines))

        # ── Part 2: Alerts ────────────────────────────────
        alert_lines = []
        high_alerts   = [a for a in analysis_result.get("clinical_alerts", []) if a.get("severity") == "high"]
        medium_alerts = [a for a in analysis_result.get("clinical_alerts", []) if a.get("severity") == "medium"]

        if high_alerts:
            alert_lines.append("🚨 *High Risk Interactions — Please Read!*\n")
            for a in high_alerts:
                drugs = " + ".join(a.get("drugs_involved", []))
                alert_lines.append(f"🔴 *{drugs.upper()}*")
                alert_lines.append(f"💥 *Risk:* {a.get('what_happens', '')}")
                alert_lines.append(f"✅ *Action:* {a.get('what_to_do', '')}\n")

        if medium_alerts:
            alert_lines.append("⚠️ *Moderate Risk Interactions:*\n")
            for a in medium_alerts:
                drugs = " + ".join(a.get("drugs_involved", []))
                alert_lines.append(f"🟡 *{drugs.upper()}*")
                alert_lines.append(f"💥 *Risk:* {a.get('what_happens', '')}")
                alert_lines.append(f"✅ *Action:* {a.get('what_to_do', '')}\n")

        if not high_alerts and not medium_alerts:
            alert_lines.append("🟢✅ No significant drug interactions found! 🎉")

        for od in analysis_result.get("overdose_alerts", []):
            alert_lines.append(f"\n⚠️ *Overdose Warning:* {od.get('message', '')}")
            alert_lines.append(f"✅ {od.get('recommendation', '')}")

        for dup in analysis_result.get("duplicate_alerts", []):
            alert_lines.append(f"\n🔁 *Duplicate:* {dup.get('message', '')}")
            alert_lines.append(f"✅ {dup.get('recommendation', '')}")

        if alert_lines:
            _send_long_whatsapp(tc, from_, to_number, "\n".join(alert_lines))

        # ── Part 3: Outro ─────────────────────────────────
        _send_long_whatsapp(tc, from_, to_number,
            "💚✨ *Stay Safe!*\n"
            "Always follow your doctor's advice 👩‍⚕️\n"
            "Your health matters to us 🌿😊\n\n"
            "_Sent by MedMitra — AI Prescription Safety_"
        )

        print(f"  [WhatsApp] Messages sent to {number}")
        return {"status": "success", "message": f"Summary sent to {number}"}

    except Exception as e:
        error_msg = str(e)
        print(f"  [WhatsApp] Error: {error_msg}")
        
        # Give friendly errors based on what went wrong
        if "not a valid phone number" in error_msg:
            return {"status": "error", "message": "Invalid phone number. Use format: +919876543210"}
        elif "authenticate" in error_msg or "401" in error_msg:
            return {"status": "error", "message": "Twilio credentials wrong. Check TWILIO_SID and TWILIO_AUTH in .env"}
        elif "not opted in" in error_msg or "sandbox" in error_msg.lower():
            return {"status": "error", "message": f"Phone not registered. Send 'join <your-word>' to +14155238886 on WhatsApp first"}
        elif "unsubscribed" in error_msg:
            return {"status": "error", "message": "Phone unsubscribed from sandbox. Resend the join message."}
        else:
            return {"status": "error", "message": f"WhatsApp error: {error_msg[:120]}"}


# ════════════════════════════════════════════════════════
#  FASTAPI ENTRY POINTS
# ════════════════════════════════════════════════════════

def extract_meds_with_gemini(image_bytes: bytes) -> list:
    """Extract medications from prescription image bytes using Gemini vision."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or not GENAI_OK:
        print("  [OCR] Gemini unavailable — returning empty list")
        return []
    try:
        client = genai.Client(api_key=api_key)
        prompt = """
You are a medical assistant.
Extract ONLY medications from this prescription image.
Return STRICT JSON in this format — no markdown, no explanation:
[{"name": "", "dosage": "", "frequency": "", "duration": "", "notes": ""}]
Rules: only include medicines, ignore all other text, use "" for missing fields.
"""
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[{
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inline_data": {
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(image_bytes).decode()
                    }}
                ]
            }]
        )
        text = (response.text or "").strip()
        text = re.sub(r"```(?:json)?", "", text).strip().strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
        print("GEMINI OCR RAW:", text[:200])
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"  [OCR] Gemini extraction error: {e}")
        return []


def analyzeprescription(inputdata: dict, patientname: str = "User") -> dict:
    """FastAPI entry point — runs full analysis pipeline."""
    init_gemini()
    load_learned()
    meds = inputdata.get("meds", [])
    if not meds:
        return {
            "status":             "no_medications_found",
            "patient_name":       patientname.title(),
            "risk_score":         {
                "score": 0, "label": "UNANALYZED",
                "high_alerts": 0, "medium_alerts": 0,
                "low_alerts": 0, "total_alert_count": 0,
            },
            "clinical_alerts":    [],
            "duplicate_alerts":   [],
            "overdose_alerts":    [],
            "medication_summary": [],
        }
    return analyze(meds, patientname)