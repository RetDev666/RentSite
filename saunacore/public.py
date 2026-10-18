from __future__ import annotations

import json
from datetime import date

from flask import Blueprint, Response, abort, redirect, render_template, request, url_for

from saunacore.db import get_db
from saunacore import seo, service

bp = Blueprint("public", __name__)


def _settings():
    return service.load_settings(get_db())


def _content():
    return service.present_content(_settings())


def _pack(settings, title, description, robots="index, follow", canonical="", image="", crumbs=None, extra_nodes=None, page_kind="WebPage"):
    description = seo.clip(description)
    base = seo.site_base(settings)
    raw = (canonical or request.path or "/").strip()
    if not raw.startswith("/"):
        raw = "/" + raw
    path, _, query = raw.partition("?")
    canonical_url = base + ("/" if path == "/" else path)
    if query:
        canonical_url += "?" + query
    content = service.present_content(settings)
    graph = None
    if robots.startswith("index"):
        nodes = [seo.webpage(title, description, canonical_url, base, page_kind)]
        if crumbs:
            nodes.append(seo.breadcrumb_list(crumbs, base, canonical_url))
        nodes.extend(extra_nodes or [])
        graph = seo.graph(settings, base, nodes)
    return {
        "seo": {
            "description": description,
            "robots": robots,
            "canonical": canonical_url,
            "image": seo.absolute(base, image or content["hero_image"]),
            "image_alt": title,
            "graph": graph,
        },
        "crumbs": crumbs or [],
    }


def _crumb(name, url=""):
    return {"name": name, "url": url}


def _trail(*parts):
    return [_crumb("Start", url_for("public.home")), *parts]


def _active_models():
    return [
        service.present_model(row)
        for row in get_db().execute("SELECT * FROM models WHERE active = 1 ORDER BY sort_order, id")
    ]


def _reviews(db, slug: str = ""):
    if slug:
        return db.execute(
            """
            SELECT * FROM reviews
            WHERE active = 1 AND (model_slug = '' OR model_slug = ?)
            ORDER BY sort_order, id
            """,
            (slug,),
        ).fetchall()
    return db.execute(
        "SELECT * FROM reviews WHERE active = 1 ORDER BY sort_order, id"
    ).fetchall()


@bp.route("/")
def home():
    db = get_db()
    settings = _settings()
    content = service.present_content(settings)
    models = _active_models()[:3]
    if (settings.get("meta_description") or "").strip():
        description = content["meta_description"]
    else:
        description = f"{content['hero_lede']} Mobile Fasssaunen zur Miete, geliefert an deine Markierung."
    return render_template(
        "home.html",
        models=models,
        reviews=_reviews(db),
        title="Premium Sauna on Demand",
        **_pack(settings, "Premium Sauna on Demand", description, image=content["hero_image"]),
    )


@bp.route("/flotte")
def fleet():
    settings = _settings()
    content = service.present_content(settings)
    models = _active_models()
    title = "Fasssaunen zur Miete"
    crumbs = _trail(_crumb("Flotte"))
    return render_template(
        "fleet.html",
        models=models,
        title=title,
        **_pack(
            settings,
            title,
            content["fleet_page_text"],
            crumbs=crumbs,
            extra_nodes=[seo.item_list(models, seo.site_base(settings))],
        ),
    )


@bp.route("/flotte/<slug>")
def model_page(slug):
    row = get_db().execute("SELECT * FROM models WHERE slug = ? AND active = 1", (slug,)).fetchone()
    if not row:
        abort(404)
    model = service.present_model(row)
    settings = _settings()
    title = f"{model['name']} mieten"
    description = (
        f"{model['name']}: {model['subtitle']}. {model['summary']} "
        f"Tagessatz {service.format_euro(model['price_cents'])} pro Tag, inklusive MwSt."
    )
    crumbs = _trail(_crumb("Flotte", url_for("public.fleet")), _crumb(model["name"]))
    base = seo.site_base(settings)
    return render_template(
        "model.html",
        model=model,
        reviews=_reviews(get_db(), slug),
        title=title,
        **_pack(
            settings,
            title,
            description,
            image=model["images"][0] if model["images"] else "",
            crumbs=crumbs,
            extra_nodes=[seo.service_node(model, base)],
        ),
    )


@bp.route("/so-funktionierts")
def how():
    settings = _settings()
    content = service.present_content(settings)
    title = "So funktioniert's"
    return render_template(
        "how.html",
        title=title,
        **_pack(settings, title, content["how_lede"], crumbs=_trail(_crumb(title))),
    )


@bp.route("/preise")
def prices():
    db = get_db()
    settings = _settings()
    content = service.present_content(settings)
    zones = db.execute("SELECT * FROM zones WHERE active = 1 ORDER BY sort_order, id").fetchall()
    extras = db.execute("SELECT * FROM extras WHERE active = 1 ORDER BY sort_order, id").fetchall()
    models = _active_models()
    title = "Preise und Lieferzonen"
    return render_template(
        "prices.html",
        models=models,
        zones=zones,
        extras=extras,
        title=title,
        **_pack(
            settings,
            title,
            content["prices_text"],
            crumbs=_trail(_crumb("Preise")),
            extra_nodes=[seo.item_list(models, seo.site_base(settings))],
        ),
    )


@bp.route("/kontakt", methods=["GET", "POST"])
def contact():
    error = None
    if request.method == "POST":
        if not service.csrf_ok():
            error = "Die Sitzung ist abgelaufen. Bitte lade die Seite neu."
        else:
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            phone = request.form.get("phone", "").strip()
            body = request.form.get("body", "").strip()
            if len(name) < 2 or len(name) > 80:
                error = "Bitte gib deinen Namen an."
            elif not service.EMAIL_RE.match(email):
                error = "Bitte gib eine gültige E-Mail an."
            elif phone and len(phone) > 40:
                error = "Die Telefonnummer ist zu lang."
            elif len(body) < 10 or len(body) > 4000:
                error = "Die Nachricht sollte zwischen 10 und 4000 Zeichen lang sein."
            else:
                get_db().execute(
                    "INSERT INTO messages (name, email, phone, body, read, created_at) VALUES (?, ?, ?, ?, 0, ?)",
                    (name, email, phone, body, service.now()),
                )
                return redirect(url_for("public.contact", sent=1))
    settings = _settings()
    content = service.present_content(settings)
    description = (
        f"{content['contact_text']} {settings['company_name']}, "
        f"{settings['street']}, {settings['postal_code']} {settings['city']}."
    )
    return render_template(
        "contact.html",
        error=error,
        sent=request.args.get("sent") == "1",
        form=request.form,
        title="Kontakt",
        **_pack(
            settings,
            "Kontakt",
            description,
            crumbs=_trail(_crumb("Kontakt")),
            page_kind="ContactPage",
        ),
    )


@bp.route("/buchen/<slug>")
def booking(slug):
    db = get_db()
    row = db.execute("SELECT * FROM models WHERE slug = ? AND active = 1", (slug,)).fetchone()
    if not row:
        abort(404)
    model = service.present_model(row)
    extras = [
        service.present_extra(item)
        for item in db.execute("SELECT * FROM extras WHERE active = 1 ORDER BY sort_order, id")
    ]
    settings = service.load_settings(db)
    boot = {
        "csrf": service.ensure_csrf(),
        "today": date.today().isoformat(),
        "minNights": int(settings["min_nights"]),
        "maxNights": int(settings["max_nights"]),
        "model": {
            "id": model["id"],
            "slug": model["slug"],
            "name": model["name"],
            "subtitle": model["subtitle"],
            "image": model["images"][0] if model["images"] else "",
            "unit": service.format_euro(model["price_cents"]),
        },
        "extras": [
            {
                "id": item["id"],
                "slug": item.get("slug", ""),
                "name": item["name"],
                "kind": item["kind"],
                "image": item.get("image", ""),
                "price_cents": item["price_cents"],
                "price": service.format_euro(item["price_cents"]),
            }
            for item in extras
        ],
        "prefill": {
            "start": (request.args.get("start") or "")[:10],
            "end": (request.args.get("end") or "")[:10],
            "address": (request.args.get("address") or "")[:200],
            "lat": (request.args.get("lat") or "")[:20],
            "lng": (request.args.get("lng") or "")[:20],
        },
        "stripe": bool((settings.get("stripe_secret") or "").strip()),
    }
    zones = db.execute("SELECT * FROM zones WHERE active = 1 ORDER BY sort_order, id").fetchall()
    boot["zones"] = [
        {
            "id": z["id"],
            "name": z["name"],
            "price_cents": int(z["price_cents"]),
            "price": "kostenlos" if int(z["price_cents"]) == 0 else service.format_euro(int(z["price_cents"])),
            "badge": service.zone_badge(z),
        }
        for z in zones
    ]
    return render_template(
        "booking.html",
        model=model,
        extras=extras,
        zones=zones,
        boot=boot,
        checkout=True,
        back_url=url_for("public.model_page", slug=slug),
        title=f"Buchen · {model['name']}",
        **_pack(
            settings,
            f"Buchen · {model['name']}",
            f"Buchung für {model['name']}. Datum, Lieferort und Extras.",
            robots="noindex, follow",
            canonical=url_for("public.model_page", slug=slug),
            image=model["images"][0] if model["images"] else "",
        ),
    )


def _load_thanks(number: str, token: str):
    row = get_db().execute("SELECT * FROM bookings WHERE number = ?", (number,)).fetchone()
    if not row or not service.tokens_match(token, row["public_token"]):
        return None
    return row


def _thanks_context(row, cancel_error: str = ""):
    db = get_db()
    settings = service.load_settings(db)
    session_id = (request.args.get("session_id") or "").strip()
    if session_id and (settings.get("stripe_secret") or "").strip():
        from saunacore.stripe_pay import pull_session

        try:
            pull_session(db, row, session_id)
        except service.QuoteError:
            pass
        row = db.execute("SELECT * FROM bookings WHERE id = ?", (row["id"],)).fetchone()
    mail = db.execute(
        "SELECT status FROM emails WHERE booking_id = ? ORDER BY id DESC LIMIT 1",
        (row["id"],),
    ).fetchone()
    token = request.args.get("t") or request.form.get("t") or ""
    return {
        "booking": row,
        "extras": json.loads(row["extras_json"]),
        "range_label": service.format_range(date.fromisoformat(row["start_date"]), date.fromisoformat(row["end_date"])),
        "checkout": True,
        "title": "Buchung bestätigt",
        "mail_sent": bool(mail and mail["status"] == "sent"),
        "can_cancel": service.guest_can_cancel(row, settings),
        "cancel_error": cancel_error,
        "token": token,
        **_pack(
            settings,
            "Buchung bestätigt",
            "Deine Buchung ist angekommen.",
            robots="noindex, follow",
            canonical=request.path + ("?t=" + token if token else ""),
        ),
    }


@bp.route("/buchung/<number>")
def thanks(number):
    row = _load_thanks(number, request.args.get("t") or "")
    if not row:
        abort(404)
    return render_template("thanks.html", **_thanks_context(row))


@bp.route("/buchung/finden", methods=["GET", "POST"])
def find_booking():
    error = ""
    if request.method == "POST":
        if not service.csrf_ok():
            error = "Die Sitzung ist abgelaufen. Bitte lade die Seite neu."
        else:
            number = (request.form.get("number") or "").strip().upper()
            email = (request.form.get("email") or "").strip().lower()
            row = get_db().execute("SELECT * FROM bookings WHERE number = ?", (number,)).fetchone()
            stored = (row["email"] if row else "").strip().lower()
            same = bool(row) and len(stored) == len(email) and service.tokens_match(email, stored)
            if not same:
                error = "Buchung nicht gefunden."
            else:
                return redirect(url_for("public.thanks", number=row["number"], t=row["public_token"]))
    return render_template(
        "find.html",
        error=error,
        title="Buchung finden",
        **_pack(
            _settings(),
            "Buchung finden",
            "Bestellnummer und dieselbe E-Mail wie bei der Buchung öffnen die Buchung.",
            robots="noindex, follow",
            crumbs=_trail(_crumb("Buchung finden")),
        ),
    )


@bp.post("/buchung/<number>/storno")
def guest_cancel(number):
    token = request.form.get("t") or ""
    row = _load_thanks(number, token)
    if not row:
        abort(404)
    if not service.csrf_ok():
        return render_template("thanks.html", **_thanks_context(row, "Die Sitzung ist abgelaufen. Bitte lade die Seite neu."))
    settings = service.load_settings(get_db())
    if not service.guest_can_cancel(row, settings):
        return render_template(
            "thanks.html",
            **_thanks_context(row, "Diese Buchung kann nicht mehr kostenlos storniert werden."),
        )
    service.set_status(get_db(), row["id"], "cancelled")
    return redirect(url_for("public.thanks", number=row["number"], t=row["public_token"]))


@bp.get("/buchung/<number>/beleg.pdf")
def guest_pdf(number):
    row = _load_thanks(number, request.args.get("t") or "")
    if not row:
        abort(404)
    from saunacore.pdf import invoice_pdf

    payload = invoice_pdf(row, service.load_settings(get_db()), json.loads(row["extras_json"]))
    return Response(
        payload,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={row['number']}.pdf",
            "X-Robots-Tag": "noindex",
        },
    )


def _legal(key: str, title: str, description: str):
    return render_template(
        "legal.html",
        legal=key,
        title=title,
        **_pack(_settings(), title, description, crumbs=_trail(_crumb(title))),
    )


@bp.route("/impressum")
def impressum():
    settings = _settings()
    return _legal(
        "impressum",
        "Impressum",
        f"Impressum: {settings['owner_name']}, {settings['street']}, {settings['postal_code']} {settings['city']}.",
    )


@bp.route("/datenschutz")
def privacy():
    content = _content()
    lead = content["privacy"][0] if content["privacy"] else "Datenschutz"
    return _legal("datenschutz", "Datenschutz", lead)


@bp.route("/agb")
def terms():
    content = _content()
    lead = content["terms"][0] if content["terms"] else "AGB"
    return _legal("agb", "AGB", lead)


@bp.route("/mietbedingungen")
def rental_terms():
    content = _content()
    lead = content["rental"][0] if content["rental"] else "Mietbedingungen"
    return _legal("mietbedingungen", "Mietbedingungen", lead)


@bp.route("/faq")
def faq():
    settings = _settings()
    content = service.present_content(settings)
    title = "Häufige Fragen"
    return render_template(
        "faq.html",
        title=title,
        **_pack(
            settings,
            title,
            "Antworten zu Preis, Lieferzone, Stornierung, Kaution und Zahlung bei der Saunamiete.",
            crumbs=_trail(_crumb("FAQ")),
            extra_nodes=[seo.faq_page(content["faq"])],
        ),
    )


@bp.get("/robots.txt")
def robots():
    base = seo.site_base(_settings())
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /api\n"
        f"Sitemap: {base}/sitemap.xml\n"
    )
    return Response(body, mimetype="text/plain")


@bp.get("/sitemap.xml")
def sitemap():
    from xml.sax.saxutils import escape

    settings = _settings()
    base = seo.site_base(settings)
    content = service.present_content(settings)
    pages = [
        ("/", [{"loc": seo.absolute(base, content["hero_image"]), "title": "Mobile Fasssauna"}]),
        ("/so-funktionierts", []),
        ("/preise", []),
        ("/kontakt", []),
        ("/faq", []),
        ("/impressum", []),
        ("/datenschutz", []),
        ("/agb", []),
        ("/mietbedingungen", []),
    ]
    models = _active_models()
    fleet_images = [
        {"loc": seo.absolute(base, model["images"][0]), "title": model["name"]}
        for model in models
        if model["images"]
    ]
    pages.insert(1, ("/flotte", fleet_images))
    for model in models:
        pages.append(
            (
                f"/flotte/{model['slug']}",
                [
                    {"loc": seo.absolute(base, image), "title": model["name"]}
                    for image in model["images"]
                ],
            )
        )
    blocks = []
    for path, images in pages:
        lines = [f"  <url><loc>{escape(base + ('/' if path == '/' else path))}</loc>"]
        for image in images:
            lines.append(
                "    <image:image>"
                f"<image:loc>{escape(image['loc'])}</image:loc>"
                f"<image:title>{escape(image['title'])}</image:title>"
                "</image:image>"
            )
        lines.append("  </url>")
        blocks.append("\n".join(lines))
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        + "\n".join(blocks)
        + "\n</urlset>\n"
    )
    return Response(xml, mimetype="application/xml")
