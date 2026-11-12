import base64
import json
from datetime import datetime, timezone

from flask import Blueprint, current_app, g, jsonify, request
from fhir.resources.bundle import Bundle
from pydantic import ValidationError
from sqlalchemy import text

from ml_pipeline.routing import route_clinical_input
from security.crypto import (
    decrypt_json,
    encrypt_json,
    decode_base64url,
    patient_pseudonym,
    verify_identity_credential,
    verify_identity_envelope,
)
from security.masking import mask_patient

from .auth import authenticate_user, issue_token, require_scope
from .db import check_dependencies, get_mongo_client, get_mysql_engine

api = Blueprint("api", __name__)


def _config():
    return current_app.config


def _audit(action, details):
    client = get_mongo_client(_config())
    encrypted = encrypt_json(
        {"action": action, "actor": g.get("user", "system"), "at": datetime.now(timezone.utc).isoformat(), **details},
        _config()["DATA_ENCRYPTION_KEY"],
    )
    client["medicard"]["audit_events"].insert_one(
        {"version": 1, "ciphertext": encrypted["ciphertext"], "nonce": encrypted["nonce"]}
    )


@api.get("/healthz")
def healthz():
    try:
        check_dependencies(_config())
        return jsonify(status="ok"), 200
    except Exception as error:
        current_app.logger.error("dependency_check_failed request_id=%s error_type=%s", g.request_id, type(error).__name__)
        return jsonify(status="unavailable"), 503


@api.post("/auth/token")
def token():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("username"), str) or not isinstance(payload.get("password"), str):
        return jsonify(error="invalid_credentials"), 401
    scopes = authenticate_user(payload["username"], payload["password"], _config()["AUTH_USERS"])
    if scopes is None:
        return jsonify(error="invalid_credentials"), 401
    return jsonify(access_token=issue_token(payload["username"], scopes, _config()), token_type="Bearer", expires_in=_config()["ACCESS_TOKEN_TTL_SECONDS"])


@api.post("/clinical/records")
@require_scope("records:write")
def save_records():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="invalid_fhir_bundle"), 400
    try:
        bundle = Bundle.model_validate(payload)
        normalized = bundle.model_dump(mode="json", by_alias=True, exclude_none=True)
    except ValidationError:
        return jsonify(error="invalid_fhir_bundle"), 400

    entries = normalized.get("entry") or []
    patients = [item.get("resource", {}) for item in entries if item.get("resource", {}).get("resourceType") == "Patient"]
    if normalized.get("resourceType") != "Bundle" or len(patients) != 1 or not patients[0].get("id"):
        return jsonify(error="bundle_must_contain_exactly_one_patient_with_id"), 400
    patient_id = patients[0]["id"]
    try:
        patient_key = patient_pseudonym(patient_id, _config()["PATIENT_HMAC_KEY"])
    except ValueError:
        return jsonify(error="invalid_patient_id"), 400
    encrypted = encrypt_json(normalized, _config()["DATA_ENCRYPTION_KEY"])
    engine = get_mysql_engine(_config())
    with engine.begin() as connection:
        result = connection.execute(
            text(
                "INSERT INTO patient_records (patient_key, ciphertext, nonce) "
                "VALUES (:patient_key, :ciphertext, :nonce)"
            ),
            {
                "patient_key": patient_key,
                "ciphertext": decode_base64url(encrypted["ciphertext"]),
                "nonce": decode_base64url(encrypted["nonce"]),
            },
        )
        record_id = result.lastrowid
    _audit("fhir_bundle_stored", {"record_ref": str(record_id), "patient_key": patient_key})
    return jsonify(status="stored", record_id=record_id), 201


@api.get("/clinical/records/<path:patient_id>")
@require_scope("records:read")
def get_records(patient_id):
    if not patient_id or len(patient_id) > 128:
        return jsonify(error="invalid_patient_id"), 400
    patient_key = patient_pseudonym(patient_id, _config()["PATIENT_HMAC_KEY"])
    engine = get_mysql_engine(_config())
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT ciphertext, nonce FROM patient_records WHERE patient_key = :patient_key ORDER BY id DESC LIMIT 50"),
            {"patient_key": patient_key},
        ).mappings().all()
    bundles = [
        decrypt_json(
            {
                "ciphertext": base64.urlsafe_b64encode(row["ciphertext"]).decode().rstrip("="),
                "nonce": base64.urlsafe_b64encode(row["nonce"]).decode().rstrip("="),
            },
            _config()["DATA_ENCRYPTION_KEY"],
        )
        for row in rows
    ]
    if "records:read:full" not in g.scopes:
        for bundle in bundles:
            for entry in bundle.get("entry", []):
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "Patient":
                    entry["resource"] = mask_patient(resource)
    _audit("fhir_bundle_read", {"record_count": len(bundles), "patient_key": patient_key})
    return jsonify(resourceType="Bundle", type="collection", total=len(bundles), entry=[{"resource": item} for item in bundles])


@api.post("/clinical/route")
@require_scope("clinical:route")
def clinical_route():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="invalid_input"), 400
    try:
        result = route_clinical_input(payload)
    except ValueError as error:
        return jsonify(error="invalid_input", detail=str(error)), 400
    _audit("clinical_route_requested", {"route": result["route"], "request_id": g.request_id})
    return jsonify(result)


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
            _config()["IDENTITY_PUBLIC_KEY"],
            _config()["IDENTITY_TRUSTED_ISSUER"],
        )
    except (ValueError, TypeError, json.JSONDecodeError):
        return jsonify(error="identity_verification_failed"), 400
    _audit("identity_credential_verified", {"subject_ref": patient_pseudonym(claims["subject"], _config()["PATIENT_HMAC_KEY"])})
    return jsonify(
        verified=True,
        issuer=claims["issuer"],
        subject_ref=patient_pseudonym(claims["subject"], _config()["PATIENT_HMAC_KEY"]),
        expires_at=claims["expires_at"],
    )


@api.post("/identity/qr")
@require_scope("identity:verify")
def create_identity_qr():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("credential"), dict):
        return jsonify(error="invalid_identity_credential"), 400
    try:
        claims = verify_identity_credential(
            payload["credential"],
            _config()["IDENTITY_PUBLIC_KEY"],
            _config()["IDENTITY_TRUSTED_ISSUER"],
        )
    except (ValueError, TypeError, KeyError):
        return jsonify(error="identity_verification_failed"), 400
    envelope = encrypt_json(payload["credential"], _config()["DATA_ENCRYPTION_KEY"])
    subject_ref = patient_pseudonym(claims["subject"], _config()["PATIENT_HMAC_KEY"])
    _audit("identity_qr_created", {"subject_ref": subject_ref})
    return jsonify(
        envelope=envelope,
        verified=True,
        issuer=claims["issuer"],
        subject_ref=subject_ref,
        expires_at=claims["expires_at"],
    )
