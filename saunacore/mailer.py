from __future__ import annotations

import smtplib
from email.message import EmailMessage

from saunacore import service
from saunacore.pdf import WINDOW_LABELS


def _store(db, booking_id, recipient: str, subject: str, body: str, status: str, error: str) -> None:
    db.execute(
        """
        INSERT INTO emails (booking_id, recipient, subject, body, status, error, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (booking_id, recipient, subject, body, status, (error or "")[:400], service.now()),
    )


def _link(booking) -> str:
    try:
        from flask import request

        root = request.url_root.rstrip("/")
    except RuntimeError:
        return ""
    return f"{root}/buchung/{booking['number']}?t={booking['public_token']}"


def _send(settings: dict, recipient: str, subject: str, body: str) -> None:
    host = (settings.get("smtp_host") or "").strip()
    port = service.int_setting(settings, "smtp_port", 587)
    sender = (settings.get("smtp_from") or settings.get("email") or "").strip()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender or recipient
    message["To"] = recipient
    message.set_content(body)
    with smtplib.SMTP(host, port, timeout=12) as smtp:
        if str(settings.get("smtp_tls") or "1") != "0":
            smtp.starttls()
        user = (settings.get("smtp_user") or "").strip()
        password = settings.get("smtp_password") or ""
        if user:
            smtp.login(user, password)
        smtp.send_message(message)


def booking_body(booking, settings: dict) -> str:
    window = WINDOW_LABELS.get(booking["arrival_window"] or "", "")
    lines = [
        f"Buchung {booking['number']}",
        "",
        f"{booking['first_name']} {booking['last_name']}",
        f"{booking['model_name']}",
        f"{booking['start_date']} bis {booking['end_date']} ({booking['nights']} Nächte)",
        booking["address"],
        f"Zone: {booking['zone_name']}",
        f"Gesamt: {service.format_euro(booking['gross_cents'])}",
    ]
    if window:
        lines.append(f"Lieferfenster: {window}")
    if booking["payment_status"] == "simulated":
        lines.append("Zahlungsstatus: Demo, keine Abbuchung.")
    elif booking["payment_status"] == "unpaid":
        lines.append("Zahlungsstatus: offen.")
    else:
        lines.append(f"Zahlungsstatus: {booking['payment_status']}.")
    link = _link(booking)
    if link:
        lines.extend(["", f"Buchung ansehen: {link}"])
    lines.extend(["", str(settings.get("company_name") or ""), str(settings.get("email") or "")])
    return "\n".join(lines)


def notify_booking(db, booking) -> str:
    settings = service.load_settings(db)
    subject = f"Buchung {booking['number']}"
    body = booking_body(booking, settings)
    recipient = booking["email"]
    if not (settings.get("smtp_host") or "").strip():
        _store(db, booking["id"], recipient, subject, body, "not-configured", "")
        return "not-configured"
    try:
        _send(settings, recipient, subject, body)
    except Exception as exc:
        _store(db, booking["id"], recipient, subject, body, "failed", str(exc))
        return "failed"
    _store(db, booking["id"], recipient, subject, body, "sent", "")
    return "sent"


def notify_reply(db, message, reply: str) -> str:
    settings = service.load_settings(db)
    subject = f"Antwort von {settings.get('company_name') or 'Saunacore'}"
    body = reply
    recipient = message["email"]
    if not (settings.get("smtp_host") or "").strip():
        return "not-configured"
    try:
        _send(settings, recipient, subject, body)
    except Exception:
        return "failed"
    return "sent"
