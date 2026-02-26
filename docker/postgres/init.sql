-- WishShare PostgreSQL initialization script
-- This script runs when the PostgreSQL container starts for the first time

-- Set timezone
SET TIME ZONE 'UTC';

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant permissions to wishshare user
GRANT ALL PRIVILEGES ON DATABASE wishshare TO wishshare;

-- Note: Tables will be created automatically by SQLAlchemy's create_all()
-- This script is primarily for initial setup and extensions
