# Backend configuration

`MEDICARD_AUTH_USERS_JSON` is a JSON object mapping account names to objects containing a PBKDF2-SHA256 password hash and a list of allowed scopes:

```json
{"clinician":{"password_hash":"pbkdf2:sha256:600000$<salt>$<hex-digest>","scopes":["records:read","records:write","clinical:route","identity:verify"]}}
```

Generate a digest with `python -c "from werkzeug.security import generate_password_hash; import getpass; print(generate_password_hash(getpass.getpass(), method='pbkdf2:sha256:600000'))"`, then store the resulting string as a deployment secret. Never put real credentials in source control. The API has no public account-registration route.

Supported scopes are `records:read`, `records:read:full`, `records:write`, `clinical:route`, and `identity:verify`. Grant `records:read:full` only to accounts that require unmasked Patient resources.

The trusted issuer must provision its own Ed25519 key pair outside MediCard. Configure the issuer's raw 32-byte public key, base64url-encoded without padding, as `IDENTITY_PUBLIC_KEY`; never configure or upload the issuer private key to this application.

The accepted clinical input is an HL7 FHIR R4 Bundle validated with `fhir.resources`. A Bundle is restricted to exactly one Patient entry for safe per-patient storage. The routing engine is explainable administrative triage only; it is not trained or cleared for diagnosis or treatment.
