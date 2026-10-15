from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saunacore import create_app


def main():
    print("=== Starting static export for Netlify ===")
    public_dir = ROOT / "public"
    if public_dir.exists():
        shutil.rmtree(public_dir)
    public_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy static assets
    print("Copying static assets to public/static...")
    shutil.copytree(ROOT / "static", public_dir / "static")

    # 2. Initialize Flask app
    app = create_app({"TESTING": True})
    client = app.test_client()

    pages = [
        ("/", "index.html"),
        ("/flotte", "flotte/index.html"),
        ("/flotte/model-s", "flotte/model-s/index.html"),
        ("/flotte/model-x", "flotte/model-x/index.html"),
        ("/flotte/model-xl", "flotte/model-xl/index.html"),
        ("/so-funktionierts", "so-funktionierts/index.html"),
        ("/preise", "preise/index.html"),
        ("/kontakt", "kontakt/index.html"),
        ("/buchen/model-s", "buchen/model-s/index.html"),
        ("/buchen/model-x", "buchen/model-x/index.html"),
        ("/buchen/model-xl", "buchen/model-xl/index.html"),
        ("/faq", "faq/index.html"),
        ("/agb", "agb/index.html"),
        ("/datenschutz", "datenschutz/index.html"),
        ("/impressum", "impressum/index.html"),
        ("/mietbedingungen", "mietbedingungen/index.html"),
        ("/buchung/finden", "buchung/finden/index.html"),
        ("/robots.txt", "robots.txt"),
        ("/sitemap.xml", "sitemap.xml"),
    ]

    for path, rel_dest in pages:
        res = client.get(path)
        if res.status_code == 200:
            dest = public_dir / rel_dest
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(res.data)
            print(f"  [OK 200] {path} -> {rel_dest}")
        else:
            print(f"  [FAIL {res.status_code}] {path}")

    # Export admin login page for /admin and /admin/login
    res_admin = client.get("/admin/login")
    if res_admin.status_code == 200:
        for rel_dest in ["admin/index.html", "admin/login/index.html"]:
            dest = public_dir / rel_dest
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(res_admin.data)
            print(f"  [OK 200] /admin/login -> {rel_dest}")
    else:
        print(f"  [FAIL {res_admin.status_code}] /admin/login")

    # Generate 404.html
    res_404 = client.get("/trigger-404-for-export")
    (public_dir / "404.html").write_bytes(res_404.data)
    print("  [OK 404] -> 404.html")

    print("=== Static export finished successfully ===")


if __name__ == "__main__":
    main()
