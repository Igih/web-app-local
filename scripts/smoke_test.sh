#!/bin/sh
set -eu

echo "== docker compose config =="
docker compose config >/dev/null

echo "== backend syntax check =="
python3 -m compileall -q backend

echo "== frontend build =="
cd frontend
npm run build

echo "Smoke checks passed."
