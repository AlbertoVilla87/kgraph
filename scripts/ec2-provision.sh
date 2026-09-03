#!/usr/bin/env bash
# ── EC2 one-time provision script ──────────────────────────────────
# Run this once on a fresh EC2 instance (Amazon Linux 2023) to set up
# the Astrolabe deployment. The instance user_data already installs
# Docker; this script clones the repo and prepares the .env file.
#
# Usage (via SSM or SSH as ec2-user):
#   bash /tmp/ec2-provision.sh
# ───────────────────────────────────────────────────────────────────

set -euo pipefail

REPO_URL="https://github.com/AlbertoVilla87/kgraph.git"
DEPLOY_DIR="/home/ec2-user/kgraph"

echo "[1/4] Cloning repo..."
if [ -d "$DEPLOY_DIR" ]; then
    echo "  Repo already exists at $DEPLOY_DIR, pulling..."
    cd "$DEPLOY_DIR"
    git pull
else
    git clone "$REPO_URL" "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
fi

echo "[2/4] Setting up .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  Created .env from .env.example — edit if needed."
else
    echo "  .env already exists, skipping."
fi

echo "[3/4] Pulling Docker images..."
docker compose pull 2>/dev/null || echo "  No pre-built images in ECR yet — will build locally on first run."

echo "[4/4] Starting services..."
docker compose up -d --remove-orphans

echo ""
echo "Done. Services:"
docker compose ps
echo ""
echo "Backend health: curl http://localhost:8000/api/health"
echo "Frontend:       http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
