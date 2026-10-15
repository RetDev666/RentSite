const { createClient } = require('C:/SRC/glanz-groom/node_modules/@libsql/client');

const TURSO_URL = 'libsql://rentsite-stanislavzubko.aws-eu-west-1.turso.io';
const TURSO_TOKEN = 'eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJleHAiOjE4MjM2MjM5NTksImlhdCI6MTc5MjA4Nzk1OSwiaWQiOiIwMWExNDBjMy1mNDAxLTcxNzgtYmJmOC1iOTFhZDJkZmMxNTIiLCJraWQiOiJyVlNETS0xc294U1UzZ3lWV2tWNEYtNzFyQzNZdmFtRm1GN215b0VySlZZIiwicmlkIjoiMzAyZWQ4ZmQtZTU1YS00Yzk4LWI3NTctNTUzNmU2YTJmYmMxIn0.mxXnfB35SnA-iG4vn-FaTjNmz6WR1iJ10_MnnAuD_N3692_BNkmwaAgSseFvlDCGwYzE-QqNlaote-5RpJsYAw';

async function main() {
  console.log("Connecting to Turso: " + TURSO_URL);
  const db = createClient({ url: TURSO_URL, authToken: TURSO_TOKEN });

  const schemaStatements = [
    `CREATE TABLE IF NOT EXISTS settings (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    )`,
    `CREATE TABLE IF NOT EXISTS admins (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      password_hash TEXT NOT NULL
    )`,
    `CREATE TABLE IF NOT EXISTS models (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    )`,
    `CREATE TABLE IF NOT EXISTS extras (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      slug TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      description TEXT NOT NULL,
      price_cents INTEGER NOT NULL,
      kind TEXT NOT NULL,
      image TEXT NOT NULL DEFAULT '',
      active INTEGER NOT NULL DEFAULT 1,
      sort_order INTEGER NOT NULL DEFAULT 0
    )`,
    `CREATE TABLE IF NOT EXISTS zones (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      prefixes TEXT NOT NULL DEFAULT '',
      cities TEXT NOT NULL DEFAULT '',
      price_cents INTEGER NOT NULL,
      note TEXT NOT NULL DEFAULT '',
      active INTEGER NOT NULL DEFAULT 1,
      sort_order INTEGER NOT NULL DEFAULT 0
    )`,
    `CREATE TABLE IF NOT EXISTS bookings (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
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
      stripe_session TEXT NOT NULL DEFAULT ''
    )`,
    `CREATE TABLE IF NOT EXISTS booking_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      booking_id INTEGER NOT NULL,
      message TEXT NOT NULL,
      created_at TEXT NOT NULL
    )`,
    `CREATE TABLE IF NOT EXISTS blocks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      model_id INTEGER NOT NULL,
      start_date TEXT NOT NULL,
      end_date TEXT NOT NULL,
      reason TEXT NOT NULL DEFAULT ''
    )`,
    `CREATE TABLE IF NOT EXISTS messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL,
      phone TEXT NOT NULL DEFAULT '',
      body TEXT NOT NULL,
      read INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,
      reply TEXT NOT NULL DEFAULT '',
      replied_at TEXT NOT NULL DEFAULT ''
    )`,
    `CREATE TABLE IF NOT EXISTS vouchers (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      code TEXT UNIQUE NOT NULL,
      cents INTEGER NOT NULL,
      note TEXT NOT NULL DEFAULT '',
      active INTEGER NOT NULL DEFAULT 1,
      max_uses INTEGER NOT NULL DEFAULT 1,
      used INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL
    )`,
    `CREATE TABLE IF NOT EXISTS reviews (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      author TEXT NOT NULL,
      text TEXT NOT NULL,
      rating INTEGER NOT NULL DEFAULT 5,
      model_slug TEXT NOT NULL DEFAULT '',
      active INTEGER NOT NULL DEFAULT 1,
      sort_order INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL
    )`,
    `CREATE TABLE IF NOT EXISTS emails (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      booking_id INTEGER,
      recipient TEXT NOT NULL,
      subject TEXT NOT NULL,
      body TEXT NOT NULL,
      status TEXT NOT NULL,
      error TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL
    )`,
    `CREATE INDEX IF NOT EXISTS idx_bookings_model ON bookings(model_id, start_date)`,
    `CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status)`,
    `CREATE INDEX IF NOT EXISTS idx_bookings_email ON bookings(email)`,
    `CREATE INDEX IF NOT EXISTS idx_blocks_model ON blocks(model_id, start_date)`,
    `CREATE INDEX IF NOT EXISTS idx_emails_booking ON emails(booking_id)`,
  ];

  for (const sql of schemaStatements) {
    await db.execute(sql);
  }
  console.log("Schema created successfully.");

  // Settings
  const settings = [
    ["company_name", "Saunacore"],
    ["owner_name", "Saunacore GmbH"],
    ["street", "Musterstraße 1"],
    ["postal_code", "10115"],
    ["city", "Berlin"],
    ["email", "hallo@saunacore.de"],
    ["phone", "+49 30 12001890"],
    ["vat_id", "DE123456789"],
    ["vat_percent", "19"],
    ["min_nights", "1"],
    ["max_nights", "21"],
    ["cancellation_days", "7"],
    ["hero_title", "Premium Sauna\\non Demand"],
    ["hero_lede", "Deine private Sauna. Geliefert. Wo und wann du willst."],
    ["hero_image", "/static/images/hero.jpg"],
    ["fleet_title", "Unsere Flotte"],
    ["fleet_text", "Exklusive Modelle für jedes Bedürfnis. Höchste Qualität, kompromissloses Design."],
    ["how_title", "Drei Schritte bis zur eigenen Sauna."],
    ["how_lede", "Modell wählen, Termin festlegen, Markierung setzen, geliefert bekommen."],
    ["prices_title", "Klare Tagessätze, Lieferung nach Zone."],
  ];

  for (const [k, v] of settings) {
    await db.execute({
      sql: `INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value`,
      args: [k, v]
    });
  }

  // Admin (hash for SaunaAdmin2026!)
  // Python: secrets.token_bytes(16) + hashlib.scrypt(..., n=16384, r=8, p=1, dklen=32)
  const crypto = require('crypto');
  const salt = crypto.randomBytes(16);
  const key = crypto.scryptSync('SaunaAdmin2026!', salt, 32, { N: 16384, r: 8, p: 1 });
  const hash = salt.toString('hex') + ':' + key.toString('hex');

  await db.execute({
    sql: `INSERT INTO admins (email, name, password_hash) VALUES (?, ?, ?)
          ON CONFLICT(email) DO UPDATE SET password_hash = excluded.password_hash`,
    args: ['admin@saunacore.de', 'Saunacore Admin', hash]
  });

  // Zones
  const zones = [
    ["Zone A", "10,12,13,14", "berlin", 0, "Berlin, kostenlos", 1],
    ["Zone B", "144,145,146,147,149,15,16,17,18,19,01,02,03,04,06,07,08,09,39", "potsdam,leipzig,dresden,hamburg,hannover,magdeburg", 5000, "Umland und ausgewählte Städte, 50 €", 2],
    ["Zone C", "*", "muenchen,münchen,munich,koeln,köln,frankfurt,stuttgart,duesseldorf,düsseldorf,nuernberg,nürnberg,bremen", 9000, "Übriges Deutschland mit fünfstelliger PLZ, 90 €", 3]
  ];

  for (const [name, prefixes, cities, price, note, sort] of zones) {
    await db.execute({
      sql: `INSERT INTO zones (name, prefixes, cities, price_cents, note, active, sort_order)
            VALUES (?, ?, ?, ?, ?, 1, ?)`,
      args: [name, prefixes, cities, price, note, sort]
    });
  }

  // Models
  const models = [
    {
      slug: "model-s",
      name: "Model S",
      subtitle: "Die kompakte Fasssauna",
      badge: "Kompakt",
      price_cents: 8900,
      capacity_min: 2,
      capacity_max: 4,
      size: "kompakt",
      features: [
        { icon: "users", label: "2–4 Pers." },
        { icon: "flame", label: "Holzofen" },
        { icon: "window", label: "Türfenster" }
      ],
      specs: [
        { icon: "users", label: "Kapazität", value: "Bis zu 4 Personen" },
        { icon: "eye", label: "Aussicht", value: "Türfenster" },
        { icon: "flame", label: "Technik", value: "Holzofen" }
      ],
      summary: "Unsere kompakte Fasssauna für zwei bis vier Personen. Thermoholz, Holzofen und ein türhohes Fenster — schnell aufgestellt, ruhig im Charakter.",
      story_title: "Klein. Warm. Vollständig.",
      story: "Model S wird in Handarbeit aus nachhaltigem Thermoholz gefertigt. Das türhohe Fenster hält den Blick nach draußen offen, der Ofen trägt die Hitze gleichmäßig.",
      highlights: ["Holzofen mit langer Glut für gleichmäßige Hitze", "Türfenster mit Blick ins Freie", "Kompaktes Maß für kleinere Gärten"],
      images: ["/static/images/model-s.jpg", "/static/images/interior.jpg", "/static/images/wood.jpg", "/static/images/stove.jpg"],
      sort_order: 1
    },
    {
      slug: "model-x",
      name: "Model X",
      subtitle: "Der Bestseller",
      badge: "Bestseller",
      price_cents: 11900,
      capacity_min: 4,
      capacity_max: 6,
      size: "mittel",
      features: [
        { icon: "users", label: "4–6 Pers." },
        { icon: "flame", label: "Holzofen" },
        { icon: "window", label: "Halbmond" }
      ],
      specs: [
        { icon: "users", label: "Kapazität", value: "Bis zu 6 Personen" },
        { icon: "eye", label: "Aussicht", value: "Halbmond-Fenster" },
        { icon: "flame", label: "Technik", value: "Holzofen" }
      ],
      summary: "Die meistgebuchte Fasssauna. Platz für vier bis sechs Personen, ein halbrundes Fenster und ein Ofen, der den Abend trägt.",
      story_title: "Der Abend gehört euch.",
      story: "Model X verbindet kompakte Logistik mit genug Raum für einen ganzen Freundeskreis. Das Halbmondfenster legt einen warmen Bogen ins Holz.",
      highlights: ["Halbmond-Fenster für weiches Licht", "Holzofen mit großer Brennkammer", "Bequem für vier bis sechs Personen"],
      images: ["/static/images/model-x.jpg", "/static/images/interior-2.jpg", "/static/images/stove.jpg", "/static/images/wood.jpg"],
      sort_order: 2
    },
    {
      slug: "model-xl",
      name: "Model XL",
      subtitle: "Das Premium-Erlebnis",
      badge: "Premium Space",
      price_cents: 14900,
      capacity_min: 6,
      capacity_max: 8,
      size: "gross",
      features: [
        { icon: "users", label: "6–8 Pers." },
        { icon: "bolt", label: "Elektro/Holz" },
        { icon: "door", label: "Vorraum" }
      ],
      specs: [
        { icon: "users", label: "Kapazität", value: "Bis zu 8 Personen" },
        { icon: "eye", label: "Aussicht", value: "Panorama-Fenster" },
        { icon: "flame", label: "Technik", value: "Premium Bio-Ofen" }
      ],
      summary: "Unsere größte mobile Wohlfühloase. Entwickelt für maximale Entspannung in der Natur, ohne Kompromisse bei Design und Komfort einzugehen.",
      story_title: "Handwerkskunst trifft auf Natur",
      story: "Jedes Model XL wird in präziser Handarbeit aus nachhaltigem Thermoholz gefertigt. Dieses spezielle Behandlungsverfahren garantiert Langlebigkeit.",
      highlights: ["Autarke Stromversorgung über Batterie", "Dimmbare LED-Innenbeleuchtung", "Inklusive Aufguss-Set und Brennholz"],
      images: ["/static/images/model-xl.jpg", "/static/images/interior.jpg", "/static/images/relax.jpg", "/static/images/stove.jpg"],
      sort_order: 3
    }
  ];

  for (const m of models) {
    await db.execute({
      sql: `INSERT INTO models (
              slug, name, subtitle, badge, price_cents, capacity_min, capacity_max, size,
              features_json, specs_json, summary, story_title, story, highlights_json,
              images_json, active, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            ON CONFLICT(slug) DO UPDATE SET
              name=excluded.name, price_cents=excluded.price_cents,
              summary=excluded.summary, story=excluded.story`,
      args: [
        m.slug, m.name, m.subtitle, m.badge, m.price_cents,
        m.capacity_min, m.capacity_max, m.size,
        JSON.stringify(m.features), JSON.stringify(m.specs),
        m.summary, m.story_title, m.story,
        JSON.stringify(m.highlights), JSON.stringify(m.images),
        m.sort_order
      ]
    });
  }

  // Extras
  const extras = [
    ["premium-handtuecher", "Premium Handtücher", "2x extra große Saunatücher aus 100% Bio-Baumwolle.", 2500, "miete", "/static/images/towels.jpg", 1],
    ["extra-kaminholz", "Extra Kaminholz", "Ein Korb kammergetrocknetes Buchenholz (ca. 12 kg).", 1500, "kauf", "/static/images/firewood.jpg", 2],
    ["bio-aufguss", "Bio-Aufguss Set", "Set aus 3 naturreinen ätherischen Ölen in Apothekerflaschen.", 3500, "kauf", "/static/images/oils.jpg", 3],
    ["vip-endreinigung", "VIP Endreinigung", "Komplette Endreinigung und Desinfektion nach der Nutzung.", 6000, "service", "", 4]
  ];

  for (const [slug, name, desc, price, kind, img, sort] of extras) {
    await db.execute({
      sql: `INSERT INTO extras (slug, name, description, price_cents, kind, image, active, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            ON CONFLICT(slug) DO UPDATE SET price_cents=excluded.price_cents`,
      args: [slug, name, desc, price, kind, img, sort]
    });
  }

  // Reviews
  const reviews = [
    ["Sophie & Marc", "Ein unvergessliches Wochenende an der Ostsee! Die Sauna kam pünktlich und war in wenigen Minuten heiß.", 5, "model-x", 1],
    ["Thomas B.", "Bester Service! Problemlose Anlieferung in unseren Schrebergarten. Wärmstens empfohlen.", 5, "model-s", 2],
    ["Elena K.", "Perfekt für unseren Mädelsabend. Das Panoramaglas ist einfach atemberaubend schön.", 5, "model-xl", 3]
  ];

  for (const [author, text, rating, model_slug, sort] of reviews) {
    await db.execute({
      sql: `INSERT INTO reviews (author, text, rating, model_slug, active, sort_order, created_at)
            VALUES (?, ?, ?, ?, 1, ?, datetime('now'))`,
      args: [author, text, rating, model_slug, sort]
    });
  }

  console.log("✅ Turso database seeded successfully!");
  const count = await db.execute("SELECT COUNT(*) AS c FROM models");
  console.log("Models in Turso:", count.rows[0].c);
}

main().catch(err => {
  console.error("Error seeding Turso:", err);
  process.exit(1);
});
