#!/usr/bin/env bash
# Ant Automations — Demo Reset
# Tears down all demo containers and volumes, then rebuilds with fresh seed data.
#
# Usage: ./demo/reset.sh

set -euo pipefail

COMPOSE_FILE="docker-compose.demo.yml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== Ant Automations Demo Reset ==="
echo ""

# Step 1: Stop all containers
echo "[1/4] Stopping containers..."
docker-compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true

# Step 2: Remove demo volumes (fresh database)
echo "[2/4] Removing demo volumes..."
docker volume rm \
  "$(basename "$PROJECT_DIR" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]')_demo-pgdata" \
  "$(basename "$PROJECT_DIR" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]')_demo-redisdata" \
  "$(basename "$PROJECT_DIR" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]')_demo-natsdata" \
  "$(basename "$PROJECT_DIR" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]')_demo-miniodata" \
  "$(basename "$PROJECT_DIR" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]')_demo-promdata" \
  "$(basename "$PROJECT_DIR" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]')_demo-grafanadata" \
  2>/dev/null || true

# Also try with docker-compose down -v which is more reliable
docker-compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true

# Step 3: Rebuild images (picks up any code changes)
echo "[3/4] Rebuilding images..."
docker-compose -f "$COMPOSE_FILE" build --quiet

# Step 4: Start fresh
echo "[4/4] Starting fresh demo environment..."
docker-compose -f "$COMPOSE_FILE" up -d

echo ""
echo "=== Waiting for services to become healthy... ==="
sleep 5

# Poll for health (up to 90 seconds)
for i in $(seq 1 18); do
    healthy=$(docker-compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null | grep -c '"healthy"' || echo "0")
    total=$(docker-compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null | grep -c '"running"' || echo "0")
    echo "  Health check $i/18: $healthy healthy, $total running"

    if [ "$healthy" -ge 5 ]; then
        break
    fi
    sleep 5
done

echo ""
echo "=== Demo Reset Complete ==="
echo ""
echo "Services:"
docker-compose -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || \
  docker-compose -f "$COMPOSE_FILE" ps

echo ""
echo "Ready for demo!"
echo "  Control Plane: http://localhost:8003/docs"
echo "  Connectors:    http://localhost:8002/docs"
echo "  Grafana:       http://localhost:3000  (admin / admin)"
echo ""
