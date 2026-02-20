from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "users" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "email" VARCHAR(255)  UNIQUE,
    "phone" VARCHAR(20)  UNIQUE,
    "username" VARCHAR(100)  UNIQUE,
    "is_active" BOOL NOT NULL  DEFAULT True,
    "is_verified" BOOL NOT NULL  DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_users_email_133a6f" ON "users" ("email");
CREATE INDEX IF NOT EXISTS "idx_users_phone_f72cc5" ON "users" ("phone");
CREATE INDEX IF NOT EXISTS "idx_users_usernam_266d85" ON "users" ("username");
COMMENT ON TABLE "users" IS 'User model for authentication and authorization.';
CREATE TABLE IF NOT EXISTS "sessions" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "session_token_hash" VARCHAR(64) NOT NULL UNIQUE,
    "expires_at" TIMESTAMPTZ NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "last_activity" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "user_agent" TEXT,
    "ip_address" VARCHAR(45),
    "user_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_sessions_session_20e2b6" ON "sessions" ("session_token_hash");
COMMENT ON TABLE "sessions" IS 'Session model for managing user sessions.';
CREATE TABLE IF NOT EXISTS "verification_codes" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "contact" VARCHAR(255) NOT NULL,
    "contact_type" VARCHAR(10) NOT NULL,
    "code_hash" VARCHAR(64) NOT NULL,
    "expires_at" TIMESTAMPTZ NOT NULL,
    "attempts" INT NOT NULL  DEFAULT 0,
    "is_used" BOOL NOT NULL  DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "user_id" UUID REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_verificatio_contact_e1b332" ON "verification_codes" ("contact");
COMMENT ON TABLE "verification_codes" IS 'Verification code for passwordless authentication.';
CREATE TABLE IF NOT EXISTS "businesses" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT NOT NULL,
    "business_type" VARCHAR(10) NOT NULL,
    "telegram_bot_token" VARCHAR(500) NOT NULL,
    "is_active" BOOL NOT NULL  DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "owner_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "businesses"."business_type" IS 'RESTAURANT: restaurant\nBARBERSHOP: barbershop\nPARKING: parking\nRETAIL: retail\nSERVICE: service\nOTHER: other';
COMMENT ON TABLE "businesses" IS 'Business model representing a business with a Telegram bot.';
CREATE TABLE IF NOT EXISTS "dishes" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "title" VARCHAR(100) NOT NULL,
    "description" TEXT NOT NULL,
    "price" DECIMAL(10,2) NOT NULL,
    "image_path" VARCHAR(500) NOT NULL,
    "is_available" BOOL NOT NULL  DEFAULT True,
    "tags" JSONB NOT NULL,
    "category" VARCHAR(50),
    "cuisine" VARCHAR(50),
    "ingredients" JSONB NOT NULL,
    "allergens" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "business_id" UUID NOT NULL REFERENCES "businesses" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_dishes_title_3b48a1" ON "dishes" ("title");
CREATE INDEX IF NOT EXISTS "idx_dishes_categor_5e30b0" ON "dishes" ("category");
CREATE INDEX IF NOT EXISTS "idx_dishes_cuisine_2eaf36" ON "dishes" ("cuisine");
COMMENT ON COLUMN "dishes"."tags" IS 'List of tags for search';
COMMENT ON COLUMN "dishes"."category" IS 'Category (e.g., ''appetizer'', ''main'', ''dessert'')';
COMMENT ON COLUMN "dishes"."cuisine" IS 'Cuisine type (e.g., ''italian'', ''asian'')';
COMMENT ON COLUMN "dishes"."ingredients" IS 'List of main ingredients';
COMMENT ON COLUMN "dishes"."allergens" IS 'List of allergens';
COMMENT ON TABLE "dishes" IS 'Dish database model representing a menu item for a business.';
CREATE TABLE IF NOT EXISTS "tg_users" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "telegram_id" BIGINT NOT NULL UNIQUE,
    "username" VARCHAR(255),
    "first_name" VARCHAR(255),
    "last_name" VARCHAR(255),
    "language_code" VARCHAR(10) NOT NULL  DEFAULT 'ru',
    "thread_id" VARCHAR(255),
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "last_interaction" TIMESTAMPTZ,
    "is_active" BOOL NOT NULL  DEFAULT True,
    "is_blocked" BOOL NOT NULL  DEFAULT False
);
CREATE INDEX IF NOT EXISTS "idx_tg_users_telegra_7c9b9b" ON "tg_users" ("telegram_id");
COMMENT ON TABLE "tg_users" IS 'Telegram user model.';
CREATE TABLE IF NOT EXISTS "tables" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "table_number" INT NOT NULL,
    "capacity" INT NOT NULL,
    "floor" INT NOT NULL  DEFAULT 1,
    "status" VARCHAR(9) NOT NULL  DEFAULT 'available',
    "is_active" BOOL NOT NULL  DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "business_id" UUID NOT NULL REFERENCES "businesses" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_tables_busines_393e00" UNIQUE ("business_id", "table_number")
);
COMMENT ON COLUMN "tables"."status" IS 'AVAILABLE: available\nBOOKED: booked\nOCCUPIED: occupied';
COMMENT ON TABLE "tables" IS 'Table model representing a restaurant table.';
CREATE TABLE IF NOT EXISTS "table_bookings" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "guest_name" VARCHAR(255) NOT NULL,
    "guest_phone" VARCHAR(20),
    "num_guests" INT NOT NULL,
    "booking_date" DATE NOT NULL,
    "booking_time" TIMETZ NOT NULL,
    "duration_minutes" INT NOT NULL  DEFAULT 120,
    "notes" TEXT,
    "is_cancelled" BOOL NOT NULL  DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "table_id" UUID NOT NULL REFERENCES "tables" ("id") ON DELETE CASCADE,
    "tg_user_id" INT NOT NULL REFERENCES "tg_users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "table_bookings" IS 'Table booking model for restaurant reservations.';
CREATE TABLE IF NOT EXISTS "barbers" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "specialization" VARCHAR(255),
    "image_path" VARCHAR(500),
    "is_active" BOOL NOT NULL  DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "business_id" UUID NOT NULL REFERENCES "businesses" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "barbers"."specialization" IS 'e.g. ''Классические стрижки, Борода''';
COMMENT ON TABLE "barbers" IS 'Barber model representing a master/barber in a barbershop.';
CREATE TABLE IF NOT EXISTS "barber_schedules" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "weekday" INT NOT NULL,
    "start_time" TIMETZ NOT NULL,
    "end_time" TIMETZ NOT NULL,
    "is_active" BOOL NOT NULL  DEFAULT True,
    "barber_id" UUID NOT NULL REFERENCES "barbers" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "barber_schedules"."weekday" IS 'Day of week: 0=Monday, 1=Tuesday, ..., 6=Sunday';
COMMENT ON COLUMN "barber_schedules"."start_time" IS 'Slot start time (e.g. 10:00)';
COMMENT ON COLUMN "barber_schedules"."end_time" IS 'Slot end time (e.g. 10:30)';
COMMENT ON TABLE "barber_schedules" IS 'Weekly schedule for a barber: which days and time slots are available.';
CREATE TABLE IF NOT EXISTS "barber_services" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "price" DECIMAL(10,2) NOT NULL,
    "duration_minutes" INT NOT NULL,
    "is_active" BOOL NOT NULL  DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "barber_id" UUID NOT NULL REFERENCES "barbers" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "barber_services"."duration_minutes" IS 'Duration of the service in minutes';
COMMENT ON TABLE "barber_services" IS 'Service offered by a barber (e.g. haircut, beard trim).';
CREATE TABLE IF NOT EXISTS "barber_appointments" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "guest_name" VARCHAR(255) NOT NULL,
    "guest_phone" VARCHAR(20),
    "appointment_date" DATE NOT NULL,
    "appointment_time" TIMETZ NOT NULL,
    "status" VARCHAR(9) NOT NULL  DEFAULT 'pending',
    "notes" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "barber_id" UUID NOT NULL REFERENCES "barbers" ("id") ON DELETE CASCADE,
    "service_id" UUID NOT NULL REFERENCES "barber_services" ("id") ON DELETE CASCADE,
    "tg_user_id" INT NOT NULL REFERENCES "tg_users" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "barber_appointments"."status" IS 'PENDING: pending\nCONFIRMED: confirmed\nCANCELLED: cancelled\nCOMPLETED: completed';
COMMENT ON TABLE "barber_appointments" IS 'Appointment record: a client books a barber for a specific service at a specific time.';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
