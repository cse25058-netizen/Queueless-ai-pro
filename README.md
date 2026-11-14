# QueueLess AI — Multi-Hospital Platform

A Flask multi-tenant pilot application for hospital discovery, patient token booking, queue visibility and hospital staff workflows.

## Included in this revised build
- Independent hospital/clinic registration and tenant-scoped hospital administration
- Patient registration/login, token booking, appointment history and cancellation
- Hospital directory, departments, doctor directory and queue display
- Hospital admin dashboard and department management
- Doctor login provisioning by the hospital admin (email + temporary password); doctor appointment lists and status updates are restricted to appointments assigned to that doctor
- Appointment QR image endpoint and staff check-in by token value
- CSRF token validation for state-changing authenticated requests, same-origin Origin checks, secure cookie options, password hashing and baseline security headers
- Health endpoint, Dockerfile and Render blueprint

## Local setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open http://127.0.0.1:5000. Set a long random `SECRET_KEY` for any shared environment. Keep `COOKIE_SECURE=true` behind HTTPS.

## Deploying a pilot to Render
1. Push this project to a private GitHub repository.
2. Create a Render Web Service from the repository, or use the included `render.yaml` blueprint.
3. Keep the persistent disk mounted at `/var/data` and `DATABASE_PATH=/var/data/queueless.db`.
4. Set a unique random `SECRET_KEY`, `COOKIE_SECURE=true`, and `APP_TIMEZONE=Asia/Kolkata`.
5. Deploy and check `/health`.

This Render configuration uses SQLite on a persistent disk and one Gunicorn worker. It is a small pilot configuration, **not** a horizontally scalable production database architecture. Before a public multi-hospital launch, migrate to managed PostgreSQL with a migration tool, connection pooling, backups and restore drills. The current app uses SQLite-specific connection and placeholder patterns; do not simply point `DATABASE_PATH` at a PostgreSQL URL.

## Integrations not active in this build
- **SMS:** no Twilio credentials or delivery workflow configured.
- **Payments:** no Razorpay order creation, signature verification or webhook workflow configured. Do not collect money through this app.
- **Automatic reminders:** no durable scheduler/worker configured. Do not rely on in-process timers for appointment reminders.
- **QR:** the app generates a QR image and supports staff check-in by entering/scanning the token value. Camera-based live scanning is not included.
- **Email verification/password recovery:** not configured.

These require provider accounts, credentials, webhook configuration, delivery-failure handling and end-to-end testing. Never commit provider secrets to GitHub or send them in chat.

## Tests and verification
Run:

```bash
python -m unittest discover -s tests -v
node --check static/app.js
python -m py_compile app.py tests/test_multitenant.py
```

The source-generation environment used for this package did not have Flask installed and had no package-network access, so Python compile checks and JavaScript syntax checks passed, but Flask runtime tests and browser end-to-end tests could not be executed here. Run the full commands in an environment with dependencies installed before deployment.

## Healthcare safety and security
This is a software pilot, not a certified hospital information system. Do not enter real patient data until a qualified application-security professional and the hospital's privacy/legal team have reviewed it. Before production, add and test: managed PostgreSQL, database migrations, rate limiting, email verification, account recovery, MFA for staff, staff invitation/activation, immutable audit coverage, backup/restore, monitoring/alerting, retention/deletion policy, privacy notice/consent, incident response and applicable Indian legal compliance (including the DPDP Act/rules as applicable). Perform tenant-isolation tests against every API endpoint, not only the included sample tests.

Queue wait estimates are simple indicative heuristics, not AI predictions or guaranteed wait times. This software is not for diagnosis, triage or emergency care.
