-- Example subscriber (email channel only) — safe to re-run
INSERT INTO alert_subscribers (
  email,
  phone_e164,
  whatsapp_e164,
  user_type,
  alert_email_enabled,
  alert_sms_enabled,
  alert_whatsapp_enabled,
  is_active
)
SELECT
  'mulombodi@sol-agri-tech.org',
  NULL,
  NULL,
  'other',
  TRUE,
  FALSE,
  FALSE,
  TRUE
WHERE NOT EXISTS (
  SELECT 1 FROM alert_subscribers
  WHERE lower(email) = 'mulombodi@sol-agri-tech.org' AND is_active
);
