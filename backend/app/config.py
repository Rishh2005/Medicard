import json
import os
import base64


class Config:
    SECRET_KEY = os.environ.get("JWT_SECRET", "")
    JWT_ISSUER = os.environ.get("JWT_ISSUER", "medicard-api")
    JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "medicard-clients")
    ACCESS_TOKEN_TTL_SECONDS = int(os.environ.get("ACCESS_TOKEN_TTL_SECONDS", "900"))
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "medicard")
    MYSQL_USER = os.environ.get("MYSQL_USER", "medicard_app")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
    MONGODB_URI = os.environ.get("MONGODB_URI", "")
    PATIENT_HMAC_KEY = os.environ.get("PATIENT_HMAC_KEY", "")
    DATA_ENCRYPTION_KEY = os.environ.get("DATA_ENCRYPTION_KEY", "")
    IDENTITY_PUBLIC_KEY = os.environ.get("IDENTITY_PUBLIC_KEY", "")
    IDENTITY_TRUSTED_ISSUER = os.environ.get("IDENTITY_TRUSTED_ISSUER", "")
    CORS_ORIGINS = [item.strip() for item in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if item.strip()]
    TRUST_PROXY = os.environ.get("TRUST_PROXY", "0") == "1"
    AUTH_USERS = json.loads(os.environ.get("MEDICARD_AUTH_USERS_JSON", "{}"))

    @staticmethod
    def validate(config):
        required = (
            "SECRET_KEY",
            "MYSQL_PASSWORD",
            "MONGODB_URI",
            "PATIENT_HMAC_KEY",
            "DATA_ENCRYPTION_KEY",
            "IDENTITY_PUBLIC_KEY",
            "IDENTITY_TRUSTED_ISSUER",
        )
        missing = [key for key in required if not config.get(key)]
        if missing:
            raise RuntimeError(f"Missing required configuration: {', '.join(missing)}")
        if len(config["SECRET_KEY"]) < 32:
            raise RuntimeError("JWT_SECRET must be at least 32 characters")
        if len(config["PATIENT_HMAC_KEY"]) < 32:
            raise RuntimeError("PATIENT_HMAC_KEY must be at least 32 characters")
        if not isinstance(config["AUTH_USERS"], dict) or not config["AUTH_USERS"]:
            raise RuntimeError("MEDICARD_AUTH_USERS_JSON must define at least one account")
        allowed_scopes = {
            "records:read",
            "records:read:full",
            "records:write",
            "clinical:route",
            "identity:verify",
        }
        for username, account in config["AUTH_USERS"].items():
            if (
                not isinstance(username, str)
                or not username
                or not isinstance(account, dict)
                or not isinstance(account.get("password_hash"), str)
                or not account["password_hash"].startswith("pbkdf2:sha256:")
                or not isinstance(account.get("scopes"), list)
                or not account["scopes"]
                or not all(isinstance(scope, str) and scope in allowed_scopes for scope in account["scopes"])
            ):
                raise RuntimeError("MEDICARD_AUTH_USERS_JSON contains an invalid account")
        try:
            encryption_key = base64.b64decode(config["DATA_ENCRYPTION_KEY"] + "=" * (-len(config["DATA_ENCRYPTION_KEY"]) % 4), altchars=b"-_", validate=True)
            identity_key = base64.b64decode(config["IDENTITY_PUBLIC_KEY"] + "=" * (-len(config["IDENTITY_PUBLIC_KEY"]) % 4), altchars=b"-_", validate=True)
        except (ValueError, TypeError) as error:
            raise RuntimeError("Encryption and identity keys must be valid base64") from error
        if len(encryption_key) != 32:
            raise RuntimeError("DATA_ENCRYPTION_KEY must decode to exactly 32 bytes")
        if len(identity_key) != 32:
            raise RuntimeError("IDENTITY_PUBLIC_KEY must decode to exactly 32 bytes")
        if config["ACCESS_TOKEN_TTL_SECONDS"] < 60 or config["ACCESS_TOKEN_TTL_SECONDS"] > 3600:
            raise RuntimeError("ACCESS_TOKEN_TTL_SECONDS must be between 60 and 3600")
        if not config["CORS_ORIGINS"]:
            raise RuntimeError("CORS_ORIGINS must contain at least one allowed origin")
