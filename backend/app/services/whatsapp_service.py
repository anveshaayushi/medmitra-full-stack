import os
from twilio.rest import Client as TwilioClient

# ── Changes from original twilio.py ──────────────────────────────────────
# 1. Removed top-level script block (json.load, input(), direct sends)
# 2. Removed hardcoded file reading — receives analysis_result dict directly
# 3. Exposed send_whatsapp_summary(analysis_result, phone_number) -> dict
# 4. _send_long_message() and message formatting identical to original
# ──────────────────────────────────────────────────────────────────────────


def _send_long_message(client, from_number: str, to_number: str, body: str):
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
        client.messages.create(from_=from_number, body=part, to=to_number)


def send_whatsapp_summary(analysis_result: dict, phone_number: str) -> dict:
    """
    Send prescription analysis summary to a WhatsApp number via Twilio.
    Reads credentials from environment variables:
        TWILIO_SID, TWILIO_AUTH, TWILIO_FROM
    """
    sid   = os.getenv("TWILIO_SID",  "").strip()
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

        # ── Part 1: Intro + Medications (same structure as original) ──────
        part1_lines = []
        part1_lines.append("🌸👋 *Smart Prescription Summary* 💊✨")
        part1_lines.append("We've checked your medicines to keep you safe 💚\n")

        patient = analysis_result.get("patient_name", "")
        if patient and patient.lower() != "user":
            part1_lines.append(f"👤 *Patient:* {patient}")

        risk       = analysis_result.get("risk_score", {})
        risk_label = risk.get("label", "UNKNOWN")
        risk_emoji = "🔴" if "HIGH" in risk_label else "🟡" if "MODERATE" in risk_label else "🟢"
        part1_lines.append(f"{risk_emoji} *Risk Level:* {risk_label}\n")

        meds = analysis_result.get("medication_summary", [])
        if meds:
            part1_lines.append("💊 *Your Medicines:* 📝")
            for med in meds:
                # Support both flat and variants format
                name     = med.get("original_name") or med.get("canonical_name", "")
                dose     = med.get("dose_mg")
                freq     = med.get("freq_per_day")
                duration = med.get("duration") or ""
                note     = med.get("notes") or ""

                line = f"• 💊 *{name}*"
                if dose:
                    line += f" {dose}mg"
                if freq:
                    line += f" — {freq}x/day"
                if duration:
                    line += f" for {duration}"
                if note:
                    line += f" ({note})"
                part1_lines.append(line)

        _send_long_message(tc, from_, to_number, "\n".join(part1_lines))

        # ── Part 2: High risk alerts (same as original) ───────────────────
        part2_lines = []
        high_alerts = [
            a for a in analysis_result.get("clinical_alerts", [])
            if a.get("severity") == "high"
        ]
        medium_alerts = [
            a for a in analysis_result.get("clinical_alerts", [])
            if a.get("severity") == "medium"
        ]

        if high_alerts:
            part2_lines.append("🚨⚠️ *High Risk Interactions Detected!*")
            part2_lines.append("Please read carefully 🧠💡\n")
            for alert in high_alerts:
                drugs = " + ".join(alert.get("drugs_involved") or [])
                # Support both old (what_happens) and new (message/mechanism) keys
                risk_text   = alert.get("what_happens") or alert.get("mechanism") or alert.get("message", "")
                action_text = alert.get("what_to_do")   or alert.get("recommendation") or "Consult your doctor."
                part2_lines.append(f"🔴⚠️ *{drugs.upper()}*")
                part2_lines.append(f"💥 *Risk:* {risk_text}")
                part2_lines.append(f"✅ *What to do:* {action_text}\n")

        if medium_alerts:
            part2_lines.append("⚠️ *Moderate Risk Interactions:*\n")
            for alert in medium_alerts:
                drugs = " + ".join(alert.get("drugs_involved") or [])
                risk_text   = alert.get("what_happens") or alert.get("mechanism") or alert.get("message", "")
                action_text = alert.get("what_to_do")   or alert.get("recommendation") or "Consult your doctor."
                part2_lines.append(f"🟡 *{drugs.upper()}*")
                part2_lines.append(f"💥 *Risk:* {risk_text}")
                part2_lines.append(f"✅ *What to do:* {action_text}\n")

        if not high_alerts and not medium_alerts:
            part2_lines.append("🟢✅ No significant interactions found! 🎉")

        _send_long_message(tc, from_, to_number, "\n".join(part2_lines))

        # ── Part 3: Outro (same as original) ─────────────────────────────
        _send_long_message(tc, from_, to_number,
            "💚✨ *Take care!*\n"
            "Always follow your doctor's advice 👩‍⚕️👨‍⚕️\n"
            "Your health matters to us 🌿😊\n\n"
            "_Sent by MedMitra — AI Prescription Safety_"
        )

        print(f"  [WhatsApp] Messages sent to {number}")
        return {"status": "success", "message": f"Summary sent to {number}"}

    except Exception as e:
        error_msg = str(e)
        print(f"  [WhatsApp] Error: {error_msg}")
        if "not a valid phone number" in error_msg:
            return {"status": "error", "message": "Invalid phone number format. Use: +919876543210"}
        elif "authenticate" in error_msg or "401" in error_msg:
            return {"status": "error", "message": "Twilio credentials wrong. Check TWILIO_SID and TWILIO_AUTH"}
        elif "not opted in" in error_msg or "sandbox" in error_msg.lower():
            return {"status": "error", "message": "Phone not registered. Send 'join <your-word>' to +14155238886 on WhatsApp first"}
        else:
            return {"status": "error", "message": f"WhatsApp error: {error_msg[:120]}"}