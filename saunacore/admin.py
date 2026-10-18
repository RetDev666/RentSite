from __future__ import annotations

import calendar
import csv
import io
import json
import re
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Blueprint, Response, abort, current_app, flash, g, redirect, render_template, request, session, url_for

from saunacore import seo, service
from saunacore.db import get_db

bp = Blueprint("admin", __name__, url_prefix="/admin")
ICON_CHOICES = ("users", "flame", "window", "eye", "bolt", "door", "leaf", "spark", "truck", "pin", "check")
SIZES = (("kompakt", "Kompakt"), ("mittel", "Mittel"), ("gross", "Groß"))


@bp.before_request
def guard():
    if request.method == "POST" and not service.csrf_ok():
        abort(400)
    if request.endpoint == "admin.login":
        return
    if not session.get("admin_id"):
        return redirect(url_for("admin.login", next=request.path))
    g.unread_messages = get_db().execute("SELECT COUNT(*) AS c FROM messages WHERE read = 0").fetchone()["c"]


def _safe_next(value: str) -> str:
    if value and value.startswith("/admin") and not value.startswith("//"):
        return value
    return url_for("admin.dashboard")


def _pad(items, size, blank):
    items = list(items)[:size]
    while len(items) < size:
        items.append(dict(blank))
    return items


def _model_fields(form, files, existing=None):
    name = form.get("name", "").strip()
    if not (1 <= len(name) <= 80):
        raise ValueError("Name fehlt.")
    subtitle = form.get("subtitle", "").strip()[:120]
    badge = form.get("badge", "").strip()[:40]
    slug = service.slugify(form.get("slug", "").strip() or name)
    price = service.parse_money(form.get("price", ""))
    if price <= 0:
        raise ValueError("Der Tagespreis muss größer als 0 sein.")
    try:
        capacity_min = int(form.get("capacity_min", ""))
        capacity_max = int(form.get("capacity_max", ""))
        sort_order = int(form.get("sort_order") or 0)
    except ValueError as exc:
        raise ValueError("Kapazität oder Reihenfolge ist ungültig.") from exc
    if not (1 <= capacity_min <= capacity_max <= 20):
        raise ValueError("Die Personenanzahl ist ungültig.")
    raw_units = form.get("units")
    if raw_units is None or str(raw_units).strip() == "":
        units = 1
    else:
        try:
            units = int(raw_units)
        except ValueError as exc:
            raise ValueError("Die Gerätezahl ist ungültig.") from exc
    if not 1 <= units <= 20:
        raise ValueError("Die Gerätezahl ist ungültig.")
    size = form.get("size", "")
    if size not in {key for key, _label in SIZES}:
        raise ValueError("Größe ist ungültig.")
    features = []
    for icon, label in zip(form.getlist("feature_icon"), form.getlist("feature_label")):
        label = label.strip()
        if not label:
            continue
        if icon not in ICON_CHOICES:
            icon = "spark"
        features.append({"icon": icon, "label": label[:40]})
    if not features:
        raise ValueError("Mindestens ein Merkmal ist nötig.")
    specs = []
    for icon, label, value in zip(form.getlist("spec_icon"), form.getlist("spec_label"), form.getlist("spec_value")):
        label = label.strip()
        value = value.strip()
        if not label and not value:
            continue
        if not label or not value:
            raise ValueError("Jede Angabe braucht Bezeichnung und Wert.")
        if icon not in ICON_CHOICES:
            icon = "spark"
        specs.append({"icon": icon, "label": label[:40], "value": value[:80]})
    if not specs:
        raise ValueError("Mindestens eine Kennzahl ist nötig.")
    summary = form.get("summary", "").strip()
    story_title = form.get("story_title", "").strip()
    story = form.get("story", "").strip()
    if len(summary) < 10 or len(story_title) < 2 or len(story) < 10:
        raise ValueError("Kurztext, Überschrift und Beschreibung werden gebraucht.")
    highlights = [line.strip() for line in form.get("highlights", "").splitlines() if line.strip()]
    images = []
    for path in form.getlist("keep_image"):
        if service.safe_image_path(path) and path not in images:
            images.append(path)
    raw_urls = form.get("image_urls", "")
    for line in raw_urls.splitlines():
        line = line.strip()
        if line and service.safe_image_path(line) and line not in images:
            images.append(line)
    for file_storage in files.getlist("images"):
        if file_storage and file_storage.filename:
            saved_path = service.save_image(file_storage)
            if saved_path not in images:
                images.append(saved_path)
    if len(images) > 40:
        raise ValueError("Höchstens 40 Bilder.")
    if not images:
        raise ValueError("Mindestens ein Bild ist nötig.")
    return {
        "slug": slug,
        "name": name,
        "subtitle": subtitle,
        "badge": badge,
        "price_cents": price,
        "capacity_min": capacity_min,
        "capacity_max": capacity_max,
        "size": size,
        "features_json": json.dumps(features, ensure_ascii=False),
        "specs_json": json.dumps(specs, ensure_ascii=False),
        "summary": summary,
        "story_title": story_title,
        "story": story,
        "highlights_json": json.dumps(highlights, ensure_ascii=False),
        "images_json": json.dumps(images, ensure_ascii=False),
        "active": 1 if form.get("active") == "1" else 0,
        "sort_order": sort_order,
        "units": units,
        "included_text": form.get("included_text", "").strip()[:2000],
        "excluded_text": form.get("excluded_text", "").strip()[:2000],
    }


def _save_model(db, fields, model_id=None):
    fields = dict(fields)
    fields["slug"] = service.unique_slug(db, "models", fields["slug"], model_id)
    columns = list(fields)
    if model_id is None:
        marks = ", ".join("?" for _ in columns)
        db.execute(
            f"INSERT INTO models ({', '.join(columns)}) VALUES ({marks})",
            [fields[column] for column in columns],
        )
        return db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    assignments = ", ".join(f"{column} = ?" for column in columns)
    db.execute(
        f"UPDATE models SET {assignments} WHERE id = ?",
        [fields[column] for column in columns] + [model_id],
    )
    return model_id


def _extra_fields(form, files):
    name = form.get("name", "").strip()
    if not (1 <= len(name) <= 80):
        raise ValueError("Name fehlt.")
    description = form.get("description", "").strip()
    if len(description) < 5:
        raise ValueError("Beschreibung fehlt.")
    kind = form.get("kind", "")
    if kind not in service.KIND_LABELS:
        raise ValueError("Art ist ungültig.")
    try:
        sort_order = int(form.get("sort_order") or 0)
    except ValueError as exc:
        raise ValueError("Reihenfolge ist ungültig.") from exc
    image = form.get("keep_image", "").strip()
    custom_url = form.get("image_url", "").strip()
    if custom_url and service.safe_image_path(custom_url):
        image = custom_url
    if image and not service.safe_image_path(image):
        image = ""
    upload = files.get("image")
    if upload and upload.filename:
        image = service.save_image(upload)
    return {
        "slug": service.slugify(form.get("slug", "").strip() or name),
        "name": name,
        "description": description,
        "price_cents": service.parse_money(form.get("price", "")),
        "kind": kind,
        "image": image,
        "active": 1 if form.get("active") == "1" else 0,
        "sort_order": sort_order,
    }


def _save_extra(db, fields, extra_id=None):
    fields = dict(fields)
    fields["slug"] = service.unique_slug(db, "extras", fields["slug"], extra_id)
    columns = list(fields)
    if extra_id is None:
        marks = ", ".join("?" for _ in columns)
        db.execute(
            f"INSERT INTO extras ({', '.join(columns)}) VALUES ({marks})",
            [fields[column] for column in columns],
        )
        return db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    assignments = ", ".join(f"{column} = ?" for column in columns)
    db.execute(
        f"UPDATE extras SET {assignments} WHERE id = ?",
        [fields[column] for column in columns] + [extra_id],
    )
    return extra_id


def _selected_extras(form):
    chosen = []
    for raw_id in form.getlist("extra_id"):
        try:
            extra_id = int(raw_id)
            qty = int(form.get(f"qty_{raw_id}") or 0)
        except ValueError:
            continue
        chosen.append({"id": extra_id, "qty": qty})
    return chosen


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_id"):
        return redirect(url_for("admin.dashboard"))
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        admin = get_db().execute("SELECT * FROM admins WHERE email = ?", (email,)).fetchone()
        if not admin or not service.verify_password(password, admin["password_hash"]):
            error = "E-Mail oder Passwort ist falsch."
        else:
            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_name"] = admin["name"]
            session.permanent = True
            return redirect(_safe_next(request.form.get("next", "")))
    return render_template(
        "admin/login.html",
        error=error,
        hint=service.demo_login_hint(get_db()),
        next_path=request.args.get("next", ""),
        title="Admin Login",
    )


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


@bp.get("/")
def dashboard():
    db = get_db()
    today = date.today().isoformat()
    month = today[:7]
    stats = {
        "new": db.execute("SELECT COUNT(*) AS c FROM bookings WHERE status = 'new'").fetchone()["c"],
        "upcoming": db.execute(
            """
            SELECT COUNT(*) AS c FROM bookings
            WHERE status IN ('new', 'confirmed', 'delivery') AND start_date >= ?
            """,
            (today,),
        ).fetchone()["c"],
        "active": db.execute("SELECT COUNT(*) AS c FROM bookings WHERE status = 'active'").fetchone()["c"],
        "revenue": db.execute(
            """
            SELECT COALESCE(SUM(gross_cents), 0) AS s FROM bookings
            WHERE status != 'cancelled' AND substr(created_at, 1, 7) = ?
            """,
            (month,),
        ).fetchone()["s"],
        "messages": g.unread_messages,
    }
    upcoming = db.execute(
        """
        SELECT * FROM bookings
        WHERE status IN ('new', 'confirmed', 'delivery') AND end_date >= ?
        ORDER BY start_date LIMIT 8
        """,
        (today,),
    ).fetchall()
    recent = db.execute("SELECT * FROM bookings ORDER BY created_at DESC LIMIT 6").fetchall()
    pins = []
    for row in db.execute(
        """
        SELECT id, number, model_name, city, address, lat, lng, status, start_date
        FROM bookings
        WHERE lat IS NOT NULL AND lng IS NOT NULL AND status != 'cancelled'
        ORDER BY start_date DESC
        LIMIT 40
        """
    ):
        pins.append(
            {
                "id": row["id"],
                "lat": row["lat"],
                "lng": row["lng"],
                "label": f"{row['number']} · {row['model_name']}",
                "href": url_for("admin.booking_detail", booking_id=row["id"]),
                "status": row["status"],
            }
        )
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        upcoming=upcoming,
        recent=recent,
        pins=pins,
        title="Überblick",
    )


@bp.get("/buchungen")
def bookings():
    db = get_db()
    status = request.args.get("status", "").strip()
    delivery_type = request.args.get("delivery_type", "").strip()
    query = request.args.get("q", "").strip()
    sql = "SELECT * FROM bookings WHERE 1 = 1"
    params: list = []
    if status in service.STATUSES:
        sql += " AND status = ?"
        params.append(status)
    if delivery_type in ("delivery", "pickup"):
        sql += " AND delivery_type = ?"
        params.append(delivery_type)
    if query:
        sql += " AND (number LIKE ? OR email LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR city LIKE ? OR address LIKE ? OR voucher_code LIKE ? OR payment_method LIKE ?)"
        like = f"%{query}%"
        params.extend([like, like, like, like, like, like, like, like])
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    total = db.execute(f"SELECT COUNT(*) AS c FROM ({sql})", params).fetchone()["c"]
    rows = db.execute(sql + " ORDER BY created_at DESC LIMIT 20 OFFSET ?", params + [(page - 1) * 20]).fetchall()
    pages = max(1, (total + 19) // 20)

    # All geo-located bookings for Leaflet map
    map_pins = []
    pin_sql = "SELECT id, number, first_name, last_name, phone, model_name, address, city, lat, lng, status, delivery_type, start_date, end_date, gross_cents FROM bookings WHERE lat IS NOT NULL AND lng IS NOT NULL"
    pin_params: list = []
    if status in service.STATUSES:
        pin_sql += " AND status = ?"
        pin_params.append(status)
    if delivery_type in ("delivery", "pickup"):
        pin_sql += " AND delivery_type = ?"
        pin_params.append(delivery_type)
    pin_sql += " ORDER BY start_date DESC LIMIT 80"
    for r in db.execute(pin_sql, pin_params):
        map_pins.append({
            "id": r["id"],
            "number": r["number"],
            "customer": f"{r['first_name']} {r['last_name']}",
            "phone": r["phone"] or "",
            "model": r["model_name"] or "Sauna",
            "address": r["address"] or "",
            "city": r["city"] or "",
            "lat": r["lat"],
            "lng": r["lng"],
            "status": r["status"],
            "delivery_type": r["delivery_type"] or "delivery",
            "dates": f"{r['start_date']} – {r['end_date']}",
            "gross": service.format_euro(r["gross_cents"]),
            "href": url_for("admin.booking_detail", booking_id=r["id"]),
        })

    return render_template(
        "admin/bookings.html",
        bookings=rows,
        status=status,
        delivery_type=delivery_type,
        query=query,
        page=page,
        pages=pages,
        map_pins=map_pins,
        title="Buchungen",
    )


@bp.get("/buchungen/export.csv")
def bookings_export():
    rows = get_db().execute("SELECT * FROM bookings ORDER BY created_at DESC").fetchall()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Nummer", "Status", "Versandart", "Zahlung", "Zahlungsstatus", "Vorname", "Nachname", "E-Mail", "Telefon",
            "Firma", "USt-IdNr", "Modell", "Anreise", "Abreise", "Nächte", "Fenster", "Adresse", "Zone",
            "Miete", "Lieferung", "Extras", "Kaution", "Gutschein", "Code", "Gesamt", "MwSt", "Angelegt",
        ]
    )
    for row in rows:
        dtype = "Selbstabholung" if row["delivery_type"] == "pickup" else "Lieferung"
        writer.writerow(
            [
                row["number"], row["status"], dtype, row["payment_method"], row["payment_status"],
                row["first_name"], row["last_name"], row["email"], row["phone"],
                row["company"], row["company_vat"], row["model_name"], row["start_date"], row["end_date"],
                row["nights"], row["arrival_window"], row["address"], row["zone_name"],
                f"{row['rent_cents'] / 100:.2f}", f"{row['delivery_cents'] / 100:.2f}",
                f"{row['extras_cents'] / 100:.2f}", f"{row['deposit_cents'] / 100:.2f}",
                f"{row['voucher_cents'] / 100:.2f}", row["voucher_code"],
                f"{row['gross_cents'] / 100:.2f}", f"{row['vat_cents'] / 100:.2f}", row["created_at"],
            ]
        )
    return Response(
        "\ufeff" + buffer.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=buchungen.csv"},
    )


@bp.get("/buchungen/<int:booking_id>/beleg.pdf")
def booking_pdf(booking_id):
    from saunacore.pdf import invoice_pdf

    booking = get_db().execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not booking:
        abort(404)
    payload = invoice_pdf(booking, service.load_settings(get_db()), json.loads(booking["extras_json"]))
    return Response(
        payload,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename={booking['number']}.pdf"},
    )


@bp.route("/buchungen/neu", methods=["GET", "POST"])
def booking_new():
    db = get_db()
    models = db.execute("SELECT * FROM models WHERE active = 1 ORDER BY sort_order, id").fetchall()
    extras = db.execute("SELECT * FROM extras WHERE active = 1 ORDER BY sort_order, id").fetchall()
    if request.method == "POST":
        delivery_type = request.form.get("delivery_type", "delivery")
        if delivery_type not in ("delivery", "pickup"):
            delivery_type = "delivery"
        data = {
            "model_id": request.form.get("model_id"),
            "delivery_type": delivery_type,
            "start": request.form.get("start"),
            "end": request.form.get("end"),
            "address": request.form.get("address", ""),
            "lat": request.form.get("lat", ""),
            "lng": request.form.get("lng", ""),
            "zone_id": request.form.get("zone_id") or "",
            "extras": _selected_extras(request.form),
            "first_name": request.form.get("first_name", ""),
            "last_name": request.form.get("last_name", ""),
            "email": request.form.get("email", ""),
            "phone": request.form.get("phone", ""),
            "notes": request.form.get("notes", ""),
            "payment_method": request.form.get("payment_method"),
            "arrival_window": (request.form.get("arrival_window") or "").strip().lower(),
            "voucher_code": (request.form.get("voucher_code") or "").strip().upper(),
            "card_last4": request.form.get("card_last4", ""),
            "card_brand": request.form.get("card_brand", ""),
            "card_exp": request.form.get("card_exp", ""),
        }
        try:
            booking = service.create_booking(
                db,
                data,
                allow_past=True,
                status=request.form.get("status") or "confirmed",
            )
        except service.QuoteError as exc:
            flash(str(exc), "error")
        else:
            flash(f"Buchung {booking['number']} angelegt.")
            return redirect(url_for("admin.booking_detail", booking_id=booking["id"]))
    zones = db.execute("SELECT * FROM zones WHERE active = 1 ORDER BY sort_order, id").fetchall()
    return render_template("admin/booking_new.html", models=models, extras=extras, zones=zones, title="Neue Buchung")


@bp.get("/buchungen/<int:booking_id>")
def booking_detail(booking_id):
    db = get_db()
    booking = db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not booking:
        abort(404)
    events = db.execute(
        "SELECT * FROM booking_events WHERE booking_id = ? ORDER BY id DESC",
        (booking_id,),
    ).fetchall()
    zones = db.execute("SELECT * FROM zones WHERE active = 1 ORDER BY sort_order, id").fetchall()
    return render_template(
        "admin/booking.html",
        booking=booking,
        extras=json.loads(booking["extras_json"]),
        zones=zones,
        events=events,
        range_label=service.format_range(date.fromisoformat(booking["start_date"]), date.fromisoformat(booking["end_date"])),
        title=booking["number"],
    )


@bp.post("/buchungen/<int:booking_id>/status")
def booking_status(booking_id):
    try:
        service.set_status(get_db(), booking_id, request.form.get("status", ""))
        flash("Status gespeichert.")
    except service.QuoteError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin.booking_detail", booking_id=booking_id))


@bp.post("/buchungen/<int:booking_id>/note")
def booking_note(booking_id):
    note = request.form.get("admin_note", "").strip()
    if len(note) > 2000:
        flash("Die Notiz ist zu lang.", "error")
    else:
        get_db().execute("UPDATE bookings SET admin_note = ? WHERE id = ?", (note, booking_id))
        flash("Notiz gespeichert.")
    return redirect(url_for("admin.booking_detail", booking_id=booking_id))


@bp.post("/buchungen/<int:booking_id>/delivery")
def booking_delivery(booking_id):
    db = get_db()
    delivery_type = request.form.get("delivery_type", "delivery").strip()
    if delivery_type not in ("delivery", "pickup"):
        delivery_type = "delivery"
    address = request.form.get("address", "").strip()
    lat = request.form.get("lat")
    lng = request.form.get("lng")
    arrival_window = (request.form.get("arrival_window") or "").strip().lower()
    if delivery_type == "pickup":
        if not address:
            address = "Tiefenbrunnen 1, 14929 Treuenbrietzen (Selbstabholung)"
        lat_val = 52.0911
        lng_val = 12.8711
    else:
        try:
            lat_val = float(lat) if lat else None
            lng_val = float(lng) if lng else None
        except ValueError:
            lat_val, lng_val = None, None

    booking = db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    new_delivery_cents = booking["delivery_cents"]
    new_zone_name = booking["zone_name"]
    zone_id = request.form.get("zone_id", "").strip()
    custom_price = request.form.get("delivery_price", "").strip()
    z = None
    if zone_id == "custom":
        new_zone_name = "Individuelle Lieferpauschale"
        if custom_price:
            try:
                new_delivery_cents = service.parse_money(custom_price)
            except ValueError:
                pass
    elif zone_id:
        z = db.execute("SELECT * FROM zones WHERE id = ?", (zone_id,)).fetchone()
        if z:
            new_zone_name = z["name"]
            new_delivery_cents = int(z["price_cents"])
            if custom_price:
                try:
                    parsed_custom = service.parse_money(custom_price)
                    if parsed_custom != int(z["price_cents"]):
                        new_delivery_cents = parsed_custom
                except ValueError:
                    pass
    elif custom_price:
        try:
            new_delivery_cents = service.parse_money(custom_price)
        except ValueError:
            pass
    if delivery_type == "pickup":
        new_delivery_cents = 0
        new_zone_name = "Selbstabholung"

    base = booking["rent_cents"] + booking["extras_cents"] + new_delivery_cents - booking["voucher_cents"]
    new_gross = max(0, base) + booking["deposit_cents"]
    settings = service.load_settings(db)
    percent = service.int_setting(settings, "vat_percent", 19)
    new_vat = service.included_vat(new_gross, percent)

    db.execute(
        """
        UPDATE bookings SET delivery_type = ?, address = ?, lat = ?, lng = ?, arrival_window = ?,
               zone_name = ?, delivery_cents = ?, gross_cents = ?, vat_cents = ?
        WHERE id = ?
        """,
        (delivery_type, address, lat_val, lng_val, arrival_window, new_zone_name, new_delivery_cents, new_gross, new_vat, booking_id),
    )
    type_label = "Selbstabholung (Treuenbrietzen)" if delivery_type == "pickup" else "Lieferung an Wunschort"
    win_label = service.WINDOW_LABELS.get(arrival_window, arrival_window) if arrival_window else ""
    win_info = f" · Fenster: {win_label}" if win_label else ""
    db.execute(
        "INSERT INTO booking_events (booking_id, message, created_at) VALUES (?, ?, ?)",
        (
            booking_id,
            f"Versandart & Zone geändert: {type_label} · Zone: {new_zone_name} ({service.format_euro(new_delivery_cents)}) — {address}{win_info}",
            service.now(),
        ),
    )
    flash(f"Versandart, Zone ({new_zone_name}) & Lieferfenster gespeichert.")
    return redirect(url_for("admin.booking_detail", booking_id=booking_id))


@bp.post("/buchungen/<int:booking_id>/zahlung")
def booking_payment(booking_id):
    db = get_db()
    method = (request.form.get("payment_method") or "").strip()
    pay_status = (request.form.get("payment_status") or "").strip()
    if method not in service.PAYMENTS or pay_status not in {"unpaid", "paid", "simulated"}:
        flash("Ungültige Angaben zur Zahlung.", "error")
    else:
        db.execute(
            "UPDATE bookings SET payment_method = ?, payment_status = ? WHERE id = ?",
            (method, pay_status, booking_id),
        )
        db.execute(
            "INSERT INTO booking_events (booking_id, message, created_at) VALUES (?, ?, ?)",
            (booking_id, f"Zahlung aktualisiert: {service.PAYMENTS[method]} · {pay_status}", service.now()),
        )
        flash("Zahlung aktualisiert.")
    return redirect(url_for("admin.booking_detail", booking_id=booking_id))


@bp.post("/buchungen/<int:booking_id>/kontakt")
def booking_contact(booking_id):
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    if not service.EMAIL_RE.match(email) or len(re_digits(phone)) < 6:
        flash("E-Mail oder Telefon ist ungültig.", "error")
    else:
        get_db().execute(
            "UPDATE bookings SET email = ?, phone = ? WHERE id = ?",
            (email, phone, booking_id),
        )
        flash("Kontaktdaten gespeichert.")
    return redirect(url_for("admin.booking_detail", booking_id=booking_id))


def re_digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


@bp.post("/buchungen/<int:booking_id>/bezahlt")
def booking_paid(booking_id):
    get_db().execute("UPDATE bookings SET payment_status = 'paid' WHERE id = ?", (booking_id,))
    get_db().execute(
        "INSERT INTO booking_events (booking_id, message, created_at) VALUES (?, ?, ?)",
        (booking_id, "Zahlung als erhalten markiert", service.now()),
    )
    flash("Zahlung als erhalten markiert.")
    return redirect(url_for("admin.booking_detail", booking_id=booking_id))


@bp.get("/kalender")
def calendar_view():
    db = get_db()
    models = db.execute("SELECT id, name FROM models ORDER BY sort_order, id").fetchall()
    if not models:
        return render_template("admin/calendar.html", models=[], weeks=[], title="Kalender")
    today = date.today()
    try:
        model_id = int(request.args.get("model") or models[0]["id"])
        year = int(request.args.get("year") or today.year)
        month = int(request.args.get("month") or today.month)
    except ValueError:
        model_id, year, month = models[0]["id"], today.year, today.month
    if not any(model["id"] == model_id for model in models):
        model_id = models[0]["id"]
    month = min(12, max(1, month))
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    marks: dict[str, list] = {}
    bookings = db.execute(
        """
        SELECT * FROM bookings
        WHERE model_id = ? AND status != 'cancelled' AND start_date < ? AND end_date > ?
        """,
        (model_id, end.isoformat(), start.isoformat()),
    ).fetchall()
    for booking in bookings:
        current = max(date.fromisoformat(booking["start_date"]), start)
        stop = min(date.fromisoformat(booking["end_date"]), end)
        while current < stop:
            marks.setdefault(current.isoformat(), []).append(
                {
                    "label": booking["last_name"],
                    "href": url_for("admin.booking_detail", booking_id=booking["id"]),
                    "status": booking["status"],
                }
            )
            current += timedelta(days=1)
    blocks = db.execute(
        """
        SELECT * FROM blocks
        WHERE model_id = ? AND start_date < ? AND end_date > ?
        """,
        (model_id, end.isoformat(), start.isoformat()),
    ).fetchall()
    for block in blocks:
        current = max(date.fromisoformat(block["start_date"]), start)
        stop = min(date.fromisoformat(block["end_date"]), end)
        while current < stop:
            marks.setdefault(current.isoformat(), []).append(
                {"label": block["reason"] or "Sperre", "href": "", "status": "block"}
            )
            current += timedelta(days=1)
    weeks = []
    for week in calendar.Calendar(firstweekday=0).monthdayscalendar(year, month):
        cells = []
        for day in week:
            if day == 0:
                cells.append(None)
            else:
                iso = date(year, month, day).isoformat()
                cells.append({"day": day, "iso": iso, "items": marks.get(iso, [])})
        weeks.append(cells)
    prev_month, prev_year = (12, year - 1) if month == 1 else (month - 1, year)
    next_month, next_year = (1, year + 1) if month == 12 else (month + 1, year)
    return render_template(
        "admin/calendar.html",
        models=models,
        model_id=model_id,
        year=year,
        month=month,
        month_name=service.MONTHS[month - 1],
        weeks=weeks,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        title="Kalender",
    )


@bp.get("/modelle")
def models():
    rows = get_db().execute("SELECT * FROM models ORDER BY sort_order, id").fetchall()
    return render_template("admin/models.html", models=[service.present_model(row) for row in rows], title="Modelle")


def _render_model_form(model=None):
    if model:
        presented = service.present_model(model)
        features = presented["features"]
        specs = presented["specs"]
        highlights = "\n".join(presented["highlights"])
        images = presented["images"]
    else:
        presented = None
        features, specs, highlights, images = [], [], "", []
    return render_template(
        "admin/model_form.html",
        model=presented,
        features=_pad(features, 4, {"icon": "users", "label": ""}),
        specs=_pad(specs, 3, {"icon": "users", "label": "", "value": ""}),
        highlights=highlights,
        images=images,
        icons=ICON_CHOICES,
        sizes=SIZES,
        title="Modell" if model else "Neues Modell",
    )


@bp.route("/modelle/neu", methods=["GET", "POST"])
def model_new():
    if request.method == "POST":
        try:
            model_id = _save_model(get_db(), _model_fields(request.form, request.files))
        except ValueError as exc:
            flash(str(exc), "error")
        else:
            flash("Modell angelegt.")
            return redirect(url_for("admin.model_edit", model_id=model_id))
    return _render_model_form()


@bp.route("/modelle/<int:model_id>", methods=["GET", "POST"])
def model_edit(model_id):
    db = get_db()
    model = db.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
    if not model:
        abort(404)
    if request.method == "POST":
        try:
            _save_model(db, _model_fields(request.form, request.files, model), model_id)
        except ValueError as exc:
            flash(str(exc), "error")
        else:
            flash("Modell gespeichert.")
            return redirect(url_for("admin.model_edit", model_id=model_id))
        model = db.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
    return _render_model_form(model)


@bp.post("/modelle/<int:model_id>/loeschen")
def model_delete(model_id):
    db = get_db()
    used = db.execute("SELECT 1 FROM bookings WHERE model_id = ?", (model_id,)).fetchone()
    if used:
        flash("Modell hat Buchungen und bleibt erhalten. Du kannst es deaktivieren.", "error")
        return redirect(url_for("admin.model_edit", model_id=model_id))
    db.execute("DELETE FROM blocks WHERE model_id = ?", (model_id,))
    db.execute("DELETE FROM models WHERE id = ?", (model_id,))
    flash("Modell gelöscht.")
    return redirect(url_for("admin.models"))


@bp.get("/extras")
def extras():
    rows = get_db().execute("SELECT * FROM extras ORDER BY sort_order, id").fetchall()
    return render_template("admin/extras.html", extras=rows, title="Extras")


def _render_extra_form(extra=None):
    return render_template("admin/extra_form.html", extra=extra, title="Extra" if extra else "Neues Extra")


@bp.route("/extras/neu", methods=["GET", "POST"])
def extra_new():
    if request.method == "POST":
        try:
            extra_id = _save_extra(get_db(), _extra_fields(request.form, request.files))
        except ValueError as exc:
            flash(str(exc), "error")
        else:
            flash("Extra angelegt.")
            return redirect(url_for("admin.extra_edit", extra_id=extra_id))
    return _render_extra_form()


@bp.route("/extras/<int:extra_id>", methods=["GET", "POST"])
def extra_edit(extra_id):
    db = get_db()
    extra = db.execute("SELECT * FROM extras WHERE id = ?", (extra_id,)).fetchone()
    if not extra:
        abort(404)
    if request.method == "POST":
        try:
            _save_extra(db, _extra_fields(request.form, request.files), extra_id)
        except ValueError as exc:
            flash(str(exc), "error")
        else:
            flash("Extra gespeichert.")
            return redirect(url_for("admin.extra_edit", extra_id=extra_id))
        extra = db.execute("SELECT * FROM extras WHERE id = ?", (extra_id,)).fetchone()
    return _render_extra_form(extra)


@bp.post("/extras/<int:extra_id>/loeschen")
def extra_delete(extra_id):
    get_db().execute("DELETE FROM extras WHERE id = ?", (extra_id,))
    flash("Extra gelöscht. Bestehende Buchungen behalten ihre gespeicherten Positionen.")
    return redirect(url_for("admin.extras"))


def _zone_from_form(form):
    name = form.get("name", "").strip()
    if not (1 <= len(name) <= 40):
        raise ValueError("Name der Zone fehlt.")
    prefixes = []
    for part in form.get("prefixes", "").replace(";", ",").split(","):
        item = part.strip().lower()
        if item == "*" or item.isdigit():
            prefixes.append(item)
    cities = []
    for part in form.get("cities", "").replace(";", ",").split(","):
        item = part.strip().lower()
        if item:
            cities.append(item)
    if not prefixes and not cities:
        raise ValueError("PLZ-Präfixe oder Orte werden gebraucht.")
    try:
        sort_order = int(form.get("sort_order") or 0)
    except ValueError as exc:
        raise ValueError("Reihenfolge ist ungültig.") from exc
    return {
        "name": name,
        "prefixes": ",".join(prefixes),
        "cities": ",".join(cities),
        "price_cents": service.parse_money(form.get("price", "0")),
        "note": form.get("note", "").strip()[:200],
        "active": 1 if form.get("active") == "1" else 0,
        "sort_order": sort_order,
    }


@bp.route("/zonen", methods=["GET", "POST"])
def zones():
    db = get_db()
    if request.method == "POST":
        try:
            fields = _zone_from_form(request.form)
            zone_id = request.form.get("zone_id", "").strip()
            if zone_id:
                db.execute(
                    """
                    UPDATE zones
                    SET name=?, prefixes=?, cities=?, price_cents=?, note=?, active=?, sort_order=?
                    WHERE id=?
                    """,
                    (
                        fields["name"], fields["prefixes"], fields["cities"], fields["price_cents"],
                        fields["note"], fields["active"], fields["sort_order"], int(zone_id),
                    ),
                )
                flash("Zone gespeichert.")
            else:
                db.execute(
                    """
                    INSERT INTO zones (name, prefixes, cities, price_cents, note, active, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fields["name"], fields["prefixes"], fields["cities"], fields["price_cents"],
                        fields["note"], fields["active"], fields["sort_order"],
                    ),
                )
                flash("Zone angelegt.")
        except (ValueError, sqlite3_error()) as exc:
            flash(str(exc), "error")
        return redirect(url_for("admin.zones"))
    rows = db.execute("SELECT * FROM zones ORDER BY sort_order, id").fetchall()
    return render_template("admin/zones.html", zones=rows, title="Lieferzonen")


def sqlite3_error():
    import sqlite3

    return sqlite3.Error


@bp.post("/zonen/<int:zone_id>/loeschen")
def zone_delete(zone_id):
    get_db().execute("DELETE FROM zones WHERE id = ?", (zone_id,))
    flash("Zone gelöscht.")
    return redirect(url_for("admin.zones"))


@bp.route("/sperren", methods=["GET", "POST"])
def blocks():
    db = get_db()
    models = db.execute("SELECT id, name FROM models ORDER BY sort_order, id").fetchall()
    if request.method == "POST":
        try:
            model_id = int(request.form.get("model_id", ""))
            start = service.parse_iso(request.form.get("start", ""))
            end_inclusive = service.parse_iso(request.form.get("end", ""))
        except (ValueError, service.QuoteError):
            flash("Modell oder Datum ist ungültig.", "error")
        else:
            if end_inclusive < start:
                flash("Das Enddatum liegt vor dem Startdatum.", "error")
            elif not any(model["id"] == model_id for model in models):
                flash("Modell nicht gefunden.", "error")
            else:
                db.execute(
                    "INSERT INTO blocks (model_id, start_date, end_date, reason) VALUES (?, ?, ?, ?)",
                    (
                        model_id,
                        start.isoformat(),
                        (end_inclusive + timedelta(days=1)).isoformat(),
                        request.form.get("reason", "").strip()[:200],
                    ),
                )
                flash("Sperre gespeichert.")
        return redirect(url_for("admin.blocks"))
    rows = db.execute(
        """
        SELECT blocks.*, models.name AS model_name
        FROM blocks JOIN models ON models.id = blocks.model_id
        ORDER BY blocks.start_date DESC
        """
    ).fetchall()
    view = []
    for row in rows:
        last = date.fromisoformat(row["end_date"]) - timedelta(days=1)
        view.append({**dict(row), "last_day": last.isoformat()})
    return render_template("admin/blocks.html", models=models, blocks=view, title="Sperrzeiten")


@bp.post("/sperren/<int:block_id>/loeschen")
def block_delete(block_id):
    get_db().execute("DELETE FROM blocks WHERE id = ?", (block_id,))
    flash("Sperre gelöscht.")
    return redirect(url_for("admin.blocks"))


@bp.get("/nachrichten")
def messages():
    rows = get_db().execute("SELECT * FROM messages ORDER BY id DESC").fetchall()
    return render_template("admin/messages.html", messages=rows, title="Nachrichten")


@bp.post("/nachrichten/<int:message_id>/gelesen")
def message_read(message_id):
    get_db().execute("UPDATE messages SET read = 1 WHERE id = ?", (message_id,))
    return redirect(url_for("admin.messages"))


@bp.post("/nachrichten/<int:message_id>/loeschen")
def message_delete(message_id):
    get_db().execute("DELETE FROM messages WHERE id = ?", (message_id,))
    flash("Nachricht gelöscht.")
    return redirect(url_for("admin.messages"))


@bp.post("/nachrichten/<int:message_id>/antwort")
def message_reply(message_id):
    from saunacore.mailer import notify_reply

    db = get_db()
    message = db.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    reply = (request.form.get("reply") or "").strip()
    if not message:
        abort(404)
    if not 2 <= len(reply) <= 4000:
        flash("Die Antwort braucht zwischen 2 und 4000 Zeichen.", "error")
        return redirect(url_for("admin.messages"))
    db.execute(
        "UPDATE messages SET reply = ?, replied_at = ?, read = 1 WHERE id = ?",
        (reply, service.now(), message_id),
    )
    status = notify_reply(db, message, reply)
    if status == "sent":
        flash("Antwort gespeichert und verschickt.")
    elif status == "failed":
        flash("Antwort gespeichert. Der Mailserver hat sie nicht angenommen.", "error")
    else:
        flash("Antwort gespeichert. Ein Mailserver ist nicht eingerichtet, deshalb ging keine E-Mail raus.")
    return redirect(url_for("admin.messages"))


def _save_setting(db, key: str, value: str) -> None:
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


@bp.route("/gutscheine", methods=["GET", "POST"])
def vouchers():
    db = get_db()
    if request.method == "POST":
        code = re.sub(r"\s+", "", (request.form.get("code") or "").strip().upper())
        note = (request.form.get("note") or "").strip()[:200]
        try:
            cents = service.parse_money(request.form.get("amount", ""))
            max_uses = int(request.form.get("max_uses") or "1")
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("admin.vouchers"))
        if not re.fullmatch(r"[A-Z0-9_-]{2,40}", code):
            flash("Der Code darf nur Buchstaben, Zahlen, _ und - enthalten.", "error")
        elif cents <= 0:
            flash("Der Wert muss größer als 0 sein.", "error")
        elif not 1 <= max_uses <= 100000:
            flash("Die Anzahl der Einlösungen ist ungültig.", "error")
        else:
            try:
                db.execute(
                    """
                    INSERT INTO vouchers (code, cents, note, active, max_uses, used, created_at)
                    VALUES (?, ?, ?, ?, ?, 0, ?)
                    """,
                    (code, cents, note, 1 if request.form.get("active") == "1" else 0, max_uses, service.now()),
                )
            except sqlite3.IntegrityError:
                flash("Diesen Code gibt es schon.", "error")
            else:
                flash("Gutschein gespeichert.")
        return redirect(url_for("admin.vouchers"))
    rows = db.execute("SELECT * FROM vouchers ORDER BY id DESC").fetchall()
    return render_template("admin/vouchers.html", vouchers=rows, title="Gutscheine")


@bp.post("/gutscheine/<int:voucher_id>/loeschen")
def voucher_delete(voucher_id):
    get_db().execute("DELETE FROM vouchers WHERE id = ?", (voucher_id,))
    flash("Gutschein gelöscht.")
    return redirect(url_for("admin.vouchers"))


@bp.route("/bewertungen", methods=["GET", "POST"])
def reviews():
    db = get_db()
    if request.method == "POST":
        author = (request.form.get("author") or "").strip()
        text = (request.form.get("text") or "").strip()
        raw_slug = (request.form.get("model_slug") or "").strip()
        model_slug = service.slugify(raw_slug) if raw_slug else ""
        try:
            rating = int(request.form.get("rating") or "5")
            sort_order = int(request.form.get("sort_order") or "0")
        except ValueError:
            flash("Bewertung oder Reihenfolge ist ungültig.", "error")
            return redirect(url_for("admin.reviews"))
        if not 2 <= len(author) <= 80 or not 10 <= len(text) <= 1000:
            flash("Name und Text werden gebraucht.", "error")
        elif not 1 <= rating <= 5:
            flash("Die Bewertung liegt zwischen 1 und 5.", "error")
        else:
            db.execute(
                """
                INSERT INTO reviews (author, text, rating, model_slug, active, sort_order, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    author,
                    text,
                    rating,
                    model_slug,
                    1 if request.form.get("active") == "1" else 0,
                    sort_order,
                    service.now(),
                ),
            )
            flash("Bewertung gespeichert. Ohne Eintrag bleibt der Bereich auf der Website leer.")
        return redirect(url_for("admin.reviews"))
    rows = db.execute("SELECT * FROM reviews ORDER BY sort_order, id DESC").fetchall()
    models = db.execute("SELECT slug, name FROM models ORDER BY sort_order, id").fetchall()
    return render_template("admin/reviews.html", reviews=rows, models=models, title="Bewertungen")


@bp.post("/bewertungen/<int:review_id>/loeschen")
def review_delete(review_id):
    get_db().execute("DELETE FROM reviews WHERE id = ?", (review_id,))
    flash("Bewertung gelöscht.")
    return redirect(url_for("admin.reviews"))


@bp.get("/kunden")
def customers():
    rows = get_db().execute(
        """
        SELECT email,
               MAX(first_name) AS first_name,
               MAX(last_name) AS last_name,
               MAX(phone) AS phone,
               COUNT(*) AS bookings,
               SUM(CASE WHEN status != 'cancelled' THEN gross_cents ELSE 0 END) AS spent,
               MAX(created_at) AS last_booking
        FROM bookings
        GROUP BY email
        ORDER BY last_booking DESC
        """
    ).fetchall()
    return render_template("admin/customers.html", customers=rows, title="Kunden")


CONTENT_IMAGES = (
    "/static/uploads/fasssauna-1.jpg",
    "/static/uploads/kombi-1.jpg",
    "/static/uploads/badefass-1.jpg",
    "/static/images/hero.jpg",
    "/static/images/choose.jpg",
    "/static/images/deliver.jpg",
    "/static/images/relax.jpg",
    "/static/images/interior.jpg",
    "/static/images/interior-2.jpg",
    "/static/images/wood.jpg",
    "/static/images/stove.jpg",
)


def get_available_images() -> list[str]:
    results = []
    try:
        uploads_dir = Path(current_app.static_folder) / "uploads"
        if uploads_dir.exists():
            for file in sorted(uploads_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True):
                if file.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".svg"}:
                    results.append(f"/static/uploads/{file.name}")
    except Exception:
        pass
    for img in CONTENT_IMAGES:
        if img not in results:
            results.append(img)
    return results


def _clip(value: str, limit: int) -> str:
    return (value or "").strip()[:limit]


def _save_content(db, form, files=None):
    files = files or {}
    hero_image = form.get("hero_image", "").strip()
    hero_upload = files.get("hero_image_file") if hasattr(files, "get") else None
    if hero_upload and hero_upload.filename:
        hero_image = service.save_image(hero_upload)
    custom_hero = form.get("hero_image_custom", "").strip()
    if custom_hero and service.safe_image_path(custom_hero):
        hero_image = custom_hero

    updates = {
        "hero_kicker": _clip(form.get("hero_kicker", ""), 80),
        "hero_title": _clip(form.get("hero_title", ""), 180),
        "hero_lede": _clip(form.get("hero_lede", ""), 400),
        "hero_image": hero_image,
        "fleet_title": _clip(form.get("fleet_title", ""), 120),
        "fleet_text": _clip(form.get("fleet_text", ""), 600),
        "fleet_page_title": _clip(form.get("fleet_page_title", ""), 180),
        "fleet_page_text": _clip(form.get("fleet_page_text", ""), 600),
        "how_kicker": _clip(form.get("how_kicker", ""), 80),
        "how_title": _clip(form.get("how_title", ""), 180),
        "how_lede": _clip(form.get("how_lede", ""), 600),
        "prices_title": _clip(form.get("prices_title", ""), 180),
        "prices_text": _clip(form.get("prices_text", ""), 800),
        "contact_title": _clip(form.get("contact_title", ""), 180),
        "contact_text": _clip(form.get("contact_text", ""), 600),
        "footer_line": _clip(form.get("footer_line", ""), 160),
        "corporate_text": _clip(form.get("corporate_text", ""), 2000),
        "meta_description": _clip(form.get("meta_description", ""), 300),
        "site_url": seo.clean_site_url(form.get("site_url", "")),
        "impressum_note": _clip(form.get("impressum_note", ""), 800),
        "privacy_text": _clip(form.get("privacy_text", ""), 6000),
        "terms_text": _clip(form.get("terms_text", ""), 6000),
        "rental_text": _clip(form.get("rental_text", ""), 6000),
    }
    if not service.safe_image_path(updates["hero_image"]):
        raise ValueError("Das Hero-Bild ist ungültig.")
    for key in ("hero_title", "hero_lede", "fleet_title", "prices_title", "contact_title"):
        if len(updates[key]) < 2:
            raise ValueError("Titel und Einleitung dürfen nicht leer sein.")
    points = []
    for icon, title, text in zip(form.getlist("point_icon"), form.getlist("point_title"), form.getlist("point_text")):
        title = title.strip()
        text = text.strip()
        if not title and not text:
            continue
        if not title or not text:
            raise ValueError("Jeder Vorteil braucht Titel und Text.")
        if icon not in ICON_CHOICES:
            icon = "spark"
        points.append({"icon": icon, "title": title[:80], "text": text[:400]})
    if not points:
        raise ValueError("Mindestens ein Vorteil wird gebraucht.")

    steps = []
    step_titles = form.getlist("step_title")
    step_texts = form.getlist("step_text")
    step_images = form.getlist("step_image")
    step_files = files.getlist("step_image_file") if hasattr(files, "getlist") else []
    for i, (title, text, image) in enumerate(zip(step_titles, step_texts, step_images)):
        title = title.strip()
        text = text.strip()
        if not title and not text:
            continue
        if not title or not text:
            raise ValueError("Jeder Schritt braucht Titel und Text.")
        if i < len(step_files) and step_files[i] and step_files[i].filename:
            image = service.save_image(step_files[i])
        elif not service.safe_image_path(image):
            image = "/static/uploads/fasssauna-1.jpg"
        steps.append({"title": title[:80], "text": text[:800], "image": image})
    if not steps:
        raise ValueError("Mindestens ein Schritt wird gebraucht.")
    faq = []
    for question, answer in zip(form.getlist("faq_q"), form.getlist("faq_a")):
        question = question.strip()
        answer = answer.strip()
        if not question and not answer:
            continue
        if not question or not answer:
            raise ValueError("Jede FAQ-Zeile braucht Frage und Antwort.")
        faq.append({"q": question[:200], "a": answer[:2000]})
    if not faq:
        raise ValueError("Mindestens eine FAQ-Frage wird gebraucht.")
    updates["points_json"] = json.dumps(points, ensure_ascii=False)
    updates["steps_json"] = json.dumps(steps, ensure_ascii=False)
    updates["faq_json"] = json.dumps(faq, ensure_ascii=False)
    for key, value in updates.items():
        db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


@bp.route("/inhalte", methods=["GET", "POST"])
def content():
    db = get_db()
    if request.method == "POST":
        try:
            _save_content(db, request.form, request.files)
        except ValueError as exc:
            flash(str(exc), "error")
        else:
            flash("Texte und Bilder gespeichert. Die Website zeigt sie sofort.")
        return redirect(url_for("admin.content"))
    settings = service.load_settings(db)
    return render_template(
        "admin/content.html",
        points=service.json_list(settings.get("points_json", ""), service.CONTENT_DEFAULTS["points_json"]),
        steps=service.json_list(settings.get("steps_json", ""), service.CONTENT_DEFAULTS["steps_json"]),
        faq=service.json_list(settings.get("faq_json", ""), service.CONTENT_DEFAULTS["faq_json"]),
        images=get_available_images(),
        icons=ICON_CHOICES,
        title="Inhalte",
    )


@bp.route("/einstellungen", methods=["GET", "POST"])
def settings():
    db = get_db()
    if request.method == "POST" and request.form.get("action") == "password":
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        again = request.form.get("new_password_again", "")
        admin = db.execute("SELECT * FROM admins WHERE id = ?", (session["admin_id"],)).fetchone()
        if not admin or not service.verify_password(current, admin["password_hash"]):
            flash("Das aktuelle Passwort ist falsch.", "error")
        elif len(new) < 8:
            flash("Das neue Passwort braucht mindestens 8 Zeichen.", "error")
        elif new != again:
            flash("Die neuen Passwörter stimmen nicht überein.", "error")
        else:
            db.execute(
                "UPDATE admins SET password_hash = ? WHERE id = ?",
                (service.hash_password(new), admin["id"]),
            )
            flash("Passwort geändert. Der Hinweis auf der Login-Seite ist damit weg.")
        return redirect(url_for("admin.settings"))
    if request.method == "POST" and request.form.get("action") == "deposit":
        try:
            cents = service.parse_money(request.form.get("deposit", "0"))
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("admin.settings"))
        if cents > 500000:
            flash("Die Kaution ist zu hoch.", "error")
            return redirect(url_for("admin.settings"))
        _save_setting(db, "deposit_cents", str(cents))
        flash("Kaution gespeichert.")
        return redirect(url_for("admin.settings"))
    if request.method == "POST" and request.form.get("action") == "mail":
        current = service.load_settings(db)
        host = (request.form.get("smtp_host") or "").strip()[:200]
        user = (request.form.get("smtp_user") or "").strip()[:200]
        sender = (request.form.get("smtp_from") or "").strip()[:200]
        try:
            port = int(request.form.get("smtp_port") or "587")
        except ValueError:
            flash("Der Port muss eine Zahl sein.", "error")
            return redirect(url_for("admin.settings"))
        if not 1 <= port <= 65535:
            flash("Der Port ist ungültig.", "error")
            return redirect(url_for("admin.settings"))
        if sender and not service.EMAIL_RE.match(sender):
            flash("Der Absender ist ungültig.", "error")
            return redirect(url_for("admin.settings"))
        password = request.form.get("smtp_password") or ""
        if not password:
            password = current.get("smtp_password") or ""
        _save_setting(db, "smtp_host", host)
        _save_setting(db, "smtp_port", str(port))
        _save_setting(db, "smtp_user", user)
        _save_setting(db, "smtp_password", password)
        _save_setting(db, "smtp_from", sender)
        _save_setting(db, "smtp_tls", "1" if request.form.get("smtp_tls") == "1" else "0")
        flash("Mailserver gespeichert. Ohne Host wird keine E-Mail verschickt.")
        return redirect(url_for("admin.settings"))
    if request.method == "POST" and request.form.get("action") == "stripe":
        current = service.load_settings(db)
        publishable = (request.form.get("stripe_publishable") or "").strip()[:200]
        secret = request.form.get("stripe_secret") or ""
        webhook = request.form.get("stripe_webhook") or ""
        if not secret:
            secret = current.get("stripe_secret") or ""
        if not webhook:
            webhook = current.get("stripe_webhook") or ""
        _save_setting(db, "stripe_publishable", publishable)
        _save_setting(db, "stripe_secret", secret.strip()[:200])
        _save_setting(db, "stripe_webhook", webhook.strip()[:200])
        flash("Zahlungsdienstleister gespeichert.")
        return redirect(url_for("admin.settings"))
    if request.method == "POST":
        updates = {}
        for key in service.DEFAULT_SETTINGS:
            value = request.form.get(key, "").strip()
            if key in {"vat_percent", "min_nights", "max_nights", "cancellation_days"}:
                try:
                    number = int(value)
                except ValueError:
                    flash(f"{key} muss eine Zahl sein.", "error")
                    return redirect(url_for("admin.settings"))
                if number < 0 or number > 100:
                    flash("Zahl liegt außerhalb des erlaubten Bereichs.", "error")
                    return redirect(url_for("admin.settings"))
                value = str(number)
            if not value and key not in {"vat_id"}:
                flash("Pflichtfelder dürfen nicht leer sein.", "error")
                return redirect(url_for("admin.settings"))
            updates[key] = value
        if int(updates["min_nights"]) > int(updates["max_nights"]):
            flash("Mindestnächte dürfen nicht über den maximalen Nächten liegen.", "error")
            return redirect(url_for("admin.settings"))
        for key, value in updates.items():
            db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
        flash("Einstellungen gespeichert.")
        return redirect(url_for("admin.settings"))
    return render_template("admin/settings.html", title="Einstellungen")


@bp.get("/medien")
def media_gallery():
    uploads_dir = Path(current_app.static_folder) / "uploads"
    files = []
    if uploads_dir.exists():
        for f in sorted(uploads_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".svg"}:
                stat = f.stat()
                size_kb = round(stat.st_size / 1024, 1)
                files.append({
                    "name": f.name,
                    "url": f"/static/uploads/{f.name}",
                    "size_kb": size_kb,
                    "date": datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M"),
                })
    return render_template(
        "admin/media.html",
        files=files,
        total_files=len(files),
        title="Medien & Fotos",
    )


@bp.post("/medien/upload")
def media_upload():
    uploaded_files = request.files.getlist("files")
    if not uploaded_files or (len(uploaded_files) == 1 and not uploaded_files[0].filename):
        single = request.files.get("file")
        uploaded_files = [single] if single and single.filename else []
    saved = []
    for f in uploaded_files:
        if f and f.filename:
            try:
                url = service.save_image(f)
                saved.append(url)
            except ValueError as exc:
                flash(f"{f.filename}: {exc}", "error")
    if saved:
        flash(f"{len(saved)} Bild(er) erfolgreich hochgeladen.")
    if request.headers.get("Accept") == "application/json" or request.is_json:
        return {"ok": True, "saved": saved}
    return redirect(url_for("admin.media_gallery"))


@bp.post("/medien/<path:filename>/loeschen")
def media_delete(filename):
    safe_name = Path(filename).name
    target = Path(current_app.static_folder) / "uploads" / safe_name
    if target.exists() and target.is_file():
        try:
            target.unlink()
            flash(f"Bild {safe_name} gelöscht.")
        except OSError as exc:
            flash(f"Konnte nicht gelöscht werden: {exc}", "error")
    else:
        flash("Datei nicht gefunden.", "error")
    return redirect(url_for("admin.media_gallery"))

