#!/usr/bin/env bash
# Pull latest code from GitHub and rebuild. Usage: sudo ./deploy/update.sh
set -euo pipefail
cd "$(dirname "$0")/.."
git pull --ff-only || echo "git pull skipped (not a git checkout or local changes)"
docker compose -f deploy/docker-compose.yml up -d --build
docker image prune -f >/dev/null
echo "Updated and running."
