-- Initialize Zid Integration Database
-- This script sets up the initial database configuration

-- Create extensions if they don't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create database schema (already created by POSTGRES_DB)
-- Just ensure proper permissions and settings

-- Set timezone
SET timezone = 'UTC';

-- Create indexes for better performance on commonly queried fields
-- These will be created by Alembic migrations, but good to have as backup

-- Log the initialization
DO $$ 
BEGIN 
    RAISE NOTICE 'Zid Integration Database initialized successfully at %', NOW();
END $$;