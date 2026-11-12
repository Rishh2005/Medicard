from functools import lru_cache

from pymongo import MongoClient
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


def get_mysql_engine(config):
    key = mysql_url(config).render_as_string(hide_password=False)
    return _mysql_engine(key)


@lru_cache(maxsize=4)
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


def get_mongo_client(config):
    return _mongo_client(config["MONGODB_URI"])


@lru_cache(maxsize=4)
def _mongo_client(uri):
    return MongoClient(
        uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=10000,
        retryWrites=True,
        appname="medicard-api",
    )


def check_dependencies(config):
    engine = get_mysql_engine(config)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    client = get_mongo_client(config)
    client.admin.command("ping")
    return engine, client
