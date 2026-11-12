# MediCard

MediCard is a deployable reference implementation for healthcare coordination: a Next.js dashboard, a Flask API, an HL7 FHIR R4 intake path, encrypted record storage, signed sovereign-identity verification, and explainable clinical routing.

> **Clinical and compliance boundary:** MediCard is not a medical device and does not diagnose, recommend treatment, or replace clinician judgment. The routing output is administrative decision support and must be reviewed by a qualified clinician. This repository is a secure engineering baseline, not a HIPAA certification or a substitute for a privacy/security risk assessment, legal review, validated clinical software lifecycle, penetration testing, or operational controls.

## Architecture

- `frontend/`: Next.js App Router dashboard with token-based API calls, records lookup, browser QR scanning, and routing results.
- `backend/`: Flask API with JWT role checks, FHIR Bundle validation, SQLAlchemy connection pooling, and structured JSON logs.
- `ml_pipeline/`: deterministic, explainable urgency routing and image-landmark biomechanics calculations. These are not diagnostic models.
- `security/`: authenticated encryption, HMAC patient pseudonyms, signed credential verification, and response masking helpers.
- `database/`: MySQL schema/configuration and MongoDB validation/replica-set initialization.
- `docker/`: backend and frontend container definitions and the local multi-container compose deployment.

## Run locally with Docker

1. Copy `.env.example` to `.env`. Generate each key independently; do not use the example value in a real deployment:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   python -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
   ```

   Use the first two outputs for `JWT_SECRET` and `PATIENT_HMAC_KEY`; use the third for `DATA_ENCRYPTION_KEY`. Configure `IDENTITY_PUBLIC_KEY` with the trusted issuer's raw Ed25519 public key encoded as base64 and configure a strong `MEDICARD_AUTH_USERS_JSON` password hash. See `backend/README.md` for the expected credential format.
2. Set `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD`, and all required secrets in `.env`.
3. Run `docker compose --env-file .env -f docker\docker-compose.yml up --build`.
4. Open `http://localhost:3000`. Obtain a JWT from your configured identity user through the sign-in form.

The compose topology is suitable for local integration and demonstration only. It runs one MySQL instance and a single-node MongoDB replica set; neither provides production high availability. The route and biomechanics functions are non-diagnostic rules, not an AI model. See [database/README.md](./database/README.md), [security/README.md](./security/README.md), and [ml_pipeline/README.md](./ml_pipeline/README.md) for deployment and clinical boundaries. Use a managed, TLS-enabled database topology with tested backups, failover, key management, and network policy for production. The application refuses to start without required cryptographic configuration.

## API

- `GET /api/v1/healthz`: dependency readiness; does not expose database details.
- `POST /api/v1/auth/token`: exchanges a configured account's password for a short-lived JWT.
- `POST /api/v1/clinical/records`: authenticated `records:write`; accepts one FHIR R4 `Bundle` containing exactly one `Patient`; stores the full Bundle encrypted.
- `POST /api/v1/clinical/records/lookup`: authenticated `records:read`; accepts `{"patient_id":"..."}` in the JSON body and returns matching decrypted FHIR Bundles with Patient direct fields masked. `records:read:full` is needed to return the full Patient resource.
- `POST /api/v1/clinical/route`: authenticated `clinical:route`; returns deterministic urgency routing and reasons, not a diagnosis.
- `POST /api/v1/identity/verify`: authenticated `identity:verify`; decrypts an encrypted QR envelope and verifies its Ed25519 issuer signature and expiry.
- `POST /api/v1/identity/qr`: authenticated `identity:verify`; verifies an issuer-signed credential then encrypts it into a QR envelope.

All API routes are under `/api/v1`. The default masking is data minimization, not a HIPAA safe-harbor de-identification guarantee. Requests require HTTPS in production; terminate TLS at a trusted reverse proxy and set `TRUST_PROXY=1` only when that proxy sanitizes forwarded headers. Restrict `CORS_ORIGINS` to the deployed frontend origin.

## Validation

Run backend tests with `python -m unittest discover -s backend\tests`. Build the frontend with `npm ci` then `npm run build` from `frontend\`. For deployment, additionally run vulnerability scanning, migrations and restore/failover exercises, access-control testing, clinical validation, and a jurisdiction-specific compliance assessment.
