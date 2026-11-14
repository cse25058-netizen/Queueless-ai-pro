# QueueLess AI — preliminary code review (not a certification)

## Changes made in this revision
- Added session-bound CSRF token checks to authenticated POST/PATCH/DELETE requests.
- Kept the CSRF token across login, signup, hospital signup and logout session changes so the frontend can continue safely.
- Restricted doctor appointment lists and status changes to appointments assigned to that doctor's linked profile.
- Added hospital-admin provisioning of a doctor login with a 12-character minimum temporary password.
- Added an authenticated QR image endpoint and staff token check-in endpoint.
- Changed appointment-date validation to use the configured Asia/Kolkata application timezone.

## Remaining risks / blockers before real patient data
- Flask runtime and integration tests have not been run in this build environment; only Python compilation and JavaScript syntax checks were possible.
- No independent penetration test or professional security audit has been performed.
- No rate limiting or abuse detection on login/signup/booking.
- No email verification, password reset, MFA, or secure doctor invitation/activation flow.
- No managed PostgreSQL migration; SQLite is only suitable for a small single-worker pilot.
- Audit logging is incomplete for all sensitive reads/changes and is not immutable.
- No automated backup/restore test, monitoring, alerting or incident-response workflow.
- Payment, SMS and reminders are not active integrations.
- QR generation is available; camera scanning is not.
- Public queue endpoint exposes token, department, slot and status; the hospital must approve that disclosure model.
- No independent validation of the hospital's authority to register or of doctor credentials.

## Required release gates
1. Run unit, integration, tenant-isolation and browser E2E tests in CI with real dependencies.
2. Perform a professional threat model and penetration test, including cross-tenant IDOR tests.
3. Migrate to managed PostgreSQL and verify backups/restores.
4. Configure HTTPS, secrets, MFA, rate limiting, email verification and operational monitoring.
5. Complete provider integrations and verify webhook signatures, retries, idempotency and failure paths.
6. Obtain hospital/legal/privacy approval before processing real patient data.
