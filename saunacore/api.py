from __future__ import annotations

from datetime import date

from flask import Blueprint, jsonify, request, url_for

from saunacore import service
from saunacore.db import get_db

bp = Blueprint("api", __name__)


@bp.before_request
def guard_json():
    if request.path == "/api/stripe/webhook":
        return None
    if request.method == "POST" and not service.csrf_ok():
        return jsonify(ok=False, error="Sitzung abgelaufen. Bitte lade die Seite neu."), 400


@bp.get("/api/reverse")
def reverse():
    try:
        lat = float(request.args["lat"])
        lng = float(request.args["lng"])
    except (KeyError, TypeError, ValueError):
        return jsonify(ok=False, error="Die Markierung ist ungültig."), 400
    try:
        info = service.reverse_geocode(lat, lng)
    except service.QuoteError as exc:
        return jsonify(ok=False, error=str(exc)), 400
    zone, _plz = service.lookup_zone(get_db(), info["address"])
    return jsonify(
        ok=True,
        address=info["address"],
        postal_code=info["postal_code"],
        city=info["city"],
        lat=lat,
        lng=lng,
        zone=None
        if zone is None
        else {
            "name": zone["name"],
            "badge": service.zone_badge(zone),
            "free": int(zone["price_cents"]) == 0,
            "price_cents": int(zone["price_cents"]),
        },
    )


@bp.get("/api/zone")
def zone():
    query = (request.args.get("q") or "").strip()
    if len(query) < 2:
        return jsonify(ok=False, error="Bitte Ort oder PLZ eingeben."), 400
    found, _plz = service.lookup_zone(get_db(), query)
    if not found:
        return jsonify(ok=False, error="Außerhalb des Liefergebiets."), 404
    price = int(found["price_cents"])
    return jsonify(
        ok=True,
        name=found["name"],
        badge=service.zone_badge(found),
        price_cents=price,
        price="kostenlos" if price == 0 else service.format_euro(price),
        free=price == 0,
    )


@bp.get("/api/busy")
def busy():
    try:
        model_id = int(request.args["model_id"])
        start = date.fromisoformat(request.args["start"])
        end = date.fromisoformat(request.args["end"])
    except (KeyError, ValueError):
        return jsonify(ok=False, error="Anfrage ist ungültig."), 400
    if end <= start or (end - start).days > 400:
        return jsonify(ok=False, error="Zeitraum ist ungültig."), 400
    return jsonify(ok=True, busy=service.busy_nights(get_db(), model_id, start, end))


@bp.post("/api/quote")
def quote():
    data = request.get_json(silent=True) or {}
    try:
        payload = service.quote_from_payload(get_db(), data)
    except service.QuoteError as exc:
        return jsonify(ok=False, error=str(exc)), 400
    return jsonify(ok=True, **payload)


@bp.post("/api/bookings")
def create_booking():
    data = request.get_json(silent=True) or {}
    try:
        booking = service.create_booking(get_db(), data)
    except service.QuoteError as exc:
        return jsonify(ok=False, error=str(exc)), 400
    redirect = url_for("public.thanks", number=booking["number"], t=booking["public_token"])
    if isinstance(booking, dict) and booking.get("checkout_url"):
        redirect = booking["checkout_url"]
    return jsonify(ok=True, number=booking["number"], redirect=redirect)


@bp.post("/api/stripe/webhook")
def stripe_webhook():
    from saunacore.stripe_pay import mark_paid, verify_event

    settings = service.load_settings(get_db())
    secret = (settings.get("stripe_webhook") or "").strip()
    payload = request.get_data()
    try:
        event = verify_event(payload, request.headers.get("Stripe-Signature", ""), secret)
    except service.QuoteError as exc:
        return jsonify(ok=False, error=str(exc)), 400
    kind = event.get("type")
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    session = data.get("object") if isinstance(data.get("object"), dict) else {}
    if kind in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        mark_paid(get_db(), session)
    return jsonify(ok=True)
