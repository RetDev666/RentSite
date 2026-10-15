CREATE TABLE "blocks" (
	"id" serial PRIMARY KEY,
	"model_id" integer NOT NULL,
	"start_date" text NOT NULL,
	"end_date" text NOT NULL,
	"reason" text DEFAULT '' NOT NULL
);
--> statement-breakpoint
CREATE TABLE "booking_events" (
	"id" serial PRIMARY KEY,
	"booking_id" integer NOT NULL,
	"message" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "bookings" (
	"id" serial PRIMARY KEY,
	"number" text NOT NULL UNIQUE,
	"public_token" text NOT NULL,
	"client_token" text UNIQUE,
	"model_id" integer NOT NULL,
	"model_name" text NOT NULL,
	"model_slug" text NOT NULL,
	"start_date" text NOT NULL,
	"end_date" text NOT NULL,
	"nights" integer NOT NULL,
	"address" text NOT NULL,
	"postal_code" text DEFAULT '' NOT NULL,
	"city" text DEFAULT '' NOT NULL,
	"country" text DEFAULT 'Deutschland' NOT NULL,
	"zone_name" text NOT NULL,
	"delivery_cents" integer NOT NULL,
	"rent_cents" integer NOT NULL,
	"extras_cents" integer NOT NULL,
	"gross_cents" integer NOT NULL,
	"vat_cents" integer NOT NULL,
	"extras" jsonb DEFAULT '[]' NOT NULL,
	"first_name" text NOT NULL,
	"last_name" text NOT NULL,
	"email" text NOT NULL,
	"phone" text NOT NULL,
	"notes" text DEFAULT '' NOT NULL,
	"payment_method" text NOT NULL,
	"payment_status" text NOT NULL,
	"card_brand" text DEFAULT '' NOT NULL,
	"card_last4" text DEFAULT '' NOT NULL,
	"card_exp" text DEFAULT '' NOT NULL,
	"status" text NOT NULL,
	"admin_note" text DEFAULT '' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"lat" double precision,
	"lng" double precision,
	"deposit_cents" integer DEFAULT 0 NOT NULL,
	"voucher_cents" integer DEFAULT 0 NOT NULL,
	"voucher_code" text DEFAULT '' NOT NULL,
	"arrival_window" text DEFAULT '' NOT NULL,
	"company" text DEFAULT '' NOT NULL,
	"company_vat" text DEFAULT '' NOT NULL,
	"access_ok" boolean DEFAULT false NOT NULL,
	"stripe_session" text DEFAULT '' NOT NULL
);
--> statement-breakpoint
CREATE TABLE "extras" (
	"id" serial PRIMARY KEY,
	"slug" text NOT NULL UNIQUE,
	"name" text NOT NULL,
	"description" text DEFAULT '' NOT NULL,
	"price_cents" integer NOT NULL,
	"kind" text NOT NULL,
	"image" text DEFAULT '' NOT NULL,
	"active" boolean DEFAULT true NOT NULL,
	"sort_order" integer DEFAULT 0 NOT NULL
);
--> statement-breakpoint
CREATE TABLE "messages" (
	"id" serial PRIMARY KEY,
	"name" text NOT NULL,
	"email" text NOT NULL,
	"phone" text DEFAULT '' NOT NULL,
	"body" text NOT NULL,
	"read" boolean DEFAULT false NOT NULL,
	"reply" text DEFAULT '' NOT NULL,
	"replied_at" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "models" (
	"id" serial PRIMARY KEY,
	"slug" text NOT NULL UNIQUE,
	"name" text NOT NULL,
	"subtitle" text DEFAULT '' NOT NULL,
	"badge" text DEFAULT '' NOT NULL,
	"price_cents" integer NOT NULL,
	"capacity_min" integer NOT NULL,
	"capacity_max" integer NOT NULL,
	"size" text NOT NULL,
	"features" jsonb DEFAULT '[]' NOT NULL,
	"specs" jsonb DEFAULT '[]' NOT NULL,
	"summary" text DEFAULT '' NOT NULL,
	"story_title" text DEFAULT '' NOT NULL,
	"story" text DEFAULT '' NOT NULL,
	"highlights" jsonb DEFAULT '[]' NOT NULL,
	"images" jsonb DEFAULT '[]' NOT NULL,
	"active" boolean DEFAULT true NOT NULL,
	"sort_order" integer DEFAULT 0 NOT NULL,
	"units" integer DEFAULT 1 NOT NULL,
	"included_text" text DEFAULT '' NOT NULL,
	"excluded_text" text DEFAULT '' NOT NULL
);
--> statement-breakpoint
CREATE TABLE "reviews" (
	"id" serial PRIMARY KEY,
	"author" text NOT NULL,
	"text" text NOT NULL,
	"rating" integer DEFAULT 5 NOT NULL,
	"model_slug" text DEFAULT '' NOT NULL,
	"active" boolean DEFAULT true NOT NULL,
	"sort_order" integer DEFAULT 0 NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "settings" (
	"key" text PRIMARY KEY,
	"value" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE "vouchers" (
	"id" serial PRIMARY KEY,
	"code" text NOT NULL UNIQUE,
	"cents" integer NOT NULL,
	"note" text DEFAULT '' NOT NULL,
	"active" boolean DEFAULT true NOT NULL,
	"max_uses" integer DEFAULT 1 NOT NULL,
	"used" integer DEFAULT 0 NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "zones" (
	"id" serial PRIMARY KEY,
	"name" text NOT NULL,
	"prefixes" text DEFAULT '' NOT NULL,
	"cities" text DEFAULT '' NOT NULL,
	"price_cents" integer NOT NULL,
	"note" text DEFAULT '' NOT NULL,
	"active" boolean DEFAULT true NOT NULL,
	"sort_order" integer DEFAULT 0 NOT NULL
);
--> statement-breakpoint
CREATE INDEX "idx_blocks_model" ON "blocks" ("model_id","start_date");--> statement-breakpoint
CREATE INDEX "idx_bookings_model" ON "bookings" ("model_id","start_date");--> statement-breakpoint
CREATE INDEX "idx_bookings_status" ON "bookings" ("status");--> statement-breakpoint
CREATE INDEX "idx_bookings_email" ON "bookings" ("email");--> statement-breakpoint
ALTER TABLE "blocks" ADD CONSTRAINT "blocks_model_id_models_id_fkey" FOREIGN KEY ("model_id") REFERENCES "models"("id") ON DELETE CASCADE;--> statement-breakpoint
ALTER TABLE "booking_events" ADD CONSTRAINT "booking_events_booking_id_bookings_id_fkey" FOREIGN KEY ("booking_id") REFERENCES "bookings"("id") ON DELETE CASCADE;--> statement-breakpoint
ALTER TABLE "bookings" ADD CONSTRAINT "bookings_model_id_models_id_fkey" FOREIGN KEY ("model_id") REFERENCES "models"("id");