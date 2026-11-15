# QueueLess AI — Multi-Hospital Platform

**Less Waiting, Better Healthcare.**

Responsive Flask application for patient booking, live queue visibility and independent hospital workspaces. Includes accessible controls, browser voice input, an in-app navigation guide and a cache-only offline app shell.

## Included and working in this release
- Patient sign-up, sign-in, sign-out and password hashing
- Hospital/clinic workspace registration and tenant separation
- Hospital directory search, departments and doctor directory
- Patient token booking, appointment history and cancellation
- Queue display and indicative wait-time estimate
- Hospital admin dashboard, department and doctor management
- Doctor accounts with doctor-scoped appointment list/status controls
- Staff check-in by token; QR image generation for appointments
- Easy-reading mode, Bengali/English home-screen switch, browser voice input where supported
- In-app QueueLess navigation guide (not a medical chatbot)
- Responsive layout, web app manifest and cache-only service worker
- CSRF checks for authenticated mutations, password hashing, same-origin checks and baseline security headers
- SQLite persistent database for a single-instance pilot; Render deployment blueprint

## Not live integrations in this package
SMS/WhatsApp and automated reminders, payment processing, camera-based live QR scanning, external generative AI, email verification, password reset, MFA, family booking and clinical triage are not implemented as live provider workflows. These require provider accounts, secrets, server-side integration, webhook handling and end-to-end testing. Browser voice support varies by device/browser.

Offline mode caches only the public application shell. It does not cache patient records or submit bookings while offline. New bookings and queue updates require connectivity.

## Local run
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```
Open http://127.0.0.1:5000. Set a unique random `SECRET_KEY` for any hosted environment. Use HTTPS and `COOKIE_SECURE=true` in production.

## Publish with Render
1. Create a private GitHub repository and upload the contents of this folder (not the ZIP itself).
2. In Render, create a Web Service from that repository or use `render.yaml`.
3. Ensure the persistent disk is mounted at `/var/data` and `DATABASE_PATH=/var/data/queueless.db`.
4. Set a strong unique `SECRET_KEY`, `COOKIE_SECURE=true`, and `APP_TIMEZONE=Asia/Kolkata`.
5. Deploy, then open `/health`. It should report `status: ok` and `database: connected`.

This is a single-instance pilot using SQLite on a persistent disk. Do not scale it to multiple instances. For a public multi-hospital production launch, migrate to managed PostgreSQL with migrations, backups, restore testing, pooling and monitoring.

## Verification
```bash
python -m unittest discover -s tests -v
node --check static/app.js
python -m py_compile app.py tests/test_multitenant.py
```
Run tests after installing requirements and perform browser-based end-to-end testing on mobile and desktop before sharing the live URL.

## Healthcare and security notice
This is a software pilot, not a certified hospital information system. Do not enter real patient data until a qualified security professional and the hospital privacy/legal team review it. Before real-world launch, implement managed PostgreSQL, rate limiting, email verification and account recovery, staff MFA, complete audit coverage, backup/restore, monitoring, data retention/deletion, privacy notice/consent, incident response and applicable Indian privacy/legal review. Queue estimates are heuristic, not medical advice, diagnosis, triage or guaranteed waiting times.
