from __future__ import annotations

import os
import secrets
from datetime import date
from pathlib import Path

from flask import Flask, flash, g, jsonify, redirect, render_template, request, url_for

from saunacore import icons, service
from saunacore.db import connect, get_db, init_db

ROOT = Path(__file__).resolve().parent.parent


def _secret(test_config: dict) -> str:
    if test_config.get("SECRET_KEY"):
        return test_config["SECRET_KEY"]
    env = os.environ.get("SAUNACORE_SECRET")
    if env:
        return env
    path = ROOT / "data" / "secret.key"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        value = secrets.token_hex(32)
        path.write_text(value, encoding="utf-8")
        return value
    except OSError:
        tmp_path = Path("/tmp/secret.key")
        try:
            if tmp_path.exists():
                return tmp_path.read_text(encoding="utf-8").strip()
            value = secrets.token_hex(32)
            tmp_path.write_text(value, encoding="utf-8")
            return value
        except OSError:
            return "saunacore-production-fallback-secret-2026"


def create_app(test_config: dict | None = None) -> Flask:
    test_config = test_config or {}
    app = Flask(
        __name__,
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
    )
    app.secret_key = _secret(test_config)

    db_path = test_config.get("DATABASE") or os.environ.get("SAUNACORE_DB")
    if not db_path:
        default_db = ROOT / "data" / "saunacore.db"
        is_writable = False
        try:
            default_db.parent.mkdir(parents=True, exist_ok=True)
            test_file = default_db.parent / ".perm_check"
            test_file.touch()
            test_file.unlink()
            is_writable = True
        except OSError:
            is_writable = False

        if is_writable:
            db_path = str(default_db)
        else:
            import shutil

            tmp_dir = Path("/tmp/data")
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tmp_db = tmp_dir / "saunacore.db"
            if not tmp_db.exists() and default_db.exists():
                try:
                    shutil.copy2(default_db, tmp_db)
                except OSError:
                    pass
            db_path = str(tmp_db)

    app.config["DATABASE"] = db_path
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    conn = connect(app.config["DATABASE"])
    try:
        init_db(conn)
    finally:
        conn.close()

    @app.route("/static/uploads/<path:filename>")
    def uploaded_file(filename: str):
        from flask import abort, send_from_directory

        uploads_dir = Path(app.static_folder) / "uploads"
        if (uploads_dir / filename).exists():
            return send_from_directory(uploads_dir, filename)
        tmp_uploads = Path("/tmp/uploads")
        if (tmp_uploads / filename).exists():
            return send_from_directory(tmp_uploads, filename)
        abort(404)

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.context_processor
    def inject():
        settings = service.redact_secrets(service.load_settings(get_db()))
        return {
            "settings": settings,
            "content": service.present_content(settings),
            "csrf_token": service.ensure_csrf,
            "icon": icons.render,
            "euro": service.format_euro,
            "money_input": service.money_input,
            "format_dt": service.format_dt,
            "status_labels": service.STATUS_LABELS,
            "kind_labels": service.KIND_LABELS,
            "maps_url": service.maps_url,
            "osm_url": service.osm_url,
            "year": date.today().year,
        }

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return jsonify(ok=False, error="Nicht gefunden."), 404
        from saunacore.public import _pack, _settings

        return render_template(
            "404.html",
            title="Seite nicht gefunden",
            **_pack(
                _settings(),
                "Seite nicht gefunden",
                "Diese Seite gibt es nicht.",
                robots="noindex, follow",
            ),
        ), 404

    @app.errorhandler(413)
    def too_large(_error):
        flash("Die Datei ist zu groß (höchstens 16 MB).", "error")
        return redirect(request.referrer or url_for("public.home"))

    @app.errorhandler(400)
    def bad_request(_error):
        if request.path.startswith("/api/"):
            return jsonify(ok=False, error="Anfrage abgelehnt."), 400
        if request.path.startswith("/admin"):
            flash("Die Sitzung ist abgelaufen. Bitte erneut versuchen.", "error")
            return redirect(request.referrer or url_for("admin.login"))
        from saunacore.public import _pack, _settings

        return render_template(
            "404.html",
            title="Anfrage abgelehnt",
            **_pack(
                _settings(),
                "Anfrage abgelehnt",
                "Die Anfrage konnte nicht verarbeitet werden.",
                robots="noindex, follow",
            ),
        ), 400

    from saunacore.admin import bp as admin_bp
    from saunacore.api import bp as api_bp
    from saunacore.public import bp as public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    return app
