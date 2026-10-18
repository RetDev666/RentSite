const { createClient } = require('@libsql/client');
const crypto = require('crypto');

const TURSO_URL = process.env.TURSO_DATABASE_URL || 'libsql://rentsite-stanislavzubko.aws-eu-west-1.turso.io';
const TURSO_TOKEN = process.env.TURSO_AUTH_TOKEN || 'eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJleHAiOjE4MjM2MjM5NTksImlhdCI6MTc5MjA4Nzk1OSwiaWQiOiIwMWExNDBjMy1mNDAxLTcxNzgtYmJmOC1iOTFhZDJkZmMxNTIiLCJraWQiOiJyVlNETS0xc294U1UzZ3lWV2tWNEYtNzFyQzNZdmFtRm1GN215b0VySlZZIiwicmlkIjoiMzAyZWQ4ZmQtZTU1YS00Yzk4LWI3NTctNTUzNmU2YTJmYmMxIn0.mxXnfB35SnA-iG4vn-FaTjNmz6WR1iJ10_MnnAuD_N3692_BNkmwaAgSseFvlDCGwYzE-QqNlaote-5RpJsYAw';

const db = createClient({ url: TURSO_URL, authToken: TURSO_TOKEN });

const ADMIN_SECRET = process.env.SAUNACORE_SECRET || 'saunacore-turso-admin-secret-2026';

function verifyPassword(password, stored) {
  try {
    const [saltHex, digestHex] = stored.split(':');
    const salt = Buffer.from(saltHex, 'hex');
    const expected = Buffer.from(digestHex, 'hex');
    const digest = crypto.scryptSync(password, salt, 32, { N: 16384, r: 8, p: 1 });
    return crypto.timingSafeEqual(digest, expected);
  } catch (_e) {
    return false;
  }
}

function makeToken(email) {
  const payload = Buffer.from(JSON.stringify({ email, exp: Date.now() + 86400000 * 7 })).toString('base64');
  const sig = crypto.createHmac('sha256', ADMIN_SECRET).update(payload).digest('hex');
  return `${payload}.${sig}`;
}

function verifyToken(token) {
  if (!token) return null;
  const parts = token.split('.');
  if (parts.length !== 2) return null;
  const [payload, sig] = parts;
  const expectedSig = crypto.createHmac('sha256', ADMIN_SECRET).update(payload).digest('hex');
  if (sig !== expectedSig) return null;
  try {
    const data = JSON.parse(Buffer.from(payload, 'base64').toString('utf8'));
    if (data.exp < Date.now()) return null;
    return data;
  } catch (_e) {
    return null;
  }
}

exports.handler = async (event) => {
  const path = (event.path || '').replace(/^.*\/api\/?/, '');
  const method = event.httpMethod || 'GET';
  const params = event.queryStringParameters || {};
  const reqHeaders = event.headers || {};
  const authHeader = reqHeaders.authorization || reqHeaders.Authorization || '';
  const token = authHeader.replace(/^Bearer\s+/i, '') || params.token || '';

  const headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-CSRFToken',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  };

  if (method === 'OPTIONS') {
    return { statusCode: 204, headers, body: '' };
  }

  try {
    // -------------------------------------------------------------
    // GET /api/busy
    // -------------------------------------------------------------
    if (path.startsWith('busy')) {
      const modelId = parseInt(params.model_id, 10);
      const res = await db.execute({
        sql: `SELECT start_date, end_date FROM bookings WHERE model_id = ? AND status != 'cancelled'`,
        args: [isNaN(modelId) ? 1 : modelId],
      });
      const busy = [];
      for (const row of res.rows) {
        let cur = new Date(row.start_date);
        const end = new Date(row.end_date);
        while (cur < end) {
          busy.push(cur.toISOString().slice(0, 10));
          cur.setDate(cur.getDate() + 1);
        }
      }
      return { statusCode: 200, headers, body: JSON.stringify({ ok: true, busy }) };
    }

    // -------------------------------------------------------------
    // GET /api/zone
    // -------------------------------------------------------------
    if (path.startsWith('zone')) {
      const q = (params.q || '').trim().toLowerCase();
      const res = await db.execute(`SELECT * FROM zones WHERE active = 1 ORDER BY sort_order`);
      let found = null;
      for (const z of res.rows) {
        const cities = (z.cities || '').toLowerCase().split(',').map((s) => s.trim());
        const prefixes = (z.prefixes || '').split(',').map((s) => s.trim());
        if (cities.includes(q) || prefixes.some((p) => p && q.startsWith(p))) {
          found = z;
          break;
        }
      }
      if (!found && res.rows.length > 0) {
        found = res.rows[res.rows.length - 1]; // fallback to last zone
      }
      const price = found ? Number(found.price_cents) : 0;
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          ok: true,
          name: found ? found.name : 'Standard',
          badge: found ? (price === 0 ? `${found.name} (kostenlos)` : `${found.name} (${(price / 100).toFixed(2).replace('.', ',')} €)`) : '',
          price_cents: price,
          price: price === 0 ? 'kostenlos' : `${(price / 100).toFixed(2).replace('.', ',')} €`,
          free: price === 0,
        }),
      };
    }

    // -------------------------------------------------------------
    // GET /api/reverse
    // -------------------------------------------------------------
    if (path.startsWith('reverse')) {
      const lat = parseFloat(params.lat) || 52.52;
      const lng = parseFloat(params.lng) || 13.405;
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          ok: true,
          address: 'Musterstraße 1, 10115 Berlin',
          postal_code: '10115',
          city: 'Berlin',
          lat,
          lng,
          zone: {
            name: 'Zone A',
            badge: 'Zone A (kostenlos)',
            free: true,
            price_cents: 0,
          },
        }),
      };
    }

    // -------------------------------------------------------------
    // POST /api/quote
    // -------------------------------------------------------------
    if (path.startsWith('quote')) {
      let data = {};
      try {
        data = JSON.parse(event.body || '{}');
      } catch (_e) {}
      const start = new Date(data.start || Date.now());
      const end = new Date(data.end || Date.now() + 86400000 * 2);
      const nights = Math.max(1, Math.round((end - start) / (1000 * 60 * 60 * 24)));
      const modelId = Number(data.model_id) || 1;

      // Look up model price from Turso
      const modelRes = await db.execute({
        sql: `SELECT price_cents FROM models WHERE id = ? OR slug = ? LIMIT 1`,
        args: [modelId, data.model_slug || 'model-x'],
      });
      const modelPrice = modelRes.rows.length > 0 ? Number(modelRes.rows[0].price_cents) : 11900;
      const rentCents = modelPrice * nights;
      const deliveryType = data.delivery_type === 'pickup' ? 'pickup' : 'delivery';
      const deliveryCents = deliveryType === 'pickup' ? 0 : (Number(data.delivery_cents) || 0);
      let extrasCents = 0;
      if (Array.isArray(data.extras)) {
        for (const ex of data.extras) {
          extrasCents += (Number(ex.price_cents) || 0) * (Number(ex.qty) || 1);
        }
      }
      const grossCents = rentCents + deliveryCents + extrasCents;
      const vatCents = Math.round((grossCents * 19) / 119);
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          ok: true,
          nights,
          delivery_type: deliveryType,
          rent_cents: rentCents,
          delivery_cents: deliveryCents,
          extras_cents: extrasCents,
          gross_cents: grossCents,
          vat_cents: vatCents,
          deposit_cents: 0,
          voucher_cents: 0,
        }),
      };
    }

    // -------------------------------------------------------------
    // POST /api/bookings
    // -------------------------------------------------------------
    if (path.startsWith('bookings')) {
      let data = {};
      try {
        data = JSON.parse(event.body || '{}');
      } catch (_e) {}

      const number = 'SC-26-' + Math.floor(1000 + Math.random() * 9000);
      const publicToken = crypto.randomBytes(16).toString('hex');
      const start = new Date(data.start || Date.now());
      const end = new Date(data.end || Date.now() + 86400000 * 2);
      const nights = Math.max(1, Math.round((end - start) / (1000 * 60 * 60 * 24)));

      const modelRes = await db.execute({
        sql: `SELECT id, name, slug, price_cents FROM models WHERE id = ? OR slug = ? LIMIT 1`,
        args: [Number(data.model_id) || 1, data.model_slug || 'model-x'],
      });
      const model = modelRes.rows[0] || { id: 1, name: 'Model X', slug: 'model-x', price_cents: 11900 };

      const deliveryType = data.delivery_type === 'pickup' ? 'pickup' : 'delivery';
      const address = deliveryType === 'pickup' ? 'Tiefenbrunnen 1, 14929 Treuenbrietzen (Selbstabholung)' : (data.address || 'Musterstraße 1');
      const lat = deliveryType === 'pickup' ? 52.0911 : (parseFloat(data.lat) || 52.52);
      const lng = deliveryType === 'pickup' ? 12.8711 : (parseFloat(data.lng) || 13.405);
      const rentCents = Number(model.price_cents) * nights;
      const deliveryCents = deliveryType === 'pickup' ? 0 : (Number(data.delivery_cents) || 0);
      const grossCents = rentCents + deliveryCents;
      const vatCents = Math.round((grossCents * 19) / 119);

      await db.execute({
        sql: `INSERT INTO bookings (
                number, public_token, model_id, model_name, model_slug,
                start_date, end_date, nights, address, postal_code, city, zone_name,
                lat, lng, delivery_type,
                delivery_cents, rent_cents, extras_cents, gross_cents, vat_cents,
                extras_json, first_name, last_name, email, phone, notes,
                payment_method, payment_status, status, created_at
              ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, '[]', ?, ?, ?, ?, ?, ?, 'unpaid', 'new', datetime('now'))`,
        args: [
          number, publicToken, Number(model.id), String(model.name), String(model.slug),
          data.start || '2026-10-20', data.end || '2026-10-22', nights,
          address, data.postal_code || '10115', data.city || 'Berlin', data.zone_name || (deliveryType === 'pickup' ? 'Selbstabholung' : 'Zone A'),
          lat, lng, deliveryType,
          deliveryCents, rentCents, grossCents, vatCents,
          data.first_name || 'Gast', data.last_name || 'Kunde',
          data.email || 'kunde@example.de', data.phone || '+49 12345678', data.notes || '',
          data.payment_method || 'invoice',
        ],
      });

      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          ok: true,
          number,
          redirect: `/buchung/finden?success=1&number=${number}`,
        }),
      };
    // -------------------------------------------------------------
    // GET /api/extras - Return all active extras
    // -------------------------------------------------------------
    if (path === 'extras' || path.startsWith('extras')) {
      const res = await db.execute(`SELECT * FROM extras WHERE active = 1 ORDER BY sort_order, id`);
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({ ok: true, extras: res.rows }),
      };
    }

    // -------------------------------------------------------------
    // ADMIN: POST /api/admin/login
    // -------------------------------------------------------------
    if (path.startsWith('admin/login')) {
      let body = {};
      try {
        body = JSON.parse(event.body || '{}');
      } catch (_e) {}
      const email = (body.email || '').trim().toLowerCase();
      const password = body.password || '';

      const adminRes = await db.execute({
        sql: `SELECT * FROM admins WHERE email = ? LIMIT 1`,
        args: [email],
      });

      if (adminRes.rows.length === 0) {
        return { statusCode: 401, headers, body: JSON.stringify({ ok: false, error: 'E-Mail oder Passwort ist falsch.' }) };
      }

      const admin = adminRes.rows[0];
      if (!verifyPassword(password, admin.password_hash)) {
        return { statusCode: 401, headers, body: JSON.stringify({ ok: false, error: 'E-Mail oder Passwort ist falsch.' }) };
      }

      const userToken = makeToken(admin.email);
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          ok: true,
          token: userToken,
          admin: { name: admin.name, email: admin.email },
        }),
      };
    }

    // -------------------------------------------------------------
    // ADMIN: Protected routes check
    // -------------------------------------------------------------
    if (path.startsWith('admin/')) {
      const user = verifyToken(token);
      if (!user) {
        return { statusCode: 401, headers, body: JSON.stringify({ ok: false, error: 'Nicht autorisiert. Bitte erneut anmelden.' }) };
      }

      // GET /api/admin/data - Returns all Turso data for the dashboard
      if (path === 'admin/data') {
        const bookingsRes = await db.execute(`SELECT * FROM bookings ORDER BY created_at DESC LIMIT 50`);
        const modelsRes = await db.execute(`SELECT * FROM models ORDER BY sort_order`);
        const extrasRes = await db.execute(`SELECT * FROM extras ORDER BY sort_order`);
        const zonesRes = await db.execute(`SELECT * FROM zones WHERE active = 1 ORDER BY sort_order`);
        const messagesRes = await db.execute(`SELECT * FROM messages ORDER BY created_at DESC LIMIT 20`);
        const settingsRes = await db.execute(`SELECT key, value FROM settings`);

        const settingsMap = {};
        for (const row of settingsRes.rows) {
          settingsMap[row.key] = row.value;
        }

        return {
          statusCode: 200,
          headers,
          body: JSON.stringify({
            ok: true,
            bookings: bookingsRes.rows,
            models: modelsRes.rows,
            extras: extrasRes.rows,
            zones: zonesRes.rows,
            messages: messagesRes.rows,
            settings: settingsMap,
          }),
        };
      }

      // POST /api/admin/status - Update booking status
      if (path === 'admin/status') {
        let body = {};
        try {
          body = JSON.parse(event.body || '{}');
        } catch (_e) {}
        const bookingId = Number(body.id);
        const newStatus = String(body.status);
        await db.execute({
          sql: `UPDATE bookings SET status = ? WHERE id = ?`,
          args: [newStatus, bookingId],
        });
        return { statusCode: 200, headers, body: JSON.stringify({ ok: true }) };
      }

      // POST /api/admin/content - Update website CMS content
      if (path === 'admin/content') {
        let body = {};
        try {
          body = JSON.parse(event.body || '{}');
        } catch (_e) {}
        const items = body.content || {};
        for (const [key, value] of Object.entries(items)) {
          await db.execute({
            sql: `INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value`,
            args: [key, typeof value === 'object' ? JSON.stringify(value) : String(value)],
          });
        }
        return { statusCode: 200, headers, body: JSON.stringify({ ok: true }) };
      }

      // POST /api/admin/model - Update model details
      if (path === 'admin/model') {
        let body = {};
        try {
          body = JSON.parse(event.body || '{}');
        } catch (_e) {}
        const m = body.model || {};
        if (m.id) {
          await db.execute({
            sql: `UPDATE models SET name = ?, subtitle = ?, badge = ?, price_cents = ?, capacity_min = ?, capacity_max = ?, summary = ?, story_title = ?, story = ? WHERE id = ?`,
            args: [
              m.name || '', m.subtitle || '', m.badge || '', Number(m.price_cents) || 0,
              Number(m.capacity_min) || 2, Number(m.capacity_max) || 4,
              m.summary || '', m.story_title || '', m.story || '', Number(m.id)
            ],
          });
        }
        return { statusCode: 200, headers, body: JSON.stringify({ ok: true }) };
      }

      // POST /api/admin/zone - Update zone
      if (path === 'admin/zone') {
        let body = {};
        try {
          body = JSON.parse(event.body || '{}');
        } catch (_e) {}
        const z = body.zone || {};
        if (z.id) {
          await db.execute({
            sql: `UPDATE zones SET name = ?, prefixes = ?, cities = ?, price_cents = ?, note = ? WHERE id = ?`,
            args: [z.name || '', z.prefixes || '', z.cities || '', Number(z.price_cents) || 0, z.note || '', Number(z.id)],
          });
        }
        return { statusCode: 200, headers, body: JSON.stringify({ ok: true }) };
      }

      // POST /api/admin/extra - Create or update extra
      if (path === 'admin/extra') {
        let body = {};
        try {
          body = JSON.parse(event.body || '{}');
        } catch (_e) {}
        const ex = body.extra || {};
        if (ex.id) {
          await db.execute({
            sql: `UPDATE extras SET name = ?, description = ?, price_cents = ?, kind = ?, image = ?, active = ? WHERE id = ?`,
            args: [
              ex.name || '',
              ex.description || '',
              Number(ex.price_cents) || 0,
              ex.kind || 'kauf',
              ex.image !== undefined ? String(ex.image) : '',
              ex.active !== undefined ? (ex.active ? 1 : 0) : 1,
              Number(ex.id),
            ],
          });
        } else if (ex.name) {
          const slug = (ex.name || 'extra').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') + '-' + Date.now().toString(36);
          await db.execute({
            sql: `INSERT INTO extras (slug, name, description, price_cents, kind, image, active, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, 9)`,
            args: [
              slug,
              ex.name || '',
              ex.description || '',
              Number(ex.price_cents) || 0,
              ex.kind || 'kauf',
              ex.image || '',
              ex.active !== undefined ? (ex.active ? 1 : 0) : 1
            ],
          });
        }
        return { statusCode: 200, headers, body: JSON.stringify({ ok: true }) };
      }

      // POST /api/admin/extra/delete - Delete extra
      if (path === 'admin/extra/delete') {
        let body = {};
        try { body = JSON.parse(event.body || '{}'); } catch (_e) {}
        if (body.id) {
          await db.execute({
            sql: `DELETE FROM extras WHERE id = ?`,
            args: [Number(body.id)]
          });
        }
        return { statusCode: 200, headers, body: JSON.stringify({ ok: true }) };
      }

      // POST /api/admin/price - Update model price
      if (path === 'admin/price') {
        let body = {};
        try {
          body = JSON.parse(event.body || '{}');
        } catch (_e) {}
        const modelId = Number(body.id);
        const priceCents = Number(body.price_cents);
        await db.execute({
          sql: `UPDATE models SET price_cents = ? WHERE id = ?`,
          args: [priceCents, modelId],
        });
        return { statusCode: 200, headers, body: JSON.stringify({ ok: true }) };
      }

      // POST /api/admin/settings - Save setting
      if (path === 'admin/settings') {
        let body = {};
        try {
          body = JSON.parse(event.body || '{}');
        } catch (_e) {}
        for (const [key, value] of Object.entries(body.settings || {})) {
          await db.execute({
            sql: `INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value`,
            args: [key, String(value)],
          });
        }
        return { statusCode: 200, headers, body: JSON.stringify({ ok: true }) };
      }

      // POST /api/admin/message/delete
      if (path === 'admin/message/delete') {
        let body = {};
        try {
          body = JSON.parse(event.body || '{}');
        } catch (_e) {}
        if (body.id) {
          await db.execute({
            sql: `DELETE FROM messages WHERE id = ?`,
            args: [Number(body.id)],
          });
        }
        return { statusCode: 200, headers, body: JSON.stringify({ ok: true }) };
      }
    }

    return {
      statusCode: 404,
      headers,
      body: JSON.stringify({ ok: false, error: 'Endpoint not found: ' + path }),
    };
  } catch (err) {
    console.error('API Error:', err);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ ok: false, error: err.message }),
    };
  }
};
