-- CLIMA-KIDS ALERT — PostgreSQL schema for alert subscribers (open-source deploy)
-- Apply on your own PostGIS/PostgreSQL instance after creating the database.
-- Compatible with Alembic migration 003 (same logical model).

CREATE TYPE IF NOT EXISTS subscriber_user_type AS ENUM (
  'school',
  'association',
  'parent',
  'other'
);

CREATE TYPE IF NOT EXISTS location_source_type AS ENUM (
  'gps',
  'ip',
  'stored'
);

-- Extend existing table (safe if columns already exist via Alembic)
ALTER TABLE alert_subscribers
  ADD COLUMN IF NOT EXISTS user_type subscriber_user_type NOT NULL DEFAULT 'other',
  ADD COLUMN IF NOT EXISTS location_source location_source_type,
  ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- Drop strict unique email if present (merge handles identity)
DROP INDEX IF EXISTS ix_alert_subscribers_email;
CREATE INDEX IF NOT EXISTS ix_alert_subscribers_email_lower
  ON alert_subscribers (lower(email));

CREATE TABLE IF NOT EXISTS unsubscribe_requests (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255),
  phone_e164 VARCHAR(32),
  whatsapp_e164 VARCHAR(32),
  user_type subscriber_user_type,
  payload_json JSONB,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_unsubscribe_requests_status ON unsubscribe_requests (status);

-- Merge helper: find an active row matching email or phone or WhatsApp
CREATE OR REPLACE FUNCTION fn_alert_subscriber_find_match(
  p_email VARCHAR,
  p_phone VARCHAR,
  p_whatsapp VARCHAR
) RETURNS INTEGER AS $$
DECLARE
  v_id INTEGER;
BEGIN
  SELECT id INTO v_id
  FROM alert_subscribers
  WHERE is_active
    AND (
      (p_email IS NOT NULL AND p_email <> '' AND lower(email) = lower(p_email))
      OR (p_phone IS NOT NULL AND p_phone <> '' AND phone_e164 = p_phone)
      OR (p_whatsapp IS NOT NULL AND p_whatsapp <> '' AND whatsapp_e164 = p_whatsapp)
      OR (p_phone IS NOT NULL AND p_phone <> '' AND whatsapp_e164 = p_phone)
      OR (p_whatsapp IS NOT NULL AND p_whatsapp <> '' AND phone_e164 = p_whatsapp)
    )
  ORDER BY id
  LIMIT 1;
  RETURN v_id;
END;
$$ LANGUAGE plpgsql STABLE;

-- BEFORE INSERT: merge into existing row when identifiers overlap
CREATE OR REPLACE FUNCTION trg_alert_subscribers_merge_bi()
RETURNS TRIGGER AS $$
DECLARE
  v_existing INTEGER;
BEGIN
  v_existing := fn_alert_subscriber_find_match(NEW.email, NEW.phone_e164, NEW.whatsapp_e164);
  IF v_existing IS NULL THEN
    NEW.updated_at := now();
    RETURN NEW;
  END IF;

  UPDATE alert_subscribers SET
    email = COALESCE(NULLIF(trim(NEW.email), ''), email),
    phone_e164 = COALESCE(NEW.phone_e164, phone_e164),
    whatsapp_e164 = COALESCE(NEW.whatsapp_e164, whatsapp_e164),
    user_type = COALESCE(NEW.user_type, user_type),
    school_id = COALESCE(NEW.school_id, school_id),
    home_lat = COALESCE(NEW.home_lat, home_lat),
    home_lon = COALESCE(NEW.home_lon, home_lon),
    location_source = COALESCE(NEW.location_source, location_source),
    alert_email_enabled = alert_email_enabled OR NEW.alert_email_enabled,
    alert_sms_enabled = alert_sms_enabled OR NEW.alert_sms_enabled,
    alert_whatsapp_enabled = alert_whatsapp_enabled OR NEW.alert_whatsapp_enabled,
    is_active = TRUE,
    updated_at = now()
  WHERE id = v_existing;

  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS alert_subscribers_merge_bi ON alert_subscribers;
CREATE TRIGGER alert_subscribers_merge_bi
  BEFORE INSERT ON alert_subscribers
  FOR EACH ROW
  EXECUTE FUNCTION trg_alert_subscribers_merge_bi();

-- BEFORE UPDATE: channel flags merge with OR semantics
CREATE OR REPLACE FUNCTION trg_alert_subscribers_merge_bu()
RETURNS TRIGGER AS $$
BEGIN
  NEW.alert_email_enabled := OLD.alert_email_enabled OR NEW.alert_email_enabled;
  NEW.alert_sms_enabled := OLD.alert_sms_enabled OR NEW.alert_sms_enabled;
  NEW.alert_whatsapp_enabled := OLD.alert_whatsapp_enabled OR NEW.alert_whatsapp_enabled;
  NEW.updated_at := now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS alert_subscribers_merge_bu ON alert_subscribers;
CREATE TRIGGER alert_subscribers_merge_bu
  BEFORE UPDATE ON alert_subscribers
  FOR EACH ROW
  EXECUTE FUNCTION trg_alert_subscribers_merge_bu();
