# Publish checklist
- [ ] Upload this folder's contents to a private GitHub repository.
- [ ] Set a unique random `SECRET_KEY`, `COOKIE_SECURE=true`, `APP_TIMEZONE=Asia/Kolkata`.
- [ ] Confirm persistent disk at `/var/data` and `DATABASE_PATH=/var/data/queueless.db`.
- [ ] Deploy one instance only (SQLite pilot).
- [ ] Open `/health` and confirm database connectivity.
- [ ] Test hospital signup, patient signup/login, booking, QR image, history, cancellation.
- [ ] Test admin department/doctor creation, doctor-scoped appointments, status changes and check-in.
- [ ] Test Android Chrome and desktop. Delete test data before a pilot.

Do not use real patient data until a qualified security/privacy review and required operational safeguards are complete. SMS, payment and camera QR integrations are not configured in this release.
