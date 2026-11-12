import json
import os


class Config:
    SECRET_KEY = os.environ.get("JWT_SECRET") or "dev-secret-key-medicard-local-1234567890"
    JWT_ISSUER = os.environ.get("JWT_ISSUER", "medicard-api")
    JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "medicard-clients")
    ACCESS_TOKEN_TTL_SECONDS = int(os.environ.get("ACCESS_TOKEN_TTL_SECONDS", "900"))
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "medicard")
    MYSQL_USER = os.environ.get("MYSQL_USER", "medicard_app")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "medicard_password")
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
    MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/medicard")
    PATIENT_HMAC_KEY = os.environ.get("PATIENT_HMAC_KEY") or "medicard-patient-hmac-key-32bytes-long!!"
    DATA_ENCRYPTION_KEY = os.environ.get("DATA_ENCRYPTION_KEY") or "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    IDENTITY_PUBLIC_KEY = os.environ.get("IDENTITY_PUBLIC_KEY", "")
    IDENTITY_TRUSTED_ISSUER = os.environ.get("IDENTITY_TRUSTED_ISSUER", "medicard-issuer")
    CORS_ORIGINS = [item.strip() for item in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if item.strip()]
    TRUST_PROXY = os.environ.get("TRUST_PROXY", "0") == "1"
    AUTH_USERS = json.loads(os.environ.get("MEDICARD_AUTH_USERS_JSON", "{}"))
    SQLITE_PATH = os.environ.get("SQLITE_PATH", os.path.abspath(os.path.join(os.getcwd(), "medicard.db")))
    DATABASE_MODE = os.environ.get("DATABASE_MODE", "sqlite")

    @staticmethod
    def validate(config):
        if config.get("SECRET_KEY") and len(config["SECRET_KEY"]) < 32:
            raise RuntimeError("JWT_SECRET must be at least 32 characters")
        if config.get("PATIENT_HMAC_KEY") and len(config["PATIENT_HMAC_KEY"]) < 32:
            raise RuntimeError("PATIENT_HMAC_KEY must be at least 32 characters")
        if not isinstance(config.get("AUTH_USERS", {}), dict):
            raise RuntimeError("MEDICARD_AUTH_USERS_JSON must be a valid JSON object")
        if config.get("ACCESS_TOKEN_TTL_SECONDS") and not (60 <= int(config["ACCESS_TOKEN_TTL_SECONDS"]) <= 3600):
            raise RuntimeError("ACCESS_TOKEN_TTL_SECONDS must be between 60 and 3600")
        if config.get("CORS_ORIGINS") == []:
            raise RuntimeError("CORS_ORIGINS must contain at least one allowed origin")
