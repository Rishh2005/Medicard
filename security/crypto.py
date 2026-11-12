import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone

from flask import Blueprint, current_app, g, jsonify, request
from fhir.resources.bundle import Bundle
from pydantic import ValidationError
from sqlalchemy import text

from ml_pipeline.inference import clinical_risk_score
from ml_pipeline.routing import route_clinical_input
from security.crypto import (
    decrypt_json,
    encrypt_json,
    decode_base64url,
    patient_pseudonym,
    verify_identity_credential,
    verify_identity_envelope,
    issue_identity_credential,
)
from security.masking import mask_patient

from .auth import authenticate_user, issue_token, require_scope
from .db import check_dependencies, get_database_engine

api = Blueprint("api", __name__)


def _config():
    return current_app.config


def _audit(action, details):
    if current_app.config.get("TESTING"):
        return
    try:
        from .db import get_database_engine

        engine = get_database_engine(_config())
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS audit_events (id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, payload TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
                )
            )
            connection.execute(
                text("INSERT INTO audit_events (action, payload) VALUES (:action, :payload)"),
                {"action": action, "payload": json.dumps({"actor": g.get("user", "system"), "at": datetime.now(timezone.utc).isoformat(), **details}, separators=(",", ":"), sort_keys=True)},
            )
    except Exception:
        return


@api.get("/health")
@api.get("/healthz")
def health():
    try:
        engine = check_dependencies(_config())
        services = {
            "backend": "ok",
            "database": "ok" if engine is not None else "unavailable",
            "ml_pipeline": "ok",
            "encryption": "ok" if _config().get("DATA_ENCRYPTION_KEY") else "unavailable",
        }
        return jsonify(status="ok", services=services), 200
    except Exception as error:
        current_app.logger.error("dependency_check_failed request_id=%s error_type=%s", g.request_id, type(error).__name__)
        return jsonify(status="degraded", services={"backend": "ok", "database": "unavailable", "ml_pipeline": "ok", "encryption": "unavailable"}, error=str(error)), 503


@api.post("/auth/token")
def token():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("username"), str) or not isinstance(payload.get("password"), str):
        return jsonify(error="invalid_credentials"), 401
    scopes = authenticate_user(payload["username"], payload["password"], _config()["AUTH_USERS"])
    if scopes is None:
        return jsonify(error="invalid_credentials"), 401
    return jsonify(access_token=issue_token(payload["username"], scopes, _config()), token_type="Bearer", expires_in=_config()["ACCESS_TOKEN_TTL_SECONDS"])


@api.post("/identity/issue")
def identity_issue():
    payload = request.get_json(silent=True) or {}
    subject = payload.get("subject") or payload.get("patient_id")
    if not isinstance(subject, str) or not subject:
        return jsonify(error="invalid_subject"), 400
    issuer = _config().get("IDENTITY_TRUSTED_ISSUER") or "medicard-issuer"
    expires_at = int(time.time()) + max(300, int(_config().get("ACCESS_TOKEN_TTL_SECONDS", 900)))
    credential = issue_identity_credential(issuer, subject, expires_at, secret_key=_config().get("JWT_SECRET"))
    did = "did:medicard:" + hashlib.sha256(f"{issuer}:{subject}".encode()).hexdigest()[:32]
    envelope = encrypt_json(credential, _config()["DATA_ENCRYPTION_KEY"])
    _audit("identity_credential_issued", {"subject": subject, "did": did})
    return jsonify(did=did, credential=credential, envelope=envelope)


@api.post("/identity/verify")
@require_scope("identity:verify")
def verify_identity():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("envelope"), dict):
        return jsonify(error="invalid_identity_envelope"), 400
    try:
        claims = verify_identity_envelope(
            payload["envelope"],
            _config()["DATA_ENCRYPTION_KEY"],
            _config().get("IDENTITY_PUBLIC_KEY", ""),
            _config().get("IDENTITY_TRUSTED_ISSUER", "medicard-issuer"),
            _config().get("JWT_SECRET", ""),
        )
    except (ValueError, TypeError, json.JSONDecodeError):
        return jsonify(error="identity_verification_failed"), 400
    _audit("identity_credential_verified", {"subject_ref": patient_pseudonym(claims["subject"], _config()["PATIENT_HMAC_KEY"])})
    return jsonify(verified=True, issuer=claims["issuer"], subject_ref=patient_pseudonym(claims["subject"], _config()["PATIENT_HMAC_KEY"]), expires_at=claims["expires_at"])


@api.post("/identity/qr")
@require_scope("identity:verify")
def create_identity_qr():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("credential"), dict):
        return jsonify(error="invalid_identity_credential"), 400
    try:
        claims = verify_identity_credential(
            payload["credential"],
            _config().get("IDENTITY_PUBLIC_KEY", ""),
            _config().get("IDENTITY_TRUSTED_ISSUER", "medicard-issuer"),
            _config().get("JWT_SECRET", ""),
        )
    except (ValueError, TypeError, KeyError):
        return jsonify(error="identity_verification_failed"), 400
    envelope = encrypt_json(payload["credential"], _config()["DATA_ENCRYPTION_KEY"])
    subject_ref = patient_pseudonym(claims["subject"], _config()["PATIENT_HMAC_KEY"])
    _audit("identity_qr_created", {"subject_ref": subject_ref})
    return jsonify(envelope=envelope, verified=True, issuer=claims["issuer"], subject_ref=subject_ref, expires_at=claims["expires_at"])


@api.post("/clinical/records")
@api.post("/fhir/validate")
@require_scope("records:write")
def save_records():
    payload = request.get_json(silent=True)
    resource = payload.get("resource") if isinstance(payload, dict) and isinstance(payload.get("resource"), dict) else payload
    if not isinstance(resource, dict):
        return jsonify(error="invalid_fhir_bundle"), 400
    try:
        bundle = Bundle.model_validate(resource)
        normalized = bundle.model_dump(mode="json", by_alias=True, exclude_none=True)
    except ValidationError:
        try:
            if resource.get("resourceType") in {"Patient", "Observation", "DiagnosticReport"}:
                bundle = Bundle(entry=[{"resource": resource}])
                normalized = bundle.model_dump(mode="json", by_alias=True, exclude_none=True)
            else:
                raise
        except Exception:
            return jsonify(error="invalid_fhir_bundle"), 400

    entries = normalized.get("entry") or []
    patients = [item.get("resource", {}) for item in entries if item.get("resource", {}).get("resourceType") == "Patient"]
    if len(patients) != 1 or not patients[0].get("id"):
        return jsonify(error="bundle_must_contain_exactly_one_patient_with_id"), 400
    patient_id = patients[0]["id"]
    patient_key = patient_pseudonym(patient_id, _config()["PATIENT_HMAC_KEY"])
    encrypted = encrypt_json(normalized, _config()["DATA_ENCRYPTION_KEY"], patient_key.encode())
    engine = get_database_engine(_config())
    with engine.begin() as connection:
        result = connection.execute(
            text("INSERT INTO patient_records (patient_key, ciphertext, nonce) VALUES (:patient_key, :ciphertext, :nonce)"),
            {
                "patient_key": patient_key,
                "ciphertext": decode_base64url(encrypted["ciphertext"]),
                "nonce": decode_base64url(encrypted["nonce"]),
            },
        )
        record_id = result.lastrowid
    _audit("fhir_bundle_stored", {"record_ref": str(record_id), "patient_key": patient_key})
    return jsonify(status="stored", patient_id=patient_id, record_id=record_id, bundle=normalized), 201


@api.get("/fhir/records/<patient_id>")
@api.post("/clinical/records/lookup")
@require_scope("records:read")
def get_records(patient_id=None):
    if request.method == "POST":
        payload = request.get_json(silent=True) if isinstance(request.get_json(silent=True), dict) else {}
        patient_id = payload.get("patient_id")
    if not isinstance(patient_id, str) or not patient_id or len(patient_id) > 128:
        return jsonify(error="invalid_patient_id"), 400
    patient_key = patient_pseudonym(patient_id, _config()["PATIENT_HMAC_KEY"])
    engine = get_database_engine(_config())
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT ciphertext, nonce FROM patient_records WHERE patient_key = :patient_key ORDER BY id DESC LIMIT 50"),
            {"patient_key": patient_key},
        ).mappings().all()
    bundles = []
    for row in rows:
        bundle = decrypt_json({"ciphertext": base64.urlsafe_b64encode(row["ciphertext"]).decode().rstrip("="), "nonce": base64.urlsafe_b64encode(row["nonce"]).decode().rstrip("=")}, _config()["DATA_ENCRYPTION_KEY"], patient_key.encode())
        if "records:read:full" not in g.scopes:
            for entry in bundle.get("entry", []):
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "Patient":
                    entry["resource"] = mask_patient(resource)
        bundles.append(bundle)
    _audit("fhir_bundle_read", {"record_count": len(bundles), "patient_key": patient_key})
    return jsonify(resourceType="Bundle", type="collection", total=len(bundles), entry=[{"resource": item} for item in bundles])


@api.post("/clinical/route")
@api.post("/diagnose/route")
@require_scope("clinical:route")
def clinical_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="invalid_input"), 400
    try:
        result = route_clinical_input(payload)
    except ValueError as error:
        return jsonify(error="invalid_input", detail=str(error)), 400
    result["audit_hash"] = hashlib.sha256(json.dumps({"route": result.get("route"), "priority": result.get("priority"), "request_id": g.request_id}, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
    _audit("clinical_route_requested", {"route": result.get("route"), "request_id": g.request_id})
    return jsonify(result)


@api.get("/api/health")
def legacy_health_alias():
    return health()


@api.get("/api/identity/issue")
def legacy_identity_issue_alias():
    return identity_issue()


@api.get("/api/fhir/records/<patient_id>")
def legacy_fhir_records_alias(patient_id):
    return get_records(patient_id)
