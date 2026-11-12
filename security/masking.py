import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _decode_key(value):
    try:
        decoded = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except (TypeError, ValueError) as error:
        raise ValueError("Invalid base64 key") from error
    if len(decoded) != 32:
        raise ValueError("Encryption key must decode to exactly 32 bytes")
    return decoded


def _decode_key_part(value):
    try:
        return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except (TypeError, ValueError) as error:
        raise ValueError("Invalid base64 value") from error


def encode_base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def encrypt_json(value, key, associated_data=None):
    nonce = os.urandom(12)
    plain = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ciphertext = AESGCM(_decode_key(key)).encrypt(nonce, plain, associated_data)
    return {
        "ciphertext": encode_base64url(ciphertext),
        "nonce": encode_base64url(nonce),
    }


def decrypt_json(envelope, key, associated_data=None):
    if not isinstance(envelope, dict) or "ciphertext" not in envelope or "nonce" not in envelope:
        raise ValueError("Invalid envelope")
    nonce = _decode_key_part(envelope["nonce"])
    ciphertext = _decode_key_part(envelope["ciphertext"])
    plain = AESGCM(_decode_key(key)).decrypt(nonce, ciphertext, associated_data)
    return json.loads(plain.decode("utf-8"))


def decode_base64url(value):
    return _decode_key_part(value)


def patient_pseudonym(patient_id, key):
    if not isinstance(patient_id, str) or not patient_id or len(patient_id) > 128:
        raise ValueError("Invalid patient identifier")
    message = b"medicard:patient-id:v1:" + patient_id.encode("utf-8")
    return hmac.new(key.encode("utf-8"), message, hashlib.sha256).hexdigest()


def issue_identity_credential(issuer, subject, expires_at, secret_key=None):
    if not isinstance(issuer, str) or not issuer or not isinstance(subject, str) or not subject:
        raise ValueError("Invalid issuer or subject")
    claims = {"issuer": issuer, "subject": subject, "expires_at": int(expires_at)}
    payload = json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8")
    if secret_key:
        claims["signature_type"] = "hmac"
        claims["signature"] = hmac.new(secret_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return claims
    return {**claims, "signature": ""}


def verify_identity_credential(credential, public_key, trusted_issuer, secret_key=None):
    if not isinstance(credential, dict):
        raise ValueError("Invalid credential")
    issuer = credential.get("issuer")
    subject = credential.get("subject")
    expires_at = credential.get("expires_at")
    signature = credential.get("signature")
    if issuer != trusted_issuer or not isinstance(subject, str) or not subject or len(subject) > 128:
        raise ValueError("Untrusted credential")
    if not isinstance(expires_at, int) or expires_at <= int(time.time()):
        raise ValueError("Expired credential")
    signed_claims = {"issuer": issuer, "subject": subject, "expires_at": expires_at}
    message = json.dumps(signed_claims, separators=(",", ":"), sort_keys=True).encode("utf-8")

    if credential.get("signature_type") == "hmac" and isinstance(secret_key, str):
        expected = hmac.new(secret_key.encode("utf-8"), message, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature or ""):
            raise ValueError("Invalid credential signature")
        return {"issuer": issuer, "subject": subject, "expires_at": expires_at}

    if isinstance(public_key, str) and public_key:
        try:
            public_bytes = _decode_key_part(public_key)
            Ed25519PublicKey.from_public_bytes(public_bytes).verify(_decode_key_part(signature), message)
            return {"issuer": issuer, "subject": subject, "expires_at": expires_at}
        except Exception as error:
            raise ValueError("Invalid credential signature") from error

    raise ValueError("Credential signature is missing or invalid")


def verify_identity_envelope(envelope, encryption_key, public_key, trusted_issuer, secret_key=None):
    if not isinstance(envelope, dict) or set(envelope) != {"ciphertext", "nonce"}:
        raise ValueError("Invalid envelope fields")
    credential = decrypt_json(envelope, encryption_key)
    return verify_identity_credential(credential, public_key, trusted_issuer, secret_key)
