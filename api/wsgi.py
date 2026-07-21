from bug_report_relay import app

# Commercial lead capture shares this app/worker/unit (see lead_relay.py).
from lead_relay import lead_bp  # noqa: E402

app.register_blueprint(lead_bp)
