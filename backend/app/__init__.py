import logging
import os
import sys
import json
from logging.config import dictConfig

from flask import Flask, g, jsonify, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .routes import api


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(
            {
                "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            },
            ensure_ascii=True,
        )


def _configure_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"json": {"()": JsonFormatter}},
            "handlers": {"stdout": {"class": "logging.StreamHandler", "stream": sys.stdout, "formatter": "json"}},
            "root": {"level": os.getenv("LOG_LEVEL", "INFO"), "handlers": ["stdout"]},
        }
    )


def create_app(test_config=None) -> Flask:
    _configure_logging()
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if not app.config.get("TESTING"):
        Config.validate(app.config)
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
    app.logger.setLevel(logging.INFO)

    if app.config.get("TRUST_PROXY"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=False,
        allow_headers=["Authorization", "Content-Type"],
        methods=["GET", "POST", "OPTIONS"],
        max_age=600,
    )
    app.register_blueprint(api, url_prefix="/api/v1")

    @app.before_request
    def assign_request_id():
        g.request_id = request.headers.get("X-Request-ID", "")[:80] or os.urandom(12).hex()

    @app.after_request
    def secure_response(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify(error="request_too_large"), 413

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return jsonify(error="not_found"), 404
        return "Not found", 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        if request.path.startswith("/api/"):
            return jsonify(error="method_not_allowed"), 405
        return "Method not allowed", 405

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error("unhandled_error request_id=%s error_type=%s", getattr(g, "request_id", ""), type(error).__name__)
        return jsonify(error="internal_server_error", request_id=getattr(g, "request_id", "")), 500

    return app
