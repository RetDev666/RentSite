// Postgres mirror of the SQLite schema in saunacore/db.py.
// Dates are stored as ISO strings (YYYY-MM-DD) like the Flask app does.
import { boolean, doublePrecision, index, integer, jsonb, pgTable, serial, text, timestamp } from "drizzle-orm/pg-core";

export const settings = pgTable("settings", {
  key: text().primaryKey(),
  value: text().notNull(),
});

export const models = pgTable("models", {
  id: serial().primaryKey(),
  slug: text().notNull().unique(),
  name: text().notNull(),
  subtitle: text().notNull().default(""),
  badge: text().notNull().default(""),
  priceCents: integer("price_cents").notNull(),
  capacityMin: integer("capacity_min").notNull(),
  capacityMax: integer("capacity_max").notNull(),
  size: text().notNull(),
  features: jsonb().notNull().default([]),
  specs: jsonb().notNull().default([]),
  summary: text().notNull().default(""),
  storyTitle: text("story_title").notNull().default(""),
  story: text().notNull().default(""),
  highlights: jsonb().notNull().default([]),
  images: jsonb().notNull().default([]),
  active: boolean().notNull().default(true),
  sortOrder: integer("sort_order").notNull().default(0),
  units: integer().notNull().default(1),
  includedText: text("included_text").notNull().default(""),
  excludedText: text("excluded_text").notNull().default(""),
});

export const extras = pgTable("extras", {
  id: serial().primaryKey(),
  slug: text().notNull().unique(),
  name: text().notNull(),
  description: text().notNull().default(""),
  priceCents: integer("price_cents").notNull(),
  kind: text().notNull(),
  image: text().notNull().default(""),
  active: boolean().notNull().default(true),
  sortOrder: integer("sort_order").notNull().default(0),
});

export const zones = pgTable("zones", {
  id: serial().primaryKey(),
  name: text().notNull(),
  prefixes: text().notNull().default(""),
  cities: text().notNull().default(""),
  priceCents: integer("price_cents").notNull(),
  note: text().notNull().default(""),
  active: boolean().notNull().default(true),
  sortOrder: integer("sort_order").notNull().default(0),
});

export const bookings = pgTable(
  "bookings",
  {
    id: serial().primaryKey(),
    number: text().notNull().unique(),
    publicToken: text("public_token").notNull(),
    clientToken: text("client_token").unique(),
    modelId: integer("model_id").notNull().references(() => models.id),
    modelName: text("model_name").notNull(),
    modelSlug: text("model_slug").notNull(),
    startDate: text("start_date").notNull(),
    endDate: text("end_date").notNull(),
    nights: integer().notNull(),
    address: text().notNull(),
    postalCode: text("postal_code").notNull().default(""),
    city: text().notNull().default(""),
    country: text().notNull().default("Deutschland"),
    zoneName: text("zone_name").notNull(),
    deliveryCents: integer("delivery_cents").notNull(),
    rentCents: integer("rent_cents").notNull(),
    extrasCents: integer("extras_cents").notNull(),
    grossCents: integer("gross_cents").notNull(),
    vatCents: integer("vat_cents").notNull(),
    extras: jsonb().notNull().default([]),
    firstName: text("first_name").notNull(),
    lastName: text("last_name").notNull(),
    email: text().notNull(),
    phone: text().notNull(),
    notes: text().notNull().default(""),
    paymentMethod: text("payment_method").notNull(),
    paymentStatus: text("payment_status").notNull(),
    cardBrand: text("card_brand").notNull().default(""),
    cardLast4: text("card_last4").notNull().default(""),
    cardExp: text("card_exp").notNull().default(""),
    status: text().notNull(),
    adminNote: text("admin_note").notNull().default(""),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
    lat: doublePrecision(),
    lng: doublePrecision(),
    depositCents: integer("deposit_cents").notNull().default(0),
    voucherCents: integer("voucher_cents").notNull().default(0),
    voucherCode: text("voucher_code").notNull().default(""),
    arrivalWindow: text("arrival_window").notNull().default(""),
    company: text().notNull().default(""),
    companyVat: text("company_vat").notNull().default(""),
    accessOk: boolean("access_ok").notNull().default(false),
    stripeSession: text("stripe_session").notNull().default(""),
  },
  (t) => [
    index("idx_bookings_model").on(t.modelId, t.startDate),
    index("idx_bookings_status").on(t.status),
    index("idx_bookings_email").on(t.email),
  ],
);

export const bookingEvents = pgTable("booking_events", {
  id: serial().primaryKey(),
  bookingId: integer("booking_id")
    .notNull()
    .references(() => bookings.id, { onDelete: "cascade" }),
  message: text().notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const blocks = pgTable(
  "blocks",
  {
    id: serial().primaryKey(),
    modelId: integer("model_id")
      .notNull()
      .references(() => models.id, { onDelete: "cascade" }),
    startDate: text("start_date").notNull(),
    endDate: text("end_date").notNull(),
    reason: text().notNull().default(""),
  },
  (t) => [index("idx_blocks_model").on(t.modelId, t.startDate)],
);

export const vouchers = pgTable("vouchers", {
  id: serial().primaryKey(),
  code: text().notNull().unique(),
  cents: integer().notNull(),
  note: text().notNull().default(""),
  active: boolean().notNull().default(true),
  maxUses: integer("max_uses").notNull().default(1),
  used: integer().notNull().default(0),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const messages = pgTable("messages", {
  id: serial().primaryKey(),
  name: text().notNull(),
  email: text().notNull(),
  phone: text().notNull().default(""),
  body: text().notNull(),
  read: boolean().notNull().default(false),
  reply: text().notNull().default(""),
  repliedAt: timestamp("replied_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const reviews = pgTable("reviews", {
  id: serial().primaryKey(),
  author: text().notNull(),
  text: text().notNull(),
  rating: integer().notNull().default(5),
  modelSlug: text("model_slug").notNull().default(""),
  active: boolean().notNull().default(true),
  sortOrder: integer("sort_order").notNull().default(0),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});
