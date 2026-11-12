import base64
import hashlib
import hmac
import json
import os
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def _decode_key(value):
    try:
        decoded = base64.b64decode(
            value + "=" * (-len(value) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, TypeError) as error:
        raise ValueError("Invalid base64 key") from error
    if len(decoded) != 32:
        raise ValueError("Encryption key must decode to exactly 32 bytes")
    return decoded


def encrypt_json(value, key):
    nonce = os.urandom(12)
    plaintext = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    ciphertext = AESGCM(_decode_key(key)).encrypt(nonce, plaintext, None)
    return {
        "ciphertext": base64.urlsafe_b64encode(ciphertext).decode().rstrip("="),
        "nonce": base64.urlsafe_b64encode(nonce).decode().rstrip("="),
    }


def decrypt_json(envelope, key):
    nonce = _decode_key_part(envelope["nonce"])
    ciphertext = _decode_key_part(envelope["ciphertext"])
    plaintext = AESGCM(_decode_key(key)).decrypt(nonce, ciphertext, None)
    return json.loads(plaintext)


def _decode_key_part(value):
    try:
        return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError("Invalid base64 value") from error


def decode_base64url(value):
    return _decode_key_part(value)


def patient_pseudonym(patient_id, key):
    if not isinstance(patient_id, str) or not patient_id or len(patient_id) > 128:
        raise ValueError("Invalid patient identifier")
    return hmac.new(key.encode(), patient_id.encode(), hashlib.sha256).hexdigest()


def verify_identity_credential(credential, public_key, trusted_issuer):
    if set(credential) != {"issuer", "subject", "expires_at", "signature"}:
        raise ValueError("Invalid credential fields")
    issuer = credential["issuer"]
    subject = credential["subject"]
    expires_at = credential["expires_at"]
    if issuer != trusted_issuer or not isinstance(subject, str) or not subject or len(subject) > 128:
        raise ValueError("Untrusted credential")
    if not isinstance(expires_at, int) or expires_at <= int(time.time()):
        raise ValueError("Expired credential")
    signed_claims = {"issuer": issuer, "subject": subject, "expires_at": expires_at}
    message = json.dumps(signed_claims, separators=(",", ":"), sort_keys=True).encode()
    try:
        key_bytes = _decode_key_part(public_key)
        signature = _decode_key_part(credential["signature"])
        Ed25519PublicKey.from_public_bytes(key_bytes).verify(signature, message)
    except Exception as error:
        raise ValueError("Invalid credential signature") from error
    return {"issuer": issuer, "subject": subject, "expires_at": expires_at}


def verify_identity_envelope(envelope, encryption_key, public_key, trusted_issuer):
    if not isinstance(envelope, dict) or set(envelope) != {"ciphertext", "nonce"}:
        raise ValueError("Invalid envelope fields")
    credential = decrypt_json(envelope, encryption_key)
    return verify_identity_credential(credential, public_key, trusted_issuer)
