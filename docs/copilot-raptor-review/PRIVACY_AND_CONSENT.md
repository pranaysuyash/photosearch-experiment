# Privacy & Consent Guide — Local-first and Cloud opt-in

This document outlines how to present and implement privacy settings, consent flows, and the user experience for local vs cloud-based processing.

## Principles

- Local by default: All processing occurs on the local machine by default; UI clearly communicates local processing.
- Explicit Consent for cloud: Any operation that sends data outside the device should require opt-in.
- Minimal data sent: When cloud providers are used, only necessary data (query text, optionally embeddings) should be sent.
- Clear messaging: Show what data is sent and why, and link to a privacy policy.
- Revocable: Provide an option to revoke cloud access and remove cloud data stored by provider if applicable.

## Default UX Behavior

1. On first run, display a welcome modal: "PhotoSearch will scan folders on your device and process data locally. Would you like to enable cloud-based AI services?"

   - Options: "Continue locally (recommended)" and "Enable cloud features"
   - Provide a short bullet list: "Enabling cloud services helps with larger models and faster processing; your data may be used by provider per their policy."

2. In `Settings > AI Providers`, allow the user to add provider credentials (e.g., OpenAI, HuggingFace token). Display the provider name and a short "what's sent" explanation.

## Consent & Licensing Copy Examples

- Short form (CTA): "Enable cloud AI (Optional) — securely send queries to cloud provider to improve semantic search accuracy."
- Detailed form (modal): "If enabled, your search queries and image embeddings (not raw images) may be sent to the selected provider to process semantic search. We don’t store your raw images on our servers. Read provider-specific policy"

## Telemetry & Usage Data

- Default: telemetry is OFF. Allow users to opt-in to help improve the app.
- If enabled, only collect aggregate metrics (response times, toggles used, UI flows) and avoid including PII or full image paths.

## Cloud Model Failover

- If cloud provider is disabled/fails, fallback to local model if available. If neither available, fallback to metadata search.
- Provide a user-facing message: "Cloud AI unavailable — using local model or metadata fallback." Also provide a 'Test model' button in Settings.

## Local Storage & Indexing

- Store embedding cache and vector store locally under `~/Library/Application Support/PhotoSearch` on macOS.
- Provide a setting to change index location and an option to clear all local caches.

## Data Deletion / Export

- Allow users to export metadata and embeddings if they want a backup.
- Provide a "Delete all processed data" option with a confirmation dialog and explain the implications.

## Security

- Use OS-level permissions for file access on Tauri.
- Do not log raw paths or user data to external logs.
- Ensure encryption (TLS) for sending data to cloud providers.

## Legal & Compliance

- Provide links to privacy policies of cloud providers used.
- Provide tools for data export & deletion for GDPR compliance.

## Next Steps (Implementation).

- Add a `Settings` page with toggles for cloud providers, telemetry, and index location.
- Add the first-run modal and highlight the local-first behavior.
- Add inline messages for each provider specifying what will be transmitted and how to revoke consent.

End of Privacy & Consent Guide
