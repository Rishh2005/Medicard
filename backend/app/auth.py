import hashlib
import json
import os
import time
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request
from werkzeug.security import check_password_hash


def issue_token(username, scopes, config):
    now = int(time.time())
    return jwt.encode(
        {
            "sub": username,
            "scope": sorted(set(scopes)),
            "iss": config["JWT_ISSUER"],
            "aud": config["JWT_AUDIENCE"],
            "iat": now,
            "nbf": now,
            "exp": now + int(config["ACCESS_TOKEN_TTL_SECONDS"]),
        },
        config["SECRET_KEY"],
        algorithm="HS256",
    )


def authenticate_user(username, password, users):
    if not isinstance(username, str) or not username:
        return None
    account = users.get(username)
    if not isinstance(account, dict) or not isinstance(account.get("password_hash"), str):
        return None
    try:
        if not check_password_hash(account["password_hash"], password):
            return None
    except (TypeError, ValueError):
        return None
    scopes = account.get("scopes")
    if not isinstance(scopes, list) or not all(isinstance(scope, str) for scope in scopes):
        return None
    return scopes


def require_scope(scope):
    def decorator(handler):
        @wraps(handler)
        def wrapped(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            scheme, _, token = header.partition(" ")
            if scheme.lower() != "bearer" or not token:
                return jsonify(error="authentication_required"), 401
            try:
                claims = jwt.decode(
                    token,
                    current_app.config["SECRET_KEY"],
                    algorithms=["HS256"],
                    issuer=current_app.config["JWT_ISSUER"],
                    audience=current_app.config["JWT_AUDIENCE"],
                    options={"require": ["sub", "exp", "iat", "iss", "aud"]},
                )
            except jwt.PyJWTError:
                return jsonify(error="invalid_or_expired_token"), 401
            scopes = claims.get("scope", [])
            if not isinstance(scopes, list) or scope not in scopes:
                return jsonify(error="insufficient_scope"), 403
            g.user = claims["sub"]
            g.scopes = scopes
            return handler(*args, **kwargs)

        return wrapped

    return decorator
