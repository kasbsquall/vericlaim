-- Dedicated VeriClaim app role. Created at DB init so the app never depends on the
-- shared "postgres" superuser (host tooling on the prod VPS keeps setting it NOLOGIN).
-- On that host, set DATABASE_URL to postgresql+asyncpg://vericlaim:vc_app_2026@localhost:5434/vericlaim
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vericlaim') THEN
    CREATE ROLE vericlaim LOGIN SUPERUSER PASSWORD 'vc_app_2026';
  ELSE
    ALTER ROLE vericlaim LOGIN SUPERUSER PASSWORD 'vc_app_2026';
  END IF;
END
$$;
ALTER ROLE postgres LOGIN;
GRANT ALL PRIVILEGES ON DATABASE vericlaim TO vericlaim;
