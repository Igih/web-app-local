#!/bin/sh
set -e
python init_db.py
alembic upgrade head
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 8
