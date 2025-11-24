import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Config


def main():
    parser = argparse.ArgumentParser(description="Execute arbitrary SQL against the configured database.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--sql",
        help="SQL statement to execute. Use parameter placeholders like :name and pass via --param name=value.",
    )
    group.add_argument(
        "--sql-file",
        help="Path to a file containing the SQL statement.",
    )
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="Parameter in the form key=value. Repeat for multiple parameters.",
    )
    args = parser.parse_args()

    params = {}
    for pair in args.param:
        if "=" not in pair:
            parser.error(f"Invalid --param '{pair}', expected key=value")
        key, value = pair.split("=", 1)
        params[key] = value

    statement = args.sql
    if args.sql_file:
        statement = Path(args.sql_file).read_text(encoding="utf-8")

    engine = create_engine(Config.DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text(statement), params)
        if result.returns_rows:
            rows = result.fetchall()
            for row in rows:
                print(dict(row._mapping))
            print(f"[INFO] Returned {len(rows)} row(s)")
        else:
            conn.commit()
            print("[INFO] Statement executed successfully")


if __name__ == "__main__":
    main()

