import base64
import json
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.auth import issue_token
from ml_pipeline.biomechanics import summarize_landmarks
from ml_pipeline.routing import route_clinical_input
from security.crypto import encrypt_json, patient_pseudonym, verify_identity_envelope
from security.masking import mask_patient


ENCRYPTION_KEY = base64.urlsafe_b64encode(bytes(range(32))).decode().rstrip("=")


class CryptoTests(unittest.TestCase):
    def test_authenticated_encryption_round_trip_and_tamper_detection(self):
        value = {"resourceType": "Patient", "id": "p-1"}
        envelope = encrypt_json(value, ENCRYPTION_KEY)
        from security.crypto import decrypt_json

        self.assertEqual(value, decrypt_json(envelope, ENCRYPTION_KEY))
        envelope["ciphertext"] = ("A" if envelope["ciphertext"][0] != "A" else "B") + envelope["ciphertext"][1:]
        with self.assertRaises(InvalidTag):
            decrypt_json(envelope, ENCRYPTION_KEY)

    def test_associated_data_binds_ciphertext_to_patient_key(self):
        envelope = encrypt_json({"value": "record"}, ENCRYPTION_KEY, b"patient-key-a")
        from security.crypto import decrypt_json

        with self.assertRaises(InvalidTag):
            decrypt_json(envelope, ENCRYPTION_KEY, b"patient-key-b")

    def test_patient_pseudonym_is_stable_and_not_the_source_identifier(self):
        digest = patient_pseudonym("patient-42", "independent-secret-key-which-is-long")
        self.assertEqual(64, len(digest))
        self.assertNotEqual("patient-42", digest)
        self.assertEqual(digest, patient_pseudonym("patient-42", "independent-secret-key-which-is-long"))

    def test_identity_verification_checks_signature_and_trusted_issuer(self):
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        claims = {"issuer": "trusted-clinic", "subject": "patient-9", "expires_at": int(time.time()) + 600}
        message = json.dumps(claims, separators=(",", ":"), sort_keys=True).encode()
        credential = {
            **claims,
            "signature": base64.urlsafe_b64encode(private_key.sign(message)).decode().rstrip("="),
        }
        envelope = encrypt_json(credential, ENCRYPTION_KEY)
        verified = verify_identity_envelope(
            envelope,
            ENCRYPTION_KEY,
            base64.urlsafe_b64encode(public_key).decode().rstrip("="),
            "trusted-clinic",
        )
        self.assertEqual(claims, verified)
        with self.assertRaises(ValueError):
            verify_identity_envelope(envelope, ENCRYPTION_KEY, base64.urlsafe_b64encode(public_key).decode().rstrip("="), "other")


class RoutingTests(unittest.TestCase):
    def test_explicit_red_flag_has_immediate_review_priority(self):
        result = route_clinical_input({"red_flag": True, "urgent_review": False, "routine_review": False})
        self.assertEqual("immediate", result["priority"])
        self.assertIsNone(result["diagnosis"])
        self.assertTrue(result["requires_clinician_review"])

    def test_mobility_summary_is_geometry_only(self):
        result = summarize_landmarks([{"x": 0, "y": 0}, {"x": 0.5, "y": 0}, {"x": 0.5, "y": 0.5}])
        self.assertEqual(3, result["landmark_count"])
        self.assertEqual(1.0, result["normalized_path_length"])
        self.assertEqual("geometry_only_not_a_clinical_assessment", result["interpretation"])

    def test_invalid_routing_input_is_rejected(self):
        with self.assertRaises(ValueError):
            route_clinical_input({"red_flag": "yes"})
        with self.assertRaises(ValueError):
            summarize_landmarks([{"x": 3, "y": 0}, {"x": 0, "y": 0}, {"x": 1, "y": 1}])


class MaskingTests(unittest.TestCase):
    def test_patient_direct_identifiers_are_removed(self):
        patient = {
            "resourceType": "Patient",
            "id": "p-1",
            "identifier": [{"value": "123"}],
            "telecom": [{"value": "555-0100"}],
            "name": [{"text": "Private Name"}],
        }
        masked = mask_patient(patient)
        self.assertNotIn("id", masked)
        self.assertNotIn("identifier", masked)
        self.assertEqual([{"text": "Protected"}], masked["name"])


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key-with-at-least-thirty-two-characters",
            "JWT_ISSUER": "test-issuer",
            "JWT_AUDIENCE": "test-audience",
            "ACCESS_TOKEN_TTL_SECONDS": 300,
            "AUTH_USERS": {},
            "CORS_ORIGINS": ["http://localhost:3000"],
        }
        self.client = create_app(self.config).test_client()

    def test_clinical_routing_requires_scope_and_returns_non_diagnostic_result(self):
        denied = self.client.post("/api/v1/clinical/route", json={"red_flag": True})
        self.assertEqual(401, denied.status_code)
        token = issue_token("clinician", ["clinical:route"], self.config)
        with patch("app.routes._audit"):
            response = self.client.post(
                "/api/v1/clinical/route",
                json={"red_flag": True},
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(200, response.status_code)
        self.assertIsNone(response.json["diagnosis"])
        self.assertTrue(response.json["requires_clinician_review"])

    def test_invalid_clinical_routing_input_returns_bad_request(self):
        token = issue_token("clinician", ["clinical:route"], self.config)
        response = self.client.post(
            "/api/v1/clinical/route",
            json={"red_flag": "urgent"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(400, response.status_code)


if __name__ == "__main__":
    unittest.main()
