const { createClient } = require('@libsql/client');
const fs = require('fs');
const path = require('path');

const TURSO_URL = 'libsql://rentsite-stanislavzubko.aws-eu-west-1.turso.io';
const TURSO_TOKEN = 'eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJleHAiOjE4MjM2MjM5NTksImlhdCI6MTc5MjA4Nzk1OSwiaWQiOiIwMWExNDBjMy1mNDAxLTcxNzgtYmJmOC1iOTFhZDJkZmMxNTIiLCJraWQiOiJyVlNETS0xc294U1UzZ3lWV2tWNEYtNzFyQzNZdmFtRm1GN215b0VySlZZIiwicmlkIjoiMzAyZWQ4ZmQtZTU1YS00Yzk4LWI3NTctNTUzNmU2YTJmYmMxIn0.mxXnfB35SnA-iG4vn-FaTjNmz6WR1iJ10_MnnAuD_N3692_BNkmwaAgSseFvlDCGwYzE-QqNlaote-5RpJsYAw';

const db = createClient({ url: TURSO_URL, authToken: TURSO_TOKEN });

const models = [
  {
    id: 1,
    slug: 'badefass',
    name: 'Amphora-Spa Badefass',
    subtitle: 'Mobiles Badefass Hot Tub mit Hydro- & Airbubble-Massage',
    badge: 'Bestseller Wellness',
    price_cents: 8500,
    capacity_min: 2,
    capacity_max: 6,
    size: 'mittel',
    features: [
      { icon: 'spark', label: 'Hydro & Air Massage' },
      { icon: 'flame', label: 'Außenofen Holz' },
      { icon: 'users', label: 'Bis zu 6 Pers.' },
      { icon: 'leaf', label: 'LED Beleuchtung' }
    ],
    specs: [
      { icon: 'users', label: 'Kapazität', value: 'Bis zu 6 Personen' },
      { icon: 'spark', label: 'Massagesysteme', value: 'Hydro- & Airbubble-Massage' },
      { icon: 'flame', label: 'Heizung', value: 'Außenstehender Holzofen auf Anhänger' },
      { icon: 'leaf', label: 'Licht', value: 'LED Innen- & Außenbeleuchtung' },
      { icon: 'truck', label: 'Lieferung', value: '1 € / km oder Selbstabholung' },
      { icon: 'spark', label: 'Kaution', value: '300 € bar bei Übergabe' }
    ],
    summary: 'Tauche ein in eine Welt voller Erholung und entspanne in einem heißen Bad unter freiem Himmel zusammen mit Partner, Freunden oder der Familie. Mit dem mobilen Amphora-Spa Badefass holst du dir dein Wellnesserlebnis direkt in den Garten.',
    story_title: 'Heißes Bad unter freiem Himmel.',
    story: 'Unser mobiles Amphora-Spa Badefass bietet maximalen Komfort für ca. 6 Personen dank des außenstehenden Holzofens auf dem Anhänger. Ausgestattet mit kraftvollen Hydro- und Airbubble-Massagedüsen sowie stimmungsvoller LED-Atmosphärenbeleuchtung. Wochentags 85 €, Feiertage 95 €, Wochenende (Fr–So) 250 €. Alles was du brauchst, ist ein Wasseranschluss, Gartenschlauch und Brennholz.',
    highlights: [
      'Außenstehender Holzofen – maximaler Sitzkomfort für 6 Personen',
      'Hydro-Massage & Airbubble-Massage für pure Tiefenentspannung',
      'LED-Atmosphären Außenbeleuchtung & LED Innenbeleuchtung mit Farbwechsel',
      'Mietvertrag & gründliche Einweisung inklusive',
      'Lieferung (1 €/km) oder kostenlose Selbstabholung mit PKW-Führerschein BE'
    ],
    images: Array.from({ length: 16 }, (_, i) => `/static/uploads/badefass-${i + 1}.jpg`),
    sort_order: 1,
    units: 1,
    included_text: 'Badefass komplett montiert auf PKW-Anhänger\nThermo-Isolierabdeckung für schnelles Aufheizen\nMassagedüsen und LED-Beleuchtungssystem\nAusführliche Einweisung und Mietvertrag',
    excluded_text: 'Brennholz (optional 10 € je Kiste)\nWasseranschluss / Gartenschlauch zum Befüllen\nKaution: 300 € bar bei Übergabe'
  },
  {
    id: 2,
    slug: 'kombi-sauna-badefass',
    name: 'Amphora-Spa Kombi',
    subtitle: 'Fasssauna & Badefass Hot Tub auf Tandem-Anhänger',
    badge: 'Das ultimative Spa',
    price_cents: 10000,
    capacity_min: 4,
    capacity_max: 10,
    size: 'gross',
    features: [
      { icon: 'users', label: 'Sauna 4 + Fass 6' },
      { icon: 'flame', label: 'Holzofen & Hot Tub' },
      { icon: 'leaf', label: 'Premium Thermoholz' },
      { icon: 'spark', label: 'Licht & Massage' }
    ],
    specs: [
      { icon: 'users', label: 'Kapazität', value: 'Sauna bis 4 Pers., Badefass bis 6 Pers.' },
      { icon: 'leaf', label: 'Material', value: 'Hochwertiges Thermoholz' },
      { icon: 'flame', label: 'Heiztechnik', value: 'Holzofen für Sauna und Badefass' },
      { icon: 'spark', label: 'Ausstattung', value: 'Stromanschluss, Licht und Whirlpool-Düsen' },
      { icon: 'truck', label: 'Lieferung', value: '2 € je Kilometer oder Selbstabholung' },
      { icon: 'spark', label: 'Kaution', value: '300 € bei Übergabe in bar' }
    ],
    summary: 'Hochwertiges Saunafass aus nachhaltigem Thermoholz kombiniert mit einem Hot Tub Badefass auf einem gemeinsamen mobilen Tandem-Anhänger. Das vollendete Spa-Erlebnis für Partys, Feiern und Familie.',
    story_title: 'Saunieren & Baden in perfekter Harmonie.',
    story: 'Der Amphora-Spa Kombi-Anhänger vereint eine vollwertige Fasssauna mit einem beheizbaren Hot Tub Badefass. Die Sauna bietet bis zu 4 Personen Platz für wohltuende Aufgüsse, während im Badefass bis zu 6 Personen im heißen Wasser entspannen. Wochentags 120 €, Feiertage 150 €, Wochenende (Fr–So) 320 €. Unvergessliche Wellness direkt bei dir zu Hause.',
    highlights: [
      'Kombinierte Fasssauna (4 Pers.) und Hot Tub Badefass (6 Pers.) auf einem Anhänger',
      'Hochwertiges Thermoholz für optimale Wärmedämmung und angenehmen Duft',
      'Schwitzraum mit sicherem Holzofen und Glas-Tür',
      'Whirlpool-Funktion, Innenbeleuchtung und Thermo-Abdeckung',
      'Lieferung (2 €/km) oder Selbstabholung mit Führerschein BE'
    ],
    images: Array.from({ length: 16 }, (_, i) => `/static/uploads/kombi-${i + 1}.jpg`),
    sort_order: 2,
    units: 1,
    included_text: 'Kombi-Anhänger mit betriebsbereiter Sauna und Badefass\nHolzofen mit Saunasteinen\nWhirlpool-Düsen und Beleuchtung\nEinweisung und Mietvertrag',
    excluded_text: 'Brennholz (optional 10 € je Kiste)\nWasseranschluss / Gartenschlauch\nKaution: 300 € bar bei Übergabe'
  },
  {
    id: 3,
    slug: 'fasssauna-panorama',
    name: 'Amphora-Spa Panoramasauna',
    subtitle: 'Mobile Fasssauna mit Relax-Vorraum auf Anhänger',
    badge: 'Panorama & Vorraum',
    price_cents: 9000,
    capacity_min: 2,
    capacity_max: 6,
    size: 'mittel',
    features: [
      { icon: 'users', label: 'Bis zu 6 Pers.' },
      { icon: 'window', label: 'Panoramafenster' },
      { icon: 'door', label: 'Separater Vorraum' },
      { icon: 'flame', label: 'Harvia Holzofen' }
    ],
    specs: [
      { icon: 'users', label: 'Kapazität', value: 'Bis zu 6 Personen' },
      { icon: 'door', label: 'Räume', value: 'Schwitzraum & separater Vorraum (Relaxraum)' },
      { icon: 'window', label: 'Aussicht', value: 'Großes Panorama-Halbmondfenster' },
      { icon: 'leaf', label: 'Material', value: 'Nachhaltiges Thermoholz' },
      { icon: 'truck', label: 'Lieferung', value: '2 € je Kilometer oder Selbstabholung' },
      { icon: 'spark', label: 'Kaution', value: '300 € bar bei Übergabe' }
    ],
    summary: 'Hochwertige mobile Fasssauna aus nachhaltigem Thermoholz mit Schwitzraum und separatem Relax-Vorraum. Platz für bis zu 6 Personen, Stromanschluss, LED-Beleuchtung und atemberaubender Panorama-Ausblick.',
    story_title: 'Entspannung pur mit Weitblick und Relaxraum.',
    story: 'Unsere Amphora-Spa Panoramasauna bietet zwei separate Räume: Einen wettergeschützten Vorraum zum Umkleiden und Ausruhen sowie den geräumigen Schwitzraum mit Panoramafenster. Der kräftige Harvia-Holzofen sorgt für authentische finnische Hitze. Wochentags 90 €, Feiertage 100 €, Wochenende (Fr–So) 270 €.',
    highlights: [
      'Zwei Räume: Schwitzraum plus separater Relax- und Umkleidevorraum',
      'Großes Panorama-Halbmondfenster für traumhafte Ausblicke',
      'Harvia Holzofen mit Saunasteinen für intensive Aufgüsse',
      'Stimmungsvolle LED-Beleuchtung und 230V-Stromanschluss',
      'Lieferung (2 €/km) oder kostenlose Selbstabholung mit Klasse BE'
    ],
    images: Array.from({ length: 19 }, (_, i) => `/static/uploads/fasssauna-${i + 1}.jpg`),
    sort_order: 3,
    units: 1,
    included_text: 'Panoramasauna mit 2 Räumen fertig auf Anhänger\nHarvia Holzofen mit Saunasteinen\nAufgusseimer, Holzkelle und Sanduhr\nEinweisung und Mietvertrag',
    excluded_text: 'Brennholz (optional 10 € je Kiste)\nKaution: 300 € bar bei Übergabe'
  }
];

const extras = [
  {
    slug: 'brennholz',
    name: 'Brennholz Kiste',
    description: 'Sauber verpacktes, ofenfertig getrocknetes Hartholz für Sauna oder Hot Tub (ca. 10 kg).',
    price_cents: 1000,
    kind: 'kauf',
    image: '/static/images/firewood.jpg',
    sort_order: 1
  },
  {
    slug: 'bio-aufguss',
    name: 'Bio-Aufguss Öle Set',
    description: 'Set aus 3 naturreinen ätherischen Ölen (Nordische Kiefer, Eukalyptus, Zitrus) für aromatische Aufgüsse.',
    price_cents: 1500,
    kind: 'kauf',
    image: '/static/images/oils.jpg',
    sort_order: 2
  },
  {
    slug: 'endreinigung',
    name: 'Endreinigung & Desinfektion',
    description: 'Lehnen Sie sich zurück: Wir übernehmen die komplette fachgerechte Innen- und Außenreinigung sowie Desinfektion.',
    price_cents: 3000,
    kind: 'service',
    image: '',
    sort_order: 3
  }
];

const zones = [
  { name: 'Zone A (Selbstabholung)', prefixes: '14929,14532,10,12,13,14', cities: 'treuenbrietzen,kleinmachnow,berlin', price_cents: 0, note: 'Kostenlose Selbstabholung in Treuenbrietzen oder Nahbereich Berlin', sort_order: 1 },
  { name: 'Zone B (Lieferung Umland)', prefixes: '144,145,146,147,149,15,16,17,18,19', cities: 'potsdam,brandenburg,ludwigsfelde,teltow', price_cents: 5000, note: 'Lieferung Berlin & näheres Umland, 50 € Pauschale', sort_order: 2 },
  { name: 'Zone C (Lieferung Weitbereich)', prefixes: '*', cities: 'leipzig,dresden,magdeburg', price_cents: 9000, note: 'Lieferung Brandenburg & Weitbereich, 90 € Pauschale', sort_order: 3 }
];

const settings = {
  company_name: 'Amphora-Spa',
  owner_name: 'Amphora-Spa Berlin-Brandenburg',
  street: 'Tiefenbrunnen 1',
  postal_code: '14929',
  city: 'Treuenbrietzen',
  email: 'info@amphora-spa.de',
  phone: '+49 176 2033 1535',
  deposit_cents: '30000',
  hero_kicker: 'Amphora-Spa Berlin-Brandenburg',
  hero_title: 'Mobile Wellness auf Rädern\nFasssauna & Badefass',
  hero_lede: 'Hot Tubs & Fasssaunen direkt an deinen Wunschort geliefert oder zur flexiblen Selbstabholung in Treuenbrietzen.',
  hero_image: '/static/uploads/fasssauna-1.jpg',
  fleet_title: 'Unsere Flotte',
  fleet_text: 'Mobiles Badefass mit Whirlpool, Fasssauna mit Vorraum oder das exklusive Kombi-Spa auf einem Anhänger.',
  fleet_page_title: 'Wähle dein mobiles Wellness-Erlebnis.',
  fleet_page_text: 'Luxuriöse Fasssaunen aus nachhaltigem Thermoholz und beheizbare Badefässer mit Massage. Berlin & Brandenburg.',
  prices_title: 'Faire Tagessätze & transparente Wochenendpreise.',
  prices_text: 'Wochentags ab 85 €, Wochenende (Fr–So) ab 250 €. Kostenlose Selbstabholung in Treuenbrietzen oder bequeme Lieferung (1–2 €/km). Alle Preise inkl. 19% MwSt.',
  how_kicker: 'So einfach geht\'s',
  how_title: 'In drei Schritten zu deinem privaten Spa.',
  how_lede: 'Modell wählen, Zeitraum festlegen, Lieferung an Wunschort oder kostenlose Selbstabholung wählen.',
  contact_title: 'Kontaktiere uns.',
  contact_text: 'Fragen zu Miete, Kauf oder Verfügbarkeit. Telefon, WhatsApp & Telegram: +49 176 2033 1535 oder +49 176 4164 4019.',
  footer_line: 'Amphora-Spa · Mobile Fasssauna & Badefass Mieten und Kaufen.',
  points_json: JSON.stringify([
    { icon: 'leaf', title: 'Premium Thermoholz', text: 'Hochwertiges, nachhaltiges Thermoholz für optimale Wärmedämmung und puren Saunaduft.' },
    { icon: 'truck', title: 'Lieferung & Abholung', text: 'Bequeme Lieferung direkt zu dir nach Hause oder kostenlose Selbstabholung in Treuenbrietzen.' },
    { icon: 'spark', title: 'Hydro- & Air-Massage', text: 'Leistungsstarke Whirlpool-Massagedüsen und stimmungsvolle LED-Beleuchtung im Hot Tub.' }
  ]),
  steps_json: JSON.stringify([
    { title: 'Auswählen', text: 'Wähle dein Wunschmodell (Badefass, Panoramasauna oder Kombi) und den Zeitraum. Preis und Verfügbarkeit siehst du sofort.', image: '/static/uploads/badefass-1.jpg' },
    { title: 'Lieferung oder Abholung', text: 'Wir bringen die Sauna an deinen Wunschort oder du holst den Anhänger kostenlos in Treuenbrietzen ab (PKW mit Führerschein BE).', image: '/static/uploads/kombi-1.jpg' },
    { title: 'Entspannen & Genießen', text: 'Lehne dich zurück und genieße dein privates Spa-Erlebnis unter freiem Himmel. Nach Ablauf holen wir die Sauna wieder ab.', image: '/static/uploads/fasssauna-1.jpg' }
  ]),
  faq_json: JSON.stringify([
    { q: 'Wie wird der Preis berechnet?', a: 'Tagessatz mal Nächte, plus eventuelle Lieferung (0 € bei Selbstabholung), plus Extras und die Kaution von 300 € (in bar bei Übergabe). Die MwSt. von 19% ist enthalten.' },
    { q: 'Was kostet die Lieferung?', a: 'Kostenlose Selbstabholung ab Treuenbrietzen (14929). Bei Lieferung berechnen wir je nach Modell 1 bis 2 Euro pro gefahrenem Kilometer.' },
    { q: 'Was benötige ich für die Selbstabholung?', a: 'Ein Auto mit Anhängerkupplung sowie einen PKW-Führerschein der Klasse BE. Der Anhänger ist vollständig zugelassen und betriebsbereit.' },
    { q: 'Was brauche ich vor Ort?', a: 'Für das Badefass einen normalen Gartenschlauch mit Wasseranschluss und Brennholz. Für Sauna und Beleuchtung genügt eine normale 230V Steckdose.' },
    { q: 'Gibt es Brennholz dazu?', a: 'Optional bieten wir trockenes, sauberes Kaminholz für 10,00 € je Kiste an.' },
    { q: 'Wie hoch ist die Kaution?', a: 'Die Kaution beträgt 300 € bei Übergabe in bar und wird bei ordnungsgemäßer Rückgabe sofort erstattet.' }
  ])
};

async function syncTurso() {
  console.log('Connecting to Turso...');
  
  // Ensure delivery_type column exists
  try {
    await db.execute("ALTER TABLE bookings ADD COLUMN delivery_type TEXT NOT NULL DEFAULT 'delivery'");
    console.log('Added delivery_type column to Turso bookings');
  } catch (_e) {
    // already exists
  }

  // Settings
  for (const [key, val] of Object.entries(settings)) {
    await db.execute({
      sql: 'INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value',
      args: [key, val]
    });
  }
  console.log('Updated Turso settings');

  // Models
  await db.execute('DELETE FROM models');
  for (const m of models) {
    await db.execute({
      sql: `INSERT INTO models (
        id, slug, name, subtitle, badge, price_cents, capacity_min, capacity_max, size,
        features_json, specs_json, summary, story_title, story, highlights_json,
        images_json, active, sort_order, units, included_text, excluded_text
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)`,
      args: [
        m.id, m.slug, m.name, m.subtitle, m.badge, m.price_cents,
        m.capacity_min, m.capacity_max, m.size,
        JSON.stringify(m.features), JSON.stringify(m.specs),
        m.summary, m.story_title, m.story,
        JSON.stringify(m.highlights), JSON.stringify(m.images),
        m.sort_order, m.units, m.included_text, m.excluded_text
      ]
    });
  }
  console.log('Updated Turso models');

  // Extras
  await db.execute('DELETE FROM extras');
  for (const e of extras) {
    await db.execute({
      sql: `INSERT INTO extras (slug, name, description, price_cents, kind, image, active, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)`,
      args: [e.slug, e.name, e.description, e.price_cents, e.kind, e.image, e.sort_order]
    });
  }
  console.log('Updated Turso extras');

  // Zones
  await db.execute('DELETE FROM zones');
  for (const z of zones) {
    await db.execute({
      sql: `INSERT INTO zones (name, prefixes, cities, price_cents, note, active, sort_order)
            VALUES (?, ?, ?, ?, ?, 1, ?)`,
      args: [z.name, z.prefixes, z.cities, z.price_cents, z.note, z.sort_order]
    });
  }
  console.log('Updated Turso zones');

  // Update existing bookings
  await db.execute("UPDATE bookings SET model_name = 'Amphora-Spa Panoramasauna', model_slug = 'fasssauna-panorama', model_id = 3, delivery_type = 'delivery' WHERE id = 1");
  await db.execute("UPDATE bookings SET model_name = 'Amphora-Spa Kombi', model_slug = 'kombi-sauna-badefass', model_id = 2, delivery_type = 'pickup', address = 'Tiefenbrunnen 1, 14929 Treuenbrietzen (Selbstabholung)', lat = 52.0911, lng = 12.8711, delivery_cents = 0 WHERE id = 2");
  await db.execute("UPDATE bookings SET model_name = 'Amphora-Spa Badefass', model_slug = 'badefass', model_id = 1, delivery_type = 'delivery' WHERE id = 3");
  console.log('Updated Turso bookings');

  console.log('Turso cloud sync complete!');
}

syncTurso().catch(console.error);
