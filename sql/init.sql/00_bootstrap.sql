-- ===================================================
-- SME Pulse: PostgreSQL Bootstrap Init
-- ===================================================
-- This script runs on first postgres start (via docker-entrypoint-initdb.d)
-- Creates all necessary databases and roles for the stack.

-- 1. Create Metabase database (analytics BI)
--    Hive Metastore uses the default 'sme' DB (via SERVICE_OPTS override)
CREATE DATABASE metabase OWNER sme;

-- 2. Grant connect on default 'sme' DB for Airflow + Hive
-- (sme DB is auto-created by POSTGRES_DB env var)
GRANT ALL PRIVILEGES ON DATABASE sme TO sme;
