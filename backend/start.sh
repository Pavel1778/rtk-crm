#!/bin/bash
set -e

echo "Running migrations..."
alembic upgrade head || echo "Migrations skipped (no alembic configured)"

echo "Seeding database (if empty)..."
python seed.py || echo "Seed skipped or already done"

echo "Starting server..."
uvicorn app.main:app --host 0.0.0.0 --port $PORT
