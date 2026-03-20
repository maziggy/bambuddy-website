"""Bug report relay service for bambuddy.cool.

Holds the GitHub PAT and SMTP credentials server-side and proxies bug report
submissions from Bambuddy instances to the GitHub Issues API.
"""

import base64
import logging
import os
import smtplib
import time
import uuid
from email.mime.text import MIMEText

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

GITHUB_TOKEN = os.environ.get("BUG_REPORT_GITHUB_TOKEN", "")
GITHUB_REPO = "maziggy/bambuddy"
GITHUB_API_BASE = "https://api.github.com"

# SMTP config (all from env vars)
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", "")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "starttls").lower()  # "starttls", "ssl", or "none"
MAINTAINER_EMAIL = os.environ.get("MAINTAINER_EMAIL", "mz@v8w.de")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting: 5 requests per hour per IP
RATE_LIMIT_WINDOW = 3600
RATE_LIMIT_MAX = 5
_rate_limits: dict[str, list[float]] = {}


def _check_rate_limit(ip: str) -> bool:
    """Return True if the IP is within rate limits."""
    now = time.time()
    timestamps = _rate_limits.get(ip, [])
    timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    if len(timestamps) >= RATE_LIMIT_MAX:
        _rate_limits[ip] = timestamps
        return False
    timestamps.append(now)
    _rate_limits[ip] = timestamps
    return True


def _github_headers() -> dict[str, str]:
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Bambuddy-BugRelay",
    }


def _ensure_assets_branch() -> None:
    """Create bug-report-assets branch from main if it doesn't exist."""
    url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/git/ref/heads/bug-report-assets"
    resp = requests.get(url, headers=_github_headers(), timeout=15)
    if resp.status_code == 200:
        return

    main_url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/git/ref/heads/main"
    main_resp = requests.get(main_url, headers=_github_headers(), timeout=15)
    if main_resp.status_code != 200:
        return

    sha = main_resp.json()["object"]["sha"]
    create_url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/git/refs"
    requests.post(
        create_url,
        headers=_github_headers(),
        json={"ref": "refs/heads/bug-report-assets", "sha": sha},
        timeout=15,
    )


def _upload_screenshot(screenshot_b64: str) -> str | None:
    """Upload screenshot to GitHub repo, return raw URL or None."""
    try:
        base64.b64decode(screenshot_b64)
    except Exception:
        return None

    try:
        _ensure_assets_branch()
        filename = f"{uuid.uuid4().hex}.png"
        url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/contents/screenshots/{filename}"
        resp = requests.put(
            url,
            headers=_github_headers(),
            json={
                "message": f"Bug report screenshot {filename}",
                "content": screenshot_b64,
                "branch": "bug-report-assets",
            },
            timeout=30,
        )
        if resp.status_code in (200, 201):
            owner, repo = GITHUB_REPO.split("/")
            return f"https://raw.githubusercontent.com/{owner}/{repo}/bug-report-assets/screenshots/{filename}"
    except Exception:
        pass
    return None


def _upload_log_file(log_content: str) -> str | None:
    """Upload sanitized logs to bug-report-assets branch, return raw URL."""
    try:
        _ensure_assets_branch()
        filename = f"{uuid.uuid4().hex}.log"
        url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/contents/logs/{filename}"
        log_b64 = base64.b64encode(log_content.encode("utf-8")).decode("ascii")
        resp = requests.put(
            url,
            headers=_github_headers(),
            json={
                "message": f"Bug report logs {filename}",
                "content": log_b64,
                "branch": "bug-report-assets",
            },
            timeout=30,
        )
        if resp.status_code in (200, 201):
            owner, repo = GITHUB_REPO.split("/")
            return f"https://raw.githubusercontent.com/{owner}/{repo}/bug-report-assets/logs/{filename}"
    except Exception:
        pass
    return None


def _build_issue_body(
    description: str,
    screenshot_url: str | None,
    support_info: dict | None,
    reporter_email: str | None,
) -> str:
    """Build the GitHub issue body markdown."""
    import json

    parts = [description, ""]

    if screenshot_url:
        parts.append("### Screenshot")
        parts.append(f"![Bug Report Screenshot]({screenshot_url})")
        parts.append("")

    if reporter_email:
        parts.append("<details>")
        parts.append("<summary>Reporter Contact</summary>")
        parts.append("")
        parts.append(f"Email: {reporter_email}")
        parts.append("")
        parts.append("</details>")
        parts.append("")

    if support_info:
        recent_logs = support_info.pop("recent_logs", None)

        parts.append("<details>")
        parts.append("<summary>System Information</summary>")
        parts.append("")
        parts.append("```json")
        parts.append(json.dumps(support_info, indent=2, default=str))
        parts.append("```")
        parts.append("</details>")
        parts.append("")

        if recent_logs:
            log_url = _upload_log_file(recent_logs)
            if log_url:
                parts.append(f"**Logs (sanitized):** [bambuddy.log]({log_url})")
            else:
                parts.append("<details>")
                parts.append("<summary>Recent Logs (sanitized)</summary>")
                parts.append("")
                parts.append("```")
                parts.append(recent_logs)
                parts.append("```")
                parts.append("</details>")
            parts.append("")

    parts.append("---")
    parts.append("*Submitted via BamBuddy Bug Report*")
    return "\n".join(parts)


def _send_maintainer_email(
    reporter_email: str | None, issue_url: str, issue_number: int, description: str
) -> None:
    """Send email notification to maintainer about new bug report."""
    if not all([SMTP_HOST, SMTP_FROM_EMAIL]):
        logger.warning("SMTP not configured, skipping maintainer email")
        return

    if reporter_email:
        subject = f"[BamBuddy Bug #{issue_number}] New report from {reporter_email}"
    else:
        subject = f"[BamBuddy Bug #{issue_number}] New report (anonymous)"

    body = (
        f"New bug report submitted.\n\n"
        f"Reporter email: {reporter_email or 'not provided'}\n"
        f"GitHub issue: {issue_url}\n\n"
        f"Description:\n{description}"
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = MAINTAINER_EMAIL
    if reporter_email:
        msg["Reply-To"] = reporter_email

    try:
        if SMTP_USE_TLS == "ssl":
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
            if SMTP_USE_TLS == "starttls":
                server.starttls()
        if SMTP_USERNAME and SMTP_PASSWORD:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM_EMAIL, MAINTAINER_EMAIL, msg.as_string())
        server.quit()
        logger.info("Maintainer email sent for bug #%s (reporter: %s)", issue_number, reporter_email)
    except Exception:
        logger.exception("Failed to send maintainer email for bug #%s", issue_number)


@app.after_request
def _add_cors_headers(response):
    """Allow any Bambuddy instance to reach the relay."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response


@app.route("/api/bug-report", methods=["POST", "OPTIONS"])
def bug_report():
    if request.method == "OPTIONS":
        return "", 204

    # Rate limit by IP
    client_ip = request.headers.get("X-Real-IP", request.remote_addr)
    if not _check_rate_limit(client_ip):
        return jsonify({"success": False, "message": "Rate limit exceeded. Please try again later."}), 429

    # Validate payload size (~10 MB)
    if request.content_length and request.content_length > 10 * 1024 * 1024:
        return jsonify({"success": False, "message": "Payload too large."}), 413

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "Invalid JSON payload."}), 400

    description = data.get("description", "").strip()
    if not description:
        return jsonify({"success": False, "message": "Description is required."}), 400

    reporter_email = data.get("reporter_email", "").strip()

    if not GITHUB_TOKEN:
        return jsonify({"success": False, "message": "Relay not configured."}), 503

    # Upload screenshot if provided
    screenshot_url = None
    screenshot_b64 = data.get("screenshot_base64")
    if screenshot_b64:
        screenshot_url = _upload_screenshot(screenshot_b64)

    # Build and create issue
    support_info = data.get("support_info")
    title = f"[Bug Report] {description[:80]}"
    body = _build_issue_body(description, screenshot_url, support_info, reporter_email)
    labels = ["bug", "user-report"]

    issue_url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/issues"
    resp = requests.post(
        issue_url,
        headers=_github_headers(),
        json={"title": title, "body": body, "labels": labels},
        timeout=15,
    )

    if resp.status_code != 201:
        return jsonify({"success": False, "message": "Failed to create GitHub issue."}), 502

    issue_data = resp.json()
    issue_html_url = issue_data["html_url"]
    issue_number = issue_data["number"]

    # Send maintainer email (non-blocking — don't fail the request if email fails)
    _send_maintainer_email(reporter_email or None, issue_html_url, issue_number, description)

    return jsonify({
        "success": True,
        "message": "Bug report submitted successfully!",
        "issue_url": issue_html_url,
        "issue_number": issue_number,
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
