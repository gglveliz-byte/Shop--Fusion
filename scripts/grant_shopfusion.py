import argparse
import os
import sys

import psycopg


def _split_sql(sql_text):
    statements = []
    for chunk in sql_text.split(";"):
        stmt = chunk.strip()
        if stmt:
            statements.append(stmt)
    return statements


def main():
    parser = argparse.ArgumentParser(
        description="Apply grants for shopfusion schema using an admin DB URL."
    )
    parser.add_argument(
        "--db-url",
        default=os.environ.get("ADMIN_DATABASE_URL"),
        help="Admin DATABASE_URL (or set ADMIN_DATABASE_URL env var).",
    )
    default_sql = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "grants_shopfusion.sql"
    )
    parser.add_argument(
        "--sql",
        default=default_sql,
        help="Path to grants SQL file (default: grants_shopfusion.sql).",
    )
    args = parser.parse_args()

    if not args.db_url:
        print("Missing ADMIN_DATABASE_URL or --db-url.", file=sys.stderr)
        return 2

    if not os.path.exists(args.sql):
        print(f"SQL file not found: {args.sql}", file=sys.stderr)
        return 2

    with open(args.sql, "r", encoding="utf-8") as f:
        sql_text = f.read()

    statements = _split_sql(sql_text)
    if not statements:
        print("No SQL statements found.", file=sys.stderr)
        return 2

    conn = psycopg.connect(args.db_url)
    try:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()

    print("Grants applied successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
