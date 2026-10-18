from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    subtitle TEXT NOT NULL DEFAULT '',
    badge TEXT NOT NULL DEFAULT '',
    price_cents INTEGER NOT NULL,
    capacity_min INTEGER NOT NULL,
    capacity_max INTEGER NOT NULL,
    size TEXT NOT NULL,
    features_json TEXT NOT NULL,
    specs_json TEXT NOT NULL,
    summary TEXT NOT NULL,
    story_title TEXT NOT NULL,
    story TEXT NOT NULL,
    highlights_json TEXT NOT NULL,
    images_json TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    units INTEGER NOT NULL DEFAULT 1,
    included_text TEXT NOT NULL DEFAULT '',
    excluded_text TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS extras (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    kind TEXT NOT NULL,
    image TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS zones (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    prefixes TEXT NOT NULL DEFAULT '',
    cities TEXT NOT NULL DEFAULT '',
    price_cents INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY,
    number TEXT UNIQUE NOT NULL,
    public_token TEXT NOT NULL,
    client_token TEXT UNIQUE,
    model_id INTEGER NOT NULL,
    model_name TEXT NOT NULL,
    model_slug TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    nights INTEGER NOT NULL,
    address TEXT NOT NULL,
    postal_code TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT '',
    country TEXT NOT NULL DEFAULT 'Deutschland',
    zone_name TEXT NOT NULL,
    delivery_cents INTEGER NOT NULL,
    rent_cents INTEGER NOT NULL,
    extras_cents INTEGER NOT NULL,
    gross_cents INTEGER NOT NULL,
    vat_cents INTEGER NOT NULL,
    extras_json TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    payment_method TEXT NOT NULL,
    payment_status TEXT NOT NULL,
    card_brand TEXT NOT NULL DEFAULT '',
    card_last4 TEXT NOT NULL DEFAULT '',
    card_exp TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    admin_note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    lat REAL,
    lng REAL,
    deposit_cents INTEGER NOT NULL DEFAULT 0,
    voucher_cents INTEGER NOT NULL DEFAULT 0,
    voucher_code TEXT NOT NULL DEFAULT '',
    arrival_window TEXT NOT NULL DEFAULT '',
    company TEXT NOT NULL DEFAULT '',
    company_vat TEXT NOT NULL DEFAULT '',
    access_ok INTEGER NOT NULL DEFAULT 0,
    stripe_session TEXT NOT NULL DEFAULT '',
    delivery_type TEXT NOT NULL DEFAULT 'delivery'
);

CREATE TABLE IF NOT EXISTS booking_events (
    id INTEGER PRIMARY KEY,
    booking_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS blocks (
    id INTEGER PRIMARY KEY,
    model_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL,
    read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    reply TEXT NOT NULL DEFAULT '',
    replied_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS vouchers (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    cents INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    max_uses INTEGER NOT NULL DEFAULT 1,
    used INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY,
    author TEXT NOT NULL,
    text TEXT NOT NULL,
    rating INTEGER NOT NULL DEFAULT 5,
    model_slug TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY,
    booking_id INTEGER,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bookings_model ON bookings(model_id, start_date);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_bookings_email ON bookings(email);
CREATE INDEX IF NOT EXISTS idx_blocks_model ON blocks(model_id, start_date);
CREATE INDEX IF NOT EXISTS idx_emails_booking ON emails(booking_id);
"""


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def _add_column(conn: sqlite3.Connection, table: str, name: str, ddl: str) -> None:
    if name not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def connect(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    for name, ddl in (
        ("lat", "lat REAL"),
        ("lng", "lng REAL"),
        ("deposit_cents", "deposit_cents INTEGER NOT NULL DEFAULT 0"),
        ("voucher_cents", "voucher_cents INTEGER NOT NULL DEFAULT 0"),
        ("voucher_code", "voucher_code TEXT NOT NULL DEFAULT ''"),
        ("arrival_window", "arrival_window TEXT NOT NULL DEFAULT ''"),
        ("company", "company TEXT NOT NULL DEFAULT ''"),
        ("company_vat", "company_vat TEXT NOT NULL DEFAULT ''"),
        ("access_ok", "access_ok INTEGER NOT NULL DEFAULT 0"),
        ("stripe_session", "stripe_session TEXT NOT NULL DEFAULT ''"),
        ("delivery_type", "delivery_type TEXT NOT NULL DEFAULT 'delivery'"),
    ):
        _add_column(conn, "bookings", name, ddl)
    for name, ddl in (
        ("units", "units INTEGER NOT NULL DEFAULT 1"),
        ("included_text", "included_text TEXT NOT NULL DEFAULT ''"),
        ("excluded_text", "excluded_text TEXT NOT NULL DEFAULT ''"),
    ):
        _add_column(conn, "models", name, ddl)
    for name, ddl in (
        ("reply", "reply TEXT NOT NULL DEFAULT ''"),
        ("replied_at", "replied_at TEXT NOT NULL DEFAULT ''"),
    ):
        _add_column(conn, "messages", name, ddl)
    from saunacore.service import backfill_model_copy, backfill_pins, ensure_settings, upgrade_shipped_copy

    ensure_settings(conn)
    upgrade_shipped_copy(conn)
    backfill_pins(conn)
    backfill_model_copy(conn)


def init_db(conn: sqlite3.Connection) -> None:
    migrate(conn)
    count = conn.execute("SELECT COUNT(*) AS c FROM models").fetchone()["c"]
    if count == 0:
        from saunacore.service import backfill_model_copy, backfill_pins, seed_demo

        seed_demo(conn)
        backfill_pins(conn)
        backfill_model_copy(conn)
