from __future__ import annotations

from pathlib import Path

from db.connection import get_connection, is_database_enabled


SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"


POST_SCHEMA_STATEMENTS = [
    """
    alter table if exists run_jobs
    add column if not exists has_keyword_match boolean not null default false
    """,
]


def initialize_database() -> bool:
    if not is_database_enabled():
        raise RuntimeError("DATABASE_URL no está configurado o psycopg no está instalado.")

    schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")

    with get_connection() as conn:
        if conn is None:
            return False

        with conn.cursor() as cur:
            cur.execute(schema_sql)
            for statement in POST_SCHEMA_STATEMENTS:
                cur.execute(statement)

    return True


def main() -> None:
    initialize_database()
    print("Base de datos inicializada correctamente.")


if __name__ == "__main__":
    main()
