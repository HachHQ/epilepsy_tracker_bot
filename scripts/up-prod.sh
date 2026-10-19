#!/usr/bin/env bash
# Build and start the VPS stack. A future deploy job should git pull, then run this.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

docker compose -f docker-compose.prod.yml up -d --build --remove-orphans --wait
docker compose -f docker-compose.prod.yml ps
