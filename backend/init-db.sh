#!/bin/bash
# Database initialization script for Docker PostgreSQL
# This runs automatically when the container starts for the first time

set -e

echo "Waiting for PostgreSQL to be ready..."
until pg_isready -U postgres; do
  sleep 1
done

echo "PostgreSQL is ready. Initializing database schema..."

# Run the Python schema creation script
cd /docker-entrypoint-initdb.d
python3 create_schema.py

echo "Database initialization complete!"
