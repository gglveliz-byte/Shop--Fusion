-- Grants for shopfusion schema only. Run as DB owner/admin (not shopfusion_user).
GRANT USAGE ON SCHEMA shopfusion TO shopfusion_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA shopfusion TO shopfusion_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA shopfusion TO shopfusion_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA shopfusion
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO shopfusion_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA shopfusion
  GRANT USAGE, SELECT ON SEQUENCES TO shopfusion_user;
