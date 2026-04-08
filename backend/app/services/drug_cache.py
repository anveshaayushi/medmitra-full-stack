# app/services/drug_cache.py
"""
Drug Dataset Cache
==================
- Checks local drug_dataset.json first
- Only calls Gemini for unknown/incomplete drugs
- Saves new findings back to dataset
- Handles brand name → generic name mapping
"""

import json
import os
import re
from pathlib import Path

DATASET_PATH = Path(__file__).parent / "drug_dataset.json"


def _load_dataset() -> dict:
    try:
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": "1.0", "drugs": {}}


def _save_dataset(data: dict):
    try:
        with open(DATASET_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  [Cache] Could not save: {e}")


def _normalize(name: str) -> str:
    """Lowercase, strip numbers and units for lookup."""
    return re.sub(
        r'\b\d+\s*(mg|ml|mcg|iu|g|tab|cap|tablet)?\b', '',
        name.lower().strip()
    ).strip()


def lookup_drug(raw_name: str) -> dict | None:
    """
    Look up a drug by brand or generic name.
    Returns drug dict if found, None if not in dataset.
    """
    data    = _load_dataset()
    drugs   = data.get("drugs", {})
    cleaned = _normalize(raw_name)

    # Direct generic name match
    if cleaned in drugs:
        return drugs[cleaned]

    # Brand name search
    for generic, info in drugs.items():
        brands = [b.lower() for b in info.get("brand_names", [])]
        if cleaned in brands or any(cleaned in b for b in brands):
            return info

    return None


def save_drug_to_dataset(drug_info: dict):
    """
    Save a newly discovered drug back to the dataset.
    Called after Gemini identifies an unknown drug.
    """
    canonical = drug_info.get("canonical_name", "").lower().strip()
    if not canonical:
        return

    data = _load_dataset()
    drugs = data.setdefault("drugs", {})

    if canonical not in drugs:
        drugs[canonical] = {
            "canonical_name":    canonical,
            "brand_names":       drug_info.get("brand_names", []),
            "drug_class":        drug_info.get("drug_class"),
            "overdose_limit_mg": drug_info.get("overdose_limit_mg"),
            "interactions":      drug_info.get("interactions", []),
            "notes":             drug_info.get("notes"),
            "source":            "gemini_learned",
        }
        _save_dataset(data)
        print(f"  [Cache] Saved new drug: {canonical}")
    else:
        # Merge missing fields only
        existing = drugs[canonical]
        changed  = False
        for field in ["drug_class", "overdose_limit_mg", "notes"]:
            if not existing.get(field) and drug_info.get(field):
                existing[field] = drug_info[field]
                changed = True
        # Add new interactions not already present
        existing_pairs = {
            tuple(sorted([canonical, i["with"]]))
            for i in existing.get("interactions", [])
        }
        for interaction in drug_info.get("interactions", []):
            pair = tuple(sorted([canonical, interaction.get("with", "")]))
            if pair not in existing_pairs:
                existing.setdefault("interactions", []).append(interaction)
                changed = True
        if changed:
            _save_dataset(data)
            print(f"  [Cache] Updated drug: {canonical}")


def get_known_interactions(drug_names: list[str]) -> list[dict]:
    """
    Get all known interactions between the given list of drugs
    purely from the local dataset — no API call needed.
    Returns list of interaction alert dicts.
    """
    data   = _load_dataset()
    drugs  = data.get("drugs", {})
    alerts = []
    seen   = set()

    resolved = {}
    for name in drug_names:
        cleaned = _normalize(name)
        info    = None
        if cleaned in drugs:
            info = drugs[cleaned]
        else:
            for generic, drug_info in drugs.items():
                brands = [b.lower() for b in drug_info.get("brand_names", [])]
                if cleaned in brands or any(cleaned in b for b in brands):
                    info = drug_info
                    break
        if info:
            resolved[name] = info

    for orig_name, drug_info in resolved.items():
        canonical = drug_info["canonical_name"]
        for interaction in drug_info.get("interactions", []):
            partner_generic = interaction.get("with", "")
            # Check if the partner drug is also in the prescription
            partner_present = any(
                resolved[n]["canonical_name"] == partner_generic
                for n in resolved
                if n != orig_name
            )
            if not partner_present:
                continue
            pair = tuple(sorted([canonical, partner_generic]))
            if pair in seen:
                continue
            seen.add(pair)
            alerts.append({
                "type":          "interaction",
                "severity":      interaction.get("severity", "medium"),
                "message":       f"{orig_name} interacts with {partner_generic}",
                "mechanism":     interaction.get("mechanism"),
                "recommendation": interaction.get("recommendation"),
                "drugs_involved": [orig_name, partner_generic],
                "source":        "local_dataset",
            })

    return alerts