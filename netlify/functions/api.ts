// Booking API backed by Netlify Database.
// Ports the public JSON endpoints of saunacore/api.py (busy, zone, reverse, quote, bookings)
// so the statically exported site can check availability, price and store real bookings.
import type { Config } from "@netlify/functions";
import { randomBytes, randomInt } from "node:crypto";
import { and, asc, eq, gt, lt, ne, sql } from "drizzle-orm";
import { db } from "../../db/index.js";
import { blocks, bookingEvents, bookings, extras, models, settings, vouchers, zones } from "../../db/schema.js";

type Q = typeof db;
type Zone = typeof zones.$inferSelect;

class QuoteError extends Error {}

const DAY_MS = 86_400_000;
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const PAYMENTS: Record<string, string> = { card: "Kreditkarte", paypal: "PayPal", invoice: "Rechnung" };
const WINDOWS = new Set(["vormittag", "nachmittag", "flexibel"]);
const MONTHS_SHORT = ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.", "Sep.", "Okt.", "Nov.", "Dez."];
const geoCache = new Map<string, { address: string; postal_code: string; city: string }>();

// ---------- formatting helpers (mirrors service.py) ----------

function formatEuro(cents: number): string {
  const sign = cents < 0 ? "-" : "";
  const abs = Math.abs(Math.trunc(cents));
  const euros = Math.floor(abs / 100).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const rest = abs % 100;
  return rest === 0 ? `${sign}${euros} €` : `${sign}${euros},${String(rest).padStart(2, "0")} €`;
}

function includedVat(gross: number, percent: number): number {
  const denom = 100 + percent;
  return Math.floor((gross * percent + Math.floor(denom / 2)) / denom);
}

function parseIso(value: unknown): Date {
  const text = String(value ?? "").trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) throw new QuoteError("Datum ist ungültig.");
  const parsed = new Date(text + "T00:00:00Z");
  if (Number.isNaN(parsed.getTime()) || iso(parsed) !== text) throw new QuoteError("Datum ist ungültig.");
  return parsed;
}

const iso = (d: Date) => d.toISOString().slice(0, 10);
const addDays = (d: Date, n: number) => new Date(d.getTime() + n * DAY_MS);
const daysBetween = (a: Date, b: Date) => Math.round((b.getTime() - a.getTime()) / DAY_MS);

function today(): Date {
  const local = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Berlin" }).format(new Date());
  return new Date(local + "T00:00:00Z");
}

const nightsLabel = (n: number) => (n === 1 ? "1 Nacht" : `${n} Nächte`);
const rentLabel = (n: number) => (n === 1 ? "1 Tag Miete" : `${n} Tage Miete`);
const formatDay = (d: Date) => `${d.getUTCDate()}. ${MONTHS_SHORT[d.getUTCMonth()]}`;

function formatRange(start: Date, end: Date): string {
  let left = formatDay(start);
  const right = `${formatDay(end)} ${end.getUTCFullYear()}`;
  if (start.getUTCFullYear() !== end.getUTCFullYear()) left = `${left} ${start.getUTCFullYear()}`;
  return `${left} – ${right} (${nightsLabel(daysBetween(start, end))})`;
}

const splitCsv = (value: string) =>
  (value || "")
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function containsCity(query: string, city: string): boolean {
  return new RegExp(`(?<![\\p{L}\\p{N}_])${escapeRegExp(city)}(?![\\p{L}\\p{N}_])`, "iu").test(query);
}

// ---------- data access ----------

async function loadSettings(q: Q): Promise<Record<string, string>> {
  const rows = await q.select().from(settings);
  return Object.fromEntries(rows.map((row) => [row.key, row.value]));
}

function intSetting(values: Record<string, string>, key: string, fallback: number): number {
  const parsed = Number.parseInt(values[key] ?? "", 10);
  return Number.isNaN(parsed) ? fallback : parsed;
}

async function lookupZone(q: Q, query: string): Promise<[Zone | null, string]> {
  const rows = await q.select().from(zones).where(eq(zones.active, true)).orderBy(asc(zones.sortOrder), asc(zones.id));
  const plz = (query || "").match(/\b(\d{5})\b/)?.[1] ?? "";
  if (plz) {
    let best: Zone | null = null;
    let bestLen = -1;
    let star: Zone | null = null;
    for (const zone of rows) {
      for (const prefix of splitCsv(zone.prefixes)) {
        if (prefix === "*") {
          star = zone;
          continue;
        }
        if (plz.startsWith(prefix) && prefix.length > bestLen) {
          best = zone;
          bestLen = prefix.length;
        }
      }
    }
    if (best) return [best, plz];
    if (star) return [star, plz];
  }
  let best: Zone | null = null;
  let bestLen = -1;
  const low = (query || "").toLowerCase();
  for (const zone of rows) {
    for (const city of splitCsv(zone.cities)) {
      if (city !== "*" && containsCity(low, city) && city.length > bestLen) {
        best = zone;
        bestLen = city.length;
      }
    }
  }
  return [best, plz];
}

function zoneBadge(zone: Zone): string {
  const raw = (zone.name || "").trim();
  const title = raw.toLowerCase().startsWith("zone") ? "LIEFER" + raw.toUpperCase() : raw.toUpperCase();
  return zone.priceCents === 0 ? `${title} (KOSTENLOS)` : `${title} (${formatEuro(zone.priceCents)})`;
}

const presentZone = (zone: Zone) => ({
  id: zone.id,
  name: zone.name,
  badge: zoneBadge(zone),
  free: zone.priceCents === 0,
  price_cents: zone.priceCents,
});

function parseAddress(address: string): [string, string] {
  const plz = (address || "").match(/\b(\d{5})\b/)?.[1] ?? "";
  let city = "";
  if (plz) city = address.split(plz).slice(1).join(plz).split(",")[0].trim();
  if (!city) {
    const parts = (address || "")
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean);
    if (parts.length) {
      city = parts[parts.length - 1];
      if (["deutschland", "germany", "de"].includes(city.toLowerCase()) && parts.length > 1) city = parts[parts.length - 2];
    }
  }
  if (plz && city.includes(plz)) city = city.replace(plz, "").replace(/^[ ,]+|[ ,]+$/g, "");
  return [plz, city.slice(0, 80)];
}

async function modelUnits(q: Q, modelId: number): Promise<number> {
  const [row] = await q.select({ units: models.units }).from(models).where(eq(models.id, modelId));
  return row && row.units >= 1 ? row.units : 1;
}

async function overlapping(q: Q, modelId: number, start: Date, end: Date) {
  const booked = await q
    .select({ startDate: bookings.startDate, endDate: bookings.endDate })
    .from(bookings)
    .where(
      and(
        eq(bookings.modelId, modelId),
        ne(bookings.status, "cancelled"),
        lt(bookings.startDate, iso(end)),
        gt(bookings.endDate, iso(start)),
      ),
    );
  const blocked = await q
    .select({ startDate: blocks.startDate, endDate: blocks.endDate })
    .from(blocks)
    .where(and(eq(blocks.modelId, modelId), lt(blocks.startDate, iso(end)), gt(blocks.endDate, iso(start))));
  return { booked, blocked };
}

async function rangeConflicts(q: Q, modelId: number, start: Date, end: Date): Promise<boolean> {
  const { booked, blocked } = await overlapping(q, modelId, start, end);
  if (blocked.length) return true;
  return booked.length >= (await modelUnits(q, modelId));
}

function* walkNights(row: { startDate: string; endDate: string }, start: Date, end: Date) {
  let current = new Date(Math.max(parseIso(row.startDate).getTime(), start.getTime()));
  const stop = new Date(Math.min(parseIso(row.endDate).getTime(), end.getTime()));
  while (current < stop) {
    yield iso(current);
    current = addDays(current, 1);
  }
}

async function busyNights(q: Q, modelId: number, start: Date, end: Date): Promise<string[]> {
  const units = await modelUnits(q, modelId);
  const { booked, blocked } = await overlapping(q, modelId, start, end);
  const counts = new Map<string, number>();
  for (const row of booked) for (const day of walkNights(row, start, end)) counts.set(day, (counts.get(day) ?? 0) + 1);
  const closed = new Set<string>();
  for (const row of blocked) for (const day of walkNights(row, start, end)) closed.add(day);
  const taken: string[] = [];
  for (let day = start; day < end; day = addDays(day, 1)) {
    const key = iso(day);
    if (closed.has(key) || (counts.get(key) ?? 0) >= units) taken.push(key);
  }
  return taken;
}

type ExtraLine = { id: number; name: string; kind: string; qty: number; unit_cents: number; line_cents: number; line: string };

async function resolveExtras(q: Q, raw: unknown): Promise<ExtraLine[]> {
  if (!raw || (Array.isArray(raw) && raw.length === 0)) return [];
  if (!Array.isArray(raw)) throw new QuoteError("Zusätze sind ungültig.");
  const resolved: ExtraLine[] = [];
  const seen = new Set<number>();
  for (const item of raw) {
    if (!item || typeof item !== "object") throw new QuoteError("Zusätze sind ungültig.");
    const extraId = Number(item.id);
    let qty = Number(item.qty || 0);
    if (!Number.isInteger(extraId) || !Number.isInteger(qty)) throw new QuoteError("Zusätze sind ungültig.");
    if (seen.has(extraId)) throw new QuoteError("Ein Zusatz wurde doppelt angegeben.");
    seen.add(extraId);
    const [extra] = await q
      .select()
      .from(extras)
      .where(and(eq(extras.id, extraId), eq(extras.active, true)));
    if (!extra) {
      if (qty > 0) throw new QuoteError("Ein Zusatz ist nicht mehr verfügbar.");
      continue;
    }
    if (extra.kind === "service") qty = qty >= 1 ? 1 : 0;
    if (qty <= 0) continue;
    if (qty > 10) throw new QuoteError("Höchstens 10 Stück pro Zusatz.");
    const line = extra.priceCents * qty;
    resolved.push({
      id: extra.id,
      name: extra.name,
      kind: extra.kind,
      qty,
      unit_cents: extra.priceCents,
      line_cents: line,
      line: formatEuro(line),
    });
  }
  return resolved;
}

// ---------- quote ----------

async function buildQuote(q: Q, data: Record<string, any>, address: string, allowPast = false) {
  const modelId = Number(data.model_id);
  if (!Number.isInteger(modelId)) throw new QuoteError("Modell ist ungültig.");
  const start = parseIso(data.start);
  const end = parseIso(data.end);
  const [model] = await q.select().from(models).where(eq(models.id, modelId));
  if (!model || !model.active) throw new QuoteError("Dieses Modell ist nicht buchbar.");
  if (end <= start) throw new QuoteError("Die Abreise muss nach der Anreise liegen.");
  if (!allowPast && start < today()) throw new QuoteError("Die Anreise kann nicht in der Vergangenheit liegen.");
  const nights = daysBetween(start, end);
  const values = await loadSettings(q);
  const minimum = intSetting(values, "min_nights", 1);
  const maximum = intSetting(values, "max_nights", 21);
  if (nights < minimum) throw new QuoteError(minimum === 1 ? "Mindestens 1 Nacht." : `Mindestens ${minimum} Nächte.`);
  if (nights > maximum) throw new QuoteError(`Höchstens ${maximum} Nächte am Stück.`);
  if (await rangeConflicts(q, model.id, start, end)) throw new QuoteError("In diesem Zeitraum ist die Sauna bereits belegt.");

  let zone: Zone | null = null;
  let delivery: number | null = null;
  let plz = "";
  let city = "";
  if (address.trim()) {
    [zone, plz] = await lookupZone(q, address);
    const [parsedPlz, parsedCity] = parseAddress(address);
    plz = plz || parsedPlz;
    city = parsedCity;
    if (!zone) throw new QuoteError("Diese Adresse liegt außerhalb unseres Liefergebiets.");
    delivery = zone.priceCents;
  }
  const chosen = await resolveExtras(q, data.extras);
  const rent = model.priceCents * nights;
  const extrasTotal = chosen.reduce((sum, item) => sum + item.line_cents, 0);
  const percent = intSetting(values, "vat_percent", 19);
  const deposit = Math.max(0, intSetting(values, "deposit_cents", 0));
  const gross = delivery === null ? null : rent + extrasTotal + delivery + deposit;
  const vat = gross === null ? null : includedVat(gross, percent);

  return {
    model_id: model.id,
    model_name: model.name,
    model_slug: model.slug,
    unit: formatEuro(model.priceCents),
    nights,
    start: iso(start),
    end: iso(end),
    range_label: formatRange(start, end),
    rent_cents: rent,
    rent_label: rentLabel(nights),
    rent: formatEuro(rent),
    delivery_cents: delivery,
    delivery: delivery === null ? null : delivery === 0 ? "kostenlos" : formatEuro(delivery),
    delivery_label: zone ? `Lieferung (${zone.name})` : "Lieferung (ca.)",
    extras: chosen,
    extras_cents: extrasTotal,
    deposit_cents: deposit,
    deposit: deposit ? formatEuro(deposit) : null,
    voucher_cents: 0,
    voucher_code: "",
    voucher: null as string | null,
    gross_cents: gross,
    gross: gross === null ? null : formatEuro(gross),
    vat_cents: vat,
    vat: vat === null ? null : formatEuro(vat),
    vat_percent: percent,
    vat_text: `inkl. MwSt. (${percent}%)`,
    needs_address: delivery === null,
    postal_code: plz,
    city,
    country: "Deutschland",
    zone: zone ? presentZone(zone) : null,
    address,
    lat: null as number | null,
    lng: null as number | null,
  };
}

type Quote = Awaited<ReturnType<typeof buildQuote>>;

async function applyVoucher(q: Q, quote: Quote, rawCode: unknown): Promise<Quote> {
  const code = String(rawCode ?? "")
    .trim()
    .toUpperCase();
  if (!code) return quote;
  if (code.length > 40 || !/^[A-Z0-9_-]+$/.test(code)) throw new QuoteError("Der Gutscheincode ist ungültig.");
  const [row] = await q.select().from(vouchers).where(eq(vouchers.code, code));
  if (!row || !row.active) throw new QuoteError("Der Gutscheincode ist ungültig.");
  if (row.used >= row.maxUses) throw new QuoteError("Der Gutscheincode ist aufgebraucht.");
  quote.voucher_code = code;
  if (quote.gross_cents === null) return quote;
  const base = quote.rent_cents + quote.extras_cents + (quote.delivery_cents ?? 0);
  const discount = Math.min(row.cents, Math.max(0, base));
  const gross = base + quote.deposit_cents - discount;
  const vat = includedVat(gross, quote.vat_percent);
  return {
    ...quote,
    voucher_cents: discount,
    voucher: discount ? formatEuro(-discount) : null,
    gross_cents: gross,
    gross: formatEuro(gross),
    vat_cents: vat,
    vat: formatEuro(vat),
  };
}

function coord(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) throw new QuoteError("Die Markierung ist ungültig.");
  return parsed;
}

async function reverseGeocode(lat: number, lng: number) {
  if (!(lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180)) throw new QuoteError("Die Markierung liegt außerhalb der Karte.");
  const key = `${lat.toFixed(5)},${lng.toFixed(5)}`;
  const cached = geoCache.get(key);
  if (cached) return cached;
  const params = new URLSearchParams({ lat: lat.toFixed(6), lon: lng.toFixed(6), format: "jsonv2", addressdetails: "1" });
  let payload: any;
  try {
    const response = await fetch("https://nominatim.openstreetmap.org/reverse?" + params, {
      headers: { "User-Agent": "Saunacore/1.0 (booking map)", "Accept-Language": "de" },
      signal: AbortSignal.timeout(6000),
    });
    payload = await response.json();
  } catch {
    throw new QuoteError("Der Ort konnte nicht ermittelt werden. Setze die Markierung erneut.");
  }
  const address = payload?.address;
  if (!address || typeof address !== "object" || payload.error) throw new QuoteError("Für diese Markierung gibt es keine Adresse.");
  const postcode = String(address.postcode ?? "");
  const city = String(address.city || address.town || address.village || address.municipality || address.county || "");
  const road = String(address.road || address.pedestrian || address.footway || "");
  const street = `${road} ${String(address.house_number ?? "")}`.trim();
  const locality = `${postcode} ${city}`.trim();
  const text = ([street, locality].filter(Boolean).join(", ") || String(payload.display_name ?? ""))
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 200);
  if (text.length < 3) throw new QuoteError("Für diese Markierung gibt es keine Adresse.");
  const info = { address: text, postal_code: postcode.slice(0, 12), city: city.slice(0, 80) };
  if (geoCache.size > 300) geoCache.clear();
  geoCache.set(key, info);
  return info;
}

async function resolveLocation(data: Record<string, any>): Promise<[string, number | null, number | null]> {
  const lat = coord(data.lat);
  const lng = coord(data.lng);
  if ((lat === null) !== (lng === null)) throw new QuoteError("Die Markierung ist unvollständig.");
  if (lat !== null && lng !== null) return [(await reverseGeocode(lat, lng)).address, lat, lng];
  const address = String(data.address ?? "").trim();
  if (address.length > 200) throw new QuoteError("Die Adresse ist zu lang.");
  return [address, null, null];
}

async function quoteFromPayload(q: Q, data: unknown): Promise<Quote> {
  if (!data || typeof data !== "object") throw new QuoteError("Anfrage ist ungültig.");
  const payload = data as Record<string, any>;
  const [address, lat, lng] = await resolveLocation(payload);
  const quote = await buildQuote(q, payload, address);
  quote.lat = lat;
  quote.lng = lng;
  return applyVoucher(q, quote, payload.voucher_code);
}

// ---------- booking ----------

const truthy = (v: unknown) => v === true || v === 1 || ["1", "true", "yes", "on"].includes(String(v).toLowerCase());
const falsey = (v: unknown) => v === false || v === 0 || ["0", "false", "no", "off"].includes(String(v).toLowerCase());

function customer(data: Record<string, any>) {
  const first = String(data.first_name ?? "").trim();
  const last = String(data.last_name ?? "").trim();
  const email = String(data.email ?? "")
    .trim()
    .toLowerCase();
  const phone = String(data.phone ?? "").trim();
  const notes = String(data.notes ?? "").trim();
  if (!(first.length >= 1 && first.length <= 60 && last.length >= 1 && last.length <= 60))
    throw new QuoteError("Bitte gib Vor- und Nachname an.");
  if (!EMAIL_RE.test(email) || email.length > 120) throw new QuoteError("Bitte gib eine gültige E-Mail an.");
  if (phone.replace(/\D/g, "").length < 6 || phone.length > 40) throw new QuoteError("Bitte gib eine gültige Telefonnummer an.");
  if (notes.length > 1000) throw new QuoteError("Die Anmerkung ist zu lang.");
  return { first, last, email, phone, notes };
}

function payment(data: Record<string, any>) {
  const method = String(data.payment_method ?? "");
  if (!(method in PAYMENTS)) throw new QuoteError("Bitte wähle eine Zahlungsart.");
  let brand = "";
  let last4 = "";
  let exp = "";
  if (method === "card") {
    last4 = String(data.card_last4 ?? "").replace(/\D/g, "");
    brand = String(data.card_brand ?? "").trim().slice(0, 20) || "Karte";
    exp = String(data.card_exp ?? "").trim();
    if (last4.length !== 4 || !/^(0[1-9]|1[0-2])\/\d{2}$/.test(exp)) throw new QuoteError("Kartendaten sind unvollständig.");
    const [month, year] = exp.split("/").map(Number);
    const now = today();
    if (2000 + year < now.getUTCFullYear() || (2000 + year === now.getUTCFullYear() && month < now.getUTCMonth() + 1))
      throw new QuoteError("Die Karte ist abgelaufen.");
  }
  return { method, brand, last4, exp };
}

function tripFields(data: Record<string, any>) {
  const window = String(data.arrival_window ?? "")
    .trim()
    .toLowerCase();
  if (window && !WINDOWS.has(window)) throw new QuoteError("Bitte wähle ein Lieferfenster.");
  const present = "access_ok" in data || "access_confirmed" in data;
  const raw = data.access_ok ?? data.access_confirmed;
  if (present && falsey(raw)) throw new QuoteError("Bitte bestätige Zufahrt, Stellfläche und Übergabe.");
  const company = String(data.company ?? "").trim().slice(0, 120);
  const companyVat = String(data.company_vat ?? "")
    .trim()
    .replace(/\s+/g, "")
    .slice(0, 20);
  if (companyVat && !/^[A-Za-z0-9]{2,20}$/.test(companyVat)) throw new QuoteError("Die USt-IdNr. ist ungültig.");
  return { window, access: present && truthy(raw), company, companyVat };
}

const bookingResult = (row: { number: string }) => ({
  number: row.number,
  redirect: `/buchung/finden?success=1&number=${encodeURIComponent(row.number)}`,
});

async function findByClientToken(q: Q, token: string) {
  const [row] = await q.select().from(bookings).where(eq(bookings.clientToken, token));
  return row;
}

async function createBooking(data: unknown) {
  if (!data || typeof data !== "object") throw new QuoteError("Anfrage ist ungültig.");
  const payload = data as Record<string, any>;
  const token = String(payload.client_token ?? "").trim().slice(0, 80);
  if (token) {
    const existing = await findByClientToken(db, token);
    if (existing) return bookingResult(existing);
  }
  const person = customer(payload);
  const pay = payment(payload);
  const trip = tripFields(payload);

  try {
    return await db.transaction(async (tx) => {
      const q = tx as unknown as Q;
      // Serialise bookings per model so two guests cannot take the last free unit at once.
      await q.execute(sql`SELECT pg_advisory_xact_lock(${Number(payload.model_id) || 0})`);
      if (token) {
        const existing = await findByClientToken(q, token);
        if (existing) return bookingResult(existing);
      }
      const quote = await quoteFromPayload(q, payload);
      const address = quote.address.trim();
      if (address.length < 5 || quote.needs_address || quote.gross_cents === null || !quote.zone)
        throw new QuoteError("Bitte setze die Markierung im Liefergebiet.");

      // Without Stripe configured, payments are simulated exactly like the Flask app does.
      const invoice = pay.method === "invoice";
      const paymentStatus = invoice ? "unpaid" : "simulated";
      const status = invoice ? "new" : "confirmed";

      if (quote.voucher_code && quote.voucher_cents > 0) {
        const changed = await q
          .update(vouchers)
          .set({ used: sql`${vouchers.used} + 1` })
          .where(and(eq(vouchers.code, quote.voucher_code), eq(vouchers.active, true), lt(vouchers.used, vouchers.maxUses)))
          .returning({ id: vouchers.id });
        if (changed.length !== 1) throw new QuoteError("Der Gutscheincode ist aufgebraucht.");
      }

      const year = today().getUTCFullYear();
      let number = "";
      for (let attempt = 0; attempt < 30 && !number; attempt++) {
        const candidate = `SC-${year}-${randomInt(1000, 10000)}`;
        const [taken] = await q.select({ id: bookings.id }).from(bookings).where(eq(bookings.number, candidate));
        if (!taken) number = candidate;
      }
      if (!number) number = `SC-${year}-${randomBytes(3).toString("hex").toUpperCase()}`;

      const [row] = await q
        .insert(bookings)
        .values({
          number,
          publicToken: randomBytes(18).toString("base64url"),
          clientToken: token || null,
          modelId: quote.model_id,
          modelName: quote.model_name,
          modelSlug: quote.model_slug,
          startDate: quote.start,
          endDate: quote.end,
          nights: quote.nights,
          address,
          postalCode: quote.postal_code,
          city: quote.city,
          country: quote.country,
          zoneName: quote.zone.name,
          deliveryCents: quote.delivery_cents ?? 0,
          rentCents: quote.rent_cents,
          extrasCents: quote.extras_cents,
          grossCents: quote.gross_cents,
          vatCents: quote.vat_cents ?? 0,
          extras: quote.extras,
          firstName: person.first,
          lastName: person.last,
          email: person.email,
          phone: person.phone,
          notes: person.notes,
          paymentMethod: pay.method,
          paymentStatus,
          cardBrand: pay.brand,
          cardLast4: pay.last4,
          cardExp: pay.exp,
          status,
          lat: quote.lat,
          lng: quote.lng,
          depositCents: quote.deposit_cents,
          voucherCents: quote.voucher_cents,
          voucherCode: quote.voucher_code,
          arrivalWindow: trip.window,
          company: trip.company,
          companyVat: trip.companyVat,
          accessOk: trip.access,
        })
        .returning({ id: bookings.id, number: bookings.number });
      await q.insert(bookingEvents).values({ bookingId: row.id, message: "Buchung eingegangen" });
      return bookingResult(row);
    });
  } catch (error: any) {
    // Unique violation: a retry with the same client token raced us, return the stored booking.
    if (token && (error?.code === "23505" || error?.cause?.code === "23505")) {
      const existing = await findByClientToken(db, token);
      if (existing) return bookingResult(existing);
    }
    throw error;
  }
}

// ---------- routing ----------

const json = (body: unknown, status = 200) => Response.json(body, { status });
const fail = (error: string, status = 400) => json({ ok: false, error }, status);

async function readJson(req: Request): Promise<unknown> {
  try {
    return await req.json();
  } catch {
    return {};
  }
}

export default async (req: Request) => {
  const url = new URL(req.url);
  const route = url.pathname.replace(/^\/api\/?/, "").replace(/\/$/, "");
  const params = url.searchParams;

  try {
    if (req.method === "GET" && route === "busy") {
      const modelId = Number(params.get("model_id"));
      if (!Number.isInteger(modelId)) return fail("Anfrage ist ungültig.");
      let start: Date;
      let end: Date;
      try {
        start = parseIso(params.get("start"));
        end = parseIso(params.get("end"));
      } catch {
        return fail("Anfrage ist ungültig.");
      }
      if (end <= start || daysBetween(start, end) > 400) return fail("Zeitraum ist ungültig.");
      return json({ ok: true, busy: await busyNights(db, modelId, start, end) });
    }

    if (req.method === "GET" && route === "zone") {
      const query = (params.get("q") ?? "").trim();
      if (query.length < 2) return fail("Bitte Ort oder PLZ eingeben.");
      const [found] = await lookupZone(db, query);
      if (!found) return fail("Außerhalb des Liefergebiets.", 404);
      return json({
        ok: true,
        name: found.name,
        badge: zoneBadge(found),
        price_cents: found.priceCents,
        price: found.priceCents === 0 ? "kostenlos" : formatEuro(found.priceCents),
        free: found.priceCents === 0,
      });
    }

    if (req.method === "GET" && route === "reverse") {
      const lat = Number(params.get("lat"));
      const lng = Number(params.get("lng"));
      if (!params.get("lat") || !params.get("lng") || !Number.isFinite(lat) || !Number.isFinite(lng))
        return fail("Die Markierung ist ungültig.");
      const info = await reverseGeocode(lat, lng);
      const [zone] = await lookupZone(db, info.address);
      return json({ ok: true, ...info, lat, lng, zone: zone ? presentZone(zone) : null });
    }

    if (req.method === "POST" && route === "quote") {
      return json({ ok: true, ...(await quoteFromPayload(db, await readJson(req))) });
    }

    if (req.method === "POST" && route === "bookings") {
      return json({ ok: true, ...(await createBooking(await readJson(req))) });
    }

    return fail("Endpoint not found", 404);
  } catch (error) {
    if (error instanceof QuoteError) return fail(error.message);
    console.error("api error", error);
    return fail("Die Anfrage konnte nicht verarbeitet werden. Bitte erneut versuchen.", 500);
  }
};

export const config: Config = {
  path: "/api/*",
};
