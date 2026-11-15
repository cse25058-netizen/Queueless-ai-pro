# External integrations required for the full feature set

The app is deployable without these services, but they cannot be activated by code alone. The account owner must create provider accounts, complete verification/billing and set secrets in the hosting dashboard.

| Feature | Provider/account required | Status in this package |
|---|---|---|
| SMS updates | Twilio account, verified sender/number, Account SID + Auth Token + From number | Optional SMS adapter; not active without credentials |
| WhatsApp notifications | WhatsApp Business Platform / approved provider, templates and sender verification | Not configured |
| Online payments | Razorpay merchant account, Key ID/Secret, webhook secret and production verification | Not configured |
| AI assistant | AI provider API key, usage limits, safety policy and privacy review | Navigation helper only; no external clinical AI |
| Live speech | Browser SpeechRecognition support and microphone permission | Browser-dependent voice input |
| Camera QR scan | Camera permission and browser QR detector support | QR image generation + manual token entry; camera scanning not enabled |
| Email verification/reset | Transactional email provider and verified sending domain | Not configured |
| Managed database | PostgreSQL provider, migration, backup and restore plan | SQLite pilot database in current deployment template |

Never place provider secrets in source code, GitHub or browser JavaScript. Configure them only as encrypted environment variables in the hosting provider.

## Healthcare production gate
Do not use real patient data until qualified security and privacy/legal reviews, access controls, retention/deletion, backups, audit trails and incident response are complete. Queue estimates are not clinical advice, triage or guarantees.
