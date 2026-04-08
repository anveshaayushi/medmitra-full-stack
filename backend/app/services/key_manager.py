# app/services/key_manager.py
"""
Smart API Key Manager
=====================
- Rotates through multiple Gemini API keys
- Tracks usage per key
- Switches BEFORE exhaustion (at 80% usage)
- Falls back to next key on any rate limit error
"""

import os
import json
import time
from pathlib import Path

USAGE_FILE = Path(__file__).parent / "key_usage.json"
DAILY_LIMIT = 20       # Gemini free tier limit per key
SWITCH_AT   = 15        # Switch to next key when this many calls used (80%)


def _load_usage() -> dict:
    try:
        with open(USAGE_FILE, "r") as f:
            data = json.load(f)
        # Reset if it's a new day
        today = time.strftime("%Y-%m-%d")
        if data.get("date") != today:
            return {"date": today, "keys": {}}
        return data
    except Exception:
        return {"date": time.strftime("%Y-%m-%d"), "keys": {}}


def _save_usage(data: dict):
    try:
        with open(USAGE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"  [KeyMgr] Could not save usage: {e}")


def _get_all_keys() -> list[str]:
    """
    Load all API keys from environment.
    Add keys as GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.
    Falls back to GEMINI_API_KEY if only one key.
    """
    keys = []
    # Primary key
    primary = os.getenv("GEMINI_API_KEY", "").strip()
    if primary:
        keys.append(primary)
    # Additional keys
    i = 1
    while True:
        key = os.getenv(f"GEMINI_API_KEY_{i}", "").strip()
        if not key:
            break
        keys.append(key)
        i += 1
    return keys


def get_best_key() -> str | None:
    """
    Returns the best available API key.
    Prefers keys with most remaining quota.
    Switches BEFORE hitting limit (at SWITCH_AT calls).
    """
    keys  = _get_all_keys()
    if not keys:
        return None

    usage = _load_usage()
    key_usage = usage.setdefault("keys", {})

    # Find best key — lowest usage that hasn't hit SWITCH_AT
    best_key       = None
    best_remaining = -1

    for key in keys:
        short = key[-8:]  # Use last 8 chars as identifier
        calls = key_usage.get(short, {}).get("calls", 0)
        exhausted = key_usage.get(short, {}).get("exhausted", False)

        if exhausted:
            continue

        remaining = DAILY_LIMIT - calls
        if calls < SWITCH_AT and remaining > best_remaining:
            best_remaining = remaining
            best_key = key

    # If all keys hit SWITCH_AT, use any non-exhausted one
    if not best_key:
        for key in keys:
            short     = key[-8:]
            exhausted = key_usage.get(short, {}).get("exhausted", False)
            calls     = key_usage.get(short, {}).get("calls", 0)
            if not exhausted and calls < DAILY_LIMIT:
                best_key = key
                break

    if best_key:
        short    = best_key[-8:]
        calls    = key_usage.get(short, {}).get("calls", 0)
        remaining = DAILY_LIMIT - calls
        print(f"  [KeyMgr] Using key ...{short} ({calls} used, {remaining} remaining)")

    return best_key


def record_key_usage(key: str, exhausted: bool = False):
    """Call this after every successful Gemini API call."""
    usage = _load_usage()
    short = key[-8:]
    entry = usage["keys"].setdefault(short, {"calls": 0, "exhausted": False})
    entry["calls"] += 1
    if exhausted:
        entry["exhausted"] = True
        print(f"  [KeyMgr] Key ...{short} marked exhausted")
    elif entry["calls"] >= SWITCH_AT:
        print(f"  [KeyMgr] Key ...{short} approaching limit ({entry['calls']}/{DAILY_LIMIT}) — will prefer other keys")
    _save_usage(usage)


def mark_key_exhausted(key: str):
    """Call this when a key hits rate limit error."""
    usage = _load_usage()
    short = key[-8:]
    usage["keys"].setdefault(short, {"calls": 0, "exhausted": False})
    usage["keys"][short]["exhausted"] = True
    _save_usage(usage)
    print(f"  [KeyMgr] Key ...{short} exhausted — switching to next key")