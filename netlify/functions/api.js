exports.handler = async (event) => {
  const path = (event.path || '').replace(/^.*\/api\/?/, '');
  const method = event.httpMethod || 'GET';
  const params = event.queryStringParameters || {};

  const headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, X-CSRFToken',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  };

  if (method === 'OPTIONS') {
    return { statusCode: 204, headers, body: '' };
  }

  // GET /api/busy
  if (path.startsWith('busy')) {
    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({ ok: true, busy: [] }),
    };
  }

  // GET /api/zone
  if (path.startsWith('zone')) {
    const q = (params.q || '').toLowerCase();
    const isFree = q.includes('berlin') || ['10', '12', '13', '14'].some((p) => q.startsWith(p));
    const priceCents = isFree ? 0 : 5000;
    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        ok: true,
        name: isFree ? 'Zone A' : 'Zone B',
        badge: isFree ? 'Zone A (kostenlos)' : 'Zone B (50 €)',
        price_cents: priceCents,
        price: isFree ? 'kostenlos' : '50,00 €',
        free: isFree,
      }),
    };
  }

  // GET /api/reverse
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

  // POST /api/quote
  if (path.startsWith('quote')) {
    let data = {};
    try {
      data = JSON.parse(event.body || '{}');
    } catch (_e) {}
    const start = new Date(data.start || Date.now());
    const end = new Date(data.end || Date.now() + 86400000 * 2);
    const nights = Math.max(1, Math.round((end - start) / (1000 * 60 * 60 * 24)));
    const modelPrice = data.model_id === 1 ? 8900 : data.model_id === 3 ? 14900 : 11900;
    const rentCents = modelPrice * nights;
    const deliveryCents = data.delivery_cents || 0;
    let extrasCents = 0;
    if (data.extras && Array.isArray(data.extras)) {
      data.extras.forEach((ex) => {
        extrasCents += (ex.price_cents || 0) * (ex.qty || 1);
      });
    }
    const grossCents = rentCents + deliveryCents + extrasCents;
    const vatCents = Math.round((grossCents * 19) / 119);
    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        ok: true,
        nights,
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

  // POST /api/bookings
  if (path.startsWith('bookings')) {
    const num = 'SC-' + Math.floor(1000 + Math.random() * 9000);
    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        ok: true,
        number: num,
        redirect: '/buchung/finden?success=1',
      }),
    };
  }

  return {
    statusCode: 404,
    headers,
    body: JSON.stringify({ ok: false, error: 'Endpoint not found' }),
  };
};
