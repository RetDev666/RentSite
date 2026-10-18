from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import current_app, request, session
from markupsafe import Markup, escape

DEMO_EMAIL = "admin@saunacore.de"
DEMO_PASSWORD = "SaunaAdmin2026!"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
STATUSES = ("new", "confirmed", "delivery", "active", "completed", "cancelled")
STATUS_LABELS = {
    "new": "Neu",
    "confirmed": "Bestätigt",
    "delivery": "Unterwegs",
    "active": "Vermietet",
    "completed": "Abgeschlossen",
    "cancelled": "Storniert",
}
PAYMENTS = {"card": "Kreditkarte", "paypal": "PayPal", "invoice": "Rechnung"}
KIND_LABELS = {"miete": "Miete", "kauf": "Kauf", "service": "Service"}
MONTHS = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]
MONTHS_SHORT = [
    "Jan.", "Feb.", "März", "Apr.", "Mai", "Juni",
    "Juli", "Aug.", "Sep.", "Okt.", "Nov.", "Dez.",
]
DEFAULT_SETTINGS = {
    "company_name": "Amphora-Spa",
    "owner_name": "Amphora-Spa Berlin-Brandenburg",
    "street": "Tiefenbrunnen 1",
    "postal_code": "14929",
    "city": "Treuenbrietzen",
    "email": "info@amphora-spa.de",
    "phone": "+49 176 2033 1535",
    "vat_id": "DE123456789",
    "vat_percent": "19",
    "min_nights": "1",
    "max_nights": "21",
    "cancellation_days": "7",
}
EXTRA_DEFAULTS = {
    "deposit_cents": "30000",
    "smtp_host": "",
    "smtp_port": "587",
    "smtp_user": "",
    "smtp_password": "",
    "smtp_from": "",
    "smtp_tls": "1",
    "stripe_publishable": "",
    "stripe_secret": "",
    "stripe_webhook": "",
    "meta_description": "",
    "site_url": "",
}
SECRET_KEYS = ("smtp_password", "stripe_secret", "stripe_webhook")

_POINTS = [
    {"icon": "leaf", "title": "Premium Thermoholz", "text": "Nachhaltiges Thermoholz für optimale Wärmedämmung und reinen Saunaduft."},
    {"icon": "truck", "title": "Lieferung & Abholung", "text": "Bequeme Lieferung direkt zu dir nach Hause oder kostenlose Selbstabholung in Treuenbrietzen."},
    {"icon": "spark", "title": "Hydro- & Air-Massage", "text": "Leistungsstarke Whirlpool-Massagedüsen und stimmungsvolle LED-Beleuchtung im Hot Tub."},
]
_STEPS = [
    {
        "title": "Auswählen",
        "text": "Wähle dein Wunschmodell (Badefass, Panoramasauna oder Kombi) und den Zeitraum. Preis und Verfügbarkeit siehst du sofort.",
        "image": "/static/uploads/badefass-1.jpg",
    },
    {
        "title": "Lieferung oder Abholung",
        "text": "Wir bringen die Sauna an deinen Wunschort oder du holst den Anhänger kostenlos in Treuenbrietzen ab (PKW mit Führerschein BE).",
        "image": "/static/uploads/kombi-1.jpg",
    },
    {
        "title": "Entspannen & Genießen",
        "text": "Lehne dich zurück und genieße dein privates Spa-Erlebnis unter freiem Himmel. Nach Ablauf holen wir die Sauna wieder ab.",
        "image": "/static/uploads/fasssauna-1.jpg",
    },
]
_PREVIOUS_FAQ = [
    {"q": "Wie wird der Preis berechnet?", "a": "Tagessatz mal Nächte, plus eventuelle Lieferung (0 € bei Selbstabholung), plus Extras. Die MwSt. von {vat}% ist enthalten."},
    {"q": "Wann ist die Lieferung kostenlos?", "a": "Kostenlose Selbstabholung ab Treuenbrietzen (14929) oder Zone A. Andere Gebiete berechnen wir nach Entfernung."},
]
_FAQ = [
    {"q": "Wie wird der Preis berechnet?", "a": "Tagessatz mal Nächte, plus eventuelle Lieferung (0 € bei Selbstabholung), plus Extras und die Kaution von 300 € (in bar bei Übergabe). Die MwSt. von {vat}% ist enthalten."},
    {"q": "Was kostet die Lieferung?", "a": "Kostenlose Selbstabholung ab Treuenbrietzen (14929). Bei Lieferung berechnen wir je nach Modell 1 bis 2 Euro pro gefahrenem Kilometer."},
    {"q": "Was benötige ich für die Selbstabholung?", "a": "Ein Auto mit Anhängerkupplung sowie einen PKW-Führerschein der Klasse BE. Der Anhänger ist vollständig zugelassen und fahrbereit."},
    {"q": "Was brauche ich vor Ort?", "a": "Für das Badefass einen normalen Gartenschlauch mit Wasseranschluss und Brennholz. Für Sauna und Beleuchtung genügt eine normale 230V-Steckdose."},
    {"q": "Gibt es Brennholz dazu?", "a": "Optional bieten wir trockenes, ofenfertiges Brennholz sauber verpackt für 10,00 € je Kiste an."},
    {"q": "Wie hoch ist die Kaution?", "a": "Die Kaution beträgt 300 € bei Übergabe in bar und wird bei ordnungsgemäßer Rückgabe sofort erstattet."},
    {"q": "Welche Zahlung gibt es?", "a": "Kreditkarte, PayPal und Barzahlung bei Übergabe / Rechnung."},
]
_PREVIOUS_PRIVACY = (
    "Für eine Buchung speichern wir Name, E-Mail, Telefon, den markierten Lieferort, Zeitraum, gewähltes Modell, Extras und die Zahlungsart.\n\n"
    "Buchungen bleiben erhalten, damit Verfügbarkeit und Nachweise stimmen. Eine Löschanfrage richtest du an {email}."
)
_PREVIOUS_TERMS = (
    "Vertragspartner ist {company}. Der Vertrag kommt zustande, wenn die Buchung eine Bestellnummer erhält.\n\n"
    "Die Sauna bleibt Eigentum von {company}. Sie ist pfleglich zu behandeln und zum vereinbarten Abreisetag bereitzuhalten."
)
_PREVIOUS_RENTAL = (
    "Eine Nacht läuft von der Anreise bis zur Abreise. Der Abreisetag ist für die nächste Buchung frei.\n\n"
    "Kostenlose Stornierung ist bis {cancel} Tage vor Mietbeginn möglich. Kaution: 300 € bei Übergabe in bar."
)
CONTENT_DEFAULTS = {
    "hero_kicker": "Amphora-Spa Berlin-Brandenburg",
    "hero_title": "Mobile Wellness auf Rädern\nFasssauna & Badefass",
    "hero_lede": "Hot Tubs & Fasssaunen direkt an deinen Wunschort geliefert oder zur flexiblen Selbstabholung in Treuenbrietzen.",
    "hero_image": "/static/uploads/fasssauna-1.jpg",
    "fleet_title": "Unsere Flotte",
    "fleet_text": "Mobiles Badefass mit Whirlpool, Fasssauna mit Vorraum oder das exklusive Kombi-Spa auf einem Anhänger.",
    "fleet_page_title": "Wähle dein mobiles Wellness-Erlebnis.",
    "fleet_page_text": "Luxuriöse Fasssaunen aus nachhaltigem Thermoholz und beheizbare Badefässer mit Massage. Berlin & Brandenburg.",
    "how_kicker": "So funktioniert's",
    "how_title": "Drei Schritte bis zu deinem privaten Spa.",
    "how_lede": "Modell wählen, Zeitraum festlegen, Lieferung an Wunschort oder kostenlose Selbstabholung.",
    "prices_title": "Faire Tagessätze & transparente Wochenendpreise.",
    "prices_text": "Wochentags ab 85 €, Wochenende (Fr–So) ab 250 €. Alle Preise sind Endpreise inklusive {vat}% MwSt. Kaution: 300 € bei Übergabe in bar.",
    "contact_title": "Kontaktiere uns.",
    "contact_text": "Fragen zu Lieferung, Modellen, Selbstabholung oder Kauf. Telefon, WhatsApp & Telegram: +49 176 2033 1535 oder +49 176 4164 4019.",
    "footer_line": "Amphora-Spa · Mobile Fasssauna & Badefass Mieten und Kaufen.",
    "impressum_note": "Angaben pflegst du in der Admin-Oberfläche unter Einstellungen. Standort & Ausstellung: Tiefenbrunnen 1, 14929 Treuenbrietzen.",
    "corporate_text": "Für Teams, Events und Feiern: schreibt uns mit Zeitraum, Personenzahl und Lieferort. Im Checkout kannst du Firma und USt-IdNr. angeben.",
    "privacy_text": "Für eine Buchung speichern wir Name, E-Mail, Telefon, den markierten Lieferort mit Koordinaten, Zeitraum, gewähltes Modell, Extras, Lieferfenster und Zahlungsart.\n\nBuchungen bleiben erhalten, damit Verfügbarkeit und Nachweise stimmen. Eine Löschanfrage richtest du an {email}.",
    "terms_text": "Vertragspartner ist {company} (Inhaber: Amphora-Spa Berlin-Brandenburg, Tiefenbrunnen 1, 14929 Treuenbrietzen). Der Vertrag kommt zustande, wenn die Buchung eine Bestellnummer erhält.\n\nEs gilt der Preis, der im letzten Schritt vor dem Absenden angezeigt wird. Enthalten ist die MwSt. von {vat}%. Kaution von 300 € wird bei Übergabe fällig.\n\nDie Sauna und das Badefass bleiben Eigentum von {company}. Sie sind pfleglich zu behandeln und zum vereinbarten Abreisetag bereitzuhalten.",
    "rental_text": "Eine Nacht läuft von der Anreise bis zur Abreise. Der Abreisetag ist für die nächste Buchung frei.\n\nKostenlose Stornierung ist bis {cancel} Tage vor Mietbeginn möglich über die Bestellseite mit Bestellnummer und E-Mail.\n\nBei Selbstabholung ist ein Auto mit Anhängerkupplung und Führerschein Klasse BE erforderlich. Bei Lieferung wird eine Pauschale von 1 bis 2 € je Kilometer berechnet. Kaution: 300 € in bar bei Übergabe.",
    "points_json": json.dumps(_POINTS, ensure_ascii=False),
    "steps_json": json.dumps(_STEPS, ensure_ascii=False),
    "faq_json": json.dumps(_FAQ, ensure_ascii=False),
}
PIN_BACKFILL = {
    "seed-max": (52.5319, 13.388),
    "seed-anna": (48.1372, 11.5755),
    "seed-jonas": (52.4667, 13.23),
}
_GEO_CACHE: dict[tuple[float, float], dict] = {}


class QuoteError(Exception):
    pass


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


def tokens_match(got: str, expected: str) -> bool:
    if not got or not expected or len(got) != len(expected):
        return False
    return hmac.compare_digest(got, expected)


def ensure_csrf() -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(32)
    return session["csrf"]


def csrf_ok() -> bool:
    return tokens_match(
        request.headers.get("X-CSRF-Token") or request.form.get("csrf_token") or "",
        session.get("csrf") or "",
    )


def format_euro(cents: int) -> str:
    cents = int(cents)
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    euros = f"{cents // 100:,}".replace(",", ".")
    rest = cents % 100
    if rest == 0:
        return f"{sign}{euros} €"
    return f"{sign}{euros},{rest:02d} €"


def money_input(cents: int) -> str:
    cents = int(cents)
    if cents % 100 == 0:
        return str(cents // 100)
    return f"{cents // 100},{cents % 100:02d}"


def parse_money(raw: str) -> int:
    text = (raw or "").strip().replace("€", "").replace(" ", "")
    if not text:
        raise ValueError("Preis fehlt.")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    try:
        value = float(text)
    except ValueError as exc:
        raise ValueError("Preis ist ungültig.") from exc
    if value < 0 or value > 100000:
        raise ValueError("Preis liegt außerhalb des erlaubten Bereichs.")
    return int(round(value * 100 + 1e-6))


def included_vat(gross_cents: int, percent: int) -> int:
    denom = 100 + percent
    return (gross_cents * percent + denom // 2) // denom


def parse_iso(value: str) -> date:
    try:
        return date.fromisoformat((value or "").strip())
    except ValueError as exc:
        raise QuoteError("Datum ist ungültig.") from exc


def nights_label(nights: int) -> str:
    return "1 Nacht" if nights == 1 else f"{nights} Nächte"


def rent_label(nights: int) -> str:
    return "1 Tag Miete" if nights == 1 else f"{nights} Tage Miete"


def format_day(value: date) -> str:
    return f"{value.day}. {MONTHS_SHORT[value.month - 1]}"


def format_range(start: date, end: date) -> str:
    nights = (end - start).days
    left = format_day(start)
    right = f"{format_day(end)} {end.year}"
    if start.year != end.year:
        left = f"{left} {start.year}"
    return f"{left} – {right} ({nights_label(nights)})"


def format_dt(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    return parsed.strftime("%d.%m.%Y %H:%M")


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "eintrag"


def unique_slug(db, table: str, slug: str, exclude_id: int | None = None) -> str:
    if table not in {"models", "extras"}:
        raise ValueError("Unbekannte Tabelle.")
    base = slug or "eintrag"
    candidate = base
    number = 2
    while True:
        row = db.execute(f"SELECT id FROM {table} WHERE slug = ?", (candidate,)).fetchone()
        if not row or (exclude_id is not None and row["id"] == exclude_id):
            return candidate
        candidate = f"{base}-{number}"
        number += 1


def load_settings(db) -> dict:
    data = dict(DEFAULT_SETTINGS)
    data.update(CONTENT_DEFAULTS)
    data.update(EXTRA_DEFAULTS)
    for row in db.execute("SELECT key, value FROM settings"):
        data[row["key"]] = row["value"]
    return data


def redact_secrets(settings: dict) -> dict:
    data = dict(settings)
    for key in SECRET_KEYS:
        data[key + "_set"] = "1" if str(data.get(key) or "").strip() else ""
        data[key] = ""
    return data


def fill_copy(text: str, settings: dict) -> str:
    return (
        str(text or "")
        .replace("{vat}", str(settings.get("vat_percent", "")))
        .replace("{cancel}", str(settings.get("cancellation_days", "")))
        .replace("{email}", str(settings.get("email", "")))
        .replace("{phone}", str(settings.get("phone", "")))
        .replace("{company}", str(settings.get("company_name", "")))
    )


def as_paragraphs(text: str) -> list[str]:
    return [part.strip() for part in str(text or "").split("\n\n") if part.strip()]


def as_html_breaks(text: str):
    return Markup("<br>".join(str(escape(line)) for line in str(text or "").split("\n")))


def json_list(raw: str, fallback: str) -> list:
    try:
        data = json.loads(raw or fallback)
    except json.JSONDecodeError:
        data = json.loads(fallback)
    return data if isinstance(data, list) else []


def present_content(settings: dict) -> dict:
    points = []
    for item in json_list(settings.get("points_json", ""), CONTENT_DEFAULTS["points_json"]):
        if not isinstance(item, dict):
            continue
        points.append(
            {
                "icon": str(item.get("icon") or "spark"),
                "title": str(item.get("title") or ""),
                "text": fill_copy(item.get("text") or "", settings),
            }
        )
    steps = []
    for index, item in enumerate(json_list(settings.get("steps_json", ""), CONTENT_DEFAULTS["steps_json"]), start=1):
        if not isinstance(item, dict):
            continue
        image = str(item.get("image") or "")
        if not safe_image_path(image):
            image = "/static/images/choose.jpg"
        steps.append(
            {
                "eyebrow": f"{index:02d}",
                "title": str(item.get("title") or ""),
                "text": fill_copy(item.get("text") or "", settings),
                "image": image,
            }
        )
    faq = []
    for item in json_list(settings.get("faq_json", ""), CONTENT_DEFAULTS["faq_json"]):
        if not isinstance(item, dict):
            continue
        question = str(item.get("q") or "").strip()
        answer = fill_copy(item.get("a") or "", settings).strip()
        if question and answer:
            faq.append({"q": question, "a": answer})
    hero_image = str(settings.get("hero_image") or "")
    if not safe_image_path(hero_image):
        hero_image = CONTENT_DEFAULTS["hero_image"]
    return {
        "hero_kicker": fill_copy(settings.get("hero_kicker", ""), settings),
        "hero_html": as_html_breaks(fill_copy(settings.get("hero_title", ""), settings)),
        "hero_lede": fill_copy(settings.get("hero_lede", ""), settings),
        "hero_image": hero_image,
        "fleet_title": fill_copy(settings.get("fleet_title", ""), settings),
        "fleet_text": fill_copy(settings.get("fleet_text", ""), settings),
        "fleet_page_title": fill_copy(settings.get("fleet_page_title", ""), settings),
        "fleet_page_text": fill_copy(settings.get("fleet_page_text", ""), settings),
        "how_kicker": fill_copy(settings.get("how_kicker", ""), settings),
        "how_title": fill_copy(settings.get("how_title", ""), settings),
        "how_lede": fill_copy(settings.get("how_lede", ""), settings),
        "prices_title": fill_copy(settings.get("prices_title", ""), settings),
        "prices_text": fill_copy(settings.get("prices_text", ""), settings),
        "contact_title": fill_copy(settings.get("contact_title", ""), settings),
        "contact_text": fill_copy(settings.get("contact_text", ""), settings),
        "footer_line": fill_copy(settings.get("footer_line", ""), settings),
        "impressum_note": fill_copy(settings.get("impressum_note", ""), settings),
        "privacy": as_paragraphs(fill_copy(settings.get("privacy_text", ""), settings)),
        "terms": as_paragraphs(fill_copy(settings.get("terms_text", ""), settings)),
        "rental": as_paragraphs(fill_copy(settings.get("rental_text", ""), settings)),
        "corporate": fill_copy(settings.get("corporate_text", ""), settings),
        "meta_description": fill_copy(settings.get("meta_description") or settings.get("hero_lede", ""), settings),
        "points": points,
        "steps": steps,
        "faq": faq,
    }


def maps_url(lat, lng, address: str = "") -> str:
    if lat is not None and lng is not None and lat != "" and lng != "":
        return f"https://www.google.com/maps?q={float(lat):.6f},{float(lng):.6f}"
    if address:
        return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(address)
    return ""


def osm_url(lat, lng, address: str = "") -> str:
    if lat is not None and lng is not None and lat != "" and lng != "":
        lat_f = float(lat)
        lng_f = float(lng)
        return f"https://www.openstreetmap.org/?mlat={lat_f:.6f}&mlon={lng_f:.6f}#map=16/{lat_f:.6f}/{lng_f:.6f}"
    if address:
        return "https://www.openstreetmap.org/search?query=" + urllib.parse.quote(address)
    return ""


def backfill_pins(conn) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(bookings)")}
    if "lat" not in columns:
        return
    for token, (lat, lng) in PIN_BACKFILL.items():
        conn.execute(
            "UPDATE bookings SET lat = ?, lng = ? WHERE client_token = ? AND lat IS NULL",
            (lat, lng, token),
        )


def ensure_settings(conn) -> None:
    for key, value in {**DEFAULT_SETTINGS, **CONTENT_DEFAULTS, **EXTRA_DEFAULTS}.items():
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO NOTHING",
            (key, value),
        )


def upgrade_shipped_copy(conn) -> None:
    replacements = {
        "privacy_text": (_PREVIOUS_PRIVACY, CONTENT_DEFAULTS["privacy_text"]),
        "terms_text": (_PREVIOUS_TERMS, CONTENT_DEFAULTS["terms_text"]),
        "rental_text": (_PREVIOUS_RENTAL, CONTENT_DEFAULTS["rental_text"]),
        "faq_json": (
            json.dumps(_PREVIOUS_FAQ, ensure_ascii=False),
            CONTENT_DEFAULTS["faq_json"],
        ),
    }
    for key, (previous, current) in replacements.items():
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row and row["value"] == previous:
            conn.execute("UPDATE settings SET value = ? WHERE key = ?", (current, key))


MODEL_COPY = {
    "model-s": (
        "Holzofen\nTürfenster\nGrundausstattung Brennholz\nAufbau und Abholung",
        "Handtücher\nZusätzliches Kaminholz\nEndreinigung",
    ),
    "model-x": (
        "Holzofen\nHalbmondfenster\nGrundausstattung Brennholz\nAufbau und Abholung",
        "Handtücher\nZusätzliches Kaminholz\nBio-Aufguss\nEndreinigung",
    ),
    "model-xl": (
        "Elektro- oder Holzofen\nVorraum\nPanorama-Fenster\nAufbau und Abholung",
        "Premium-Handtücher\nZusätzliches Kaminholz\nBio-Aufguss\nVIP-Endreinigung",
    ),
    "model-panorama": (
        "Holzofen\nVollglasfront\nGrundausstattung Brennholz\nAufbau und Abholung",
        "Handtücher\nZusätzliches Kaminholz\nEndreinigung",
    ),
}


def backfill_model_copy(conn) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(models)")}
    if "included_text" not in columns:
        return
    for slug, (included, excluded) in MODEL_COPY.items():
        conn.execute(
            "UPDATE models SET included_text = ? WHERE slug = ? AND included_text = ''",
            (included, slug),
        )
        conn.execute(
            "UPDATE models SET excluded_text = ? WHERE slug = ? AND excluded_text = ''",
            (excluded, slug),
        )


def int_setting(settings: dict, key: str, fallback: int) -> int:
    try:
        return int(settings.get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def split_csv(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def contains_city(query: str, city: str) -> bool:
    return re.search(rf"(?<![\w]){re.escape(city)}(?![\w])", query, flags=re.IGNORECASE) is not None


def lookup_zone(db, query: str):
    zones = db.execute(
        "SELECT * FROM zones WHERE active = 1 ORDER BY sort_order, id"
    ).fetchall()
    match = re.search(r"\b(\d{5})\b", query or "")
    plz = match.group(1) if match else ""
    if plz:
        best = None
        best_len = -1
        star = None
        for zone in zones:
            for prefix in split_csv(zone["prefixes"]):
                if prefix == "*":
                    star = zone
                    continue
                if plz.startswith(prefix) and len(prefix) > best_len:
                    best = zone
                    best_len = len(prefix)
        if best:
            return best, plz
        if star:
            return star, plz
    best = None
    best_len = -1
    low = (query or "").lower()
    for zone in zones:
        for city in split_csv(zone["cities"]):
            if city != "*" and contains_city(low, city) and len(city) > best_len:
                best = zone
                best_len = len(city)
    return best, plz


def zone_badge(zone) -> str:
    raw = (zone["name"] or "").strip()
    title = ("LIEFER" + raw.upper()) if raw.lower().startswith("zone") else raw.upper()
    if int(zone["price_cents"]) == 0:
        return f"{title} (KOSTENLOS)"
    return f"{title} ({format_euro(int(zone['price_cents']))})"


def parse_address(address: str) -> tuple[str, str, str]:
    match = re.search(r"\b(\d{5})\b", address or "")
    plz = match.group(1) if match else ""
    city = ""
    if plz:
        city = re.split(r",", address.split(plz, 1)[1])[0].strip()
    if not city:
        parts = [part.strip() for part in (address or "").split(",") if part.strip()]
        if parts:
            city = parts[-1]
            if city.lower() in {"deutschland", "germany", "de"} and len(parts) > 1:
                city = parts[-2]
    if plz and plz in city:
        city = city.replace(plz, "").strip(" ,")
    return plz, city[:80], "Deutschland"


def present_model(row) -> dict:
    data = dict(row)
    data["features"] = json.loads(row["features_json"])
    data["specs"] = json.loads(row["specs_json"])
    data["highlights"] = json.loads(row["highlights_json"])
    data["images"] = json.loads(row["images_json"])
    data["persons"] = f"{row['capacity_min']}-{row['capacity_max']}"
    return data


def present_extra(row) -> dict:
    return dict(row)


def model_units(db, model_id: int) -> int:
    row = db.execute("SELECT units FROM models WHERE id = ?", (model_id,)).fetchone()
    if not row:
        return 1
    try:
        units = int(row["units"])
    except (TypeError, ValueError):
        return 1
    return units if units >= 1 else 1


def range_conflicts(db, model_id: int, start: date, end: date, exclude_id: int | None = None) -> bool:
    blocked = db.execute(
        """
        SELECT 1 FROM blocks
        WHERE model_id = ? AND start_date < ? AND end_date > ?
        """,
        (model_id, end.isoformat(), start.isoformat()),
    ).fetchone()
    if blocked:
        return True
    params: list = [model_id, end.isoformat(), start.isoformat()]
    sql = """
        SELECT COUNT(*) AS c FROM bookings
        WHERE model_id = ? AND status != 'cancelled'
          AND start_date < ? AND end_date > ?
    """
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    count = db.execute(sql, params).fetchone()["c"]
    return count >= model_units(db, model_id)


def _walk_nights(row, start: date, end: date):
    current = max(date.fromisoformat(row["start_date"]), start)
    stop = min(date.fromisoformat(row["end_date"]), end)
    while current < stop:
        yield current
        current += timedelta(days=1)


def busy_nights(db, model_id: int, start: date, end: date) -> list[str]:
    units = model_units(db, model_id)
    rows = db.execute(
        """
        SELECT start_date, end_date FROM bookings
        WHERE model_id = ? AND status != 'cancelled'
          AND start_date < ? AND end_date > ?
        """,
        (model_id, end.isoformat(), start.isoformat()),
    ).fetchall()
    blocks = db.execute(
        """
        SELECT start_date, end_date FROM blocks
        WHERE model_id = ? AND start_date < ? AND end_date > ?
        """,
        (model_id, end.isoformat(), start.isoformat()),
    ).fetchall()
    counts: dict[date, int] = {}
    for row in rows:
        for current in _walk_nights(row, start, end):
            counts[current] = counts.get(current, 0) + 1
    blocked = set()
    for row in blocks:
        blocked.update(_walk_nights(row, start, end))
    taken = []
    day = start
    while day < end:
        if day in blocked or counts.get(day, 0) >= units:
            taken.append(day.isoformat())
        day += timedelta(days=1)
    return taken


def _resolve_extras(db, raw) -> list[dict]:
    if not raw:
        return []
    if not isinstance(raw, list):
        raise QuoteError("Zusätze sind ungültig.")
    resolved = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            raise QuoteError("Zusätze sind ungültig.")
        try:
            extra_id = int(item.get("id"))
            qty = int(item.get("qty") or 0)
        except (TypeError, ValueError) as exc:
            raise QuoteError("Zusätze sind ungültig.") from exc
        if extra_id in seen:
            raise QuoteError("Ein Zusatz wurde doppelt angegeben.")
        seen.add(extra_id)
        extra = db.execute("SELECT * FROM extras WHERE id = ? AND active = 1", (extra_id,)).fetchone()
        if not extra:
            if qty > 0:
                raise QuoteError("Ein Zusatz ist nicht mehr verfügbar.")
            continue
        if extra["kind"] == "service":
            qty = 1 if qty >= 1 else 0
        if qty <= 0:
            continue
        if qty > 10:
            raise QuoteError("Höchstens 10 Stück pro Zusatz.")
        line = int(extra["price_cents"]) * qty
        resolved.append(
            {
                "id": extra["id"],
                "name": extra["name"],
                "kind": extra["kind"],
                "qty": qty,
                "unit_cents": int(extra["price_cents"]),
                "line_cents": line,
                "line": format_euro(line),
            }
        )
    return resolved


def build_quote(db, *, model_id: int, start: date, end: date, address: str, extras, check_availability=True, exclude_booking_id=None, allow_past=False) -> dict:
    try:
        model_id = int(model_id)
    except (TypeError, ValueError) as exc:
        raise QuoteError("Modell ist ungültig.") from exc
    model = db.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
    if not model or not model["active"]:
        raise QuoteError("Dieses Modell ist nicht buchbar.")
    if end <= start:
        raise QuoteError("Die Abreise muss nach der Anreise liegen.")
    if not allow_past and start < date.today():
        raise QuoteError("Die Anreise kann nicht in der Vergangenheit liegen.")
    nights = (end - start).days
    settings = load_settings(db)
    minimum = int_setting(settings, "min_nights", 1)
    maximum = int_setting(settings, "max_nights", 21)
    if nights < minimum:
        raise QuoteError("Mindestens 1 Nacht." if minimum == 1 else f"Mindestens {minimum} Nächte.")
    if nights > maximum:
        raise QuoteError(f"Höchstens {maximum} Nächte am Stück.")
    if check_availability and range_conflicts(db, model["id"], start, end, exclude_booking_id):
        raise QuoteError("In diesem Zeitraum ist die Sauna bereits belegt.")
    zone = None
    delivery = None
    plz = ""
    city = ""
    if (address or "").strip():
        zone, plz = lookup_zone(db, address)
        parsed_plz, city, _country = parse_address(address)
        plz = plz or parsed_plz
        if zone is None:
            raise QuoteError("Diese Adresse liegt außerhalb unseres Liefergebiets.")
        delivery = int(zone["price_cents"])
    chosen = _resolve_extras(db, extras)
    rent = int(model["price_cents"]) * nights
    extras_total = sum(item["line_cents"] for item in chosen)
    percent = int_setting(settings, "vat_percent", 19)
    deposit = max(0, int_setting(settings, "deposit_cents", 0))
    gross = None if delivery is None else rent + extras_total + delivery + deposit
    vat = None if gross is None else included_vat(gross, percent)
    delivery_text = None
    if delivery is None:
        delivery_label = "Lieferung (ca.)"
    elif delivery == 0:
        delivery_text = "kostenlos"
        delivery_label = f"Lieferung ({zone['name']})"
    else:
        delivery_text = format_euro(delivery)
        delivery_label = f"Lieferung ({zone['name']})"
    return {
        "model_id": model["id"],
        "model_name": model["name"],
        "model_slug": model["slug"],
        "unit": format_euro(model["price_cents"]),
        "nights": nights,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "range_label": format_range(start, end),
        "rent_cents": rent,
        "rent_label": rent_label(nights),
        "rent": format_euro(rent),
        "delivery_cents": delivery,
        "delivery": delivery_text,
        "delivery_label": delivery_label,
        "extras": chosen,
        "extras_cents": extras_total,
        "deposit_cents": deposit,
        "deposit": None if not deposit else format_euro(deposit),
        "voucher_cents": 0,
        "voucher_code": "",
        "voucher": None,
        "gross_cents": gross,
        "gross": None if gross is None else format_euro(gross),
        "vat_cents": vat,
        "vat": None if vat is None else format_euro(vat),
        "vat_percent": percent,
        "vat_text": f"inkl. MwSt. ({percent}%)",
        "needs_address": delivery is None,
        "postal_code": plz,
        "city": city,
        "country": "Deutschland",
        "zone": None
        if zone is None
        else {
            "id": zone["id"],
            "name": zone["name"],
            "badge": zone_badge(zone),
            "free": int(zone["price_cents"]) == 0,
            "price_cents": int(zone["price_cents"]),
        },
    }


def _coord(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise QuoteError("Die Markierung ist ungültig.") from exc


def reverse_geocode(lat: float, lng: float) -> dict:
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise QuoteError("Die Markierung liegt außerhalb der Karte.")
    key = (round(lat, 5), round(lng, 5))
    cached = _GEO_CACHE.get(key)
    if cached:
        return cached
    query = urllib.parse.urlencode(
        {
            "lat": f"{lat:.6f}",
            "lon": f"{lng:.6f}",
            "format": "jsonv2",
            "addressdetails": 1,
        }
    )
    req = urllib.request.Request(
        "https://nominatim.openstreetmap.org/reverse?" + query,
        headers={
            "User-Agent": "SaunacoreLocal/1.0 (booking map)",
            "Accept-Language": "de",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise QuoteError("Der Ort konnte nicht ermittelt werden. Setze die Markierung erneut.") from exc
    address = payload.get("address") or {}
    if not isinstance(address, dict) or payload.get("error"):
        raise QuoteError("Für diese Markierung gibt es keine Adresse.")
    postcode = str(address.get("postcode") or "")
    city = str(
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or address.get("county")
        or ""
    )
    road = str(address.get("road") or address.get("pedestrian") or address.get("footway") or "")
    number = str(address.get("house_number") or "")
    street = f"{road} {number}".strip()
    locality = f"{postcode} {city}".strip()
    text = ", ".join(part for part in (street, locality) if part) or str(payload.get("display_name") or "")
    text = re.sub(r"\s+", " ", text).strip()[:200]
    if len(text) < 3:
        raise QuoteError("Für diese Markierung gibt es keine Adresse.")
    info = {"address": text, "postal_code": postcode[:12], "city": city[:80]}
    if len(_GEO_CACHE) > 300:
        _GEO_CACHE.clear()
    _GEO_CACHE[key] = info
    return info


def resolve_location(data: dict) -> tuple[str, float | None, float | None]:
    lat = _coord(data.get("lat"))
    lng = _coord(data.get("lng"))
    if (lat is None) != (lng is None):
        raise QuoteError("Die Markierung ist unvollständig.")
    if lat is not None and lng is not None:
        info = reverse_geocode(lat, lng)
        return info["address"], lat, lng
    address = str(data.get("address") or "").strip()
    if len(address) > 200:
        raise QuoteError("Die Adresse ist zu lang.")
    return address, None, None


def _apply_voucher(db, quote: dict, raw_code) -> dict:
    code = str(raw_code or "").strip().upper()
    if not code:
        return quote
    if len(code) > 40 or not re.fullmatch(r"[A-Z0-9_-]+", code):
        raise QuoteError("Der Gutscheincode ist ungültig.")
    row = db.execute("SELECT * FROM vouchers WHERE code = ?", (code,)).fetchone()
    if not row or not int(row["active"]):
        raise QuoteError("Der Gutscheincode ist ungültig.")
    if int(row["used"]) >= int(row["max_uses"]):
        raise QuoteError("Der Gutscheincode ist aufgebraucht.")
    quote["voucher_code"] = code
    if quote["gross_cents"] is None:
        return quote
    base = quote["rent_cents"] + quote["extras_cents"] + int(quote["delivery_cents"] or 0)
    discount = min(int(row["cents"]), max(0, base))
    deposit = int(quote["deposit_cents"] or 0)
    gross = base + deposit - discount
    quote["voucher_cents"] = discount
    quote["voucher"] = format_euro(-discount) if discount else None
    quote["gross_cents"] = gross
    quote["gross"] = format_euro(gross)
    vat = included_vat(gross, quote["vat_percent"])
    quote["vat_cents"] = vat
    quote["vat"] = format_euro(vat)
    return quote


WINDOWS = {"vormittag", "nachmittag", "flexibel"}


def _truthy(value) -> bool:
    return value in (True, 1) or str(value).lower() in {"1", "true", "yes", "on"}


def _falsey(value) -> bool:
    return value in (False, 0) or str(value).lower() in {"0", "false", "no", "off"}


def trip_fields(data: dict) -> tuple[str, int, str, str]:
    window = str(data.get("arrival_window") or "").strip().lower()
    if window and window not in WINDOWS:
        raise QuoteError("Bitte wähle ein Lieferfenster.")
    present = "access_ok" in data or "access_confirmed" in data
    raw = data.get("access_ok", data.get("access_confirmed"))
    if present and _falsey(raw):
        raise QuoteError("Bitte bestätige Zufahrt, Stellfläche und Übergabe.")
    access = 1 if present and _truthy(raw) else 0
    company = str(data.get("company") or "").strip()[:120]
    company_vat = re.sub(r"\s+", "", str(data.get("company_vat") or "").strip())[:20]
    if company_vat and not re.fullmatch(r"[A-Za-z0-9]{2,20}", company_vat):
        raise QuoteError("Die USt-IdNr. ist ungültig.")
    return window, access, company, company_vat


def guest_can_cancel(row, settings: dict, today: date | None = None) -> bool:
    today = today or date.today()
    if row["status"] in {"cancelled", "completed", "active"}:
        return False
    start = date.fromisoformat(row["start_date"])
    days = int_setting(settings, "cancellation_days", 7)
    return today <= start - timedelta(days=days)


def quote_from_payload(db, data: dict, allow_past=False) -> dict:
    if not isinstance(data, dict):
        raise QuoteError("Anfrage ist ungültig.")
    start = parse_iso(str(data.get("start") or ""))
    end = parse_iso(str(data.get("end") or ""))
    delivery_type = "pickup" if data.get("delivery_type") == "pickup" else "delivery"
    if delivery_type == "pickup":
        address = "Tiefenbrunnen 1, 14929 Treuenbrietzen (Selbstabholung)"
        lat = 52.0911
        lng = 12.8711
    else:
        address, lat, lng = resolve_location(data)
    result = build_quote(
        db,
        model_id=data.get("model_id"),
        start=start,
        end=end,
        address=address,
        extras=data.get("extras") or [],
        allow_past=allow_past,
    )
    if delivery_type == "pickup":
        result["delivery_cents"] = 0
        result["delivery"] = "kostenlose Selbstabholung"
        result["zone"] = {"name": "Selbstabholung", "price_cents": 0, "badge": "Abholstation Treuenbrietzen"}
        result["needs_address"] = False
        base = result["rent_cents"] + result["extras_cents"]
        deposit = int(result["deposit_cents"] or 0)
        gross = base + deposit
        result["gross_cents"] = gross
        result["gross"] = format_euro(gross)
        vat = included_vat(gross, result["vat_percent"])
        result["vat_cents"] = vat
        result["vat"] = format_euro(vat)
    result["address"] = address
    result["lat"] = lat
    result["lng"] = lng
    result["delivery_type"] = delivery_type
    return _apply_voucher(db, result, data.get("voucher_code"))


def _customer(data: dict) -> tuple[str, str, str, str, str]:
    first = str(data.get("first_name") or "").strip()
    last = str(data.get("last_name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    phone = str(data.get("phone") or "").strip()
    notes = str(data.get("notes") or "").strip()
    if not (1 <= len(first) <= 60 and 1 <= len(last) <= 60):
        raise QuoteError("Bitte gib Vor- und Nachname an.")
    if not EMAIL_RE.match(email) or len(email) > 120:
        raise QuoteError("Bitte gib eine gültige E-Mail an.")
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 6 or len(phone) > 40:
        raise QuoteError("Bitte gib eine gültige Telefonnummer an.")
    if len(notes) > 1000:
        raise QuoteError("Die Anmerkung ist zu lang.")
    return first, last, email, phone, notes


def _payment(data: dict) -> tuple[str, str, str, str, str]:
    method = str(data.get("payment_method") or "")
    if method not in PAYMENTS:
        raise QuoteError("Bitte wähle eine Zahlungsart.")
    brand = ""
    last4 = ""
    exp = ""
    if method == "card":
        last4 = re.sub(r"\D", "", str(data.get("card_last4") or ""))
        brand = str(data.get("card_brand") or "").strip()[:20] or "Karte"
        exp = str(data.get("card_exp") or "").strip()
        if len(last4) != 4 or not re.fullmatch(r"(0[1-9]|1[0-2])/\d{2}", exp):
            raise QuoteError("Kartendaten sind unvollständig.")
        month, year = exp.split("/")
        if (2000 + int(year), int(month)) < (date.today().year, date.today().month):
            raise QuoteError("Die Karte ist abgelaufen.")
    return method, brand, last4, exp, PAYMENTS[method]


def _new_number(db) -> str:
    year = date.today().year
    for _ in range(30):
        number = f"SC-{year}-{secrets.randbelow(9000) + 1000}"
        if not db.execute("SELECT 1 FROM bookings WHERE number = ?", (number,)).fetchone():
            return number
    return f"SC-{year}-{secrets.token_hex(3).upper()}"


def create_booking(db, data: dict, *, allow_past=False, status: str | None = None, payment_status: str | None = None):
    if not isinstance(data, dict):
        raise QuoteError("Anfrage ist ungültig.")
    token = str(data.get("client_token") or "").strip()[:80]
    if token:
        existing = db.execute("SELECT * FROM bookings WHERE client_token = ?", (token,)).fetchone()
        if existing:
            return existing
    first, last, email, phone, notes = _customer(data)
    if status is not None and status not in STATUSES:
        raise QuoteError("Status ist ungültig.")
    settings = load_settings(db)
    secret = (settings.get("stripe_secret") or "").strip()
    method = str(data.get("payment_method") or "")
    if method not in PAYMENTS:
        raise QuoteError("Bitte wähle eine Zahlungsart.")
    defer_card = bool(secret) and method == "card" and status is None and payment_status is None and not str(data.get("card_last4") or "").strip()
    if defer_card:
        brand, last4, exp = "", "", ""
    else:
        method, brand, last4, exp, _label = _payment(data)
    window, access, company, company_vat = trip_fields(data)
    checkout_url = ""
    db.execute("BEGIN IMMEDIATE")
    try:
        if token:
            existing = db.execute("SELECT * FROM bookings WHERE client_token = ?", (token,)).fetchone()
            if existing:
                db.execute("COMMIT")
                return existing
        quote = quote_from_payload(db, data, allow_past=allow_past)
        address = str(quote.get("address") or "").strip()
        if len(address) < 5 or quote["needs_address"] or quote["gross_cents"] is None:
            raise QuoteError("Bitte setze die Markierung im Liefergebiet.")
        use_stripe = bool(secret) and method in {"card", "paypal"} and status is None and payment_status is None and int(quote["gross_cents"]) > 0
        if method == "card" and not last4 and not use_stripe:
            raise QuoteError("Kartendaten sind unvollständig.")
        if use_stripe:
            pay_state = "unpaid"
            book_status = "new"
        elif method == "invoice":
            pay_state = payment_status or "unpaid"
            book_status = status or "new"
        else:
            pay_state = payment_status or "simulated"
            book_status = status or "confirmed"
        if pay_state not in {"simulated", "unpaid", "paid"}:
            raise QuoteError("Zahlungsstatus ist ungültig.")
        voucher_code = quote.get("voucher_code") or ""
        voucher_cents = int(quote.get("voucher_cents") or 0)
        if voucher_code and voucher_cents > 0:
            changed = db.execute(
                "UPDATE vouchers SET used = used + 1 WHERE code = ? AND active = 1 AND used < max_uses",
                (voucher_code,),
            ).rowcount
            if changed != 1:
                raise QuoteError("Der Gutscheincode ist aufgebraucht.")
        number = _new_number(db)
        public_token = secrets.token_urlsafe(18)
        created = now()
        delivery_type = "pickup" if data.get("delivery_type") == "pickup" else "delivery"
        db.execute(
            """
            INSERT INTO bookings (
                number, public_token, client_token, model_id, model_name, model_slug,
                start_date, end_date, nights, address, postal_code, city, country,
                zone_name, delivery_cents, rent_cents, extras_cents, gross_cents, vat_cents,
                extras_json, first_name, last_name, email, phone, notes,
                payment_method, payment_status, card_brand, card_last4, card_exp,
                status, admin_note, created_at, lat, lng,
                deposit_cents, voucher_cents, voucher_code, arrival_window,
                company, company_vat, access_ok, stripe_session, delivery_type
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                number,
                public_token,
                token or None,
                quote["model_id"],
                quote["model_name"],
                quote["model_slug"],
                quote["start"],
                quote["end"],
                quote["nights"],
                address,
                quote["postal_code"],
                quote["city"],
                quote["country"],
                quote["zone"]["name"],
                quote["delivery_cents"],
                quote["rent_cents"],
                quote["extras_cents"],
                quote["gross_cents"],
                quote["vat_cents"],
                json.dumps(quote["extras"], ensure_ascii=False),
                first,
                last,
                email,
                phone,
                notes,
                method,
                pay_state,
                brand,
                last4,
                exp,
                book_status,
                "",
                created,
                quote.get("lat"),
                quote.get("lng"),
                int(quote.get("deposit_cents") or 0),
                voucher_cents,
                voucher_code,
                window,
                company,
                company_vat,
                access,
                "",
                delivery_type,
            ),
        )
        booking_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        db.execute(
            "INSERT INTO booking_events (booking_id, message, created_at) VALUES (?,?,?)",
            (booking_id, "Buchung eingegangen", created),
        )
        if use_stripe:
            from flask import url_for

            from saunacore.stripe_pay import create_checkout

            success = url_for("public.thanks", number=number, t=public_token, _external=True)
            success += "&session_id={CHECKOUT_SESSION_ID}"
            cancel = url_for("public.booking", slug=quote["model_slug"], _external=True)
            draft = {
                "number": number,
                "public_token": public_token,
                "email": email,
                "model_name": quote["model_name"],
                "gross_cents": quote["gross_cents"],
                "payment_method": method,
            }
            session_id, checkout_url = create_checkout(settings, draft, success, cancel)
            db.execute("UPDATE bookings SET stripe_session = ? WHERE id = ?", (session_id, booking_id))
            db.execute(
                "INSERT INTO booking_events (booking_id, message, created_at) VALUES (?,?,?)",
                (booking_id, "Weiterleitung zur Zahlung", created),
            )
        db.execute("COMMIT")
    except sqlite3.IntegrityError:
        db.execute("ROLLBACK")
        if token:
            existing = db.execute("SELECT * FROM bookings WHERE client_token = ?", (token,)).fetchone()
            if existing:
                return existing
        raise QuoteError("Die Buchung konnte nicht gespeichert werden. Bitte erneut versuchen.")
    except Exception:
        db.execute("ROLLBACK")
        raise
    row = db.execute("SELECT * FROM bookings WHERE number = ?", (number,)).fetchone()
    try:
        from saunacore.mailer import notify_booking

        notify_booking(db, row)
    except Exception:
        pass
    if checkout_url:
        payload = {key: row[key] for key in row.keys()}
        payload["checkout_url"] = checkout_url
        return payload
    return row


def set_status(db, booking_id: int, new_status: str):
    if new_status not in STATUSES:
        raise QuoteError("Status ist ungültig.")
    row = db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not row:
        raise QuoteError("Buchung nicht gefunden.")
    if row["status"] == new_status:
        return row
    db.execute("BEGIN IMMEDIATE")
    try:
        if new_status != "cancelled":
            if range_conflicts(
                db,
                row["model_id"],
                date.fromisoformat(row["start_date"]),
                date.fromisoformat(row["end_date"]),
                exclude_id=row["id"],
            ):
                raise QuoteError("Der Zeitraum ist inzwischen belegt.")
        db.execute("UPDATE bookings SET status = ? WHERE id = ?", (new_status, booking_id))
        db.execute(
            "INSERT INTO booking_events (booking_id, message, created_at) VALUES (?,?,?)",
            (booking_id, f"Status: {STATUS_LABELS[new_status]}", now()),
        )
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
    return db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()


def demo_login_hint(db) -> str:
    row = db.execute("SELECT password_hash FROM admins WHERE email = ?", (DEMO_EMAIL,)).fetchone()
    if row and verify_password(DEMO_PASSWORD, row["password_hash"]):
        return f"{DEMO_EMAIL} / {DEMO_PASSWORD}"
    return ""


def save_image(file_storage) -> str:
    data = file_storage.read()
    if not data:
        raise ValueError("Leere Datei.")
    if len(data) > 5 * 1024 * 1024:
        raise ValueError("Bild ist größer als 5 MB.")
    if data.startswith(b"\xff\xd8\xff"):
        ext = ".jpg"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        ext = ".png"
    elif len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        ext = ".webp"
    else:
        raise ValueError("Nur JPG, PNG oder WebP.")
    folder = Path(current_app.static_folder) / "uploads"
    name = secrets.token_hex(8) + ext
    try:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(data)
    except OSError:
        tmp_folder = Path("/tmp/uploads")
        tmp_folder.mkdir(parents=True, exist_ok=True)
        (tmp_folder / name).write_bytes(data)
    return f"/static/uploads/{name}"


def safe_image_path(path: str) -> bool:
    p = str(path or "").strip()
    return (
        p.startswith("/static/images/")
        or p.startswith("/static/uploads/")
        or p.startswith("http://")
        or p.startswith("https://")
        or (p.startswith("/static/") and any(p.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".svg")))
    )


def seed_demo(conn) -> None:
    for key, value in DEFAULT_SETTINGS.items():
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO NOTHING",
            (key, value),
        )
    conn.execute(
        "INSERT INTO admins (email, name, password_hash) VALUES (?, ?, ?)",
        (DEMO_EMAIL, "Saunacore Admin", hash_password(DEMO_PASSWORD)),
    )
    zones = [
        ("Zone A", "10,12,13,14", "berlin", 0, "Berlin, kostenlos", 1),
        (
            "Zone B",
            "144,145,146,147,149,15,16,17,18,19,01,02,03,04,06,07,08,09,39",
            "potsdam,leipzig,dresden,hamburg,hannover,magdeburg",
            5000,
            "Umland und ausgewählte Städte, 50 €",
            2,
        ),
        (
            "Zone C",
            "*",
            "muenchen,münchen,munich,koeln,köln,frankfurt,stuttgart,duesseldorf,düsseldorf,nuernberg,nürnberg,bremen",
            9000,
            "Übriges Deutschland mit fünfstelliger PLZ, 90 €",
            3,
        ),
    ]
    for name, prefixes, cities, price, note, sort in zones:
        conn.execute(
            """
            INSERT INTO zones (name, prefixes, cities, price_cents, note, active, sort_order)
            VALUES (?, ?, ?, ?, ?, 1, ?)
            """,
            (name, prefixes, cities, price, note, sort),
        )
    models = [
        {
            "slug": "badefass",
            "name": "Amphora-Spa Badefass",
            "subtitle": "Mobiles Badefass Hot Tub mit Hydro- & Airbubble-Massage",
            "badge": "Bestseller Wellness",
            "price_cents": 8500,
            "capacity_min": 2,
            "capacity_max": 6,
            "size": "mittel",
            "features": [
                {"icon": "spark", "label": "Hydro & Air Massage"},
                {"icon": "flame", "label": "Außenofen Holz"},
                {"icon": "users", "label": "Bis zu 6 Pers."},
                {"icon": "leaf", "label": "LED Beleuchtung"},
            ],
            "specs": [
                {"icon": "users", "label": "Kapazität", "value": "Bis zu 6 Personen"},
                {"icon": "spark", "label": "Massagesysteme", "value": "Hydro- & Airbubble-Massage"},
                {"icon": "flame", "label": "Heizung", "value": "Außenstehender Holzofen auf Anhänger"},
                {"icon": "leaf", "label": "Licht", "value": "LED Innen- & Außenbeleuchtung"},
                {"icon": "truck", "label": "Lieferung", "value": "1 € / km oder Selbstabholung"},
                {"icon": "spark", "label": "Kaution", "value": "300 € bar bei Übergabe"},
            ],
            "summary": "Tauche ein in eine Welt voller Erholung und entspanne in einem heißen Bad unter freiem Himmel zusammen mit Partner, Freunden oder der Familie. Mit dem mobilen Amphora-Spa Badefass holst du dir dein Wellnesserlebnis direkt in den Garten.",
            "story_title": "Heißes Bad unter freiem Himmel.",
            "story": "Unser mobiles Amphora-Spa Badefass bietet maximalen Komfort für ca. 6 Personen dank des außenstehenden Holzofens auf dem Anhänger. Ausgestattet mit kraftvollen Hydro- und Airbubble-Massagedüsen sowie stimmungsvoller LED-Atmosphärenbeleuchtung. Wochentags 85 €, Feiertage 95 €, Wochenende (Fr–So) 250 €. Alles was du brauchst, ist ein Wasseranschluss, Gartenschlauch und Brennholz.",
            "highlights": [
                "Außenstehender Holzofen – maximaler Sitzkomfort für 6 Personen",
                "Hydro-Massage & Airbubble-Massage für pure Tiefenentspannung",
                "LED-Atmosphären Außenbeleuchtung & LED Innenbeleuchtung mit Farbwechsel",
                "Mietvertrag & gründliche Einweisung inklusive",
                "Lieferung (1 €/km) oder kostenlose Selbstabholung mit PKW-Führerschein BE",
            ],
            "images": [f"/static/uploads/badefass-{i}.jpg" for i in range(1, 17)],
            "sort_order": 1,
        },
        {
            "slug": "kombi-sauna-badefass",
            "name": "Amphora-Spa Kombi",
            "subtitle": "Fasssauna & Badefass Hot Tub auf Tandem-Anhänger",
            "badge": "Das ultimative Spa",
            "price_cents": 10000,
            "capacity_min": 4,
            "capacity_max": 10,
            "size": "gross",
            "features": [
                {"icon": "users", "label": "Sauna 4 + Fass 6"},
                {"icon": "flame", "label": "Holzofen & Hot Tub"},
                {"icon": "leaf", "label": "Premium Thermoholz"},
                {"icon": "spark", "label": "Licht & Massage"},
            ],
            "specs": [
                {"icon": "users", "label": "Kapazität", "value": "Sauna bis 4 Pers., Badefass bis 6 Pers."},
                {"icon": "leaf", "label": "Material", "value": "Hochwertiges Thermoholz"},
                {"icon": "flame", "label": "Heiztechnik", "value": "Holzofen für Sauna und Badefass"},
                {"icon": "spark", "label": "Ausstattung", "value": "Stromanschluss, Licht und Whirlpool-Düsen"},
                {"icon": "truck", "label": "Lieferung", "value": "2 € je Kilometer oder Selbstabholung"},
                {"icon": "spark", "label": "Kaution", "value": "300 € bei Übergabe in bar"},
            ],
            "summary": "Hochwertiges Saunafass aus nachhaltigem Thermoholz kombiniert mit einem Hot Tub Badefass auf einem gemeinsamen mobilen Tandem-Anhänger. Das vollendete Spa-Erlebnis für Partys, Feiern und Familie.",
            "story_title": "Saunieren & Baden in perfekter Harmonie.",
            "story": "Der Amphora-Spa Kombi-Anhänger vereint eine vollwertige Fasssauna mit einem beheizbaren Hot Tub Badefass. Die Sauna bietet bis zu 4 Personen Platz für wohltuende Aufgüsse, während im Badefass bis zu 6 Personen im heißen Wasser entspannen. Wochentags 120 €, Feiertage 150 €, Wochenende (Fr–So) 320 €. Unvergessliche Wellness direkt bei dir zu Hause.",
            "highlights": [
                "Kombinierte Fasssauna (4 Pers.) und Hot Tub Badefass (6 Pers.) auf einem Anhänger",
                "Hochwertiges Thermoholz für optimale Wärmedämmung und angenehmen Duft",
                "Schwitzraum mit sicherem Holzofen und Glas-Tür",
                "Whirlpool-Funktion, Innenbeleuchtung und Thermo-Abdeckung",
                "Lieferung (2 €/km) oder Selbstabholung mit Führerschein BE",
            ],
            "images": [f"/static/uploads/kombi-{i}.jpg" for i in range(1, 17)],
            "sort_order": 2,
        },
        {
            "slug": "fasssauna-panorama",
            "name": "Amphora-Spa Panoramasauna",
            "subtitle": "Mobile Fasssauna mit Relax-Vorraum auf Anhänger",
            "badge": "Panorama & Vorraum",
            "price_cents": 9000,
            "capacity_min": 2,
            "capacity_max": 6,
            "size": "mittel",
            "features": [
                {"icon": "users", "label": "Bis zu 6 Pers."},
                {"icon": "window", "label": "Panoramafenster"},
                {"icon": "door", "label": "Separater Vorraum"},
                {"icon": "flame", "label": "Harvia Holzofen"},
            ],
            "specs": [
                {"icon": "users", "label": "Kapazität", "value": "Bis zu 6 Personen"},
                {"icon": "door", "label": "Räume", "value": "Schwitzraum & separater Vorraum (Relaxraum)"},
                {"icon": "window", "label": "Aussicht", "value": "Großes Panorama-Halbmondfenster"},
                {"icon": "leaf", "label": "Material", "value": "Nachhaltiges Thermoholz"},
                {"icon": "truck", "label": "Lieferung", "value": "2 € je Kilometer oder Selbstabholung"},
                {"icon": "spark", "label": "Kaution", "value": "300 € bar bei Übergabe"},
            ],
            "summary": "Hochwertige mobile Fasssauna aus nachhaltigem Thermoholz mit Schwitzraum und separatem Relax-Vorraum. Platz für bis zu 6 Personen, Stromanschluss, LED-Beleuchtung und atemberaubender Panorama-Ausblick.",
            "story_title": "Entspannung pur mit Weitblick und Relaxraum.",
            "story": "Unsere Amphora-Spa Panoramasauna bietet zwei separate Räume: Einen wettergeschützten Vorraum zum Umkleiden und Ausruhen sowie den geräumigen Schwitzraum mit Panoramafenster. Der kräftige Harvia-Holzofen sorgt für authentische finnische Hitze. Wochentags 90 €, Feiertage 100 €, Wochenende (Fr–So) 270 €.",
            "highlights": [
                "Zwei Räume: Schwitzraum plus separater Relax- und Umkleidevorraum",
                "Großes Panorama-Halbmondfenster für traumhafte Ausblicke",
                "Harvia Holzofen mit Saunasteinen für intensive Aufgüsse",
                "Stimmungsvolle LED-Beleuchtung und 230V-Stromanschluss",
                "Lieferung (2 €/km) oder kostenlose Selbstabholung mit Klasse BE",
            ],
            "images": [f"/static/uploads/fasssauna-{i}.jpg" for i in range(1, 20)],
            "sort_order": 3,
        },
    ]
    for item in models:
        conn.execute(
            """
            INSERT INTO models (
                slug, name, subtitle, badge, price_cents, capacity_min, capacity_max, size,
                features_json, specs_json, summary, story_title, story, highlights_json,
                images_json, active, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                item["slug"], item["name"], item["subtitle"], item["badge"], item["price_cents"],
                item["capacity_min"], item["capacity_max"], item["size"],
                json.dumps(item["features"], ensure_ascii=False),
                json.dumps(item["specs"], ensure_ascii=False),
                item["summary"], item["story_title"], item["story"],
                json.dumps(item["highlights"], ensure_ascii=False),
                json.dumps(item["images"], ensure_ascii=False),
                item["sort_order"],
            ),
        )
    extras = [
        (
            "premium-handtuecher",
            "Premium Handtücher",
            "2x extra große, extrem saugfähige Saunatücher (100×220 cm) aus 100% zertifizierter Bio-Baumwolle.",
            2500,
            "miete",
            "/static/images/towels.jpg",
            1,
        ),
        (
            "extra-kaminholz",
            "Extra Kaminholz",
            "Ein zusätzlicher Korb kammergetrocknetes Buchenholz (ca. 12 kg) für besonders lange und heiße Saunaabende.",
            1500,
            "kauf",
            "/static/images/firewood.jpg",
            2,
        ),
        (
            "bio-aufguss",
            "Bio-Aufguss Set",
            "Kuratiertes Set aus 3 naturreinen ätherischen Ölen (Nordische Kiefer, Eukalyptus, Zitrus) in Apothekerflaschen.",
            3500,
            "kauf",
            "/static/images/oils.jpg",
            3,
        ),
        (
            "vip-endreinigung",
            "VIP Endreinigung",
            "Lehnen Sie sich zurück. Wir übernehmen die komplette, professionelle Endreinigung und Desinfektion nach der Nutzung.",
            6000,
            "service",
            "",
            4,
        ),
    ]
    for slug, name, description, price, kind, image, sort in extras:
        conn.execute(
            """
            INSERT INTO extras (slug, name, description, price_cents, kind, image, active, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (slug, name, description, price, kind, image, sort),
        )
    model_ids = {row["slug"]: row["id"] for row in conn.execute("SELECT id, slug FROM models")}
    extra_ids = {row["slug"]: row["id"] for row in conn.execute("SELECT id, slug FROM extras")}
    today = date.today()
    create_booking(
        conn,
        {
            "model_id": model_ids.get("fasssauna-panorama") or list(model_ids.values())[0],
            "delivery_type": "delivery",
            "start": (today + timedelta(days=8)).isoformat(),
            "end": (today + timedelta(days=11)).isoformat(),
            "address": "Musterstraße 12, 10115 Berlin",
            "extras": [{"id": extra_ids["extra-kaminholz"], "qty": 1}] if "extra-kaminholz" in extra_ids else [],
            "first_name": "Max",
            "last_name": "Mustermann",
            "email": "max@example.com",
            "phone": "+49 123 456789",
            "notes": "Bitte im Hof abstellen.",
            "payment_method": "card",
            "card_last4": "4242",
            "card_brand": "Visa",
            "card_exp": "12/28",
            "client_token": "seed-max",
        },
    )
    create_booking(
        conn,
        {
            "model_id": model_ids.get("kombi-sauna-badefass") or list(model_ids.values())[0],
            "delivery_type": "delivery",
            "start": (today + timedelta(days=3)).isoformat(),
            "end": (today + timedelta(days=5)).isoformat(),
            "address": "Hauptstraße 5, 14467 Potsdam",
            "extras": [{"id": extra_ids["vip-endreinigung"], "qty": 1}] if "vip-endreinigung" in extra_ids else [],
            "first_name": "Anna",
            "last_name": "Berger",
            "email": "anna@example.com",
            "phone": "+49 171 2223344",
            "notes": "",
            "payment_method": "invoice",
            "client_token": "seed-anna",
        },
    )
    create_booking(
        conn,
        {
            "model_id": model_ids.get("badefass") or list(model_ids.values())[0],
            "delivery_type": "pickup",
            "start": (today - timedelta(days=6)).isoformat(),
            "end": (today - timedelta(days=4)).isoformat(),
            "address": "Tiefenbrunnen 1, 14929 Treuenbrietzen (Selbstabholung)",
            "extras": [],
            "first_name": "Jonas",
            "last_name": "Krüger",
            "email": "jonas@example.com",
            "phone": "+49 160 998877",
            "notes": "Selbstabholung mit Hänger am Nachmittag.",
            "payment_method": "paypal",
            "client_token": "seed-jonas",
        },
        allow_past=True,
        status="completed",
        payment_status="paid",
    )
    block_start = today + timedelta(days=20)
    block_end = today + timedelta(days=23)
    target_block_model = model_ids.get("badefass") or list(model_ids.values())[0]
    conn.execute(
        "INSERT INTO blocks (model_id, start_date, end_date, reason) VALUES (?, ?, ?, ?)",
        (target_block_model, block_start.isoformat(), block_end.isoformat(), "Wartung Brenner und Dichtungen"),
    )
    conn.execute(
        "INSERT INTO messages (name, email, phone, body, read, created_at) VALUES (?, ?, ?, ?, 0, ?)",
        (
            "Lena Hoffmann",
            "lena@example.com",
            "+49 170 1234567",
            "Können Sie die Panoramasauna auch nach Potsdam liefern, und ist der Vorraum beheizt?",
            now(),
        ),
    )

