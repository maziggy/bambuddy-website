"""Commercial lead relay for bambuddy.cool.

Receives structured enquiries from the appliance / business pages and emails
them to the right role address (appliance@ or business@), with the sender set
as Reply-To so a reply goes straight back to the prospect.

Deployed in the SAME process as the bug-report relay (see wsgi.py) so it shares
one gunicorn worker, one systemd unit, and the app-level CORS handler. It reuses
the bug relay's SMTP_* environment variables — no new secrets required. The only
optional new vars are the destination addresses, which default to the role
mailboxes.

Design notes:
  * Independent abuse counters. Leads are a handful/day; a bug-relay flood must
    not exhaust the lead budget and vice versa, so the two modules keep separate
    per-IP / global / dedup state.
  * Honeypot ("website" field). Bots fill every field; a real browser leaves the
    hidden one empty. A filled honeypot returns a 200 that LOOKS accepted but
    sends nothing, so the bot has no signal to adapt.
  * No PII in logs. The prospect's email and message never hit the log — only
    the interest bucket, the outcome, and the client IP.
"""

import logging
import os
import re
import smtplib
import threading
import time
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

lead_bp = Blueprint("lead", __name__)

# SMTP config — shared with the bug relay (same /etc/bambuddy-relay/env file).
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", "")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "starttls").lower()  # "starttls", "ssl", or "none"

# Where each interest routes. Overridable via env; defaults to the role mailboxes.
LEAD_TO_APPLIANCE = os.environ.get("LEAD_TO_APPLIANCE", "appliance@bambuddy.cool")
LEAD_TO_BUSINESS = os.environ.get("LEAD_TO_BUSINESS", "business@bambuddy.cool")

# --- Field vocabularies (server-side allow-lists; anything else is coerced) ---
# appliance-page interests route to the appliance mailbox; business-page
# interests route to the business mailbox. The label is what lands in the email.
INTEREST_ROUTING = {
    "buy_appliance": ("Buy an appliance", LEAD_TO_APPLIANCE),
    "reseller": ("Become a reseller", LEAD_TO_APPLIANCE),
    "support": ("Priority support / SLA", LEAD_TO_BUSINESS),
    "licensing": ("Commercial / redistribution licence", LEAD_TO_BUSINESS),
    "custom_dev": ("Deployment / custom development", LEAD_TO_BUSINESS),
}
PRINTERS_LABELS = {
    "1-5": "1-5 printers",
    "6-15": "6-15 printers",
    "16-40": "16-40 printers",
    "40+": "40+ printers",
}
TIMEFRAME_LABELS = {
    "now": "Ready now",
    "quarter": "This quarter",
    "exploring": "Just exploring",
}

# --- Abuse controls (independent of the bug relay) ------------------------
RATE_LIMIT_WINDOW = 3600
RATE_LIMIT_MAX = int(os.environ.get("LEAD_RATE_LIMIT_MAX", "5"))    # per IP / hour
GLOBAL_WINDOW = 3600
GLOBAL_MAX = int(os.environ.get("LEAD_GLOBAL_MAX", "30"))          # total / hour
DEDUP_WINDOW = int(os.environ.get("LEAD_DEDUP_WINDOW", "3600"))    # identical (email,msg) / window

_lock = threading.Lock()
_rate_limits: dict[str, list[float]] = {}
_global_sends: list[float] = []
_recent: dict[str, float] = {}

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MAX_MESSAGE = 4000
_MAX_FIELD = 200


def _within(seq: list[float], now: float, window: int) -> list[float]:
    return [t for t in seq if now - t < window]


def _check_rate_limit(ip: str) -> bool:
    now = time.time()
    with _lock:
        stamps = _within(_rate_limits.get(ip, []), now, RATE_LIMIT_WINDOW)
        if len(stamps) >= RATE_LIMIT_MAX:
            _rate_limits[ip] = stamps
            return False
        stamps.append(now)
        _rate_limits[ip] = stamps
        return True


def _check_global_and_dedup(fingerprint: str) -> str | None:
    """Read-only gate. A slot is only committed in _record_send() after the mail
    actually goes out, so an SMTP outage never burns the budget or blocks a retry."""
    now = time.time()
    with _lock:
        last = _recent.get(fingerprint)
        if last is not None and now - last < DEDUP_WINDOW:
            return "duplicate"
        if len(_within(_global_sends, now, GLOBAL_WINDOW)) >= GLOBAL_MAX:
            return "global"
    return None


def _record_send(fingerprint: str) -> None:
    now = time.time()
    with _lock:
        _global_sends[:] = _within(_global_sends, now, GLOBAL_WINDOW)
        _global_sends.append(now)
        _recent[fingerprint] = now
        for key, ts in list(_recent.items()):
            if now - ts >= DEDUP_WINDOW:
                del _recent[key]


def _send_lead_email(to_addr: str, subject: str, body: str, reply_to: str) -> bool:
    if not all([SMTP_HOST, SMTP_FROM_EMAIL]):
        logger.warning("SMTP not configured, cannot relay lead")
        return False

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = formataddr(("Bambuddy Leads", SMTP_FROM_EMAIL))
    msg["To"] = to_addr
    msg["Reply-To"] = reply_to

    try:
        if SMTP_USE_TLS == "ssl":
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
            if SMTP_USE_TLS == "starttls":
                server.starttls()
        if SMTP_USERNAME and SMTP_PASSWORD:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM_EMAIL, [to_addr], msg.as_string())
        server.quit()
        return True
    except Exception:
        logger.exception("Failed to relay lead email")
        return False


def _clean(value, limit: int = _MAX_FIELD) -> str:
    return str(value or "").strip()[:limit]


@lead_bp.route("/api/lead", methods=["POST", "OPTIONS"])
def lead():
    if request.method == "OPTIONS":
        return "", 204

    client_ip = request.headers.get("X-Real-IP", request.remote_addr)
    if not _check_rate_limit(client_ip):
        return jsonify({"success": False, "message": "Too many submissions. Please try again later."}), 429

    if request.content_length and request.content_length > 64 * 1024:
        return jsonify({"success": False, "message": "Payload too large."}), 413

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "Invalid submission."}), 400

    # Honeypot: a real browser never fills the hidden "website" field. If it is
    # set, pretend success and drop the payload — the bot gets no signal.
    if _clean(data.get("website")):
        logger.info("Lead honeypot tripped (ip=%s)", client_ip)
        return jsonify({"success": True, "message": "Thanks — we'll be in touch."})

    interest = _clean(data.get("interest"))
    if interest not in INTEREST_ROUTING:
        return jsonify({"success": False, "message": "Please choose what you're interested in."}), 400

    email = _clean(data.get("email"))
    # parseaddr strips display names; validate the bare address.
    email = parseaddr(email)[1]
    if not _EMAIL_RE.match(email):
        return jsonify({"success": False, "message": "Please enter a valid email address."}), 400

    printers = _clean(data.get("printers"))
    timeframe = _clean(data.get("timeframe"))
    region = _clean(data.get("region"))
    context = _clean(data.get("context"))
    message = _clean(data.get("message"), _MAX_MESSAGE)

    interest_label, to_addr = INTEREST_ROUTING[interest]
    printers_label = PRINTERS_LABELS.get(printers, printers or "not stated")
    timeframe_label = TIMEFRAME_LABELS.get(timeframe, timeframe or "not stated")

    # Global circuit breaker + dedup on (email, message). Cheap, before SMTP.
    fingerprint = f"{email}|{message}"
    reason = _check_global_and_dedup(fingerprint)
    if reason == "duplicate":
        return jsonify({"success": True, "message": "Thanks — we already have this and will be in touch."})
    if reason == "global":
        logger.warning("Lead global rate limit hit (ip=%s)", client_ip)
        return jsonify({"success": False, "message": "We're getting a lot of enquiries right now. Please try again shortly."}), 429

    subject = f"[Bambuddy Lead] {interest_label} — {printers_label}"
    if region:
        subject += f" ({region})"

    body_lines = [
        "New enquiry from bambuddy.cool",
        "",
        f"Interest:   {interest_label}",
        f"Printers:   {printers_label}",
        f"Timeframe:  {timeframe_label}",
        f"Region:     {region or 'not stated'}",
        f"Email:      {email}",
        f"From page:  {context or 'unknown'}",
        "",
        "Message:",
        message or "(none)",
        "",
        "---",
        "Reply directly to this email to reach the prospect.",
    ]
    if not _send_lead_email(to_addr, subject, "\n".join(body_lines), reply_to=email):
        return jsonify({"success": False, "message": "Could not send right now. Please email us directly."}), 502

    _record_send(fingerprint)
    logger.info("Lead relayed (interest=%s, ip=%s)", interest, client_ip)
    return jsonify({"success": True, "message": "Thanks — we'll be in touch shortly."})
