import os
from functools import lru_cache

from sqlalchemy import create_engine, text


def mysql_url(config):
    from sqlalchemy.engine import URL

    return URL.create(
        "mysql+pymysql",
        username=config["MYSQL_USER"],
        password=config["MYSQL_PASSWORD"],
        host=config["MYSQL_HOST"],
        port=config["MYSQL_PORT"],
        database=config["MYSQL_DATABASE"],
        query={"charset": "utf8mb4"},
    )


def get_sqlite_path(config):
    return config.get("SQLITE_PATH", os.path.abspath(os.path.join(os.getcwd(), "medicard.db")))


@lru_cache(maxsize=8)
def _sqlite_engine(path):
    engine = create_engine(f"sqlite:///{path}", future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS patient_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_key TEXT NOT NULL,
                    ciphertext BLOB NOT NULL,
                    nonce BLOB NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_patient_records_patient_key ON patient_records(patient_key)"
            )
        )
    return engine


@lru_cache(maxsize=8)
def _mysql_engine(url):
    return create_engine(
        url,
        pool_size=10,
        max_overflow=5,
        pool_timeout=10,
        pool_recycle=1800,
        pool_pre_ping=True,
        pool_use_lifo=True,
    )


def get_mysql_engine(config):
    return _mysql_engine(mysql_url(config).render_as_string(hide_password=False))


def get_sqlite_engine(config):
    return _sqlite_engine(get_sqlite_path(config))


def get_database_engine(config):
    mysql_host = str(config.get("MYSQL_HOST") or "").strip()
    if mysql_host:
        try:
            engine = get_mysql_engine(config)
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return engine
        except Exception:
            return get_sqlite_engine(config)
    return get_sqlite_engine(config)


def check_dependencies(config):
    engine = get_database_engine(config)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return engine
