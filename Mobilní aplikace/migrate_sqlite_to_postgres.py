import argparse
import os
import sqlite3
from datetime import date

from flask import Flask
from sqlalchemy import text

from models import db, Pozadavek, Uzivatel


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "databaze.db")


def normalize_database_url(database_url):
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    return database_url


def create_app(database_url):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "migration-only"
    app.config["SQLALCHEMY_DATABASE_URI"] = normalize_database_url(database_url)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    return app


def parse_date(value):
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def fetch_rows(sqlite_path, table_name):
    connection = sqlite3.connect(sqlite_path)
    connection.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in connection.execute(f"SELECT * FROM {table_name}")]
    finally:
        connection.close()


def reset_postgres_sequence(table_name):
    sequence_sql = text(
        f"""
        SELECT setval(
            pg_get_serial_sequence('{table_name}', 'id'),
            COALESCE((SELECT MAX(id) FROM {table_name}), 1),
            (SELECT COUNT(*) FROM {table_name}) > 0
        )
        """
    )
    db.session.execute(sequence_sql)


def migrate(sqlite_path, database_url):
    app = create_app(database_url)

    with app.app_context():
        db.create_all()

        users = fetch_rows(sqlite_path, "uzivatel")
        requests = fetch_rows(sqlite_path, "pozadavek")

        for row in users:
            db.session.merge(
                Uzivatel(
                    id=row["id"],
                    uzivatelske_jmeno=row["uzivatelske_jmeno"],
                    heslo_hash=row["heslo_hash"],
                    realne_jmeno=row["realne_jmeno"],
                    role=row["role"],
                )
            )

        for row in requests:
            db.session.merge(
                Pozadavek(
                    id=row["id"],
                    jmeno=row["jmeno"],
                    pozice=row["pozice"],
                    datum=parse_date(row["datum"]),
                    typ_pozadavku=row["typ_pozadavku"],
                    poznamka=row["poznamka"],
                    stav=row["stav"],
                    admin_poznamka=row["admin_poznamka"],
                )
            )

        if db.engine.dialect.name == "postgresql":
            reset_postgres_sequence("uzivatel")
            reset_postgres_sequence("pozadavek")

        db.session.commit()
        print(f"Hotovo: preneseno {len(users)} uzivatelu a {len(requests)} pozadavku.")


def main():
    parser = argparse.ArgumentParser(description="Prenese data ze SQLite databaze do PostgreSQL.")
    parser.add_argument("--sqlite", default=DEFAULT_SQLITE_PATH, help="Cesta k SQLite souboru.")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL DATABASE_URL. Pokud neni zadano, pouzije se promenna prostredi DATABASE_URL.",
    )
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("Chybi DATABASE_URL. Zadej --database-url nebo nastav promennou prostredi DATABASE_URL.")

    if not os.path.exists(args.sqlite):
        raise SystemExit(f"SQLite databaze neexistuje: {args.sqlite}")

    migrate(args.sqlite, args.database_url)


if __name__ == "__main__":
    main()
