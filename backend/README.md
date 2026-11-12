# Backend configuration

`MEDICARD_AUTH_USERS_JSON` is a JSON object mapping account names to objects containing a PBKDF2-SHA256 password hash and a list of allowed scopes:

```json
{"clinician":{"password_hash":"pbkdf2:sha256:600000$<salt>$<hex-digest>","scopes":["records:read","records:write","clinical:route","identity:verify"]}}
```

Generate a digest with Werkzeug's `generate_password_hash(password, method="pbkdf2:sha256:600000")`, then store the resulting string as a deployment secret. Never put real credentials in source control. The API has no public account-registration route.

The accepted clinical input is an HL7 FHIR R4 Bundle validated with `fhir.resources`. A Bundle is restricted to exactly one Patient entry for safe per-patient storage. The routing engine is explainable administrative triage only; it is not trained or cleared for diagnosis or treatment.
