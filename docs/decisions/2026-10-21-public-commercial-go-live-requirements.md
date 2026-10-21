# Decision record: what it takes to go public — and to charge for it — 2026-10-21

Release-readiness framing (`RELEASE_READINESS_DOCTRINE.md` semantics): GO /
CONDITIONAL GO / NO-GO / NOT READY TO DECIDE. Three audiences, three verdicts.

| Audience | Verdict today | What closes it |
|---|---|---|
| **Owner-only (you, this machine)** | **GO** once `59ea8ee` is pushed | Nothing further — C1–C3 of the launch council are done |
| **Public, free distribution** | **CONDITIONAL GO** | B1–B9 below (~1–2 focused weeks) |
| **Commercial (paid)** | **NO-GO** | Three hard blockers H1–H3, then the commercial plumbing |

Everything below is labeled by truth status. "Observed" = seen in this repo
this session. "Researched" = external fact from training knowledge, to be
re-verified against the current source before relying on it.

## Evidence base (observed, 2026-10-20/21)

- **Tauri shell** (`src-tauri/tauri.conf.json`): productName `PhotoSearch`,
  version `0.1.0`, identifier `com.photosearch.experiment`, bundle targets
  `all`, **macOS signing config `null`, no updater plugin**, CSP present and
  tight (`script-src 'self'`, connect limited to loopback + ipc). Rust
  toolchain present locally.
- **The Tauri shell does not launch the backend.** No sidecar is configured;
  the Python server is started separately by `scripts/dev-restart.sh`
  (`python server/main.py`). A public build must bundle and spawn it.
- **Server bind:** `server/main.py` `__main__` bound `0.0.0.0:8000` — the
  full-resolution photo and face-data server was LAN-reachable by default.
  **Fixed this session** (staged): canonical `Settings.HOST="127.0.0.1"` /
  `PORT=8000`, env-overridable for deliberate LAN use.
- **No LICENSE file** in the repo. **No third-party telemetry or crash
  reporting** anywhere in `ui/src` or `server/` — a genuine local-first
  posture worth preserving as a claim.
- **Models referenced in code:** InsightFace `buffalo_l` (17 refs; face
  embeddings, `embedding_version="insightface-buffalo_l"`), Whisper (24),
  EmbeddingGemma/Gemma (18), BLIP (1), Ollama-served `deepseek-ocr` (54 ollama
  refs), sentence-transformers (6).
- **Dependency licenses (scanned):**
  - npm production (`license-checker`): 124 MIT, 6 Apache-2.0, 4 ISC, 2
    BSD-3, 1 0BSD, 1 "MIT*" (guessed), 1 UNLICENSED — almost certainly the
    app's own root package (no `license` field); verify. **No copyleft.**
  - Python (`importlib.metadata`, heuristic): 79 permissive, **59 with no
    license metadata** (needs a proper `pip-licenses` pass — most are
    well-known permissive: numpy, fastapi, pillow, cryptography, faiss-cpu,
    onnx, insightface *code*), 3 heuristic flags on manual check: `scipy`
    and `pandas` are BSD-3 (regex hit text inside their license files —
    false positives); `IPTCInfo3` is dual `Artistic-1.0 OR GPL-1.0-or-later`
    — use under Artistic or replace.
- **Commercial scaffolding exists but is a stub:** `server/pricing.py` +
  `server/api/routers/pricing.py` define `PricingTier` with
  `stripe_price_id` fields and a `pricing_manager`; no payment, entitlement,
  or license-key flow behind it.
- **Compliance scaffolding exists:** `server/compliance/gdpr_manager.py`
  (deletion requests surfaced in CI test names), `/privacy/*` per-photo
  controls, serve-time enforcement (committed 10-14).
- **Claim-reality item:** the API carries `encryption_enabled` /
  `encryption_key_hash` on privacy controls and the UI has an "encryption"
  tab, but at-rest encryption of photos is **not verified to exist**. The
  client-side `btoa` fake hash is already gone. Until real at-rest encryption
  is implemented, the word "encryption" must not appear in user-facing copy
  (Operating Doctrine §13).

## H1 — Face-recognition model licensing (hard blocker for anything paid)

**Researched:** InsightFace's code is MIT, but its model-zoo pretrained
weights — including `buffalo_l` and `antelopev2` — are provided for
**non-commercial research use only**. People/faces clustering is a core
feature of this product, so a paid product cannot ship these weights.
(Already flagged in project memory on 2026-10-19; this record makes it the
gating item.) Re-verify the exact current wording in the InsightFace README
before any commercial decision.

Options, in my preference order:
1. **Apple Vision framework via a small Swift sidecar (macOS).** Face
   detection + feature prints are on-device, free, commercial-OK, and fit a
   Tauri macOS app. Cost: an embedding migration (existing clusters keyed to
   `insightface-buffalo_l`; the `embedding_version` field already exists for
   exactly this) and macOS-only for that feature.
2. **InsightFace commercial license** (they license commercially on
   request). Fastest if the price is acceptable; zero code change.
3. **Permissively licensed open weights.** Quality-competitive face
   recognition under a true commercial license is scarce; treat as research,
   not a plan.
4. **Ship paid tiers without faces.** Honest but removes a headline feature.

Note the subtlety for a *free* public release: "non-commercial" is about
purpose, not price — a free app from an individual with no revenue is
arguably non-commercial, but that is a counsel question, not an engineering
one. Safest sequencing: do the Vision swap before any public build.

## H2 — Distribution pipeline (hard blocker for public, free or paid)

- **Bundle the backend.** PyInstaller (or equivalent) sidecar for the
  Python server, spawned by Tauri; health-wait on loopback; graceful
  shutdown. Today users would have to run a dev script.
- **Model weights at first run.** EmbeddingGemma is HF-gated (requires a
  token — unacceptable to demand from customers): redistribute under the
  Gemma Terms of Use (permitted, with notice/prohibited-use obligations) or
  host a mirror. `buffalo_l` redistribution is itself restricted (see H1).
  Whisper (MIT), BLIP (BSD-3), deepseek-ocr (MIT per its release) are fine.
- **macOS:** Developer ID signing + notarization + hardened runtime (Tauri
  bundler supports this via `APPLE_*` env), real reverse-DNS identifier,
  signed auto-updates via `tauri-plugin-updater`. **Windows** (if targeted):
  EV code signing. **App Store** is the hard path: sandboxing a spawned
  Python backend is a serious constraint; a notarized DMG with direct
  distribution is the realistic route.
- **Operability:** opt-in crash reporting (keep "no telemetry" as a default
  and a claim), release notes, a support channel, versioned releases.

## H3 — Biometric data legal basis (hard blocker for public)

**Researched:** face embeddings are biometric identifiers. Illinois BIPA
requires written consent, a public retention/destruction schedule, and bars
profiting from biometrics; Texas CUBI and Washington have analogues; GDPR
treats biometrics as Article 9 special-category data (explicit consent,
likely a DPIA); CPRA classes it as sensitive personal information.
**On-device-only processing is a strong mitigant, not an exemption.**

Required: an explicit opt-in before the first face scan (not buried in
settings), a retention/deletion statement that the existing
`gdpr_manager` deletion flow actually honors for embeddings and crops, a
privacy policy that states processing is local, and counsel review before
public launch. The compliance module is a real head start; the consent UX
in front of it is the missing piece.

## B-list — public, free distribution (even before charging)

- **B1** `LICENSE` (proprietary EULA or an OSS license — a product decision)
  + `THIRD_PARTY_LICENSES` notices generated from the dependency scan
  (MIT/Apache/BSD attributions; Gemma Terms notice; Whisper MIT; BLIP BSD-3);
  resolve the 59 metadata-missing Python entries with `pip-licenses`;
  replace or license-pick `IPTCInfo3`.
- **B2** Privacy policy whose claims match the code: local-first, no
  telemetry (true today), what face processing does, how to delete.
- **B3** Encryption claim reality: implement real at-rest encryption or
  remove the encryption tab/copy (§13).
- **B4** Identity model: serve-time enforcement trusts an `X-User-ID`
  header — correct for single-user local, unsafe for any shared-device or
  multi-user mode. Document the single-user scope or add real auth first.
- **B5** Loopback bind — **done** (staged this session).
- **B6** Real bundle identifier and product metadata; icon set; version
  scheme.
- **B7** Recorded keyboard + VoiceOver pass over browse/search/privacy-toggle
  (today's a11y claims are code-verified, not AT-verified).
- **B8** Fresh full Mimosa scan; baseline reconciled (13 accepted today,
  review expiry 2026-11-19).
- **B9** Support path + release notes + crash-report opt-in.

## Commercial plumbing (after H1–H3)

- Legal entity and terms of sale; refund policy.
- **Merchant of record** (Paddle or Lemon Squeezy) handles global VAT/sales
  tax and invoices — strongly preferred over Stripe-direct for a solo
  desktop product. Wire it into `server/pricing.py` (the `stripe_price_id`
  scaffold generalizes to a `provider_price_id`).
- License keys / entitlements with offline grace periods (desktop apps must
  work offline); trial logic; device limits; upgrade/downgrade paths.
- Receipts, tax handling, chargeback process, support SLA you can keep.

## Recommended sequencing

1. **Now:** owner-only GO on push of `59ea8ee`.
2. **Public-free beta (~1–2 weeks):** H2 bundling + signing + updater, H3
   consent UX + policy + counsel, B1–B9, **and the Apple Vision face swap**
   so the public build never ships non-commercial weights.
3. **Paid (~2–4 weeks after beta):** merchant of record + entitlements on
   the existing pricing scaffold; at-rest encryption only if it becomes a
   sold feature, otherwise remove the claim.

## What would change this assessment

- InsightFace granting a commercial license at acceptable cost removes the
  Vision migration from the critical path.
- Deciding faces are not a sold feature collapses H1 and most of H3.
- Choosing OSS licensing for the app changes B1 and the pricing model but
  none of H1–H3.

## Validation and unverified items

- Observed items: config files, grep counts, scan outputs, bind fix
  (`settings.HOST == "127.0.0.1"` confirmed at import).
- Unverified: current InsightFace license text (researched, re-check);
  the 59 metadata-missing Python deps; the UNLICENSED npm entry identity;
  whether `gdpr_manager` deletion reaches face embeddings/crops; whether any
  at-rest encryption exists.
- Not estimated by anyone with authority: counsel cost/time; InsightFace
  commercial pricing.
