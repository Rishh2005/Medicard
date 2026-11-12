# Identity and data protection protocol

Trusted issuers sign the UTF-8 bytes of a JSON object with sorted keys and compact separators:

```json
{"expires_at":<unix-seconds>,"issuer":"<trusted-issuer>","subject":"<issuer-scoped-subject>"}
```

They provide the Ed25519 signature as unpadded base64url in an object containing exactly `issuer`, `subject`, `expires_at`, and `signature`. MediCard checks the configured issuer, signature, subject bounds, and expiry before encrypting the signed credential into a QR envelope. The QR carries only the base64url AES-GCM ciphertext and 96-bit nonce; the backend verifies the envelope and issuer signature again when scanned. The trusted issuer private key must never be deployed to MediCard.

`DATA_ENCRYPTION_KEY` is a 32-byte AES-256-GCM key encoded as base64url and is used here for both patient bundles and QR envelopes. This reference setup has no key versioning or rotation workflow; production deployments need a KMS/HSM-backed envelope-encryption design, key version identifiers, rotation/re-encryption procedures, and operational access controls. `PATIENT_HMAC_KEY` is an independent secret used for pseudonymous lookup keys. Hashes are stable only within the secret's scope and are not anonymization.

The Patient response masker removes direct fields from the Patient resource only. It is not complete FHIR de-identification: references and identifying content in other resources may remain. Keep unmasked reads restricted and perform a jurisdiction-specific privacy assessment before any secondary use.
