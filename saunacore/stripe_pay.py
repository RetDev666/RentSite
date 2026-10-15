from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from saunacore import service

_SESSION_RE = re.compile(r"cs_[A-Za-z0-9_]+")


def enabled(settings: dict) -> bool:
    return bool((settings.get("stripe_secret") or "").strip())


def _request(secret: str, url: str, body: dict | None = None, idempotency: str = "") -> dict:
    basic = base64.b64encode(f"{secret}:".encode()).decode()
    data = None if body is None else urllib.parse.urlencode(body).encode()
    headers = {"Authorization": f"Basic {basic}"}
    if idempotency:
        headers["Idempotency-Key"] = idempotency[:80]
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        exc.read()
        raise service.QuoteError("Die Zahlung konnte nicht gestartet werden.") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise service.QuoteError("Die Zahlung konnte nicht gestartet werden.") from exc


def create_checkout(settings: dict, booking, success_url: str, cancel_url: str) -> tuple[str, str]:
    secret = (settings.get("stripe_secret") or "").strip()
    method = "card" if booking["payment_method"] == "card" else "paypal"
    payload = _request(
        secret,
        "https://api.stripe.com/v1/checkout/sessions",
        {
            "mode": "payment",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "client_reference_id": booking["number"],
            "customer_email": booking["email"],
            "metadata[number]": booking["number"],
            "line_items[0][quantity]": "1",
            "line_items[0][price_data][currency]": "eur",
            "line_items[0][price_data][unit_amount]": str(int(booking["gross_cents"])),
            "line_items[0][price_data][product_data][name]": f"{booking['model_name']} {booking['number']}"[:120],
            "payment_method_types[0]": method,
        },
        idempotency=booking["public_token"],
    )
    session_id = str(payload.get("id") or "")
    url = str(payload.get("url") or "")
    if not _SESSION_RE.fullmatch(session_id) or not url.startswith("https://"):
        raise service.QuoteError("Die Zahlung konnte nicht gestartet werden.")
    return session_id, url


def verify_event(payload: bytes, header: str, secret: str) -> dict:
    if not header or not secret:
        raise service.QuoteError("Signatur fehlt.")
    signatures = []
    timestamp = ""
    for item in header.split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        if key == "v1":
            signatures.append(value)
        elif key == "t":
            timestamp = value
    if not timestamp.isdigit() or abs(int(time.time()) - int(timestamp)) > 300:
        raise service.QuoteError("Signatur ungültig.")
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256).hexdigest()
    if not signatures or not any(hmac.compare_digest(digest, sig) for sig in signatures):
        raise service.QuoteError("Signatur ungültig.")
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise service.QuoteError("Signatur ungültig.") from exc


def mark_paid(db, session: dict) -> None:
    if session.get("payment_status") != "paid":
        return
    metadata = session.get("metadata") if isinstance(session.get("metadata"), dict) else {}
    number = str(session.get("client_reference_id") or metadata.get("number") or "")
    row = db.execute("SELECT * FROM bookings WHERE number = ?", (number,)).fetchone()
    if not row or row["status"] in {"cancelled", "completed"}:
        return
    stored = row["stripe_session"] or ""
    session_id = str(session.get("id") or "")
    if stored and session_id and stored != session_id:
        return
    amount = session.get("amount_total")
    if amount is not None and int(amount) != int(row["gross_cents"]):
        return
    if row["payment_status"] == "paid":
        return
    db.execute(
        """
        UPDATE bookings
        SET payment_status = 'paid',
            status = CASE WHEN status = 'new' THEN 'confirmed' ELSE status END
        WHERE id = ?
        """,
        (row["id"],),
    )
    db.execute(
        "INSERT INTO booking_events (booking_id, message, created_at) VALUES (?, ?, ?)",
        (row["id"], "Zahlung über Stripe bestätigt", service.now()),
    )


def pull_session(db, booking, session_id: str) -> None:
    if not _SESSION_RE.fullmatch(session_id or ""):
        return
    settings = service.load_settings(db)
    secret = (settings.get("stripe_secret") or "").strip()
    if not secret:
        return
    session = _request(secret, f"https://api.stripe.com/v1/checkout/sessions/{session_id}")
    mark_paid(db, session)
