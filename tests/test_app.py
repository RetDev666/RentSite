import io
import re
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from saunacore import create_app, service
from saunacore.db import get_db


JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16


class SaunacoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "DATABASE": str(Path(self.tmp.name) / "saunacore.db"),
                "SECRET_KEY": "test-secret",
                "TESTING": True,
            }
        )
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.db = get_db()
        self.today = date.today()

    def tearDown(self):
        self.db.close()
        self.ctx.pop()
        self.tmp.cleanup()

    def csrf(self):
        self.client.get("/")
        with self.client.session_transaction() as sess:
            return sess["csrf"]

    def model_id(self, slug):
        return self.db.execute("SELECT id FROM models WHERE slug = ?", (slug,)).fetchone()["id"]

    def extra_id(self, slug):
        return self.db.execute("SELECT id FROM extras WHERE slug = ?", (slug,)).fetchone()["id"]

    def quote(self, **payload):
        token = self.csrf()
        return self.client.post(
            "/api/quote",
            json=payload,
            headers={"X-CSRF-Token": token},
        )

    def book(self, **payload):
        token = self.csrf()
        return self.client.post(
            "/api/bookings",
            json=payload,
            headers={"X-CSRF-Token": token},
        )

    def span(self, start_offset, nights):
        start = self.today + timedelta(days=start_offset)
        return start.isoformat(), (start + timedelta(days=nights)).isoformat()

    def guest(self, **overrides):
        start, end = self.span(40, 3)
        data = {
            "model_id": self.model_id("model-xl"),
            "start": start,
            "end": end,
            "address": "Unter den Linden 1, 10115 Berlin",
            "extras": [],
            "first_name": "Eva",
            "last_name": "Sommer",
            "email": "eva@example.com",
            "phone": "+49 170 1112233",
            "notes": "",
            "payment_method": "paypal",
            "client_token": "guest-eva",
            "gross_cents": 1,
        }
        data.update(overrides)
        return data

    def login(self):
        self.client.get("/admin/login")
        with self.client.session_transaction() as sess:
            token = sess["csrf"]
        response = self.client.post(
            "/admin/login",
            data={
                "csrf_token": token,
                "email": service.DEMO_EMAIL,
                "password": service.DEMO_PASSWORD,
                "next": "/admin/",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/admin/"))

    def admin_token(self):
        self.client.get("/admin/")
        with self.client.session_transaction() as sess:
            return sess["csrf"]

    def test_money_and_included_vat(self):
        self.assertEqual(service.format_euro(44700), "447 €")
        self.assertEqual(service.format_euro(46200), "462 €")
        self.assertEqual(service.format_euro(1500), "15 €")
        self.assertEqual(service.included_vat(44700, 19), 7137)
        self.assertEqual(service.included_vat(46200, 19), 7376)
        self.assertEqual(service.parse_money("149"), 14900)
        self.assertEqual(service.parse_money("15,50"), 1550)

    def test_zones_longest_prefix_and_cities(self):
        zone, plz = service.lookup_zone(self.db, "Berlin")
        self.assertEqual(zone["name"], "Zone A")
        self.assertEqual(int(zone["price_cents"]), 0)
        self.assertEqual(plz, "")
        zone, plz = service.lookup_zone(self.db, "10115 Berlin")
        self.assertEqual(zone["name"], "Zone A")
        self.assertEqual(plz, "10115")
        zone, _plz = service.lookup_zone(self.db, "14467 Potsdam")
        self.assertEqual(zone["name"], "Zone B")
        self.assertEqual(int(zone["price_cents"]), 5000)
        zone, _plz = service.lookup_zone(self.db, "Hauptstraße 5, 80331 München")
        self.assertEqual(zone["name"], "Zone C")
        self.assertEqual(int(zone["price_cents"]), 9000)
        zone, _plz = service.lookup_zone(self.db, "Potsdam")
        self.assertEqual(zone["name"], "Zone B")
        missing, _plz = service.lookup_zone(self.db, "Qqqville")
        self.assertIsNone(missing)
        response = self.client.get("/api/zone?q=10115")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["price_cents"], 0)
        self.assertEqual(self.client.get("/api/zone?q=Qqqville").status_code, 404)

    def test_pin_quote_uses_coordinates_and_maps_link(self):
        def fake(lat, lng):
            return {"address": "Unter den Linden 1, 10115 Berlin", "postal_code": "10115", "city": "Berlin"}

        original = service.reverse_geocode
        service.reverse_geocode = fake
        try:
            start, end = self.span(55, 2)
            response = self.quote(
                model_id=self.model_id("model-xl"),
                start=start,
                end=end,
                address="irgendwo anders, 80331 München",
                lat=52.52,
                lng=13.40,
                extras=[],
            )
            self.assertEqual(response.status_code, 200, response.get_json())
            body = response.get_json()
            self.assertEqual(body["delivery_cents"], 0)
            self.assertEqual(body["address"], "Unter den Linden 1, 10115 Berlin")
            self.assertEqual(body["lat"], 52.52)
            saved = self.book(**self.guest(
                start=start,
                end=end,
                address="irgendwo anders, 80331 München",
                lat=52.52,
                lng=13.40,
                client_token="pin-eva",
                email="pin@example.com",
            ))
            self.assertEqual(saved.status_code, 200, saved.get_json())
            row = self.db.execute("SELECT * FROM bookings WHERE client_token = 'pin-eva'").fetchone()
            self.assertEqual(row["zone_name"], "Zone A")
            self.assertAlmostEqual(row["lat"], 52.52)
            self.assertIn("maps?q=52.520000,13.400000", service.maps_url(row["lat"], row["lng"], row["address"]))
        finally:
            service.reverse_geocode = original

    def test_quote_uses_server_price(self):
        start, end = self.span(50, 3)
        plain = self.quote(
            model_id=self.model_id("model-xl"),
            start=start,
            end=end,
            address="Pariser Platz 1, 10115 Berlin",
            extras=[],
            gross_cents=1,
        )
        self.assertEqual(plain.status_code, 200, plain.get_json())
        body = plain.get_json()
        self.assertEqual(body["nights"], 3)
        self.assertEqual(body["rent_cents"], 44700)
        self.assertEqual(body["delivery_cents"], 0)
        self.assertEqual(body["gross_cents"], 44700)
        self.assertEqual(body["vat_cents"], 7137)
        wood = self.quote(
            model_id=self.model_id("model-xl"),
            start=start,
            end=end,
            address="Pariser Platz 1, 10115 Berlin",
            extras=[{"id": self.extra_id("extra-kaminholz"), "qty": 1}],
        )
        self.assertEqual(wood.get_json()["gross_cents"], 46200)
        self.assertEqual(wood.get_json()["vat_cents"], 7376)
        self.assertEqual(self.quote(model_id=self.model_id("model-xl"), start="nope", end=end).status_code, 400)
        denied = self.client.post("/api/quote", json={"model_id": 1, "start": start, "end": end})
        self.assertEqual(denied.status_code, 400)

    def test_seed_booking_and_maintenance_block(self):
        seeded = self.db.execute("SELECT * FROM bookings WHERE client_token = 'seed-max'").fetchone()
        self.assertEqual(seeded["gross_cents"], 46200)
        self.assertEqual(seeded["vat_cents"], 7376)
        self.assertEqual(seeded["payment_status"], "simulated")
        self.assertNotIn(seeded["card_last4"], {"", None})
        anna = self.db.execute("SELECT * FROM bookings WHERE client_token = 'seed-anna'").fetchone()
        self.assertEqual(anna["status"], "new")
        self.assertEqual(anna["payment_status"], "unpaid")
        self.assertEqual(anna["payment_method"], "invoice")
        start, end = self.span(20, 2)
        blocked = self.quote(
            model_id=self.model_id("model-s"),
            start=start,
            end=end,
            address="Seeweg 2, 14193 Berlin",
            extras=[],
        )
        self.assertEqual(blocked.status_code, 400)
        self.assertIn("belegt", blocked.get_json()["error"])

    def test_booking_overlap_cancel_rebook_and_idempotency(self):
        first = self.book(**self.guest(client_token="once"))
        self.assertEqual(first.status_code, 200, first.get_json())
        payload = first.get_json()
        self.assertTrue(payload["number"].startswith("SC-"))
        again = self.book(**self.guest(client_token="once", email="other@example.com"))
        self.assertEqual(again.get_json()["number"], payload["number"])
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) AS c FROM bookings WHERE client_token = 'once'").fetchone()["c"],
            1,
        )
        overlap = self.book(**self.guest(client_token="twice", email="two@example.com"))
        self.assertEqual(overlap.status_code, 400)
        row = self.db.execute("SELECT * FROM bookings WHERE client_token = 'once'").fetchone()
        self.assertEqual(row["gross_cents"], 44700)
        self.assertNotIn("4242424242424242", " ".join(str(value) for value in tuple(row)))
        service.set_status(self.db, row["id"], "cancelled")
        rebooked = self.book(**self.guest(client_token="third", email="three@example.com"))
        self.assertEqual(rebooked.status_code, 200, rebooked.get_json())
        thanks = self.client.get(payload["redirect"])
        self.assertEqual(thanks.status_code, 200)
        self.assertIn("Vielen Dank", thanks.get_data(as_text=True))
        self.assertIn(payload["number"], thanks.get_data(as_text=True))
        self.assertNotIn("E-Mail gesendet", thanks.get_data(as_text=True))
        self.assertEqual(self.client.get(payload["redirect"].split("?")[0]).status_code, 404)

    def test_card_and_invoice_payment_states(self):
        missing = self.book(**self.guest(payment_method="card", client_token="card-bad", card_last4="", card_exp="12/28"))
        self.assertEqual(missing.status_code, 400)
        expired = self.book(
            **self.guest(
                payment_method="card",
                client_token="card-old",
                card_last4="4242",
                card_brand="Visa",
                card_exp="01/20",
                email="old@example.com",
            )
        )
        self.assertEqual(expired.status_code, 400)
        start, end = self.span(60, 1)
        card = self.book(
            **self.guest(
                start=start,
                end=end,
                payment_method="card",
                client_token="card-ok",
                card_last4="4242",
                card_brand="Visa",
                card_exp="12/30",
                card_number="4242424242424242",
                email="card@example.com",
            )
        )
        self.assertEqual(card.status_code, 200, card.get_json())
        stored = self.db.execute("SELECT * FROM bookings WHERE client_token = 'card-ok'").fetchone()
        self.assertEqual(stored["status"], "confirmed")
        self.assertEqual(stored["payment_status"], "simulated")
        self.assertEqual(stored["card_last4"], "4242")
        self.assertNotIn("4242424242424242", " ".join(str(value) for value in tuple(stored)))
        invoice_start, invoice_end = self.span(70, 2)
        invoice = self.book(
            **self.guest(
                model_id=self.model_id("model-x"),
                start=invoice_start,
                end=invoice_end,
                address="Markt 1, 80331 München",
                payment_method="invoice",
                client_token="invoice-ok",
                email="bill@example.com",
            )
        )
        self.assertEqual(invoice.status_code, 200, invoice.get_json())
        bill = self.db.execute("SELECT * FROM bookings WHERE client_token = 'invoice-ok'").fetchone()
        self.assertEqual(bill["status"], "new")
        self.assertEqual(bill["payment_status"], "unpaid")
        self.assertEqual(bill["delivery_cents"], 9000)
        self.assertEqual(bill["rent_cents"], 23800)
        self.assertEqual(bill["gross_cents"], 32800)

    def test_public_pages_and_contact(self):
        pages = {
            "/": "Premium Sauna",
            "/flotte": "Model Panorama",
            "/flotte/model-xl": "Handwerkskunst trifft auf Natur",
            "/buchen/model-xl": "Weiter zu Extras",
            "/so-funktionierts": "Wir liefern",
            "/preise": "Endpreise",
            "/kontakt": "Nachricht",
            "/faq": "Stornierung",
            "/impressum": "Musterstraße",
            "/datenschutz": "hallo@saunacore.de",
            "/agb": "MwSt",
            "/mietbedingungen": "7",
        }
        for path, needle in pages.items():
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn(needle, response.get_data(as_text=True))
        booking = self.client.get("/buchen/model-xl?start=2026-11-01&end=2026-11-04&address=10115%20Berlin")
        self.assertIn("booking.js", booking.get_data(as_text=True))
        self.assertIn("noindex", booking.get_data(as_text=True))

        def description(path):
            html = self.client.get(path).get_data(as_text=True)
            match = re.search(r'<meta name="description" content="([^"]*)"', html)
            self.assertIsNotNone(match, path)
            return match.group(1)

        self.assertNotEqual(description("/"), description("/flotte"))
        self.assertNotEqual(description("/flotte"), description("/kontakt"))
        self.assertIn("Model XL mieten", self.client.get("/flotte/model-xl").get_data(as_text=True))
        home = self.client.get("/")
        self.assertIn("application/ld+json", home.get_data(as_text=True))
        self.assertIn('rel="canonical"', home.get_data(as_text=True))
        robots = self.client.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        self.assertIn("Disallow: /admin", robots.get_data(as_text=True))
        self.assertIn("Disallow: /api", robots.get_data(as_text=True))
        sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
        self.assertIn("/flotte/model-xl", sitemap)
        self.assertNotIn("/buchen/", sitemap)
        self.assertNotIn("/buchung/", sitemap)
        self.assertNotIn("/admin", sitemap)
        missing = self.client.get("/gibt-es-nicht")
        self.assertEqual(missing.status_code, 404)
        self.assertIn("noindex", missing.get_data(as_text=True))
        self.assertIn("2026-11-01", booking.get_data(as_text=True))
        self.assertEqual(self.client.get("/flotte/missing").status_code, 404)
        token = self.csrf()
        sent = self.client.post(
            "/kontakt",
            data={
                "csrf_token": token,
                "name": "Mara Lind",
                "email": "mara@example.com",
                "phone": "+49 170 555666",
                "body": "Ist Model Panorama im November frei?",
            },
        )
        self.assertEqual(sent.status_code, 302)
        message = self.db.execute("SELECT * FROM messages WHERE email = 'mara@example.com'").fetchone()
        self.assertIsNotNone(message)
        self.assertEqual(message["read"], 0)

    def test_admin_guard_dashboard_and_settings_guard(self):
        guarded = self.client.get("/admin/")
        self.assertEqual(guarded.status_code, 302)
        self.assertIn("/admin/login", guarded.location)
        login = self.client.get("/admin/login")
        self.assertEqual(login.status_code, 200)
        self.assertIn(service.DEMO_EMAIL, login.get_data(as_text=True))
        self.login()
        for path, needle in {
            "/admin/": "Überblick",
            "/admin/buchungen": "SC-",
            "/admin/buchungen/neu": "Neue Buchung",
            "/admin/kalender": "Kalender",
            "/admin/modelle": "Model XL",
            "/admin/extras": "VIP Endreinigung",
            "/admin/zonen": "Zone A",
            "/admin/sperren": "Wartung",
            "/admin/nachrichten": "Lena Hoffmann",
            "/admin/kunden": "max@example.com",
            "/admin/einstellungen": "Mindestnächte",
            "/admin/inhalte": "Startseite",
        }.items():
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn(needle, response.get_data(as_text=True))
        detail = self.db.execute("SELECT id FROM bookings WHERE client_token = 'seed-anna'").fetchone()["id"]
        opened = self.client.get(f"/admin/buchungen/{detail}")
        self.assertEqual(opened.status_code, 200)
        self.assertIn("Demo", opened.get_data(as_text=True))
        token = self.admin_token()
        paid = self.client.post(f"/admin/buchungen/{detail}/bezahlt", data={"csrf_token": token})
        self.assertEqual(paid.status_code, 302)
        self.assertEqual(
            self.db.execute("SELECT payment_status FROM bookings WHERE id = ?", (detail,)).fetchone()["payment_status"],
            "paid",
        )
        before = service.load_settings(self.db)
        rejected = self.client.post(
            "/admin/einstellungen",
            data={
                "csrf_token": self.admin_token(),
                "company_name": before["company_name"],
                "owner_name": before["owner_name"],
                "street": before["street"],
                "postal_code": before["postal_code"],
                "city": before["city"],
                "email": before["email"],
                "phone": before["phone"],
                "vat_id": before["vat_id"],
                "vat_percent": before["vat_percent"],
                "min_nights": "10",
                "max_nights": "2",
                "cancellation_days": before["cancellation_days"],
            },
        )
        self.assertEqual(rejected.status_code, 302)
        after = service.load_settings(self.db)
        self.assertEqual(after["min_nights"], "1")
        self.assertEqual(after["max_nights"], "21")

    def test_admin_can_create_model_extra_zone_and_block(self):
        self.login()
        token = self.admin_token()
        created = self.client.post(
            "/admin/modelle/neu",
            data={
                "csrf_token": token,
                "name": "Testsauna",
                "subtitle": "Nur für den Test",
                "badge": "Test",
                "price": "99",
                "sort_order": "9",
                "capacity_min": "2",
                "capacity_max": "3",
                "size": "kompakt",
                "active": "1",
                "summary": "Eine kompakte Testsauna mit genug Text für die Prüfung.",
                "story_title": "Testgeschichte",
                "story": "Die Testsauna bleibt nur so lange online, wie dieser Test sie braucht.",
                "highlights": "Fenster\nOfen",
                "feature_icon": ["users"],
                "feature_label": ["2–3 Pers."],
                "spec_icon": ["users"],
                "spec_label": ["Kapazität"],
                "spec_value": ["Bis zu 3"],
                "images": (io.BytesIO(JPEG), "sauna.jpg"),
            },
        )
        self.assertEqual(created.status_code, 302, created.get_data(as_text=True))
        row = self.db.execute("SELECT * FROM models WHERE name = 'Testsauna'").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["price_cents"], 9900)
        self.assertIn("/static/uploads/", row["images_json"])
        public = self.client.get("/flotte/testsauna")
        self.assertEqual(public.status_code, 200)
        extra = self.client.post(
            "/admin/extras/neu",
            data={
                "csrf_token": self.admin_token(),
                "name": "Saunahut",
                "description": "Ein Filzhut für den Test.",
                "price": "12",
                "kind": "kauf",
                "sort_order": "8",
                "active": "1",
            },
        )
        self.assertEqual(extra.status_code, 302)
        self.assertIsNotNone(self.db.execute("SELECT 1 FROM extras WHERE slug = 'saunahut'").fetchone())
        zone = self.client.post(
            "/admin/zonen",
            data={
                "csrf_token": self.admin_token(),
                "name": "Zone Test",
                "prefixes": "99",
                "cities": "teststadt",
                "price": "25",
                "note": "Testzone",
                "sort_order": "9",
                "active": "1",
            },
        )
        self.assertEqual(zone.status_code, 302)
        found, _plz = service.lookup_zone(self.db, "99001 Teststadt")
        self.assertEqual(found["name"], "Zone Test")
        self.assertEqual(int(found["price_cents"]), 2500)
        start, end = self.span(80, 2)
        block = self.client.post(
            "/admin/sperren",
            data={
                "csrf_token": self.admin_token(),
                "model_id": str(row["id"]),
                "start": start,
                "end": (self.today + timedelta(days=81)).isoformat(),
                "reason": "Testwartung",
            },
        )
        self.assertEqual(block.status_code, 302)
        busy = self.client.get(f"/api/busy?model_id={row['id']}&start={start}&end={end}")
        self.assertIn(start, busy.get_json()["busy"])
        self.assertNotIn(end, busy.get_json()["busy"])


if __name__ == "__main__":
    unittest.main()
