#!/usr/bin/env python3
"""Seed the demo database and verify readiness.

Usage:
    python demo/seed.py                      # default: localhost:5432
    python demo/seed.py --dsn postgresql://ant:ant@postgres:5432/ant
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

SEED_SQL = Path(__file__).parent / "seed.sql"

DEFAULT_DSN = "postgresql://ant:ant@localhost:5432/ant"


def wait_for_postgres(dsn: str, retries: int = 30, delay: float = 2.0) -> None:
    """Block until Postgres accepts connections."""
    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["psql", dsn, "-c", "SELECT 1"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                print(f"  Postgres ready (attempt {attempt + 1})")
                return
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        print(f"  Waiting for Postgres... ({attempt + 1}/{retries})")
        time.sleep(delay)
    print("ERROR: Postgres did not become ready", file=sys.stderr)
    sys.exit(1)


def run_migrations(dsn: str) -> None:
    """Run Alembic migrations to create tables."""
    control_plane_dir = Path(__file__).parent.parent / "services" / "control-plane"
    print("Running Alembic migrations...")
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=control_plane_dir,
        env={**__import__("os").environ, "POSTGRES_DSN": dsn},
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Migrations may already be applied — check for "already at head"
        if "already" in result.stdout.lower() or "already" in result.stderr.lower():
            print("  Migrations already applied.")
        else:
            print(f"  Migration output: {result.stdout}")
            print(f"  Migration errors: {result.stderr}")
            # Continue anyway — tables may already exist from prior run


def load_seed_data(dsn: str) -> None:
    """Load seed SQL into the database."""
    print(f"Loading seed data from {SEED_SQL.name}...")
    result = subprocess.run(
        ["psql", dsn, "-f", str(SEED_SQL)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  psql stderr: {result.stderr}")
        # Check for duplicate key errors (idempotent re-run)
        if "duplicate key" in result.stderr.lower():
            print("  Seed data already loaded (duplicate keys detected). Skipping.")
            return
        print("WARNING: Seed loading had errors — check output above.", file=sys.stderr)
    else:
        print("  Seed data loaded successfully.")


def verify(dsn: str) -> None:
    """Print row counts for each seeded table."""
    tables = ["tenants", "approval_requests", "approval_steps", "audit_events"]
    print("\n=== Demo Data Verification ===")
    for table in tables:
        result = subprocess.run(
            ["psql", dsn, "-t", "-c", f"SELECT COUNT(*) FROM {table}"],
            capture_output=True,
            text=True,
        )
        count = result.stdout.strip() if result.returncode == 0 else "ERROR"
        print(f"  {table}: {count} rows")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Ant Automations demo database")
    parser.add_argument("--dsn", default=DEFAULT_DSN, help="PostgreSQL connection string")
    parser.add_argument("--skip-migrations", action="store_true", help="Skip Alembic migrations")
    args = parser.parse_args()

    print("=== Ant Automations Demo Seeder ===\n")

    wait_for_postgres(args.dsn)

    if not args.skip_migrations:
        run_migrations(args.dsn)

    load_seed_data(args.dsn)
    verify(args.dsn)

    print("Demo environment ready!")
    print("  Control Plane API: http://localhost:8003")
    print("  Connectors API:    http://localhost:8002")
    print("  Grafana:           http://localhost:3000  (admin / admin)")
    print("  Prometheus:        http://localhost:9090")
    print()


if __name__ == "__main__":
    main()
