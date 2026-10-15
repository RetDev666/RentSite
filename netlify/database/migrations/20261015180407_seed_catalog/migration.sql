-- Seed catalog data (models, extras, delivery zones, settings) shipped with the Flask app.
INSERT INTO settings (key, value) VALUES
  ('cancellation_days', '7'),
  ('city', 'Berlin'),
  ('company_name', 'Saunacore'),
  ('contact_text', 'Fragen zu Lieferung, Modellen oder einem bestehenden Termin.'),
  ('contact_title', 'Schreib uns.'),
  ('corporate_text', 'Für Teams, Events und mehrere Geräte: schreibt uns mit Zeitraum, Personenzahl und Lieferort. Im Checkout kannst du Firma und USt-IdNr. angeben. Der Preis bleibt der ausgewiesene Endpreis.'),
  ('deposit_cents', '0'),
  ('email', 'hallo@saunacore.de'),
  ('faq_json', '[{"q": "Wie wird der Preis berechnet?", "a": "Tagessatz mal Nächte, plus die Lieferzone der Markierung, plus Extras, plus eine Kaution, falls sie hinterlegt ist, abzüglich eines gültigen Gutscheins. Eine Nacht ist der Abstand zwischen Anreise und Abreise. Die MwSt. von {vat}% ist enthalten."}, {"q": "Wann ist die Lieferung kostenlos?", "a": "Zone A, standardmäßig Berlin, ist kostenlos. Andere Zonen haben einen festen Preis. Beides steht vor dem Abschluss und lässt sich im Admin ändern."}, {"q": "Kann derselbe Tag zweimal vergeben werden?", "a": "Nur so oft, wie Geräte dieses Modells hinterlegt sind. Standard ist ein Gerät. Eine Sperrzeit blockiert das ganze Modell. Der Abreisetag kann die nächste Anreise sein."}, {"q": "Wie storniere ich?", "a": "Bis {cancel} Tage vor Mietbeginn ist die Stornierung kostenlos. Unter Buchung finden gibst du Bestellnummer und E-Mail ein und stornierst selbst. Danach bleibt der Zeitraum belegt, bis der Status geändert wird."}, {"q": "Wann kommt die Sauna?", "a": "Du wählst Vormittag, Nachmittag oder ein flexibles Fenster. Das ist ein Wunsch. Die genaue Uhrzeit stimmen wir danach ab."}, {"q": "Gibt es eine Kaution?", "a": "Nur wenn in den Einstellungen ein Betrag steht. Er ist im Endpreis enthalten und in der Übersicht als eigene Zeile sichtbar. Steht dort nichts, gibt es keine Kaution."}, {"q": "Welche Zahlung gibt es?", "a": "Kreditkarte, PayPal und Rechnung. Ohne Zahlungsdienstleister wird keine echte Abbuchung ausgelöst. Der Admin sieht den Zahlungsstatus und kann eine Rechnung als bezahlt markieren."}]'),
  ('fleet_page_text', 'Luxuriöse Fasssaunen, geliefert an deinen Wunschort. Kompromisslose Qualität für tiefste Entspannung.'),
  ('fleet_page_title', 'Wähle dein mobiles Wellness-Erlebnis.'),
  ('fleet_text', 'Exklusive Modelle für jedes Bedürfnis. Höchste Qualität, kompromissloses Design.'),
  ('fleet_title', 'Unsere Flotte'),
  ('footer_line', 'Luxury Mobile Saunas.'),
  ('hero_image', '/static/images/hero.jpg'),
  ('hero_kicker', 'Saunacore'),
  ('hero_lede', 'Deine private Sauna. Geliefert. Wo und wann du willst.'),
  ('hero_title', 'Premium Sauna
on Demand'),
  ('how_kicker', 'So funktioniert''s'),
  ('how_lede', 'Modell wählen, Termin festlegen, Markierung setzen, geliefert bekommen. Abholung inklusive.'),
  ('how_title', 'Drei Schritte bis zur eigenen Sauna.'),
  ('impressum_note', 'Angaben pflegst du in der Admin-Oberfläche unter Einstellungen. Dieses Impressum ist eine Vorlage und ersetzt keine rechtliche Prüfung.'),
  ('max_nights', '21'),
  ('meta_description', ''),
  ('min_nights', '1'),
  ('owner_name', 'Saunacore GmbH'),
  ('phone', '+49 30 12001890'),
  ('points_json', '[{"icon": "leaf", "title": "Premium Holz", "text": "Nachhaltiges Thermoholz für optimale Hitze und Langlebigkeit."}, {"icon": "truck", "title": "Schnelle Lieferung", "text": "Wir bringen die Sauna direkt an deinen Wunschort."}, {"icon": "spark", "title": "Einfache Bedienung", "text": "Intuitive Steuerung für ein ungestörtes Sauna-Erlebnis."}]'),
  ('postal_code', '10115'),
  ('prices_text', 'Alle Preise sind Endpreise inklusive {vat}% MwSt. Die Miete rechnet sich pro Nacht, von der Anreise bis zur Abreise. Modelle, Extras, Zonen und der Steuersatz kommen aus der Admin-Oberfläche.'),
  ('prices_title', 'Klare Tagessätze, Lieferung nach Zone.'),
  ('privacy_text', 'Für eine Buchung speichern wir Name, E-Mail, Telefon, den markierten Lieferort mit Koordinaten, Zeitraum, gewähltes Modell, Extras, Lieferfenster, optionale Firma und die Zahlungsart. Bei der Demo-Karte speichern wir Marke, Ablauf und die letzten vier Stellen. Die volle Kartennummer und der CVC werden nicht gespeichert. Ist ein Zahlungsdienstleister eingerichtet, läuft die Zahlung dort. Wir speichern dann nur die Sitzungskennung.

Die Karte lädt erst nach dem Klick auf Karte laden. Danach holt der Browser Kacheln von OpenStreetMap. Die Adresse zur Markierung ermitteln wir zur Zuordnung der Lieferzone. Die Zustimmung bleibt in diesem Browser.

Nachrichten aus dem Formular bleiben in der Admin-Oberfläche, bis sie gelöscht werden. Eine Antwort speichern wir dort. Ein Versand per E-Mail erfolgt nur, wenn ein Mailserver eingerichtet ist.

Buchungen bleiben erhalten, damit Verfügbarkeit und Nachweise stimmen. Eine Löschanfrage richtest du an {email}. Die Bestellseite erreichst du mit Bestellnummer und derselben E-Mail.'),
  ('rental_text', 'Eine Nacht läuft von der Anreise bis zur Abreise. Der Abreisetag ist für die nächste Buchung frei.

Kostenlose Stornierung ist bis {cancel} Tage vor Mietbeginn möglich, über die Bestellseite mit Bestellnummer und E-Mail. Danach bleibt der gebuchte Betrag bestehen, sofern nichts anderes vereinbart wird. Laufende und abgeschlossene Mieten lassen sich dort nicht mehr stornieren.

Die Lieferung erfolgt an die gesetzte Markierung, wenn sie in einer aktiven Zone liegt. Außerhalb des Liefergebiets ist keine Buchung möglich. Ein Lieferfenster ist eine Wunschangabe.

Zufahrt, Stellfläche und eine Person zur Übergabe bestätigst du vor dem Abschluss. Brennholz der Grundausstattung, soweit beim Modell genannt, ist enthalten. Weitere Mengen buchst du als Extra.'),
  ('site_url', ''),
  ('smtp_from', ''),
  ('smtp_host', ''),
  ('smtp_port', '587'),
  ('smtp_tls', '1'),
  ('smtp_user', ''),
  ('steps_json', '[{"title": "Auswählen", "text": "Wähle dein Modell, den Zeitraum und setze die Markierung auf der Karte. Preis und Verfügbarkeit siehst du sofort.", "image": "/static/images/choose.jpg"}, {"title": "Wir liefern", "text": "Unser Team bringt die Sauna pünktlich an den markierten Ort, stellt sie sicher auf und gibt dir eine kurze Einweisung.", "image": "/static/images/deliver.jpg"}, {"title": "Entspannen", "text": "Lehne dich zurück und genieße dein privates Spa-Erlebnis. Nach Ablauf der Zeit holen wir die Sauna wieder ab. Storno ist bis {cancel} Tage vorher kostenlos.", "image": "/static/images/relax.jpg"}]'),
  ('street', 'Musterstraße 1'),
  ('stripe_publishable', ''),
  ('terms_text', 'Vertragspartner ist {company}. Der Vertrag kommt zustande, wenn die Buchung eine Bestellnummer erhält.

Es gilt der Preis, der im letzten Schritt vor dem Absenden angezeigt wird: Tagessatz mal Nächte, plus Lieferung der erkannten Zone, plus gewählte Extras, plus eine Kaution, sofern sie hinterlegt ist, abzüglich eines gültigen Gutscheins. Enthalten ist die MwSt. von {vat}%. Die Kaution ist Teil des angezeigten Endpreises.

Die Sauna bleibt Eigentum von {company}. Sie ist pfleglich zu behandeln und zum vereinbarten Abreisetag bereitzuhalten. Eine optionale Firmenangabe ändert den ausgewiesenen Preis nicht. Diese Texte sind eine Vorlage und ersetzen keine rechtliche Prüfung.'),
  ('vat_id', 'DE123456789'),
  ('vat_percent', '19')
ON CONFLICT (key) DO NOTHING;
--> statement-breakpoint
INSERT INTO zones (id, name, prefixes, cities, price_cents, note, active, sort_order) VALUES
  (1, 'Zone A', '10,12,13,14', 'berlin', 0, 'Berlin, kostenlos', true, 1),
  (2, 'Zone B', '144,145,146,147,149,15,16,17,18,19,01,02,03,04,06,07,08,09,39', 'potsdam,leipzig,dresden,hamburg,hannover,magdeburg', 5000, 'Umland und ausgewählte Städte, 50 €', true, 2),
  (3, 'Zone C', '*', 'muenchen,münchen,munich,koeln,köln,frankfurt,stuttgart,duesseldorf,düsseldorf,nuernberg,nürnberg,bremen', 9000, 'Übriges Deutschland mit fünfstelliger PLZ, 90 €', true, 3)
ON CONFLICT (id) DO NOTHING;
--> statement-breakpoint
INSERT INTO models (id, slug, name, subtitle, badge, price_cents, capacity_min, capacity_max, size, features, specs, summary, story_title, story, highlights, images, active, sort_order, units, included_text, excluded_text) VALUES
  (1, 'model-s', 'Model S', 'Die kompakte Fasssauna', 'Kompakt', 8900, 2, 4, 'kompakt', '[{"icon": "users", "label": "2–4 Pers."}, {"icon": "flame", "label": "Holzofen"}, {"icon": "window", "label": "Türfenster"}]'::jsonb, '[{"icon": "users", "label": "Kapazität", "value": "Bis zu 4 Personen"}, {"icon": "eye", "label": "Aussicht", "value": "Türfenster"}, {"icon": "flame", "label": "Technik", "value": "Holzofen"}]'::jsonb, 'Unsere kompakte Fasssauna für zwei bis vier Personen. Thermoholz, Holzofen und ein türhohes Fenster — schnell aufgestellt, ruhig im Charakter.', 'Klein. Warm. Vollständig.', 'Model S wird in Handarbeit aus nachhaltigem Thermoholz gefertigt. Das türhohe Fenster hält den Blick nach draußen offen, der Ofen trägt die Hitze gleichmäßig. Sie passt in kleinere Gärten und steht in wenigen Minuten bereit.', '["Holzofen mit langer Glut für gleichmäßige Hitze", "Türfenster mit Blick ins Freie", "Kompaktes Maß, das auch in kleinere Gärten passt"]'::jsonb, '["/static/images/model-s.jpg", "/static/images/interior.jpg", "/static/images/wood.jpg", "/static/images/stove.jpg"]'::jsonb, true, 1, 1, 'Holzofen
Türfenster
Grundausstattung Brennholz
Aufbau und Abholung', 'Handtücher
Zusätzliches Kaminholz
Endreinigung'),
  (2, 'model-x', 'Model X', 'Der Bestseller', 'Bestseller', 11900, 4, 6, 'mittel', '[{"icon": "users", "label": "4–6 Pers."}, {"icon": "flame", "label": "Holzofen"}, {"icon": "window", "label": "Halbmond"}]'::jsonb, '[{"icon": "users", "label": "Kapazität", "value": "Bis zu 6 Personen"}, {"icon": "eye", "label": "Aussicht", "value": "Halbmond-Fenster"}, {"icon": "flame", "label": "Technik", "value": "Holzofen"}]'::jsonb, 'Die meistgebuchte Fasssauna. Platz für vier bis sechs Personen, ein halbrundes Fenster und ein Ofen, der den Abend trägt.', 'Der Abend gehört euch.', 'Model X verbindet kompakte Logistik mit genug Raum für einen ganzen Freundeskreis. Das Halbmondfenster legt einen warmen Bogen ins Holz, der Ofen hält die Temperatur, ohne dass jemand nachlegen muss.', '["Halbmond-Fenster für weiches Licht", "Holzofen mit großer Brennkammer", "Bequem für vier bis sechs Personen"]'::jsonb, '["/static/images/model-x.jpg", "/static/images/interior-2.jpg", "/static/images/stove.jpg", "/static/images/wood.jpg"]'::jsonb, true, 2, 1, 'Holzofen
Halbmondfenster
Grundausstattung Brennholz
Aufbau und Abholung', 'Handtücher
Zusätzliches Kaminholz
Bio-Aufguss
Endreinigung'),
  (3, 'model-xl', 'Model XL', 'Das Premium-Erlebnis', 'Premium Space', 14900, 6, 8, 'gross', '[{"icon": "users", "label": "6–8 Pers."}, {"icon": "bolt", "label": "Elektro/Holz"}, {"icon": "door", "label": "Vorraum"}]'::jsonb, '[{"icon": "users", "label": "Kapazität", "value": "Bis zu 8 Personen"}, {"icon": "eye", "label": "Aussicht", "value": "Panorama-Fenster"}, {"icon": "flame", "label": "Technik", "value": "Premium Bio-Ofen"}]'::jsonb, 'Unsere größte mobile Wohlfühloase. Entwickelt für maximale Entspannung in der Natur, ohne Kompromisse bei Design und Komfort einzugehen. Ausgestattet mit modernster Heiztechnik und rahmenlosem Panoramablick.', 'Handwerkskunst trifft auf Natur', 'Jedes Model XL wird in präziser Handarbeit aus nachhaltigem Thermoholz gefertigt. Dieses spezielle Behandlungsverfahren garantiert nicht nur eine außergewöhnliche Langlebigkeit und Witterungsbeständigkeit, sondern verleiht dem Holz auch seinen charakteristischen, tiefen Duft, der das Spa-Erlebnis abrundet.', '["Autarke Stromversorgung über integrierte Batterie für grenzenlose Freiheit", "Indirekte, dimmbare LED-Innenbeleuchtung für die perfekte Atmosphäre", "Inklusive hochwertigem Aufguss-Set, ätherischen Ölen und Brennholz"]'::jsonb, '["/static/images/model-xl.jpg", "/static/images/interior.jpg", "/static/images/relax.jpg", "/static/images/stove.jpg"]'::jsonb, true, 3, 1, 'Elektro- oder Holzofen
Vorraum
Panorama-Fenster
Aufbau und Abholung', 'Premium-Handtücher
Zusätzliches Kaminholz
Bio-Aufguss
VIP-Endreinigung'),
  (4, 'model-panorama', 'Model Panorama', 'Der Glas-Pavillon', 'Exklusiv', 17900, 4, 6, 'gross', '[{"icon": "users", "label": "4–6 Pers."}, {"icon": "flame", "label": "Holzofen"}, {"icon": "window", "label": "Vollglas"}]'::jsonb, '[{"icon": "users", "label": "Kapazität", "value": "Bis zu 6 Personen"}, {"icon": "eye", "label": "Aussicht", "value": "Vollglas"}, {"icon": "flame", "label": "Technik", "value": "Holzofen"}]'::jsonb, 'Eine Fasssauna mit vollverglaster Front. Der Himmel bleibt sichtbar, die Wärme bleibt drinnen. Für Abende, an denen der Ort genauso wichtig ist wie die Hitze.', 'Nacht, Glas und Glut', 'Model Panorama öffnet die Stirnseite fast vollständig zum Glas. Drinnen bleibt das Thermoholz, draußen Schnee, See oder Garten. Der Holzofen liefert die tiefe, trockene Hitze, die eine Fasssauna ausmacht.', '["Vollglasfront ohne störenden Rahmen", "Holzofen für tiefe, trockene Hitze", "Exklusive Ausstattung für vier bis sechs Personen"]'::jsonb, '["/static/images/model-panorama.jpg", "/static/images/relax.jpg", "/static/images/interior-2.jpg", "/static/images/wood.jpg"]'::jsonb, true, 4, 1, 'Holzofen
Vollglasfront
Grundausstattung Brennholz
Aufbau und Abholung', 'Handtücher
Zusätzliches Kaminholz
Endreinigung')
ON CONFLICT (id) DO NOTHING;
--> statement-breakpoint
INSERT INTO extras (id, slug, name, description, price_cents, kind, image, active, sort_order) VALUES
  (1, 'premium-handtuecher', 'Premium Handtücher', '2x extra große, extrem saugfähige Saunatücher (100×220 cm) aus 100% zertifizierter Bio-Baumwolle.', 2500, 'miete', '/static/images/towels.jpg', true, 1),
  (2, 'extra-kaminholz', 'Extra Kaminholz', 'Ein zusätzlicher Korb kammergetrocknetes Buchenholz (ca. 12 kg) für besonders lange und heiße Saunaabende.', 1500, 'kauf', '/static/images/firewood.jpg', true, 2),
  (3, 'bio-aufguss', 'Bio-Aufguss Set', 'Kuratiertes Set aus 3 naturreinen ätherischen Ölen (Nordische Kiefer, Eukalyptus, Zitrus) in Apothekerflaschen.', 3500, 'kauf', '/static/images/oils.jpg', true, 3),
  (4, 'vip-endreinigung', 'VIP Endreinigung', 'Lehnen Sie sich zurück. Wir übernehmen die komplette, professionelle Endreinigung und Desinfektion nach der Nutzung.', 6000, 'service', '', true, 4)
ON CONFLICT (id) DO NOTHING;
--> statement-breakpoint
SELECT setval(pg_get_serial_sequence('zones', 'id'), (SELECT COALESCE(MAX(id), 1) FROM zones));
--> statement-breakpoint
SELECT setval(pg_get_serial_sequence('models', 'id'), (SELECT COALESCE(MAX(id), 1) FROM models));
--> statement-breakpoint
SELECT setval(pg_get_serial_sequence('extras', 'id'), (SELECT COALESCE(MAX(id), 1) FROM extras));
