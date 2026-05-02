#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import psycopg


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT_DIR / ".env"


def load_database_url() -> str:
    if not ENV_FILE.exists():
        raise FileNotFoundError(f".env file not found: {ENV_FILE}")

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "DATABASE_URL":
            db_url = value.strip().strip('"').strip("'")
            if db_url:
                return db_url

    raise RuntimeError("DATABASE_URL is missing in .env")


def migrate() -> None:
    database_url = load_database_url()

    statements = [
        "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS password_hash TEXT",
        "ALTER TABLE profiles ALTER COLUMN password_hash DROP NOT NULL",
    ]

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)

            cur.execute(
                """
                SELECT column_name, is_nullable, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'profiles'
                  AND column_name = 'password_hash'
                """
            )
            row = cur.fetchone()

        conn.commit()

    if not row:
        raise RuntimeError("Migration failed: profiles.password_hash not found")

    print("Migration complete")
    print(f"column={row[0]} nullable={row[1]} type={row[2]}")


if __name__ == "__main__":
    migrate()