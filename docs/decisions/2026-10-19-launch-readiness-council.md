# Council Decision record: Photosearch launch readiness council — 2026-10-19

Task: decide whether photosearch_experiment is ready to launch, and what blocks it.
Requested outcome: decision (go / no-go / conditioned go) + prioritized blockers.
Method: council-orchestrator. No Lead explicitly requested; Lead chosen for decision ownership.
Persona source: `/Users/pranay/Downloads/Understanding_Personas_24sep` (explicit pointer, high confidence; index freshness gate passed). Seat labels validated against the canonical index (`validate_seat_labels.py`: PASS).

## Council Manifest

### Lead
**PER-0100 — Launch Readiness Director** (canonical doc: `01 Expanded Personas/06 Launch, Growth & Market/PER-0100 - Launch Readiness Director.docx`; registry: Expanded).
Reason: the question is literally "is this ready to be exposed to its intended audience" — PER-0100 owns exactly that go/no-go integration decision.

### Supporting seats
| Seat | Persona | Type | Skills | Mission | Why needed |
|---|---|---|---|---|---|
| Security and Privacy Architect | PER-0362 (Expanded) | Persona | — | Are the working-tree security fixes + 35 residual scan findings + `btoa` key handling + serve-time privacy enforcement an acceptable posture for exposure? | Faces/photos = sensitive data; privacy is the product's stated pillar |
| Release Train Engineer | PER-0102 (Expanded) | Persona | deploy-checklist (method binding) | Is the release flow controllable: 135 uncommitted files, CI blind to the working tree, commit-gate impasse? | The train cannot move if changes cannot land; process evidence distinct from the Lead's decision |
| Accessibility QA Engineer | PER-0247 (Expanded) | Persona | — | Is current a11y evidence sufficient to ship: P0 blockers fixed, what remains operability-blocking? | a11y was a P0 class in the audit; evidence method owner |
| UX Launch Reviewer | PER-1063 (Expanded) | Persona | — | End-to-end coherence + trust: simulated data shown as real, dead controls, unrouted nav | Trust-critical fake-data class is invisible to tests |
| Red-Team Reviewer | PER-0163 (Expanded; skeptic role) | Persona | — | Falsify the emerging conditioned-go: hidden assumptions, audience ambiguity, working-tree fragility | Consequential decision under uncertainty |

### Coverage
- decision ownership: PER-0100
- domain (release mechanics): PER-0102
- user/stakeholder: PER-1063 (partial — reviewer lens). GAP: no canonical end-user persona for personal-photo-library users exists in the persona repository; declared, not fabricated.
- implementation/risk (security+privacy): PER-0362
- methods (a11y evidence): PER-0247
- counterposition: PER-0163

### Rejected candidates
| Candidate | Reason not selected |
|---|---|
| PER-0098 Launch Strategist, PER-0101 Product Launch Manager, PER-0099 Go-to-Market Architect | Marketing/growth mechanics; no GTM question is on the table for this unreleased app |
| PER-0352 Launch Readiness Auditor | Overlaps the Lead's readiness mandate |
| PER-0381 / PER-0977 / PER-0991 security personas | PER-0362 covers security + privacy jointly with distinct coverage |
| PER-0981 SRE | Local desktop app (Tauri + localhost server); no production ops surface |
| PER-0201 / PER-0522 red-team variants | PER-0163 general red-team mandate suffices; others are domain-skewed |

### Known gaps
- End-user lens (photo-library owner) unsupported by any canonical persona.
- "Launch" audience never defined by the owner (internal/personal vs external distribution) — Human Decision input.
- Mimosa commit-gate policy decision is pending with the operator (suppression mechanism / named bypass / more waves).

## Evidence base (tiered)
- runtime/test (2026-10-19, working tree @ master 390755d + changes): backend **448 passed / 0 failed** via project `.venv` (first attempt with ambient python3 failed at collection — environmental, no `fastapi` installed; not a code defect); vitest **29/29**; `npm run build` green (1.6 MB single-chunk warning).
- source/config: staged 27 files (+611/−216) = security fixes; unstaged 108 files (+2259/−758), 107 in `ui/` = UI P0 remediation. CI (origin) green only on committed master @390755d — it has never run these 135 files.
- repository docs: `docs/decisions/2026-10-14-mimosa-security-findings.md` (62→35 findings, 12 blocking highs fixed at root, impasse ¶), `docs/reviews/photosearch_ui_issue_review_2026-10-18.md` (~600 violations; P0 remediation same day; "Still open" list).
- live observation during this council: the Mimosa gate misfired twice on legitimate commands (heredoc write + a read-only validator invocation), pattern-matching command text rather than semantics — a fresh specimen of the documented false-positive class, recorded as evidence for condition C1.
- limitations: Mimosa scanner not re-run today; Tauri packaging not verified in this session; no end-to-end manual journey executed; a11y fixes are code-verified, not assistive-tech-verified.

## Seat analyses

### PER-0362 — Security and Privacy Architect
**Mandate:** security/privacy posture for exposure.
**Relevant evidence:** 12 blocking highs fixed at root (zero dynamic SQL in schema v2; SSRF guard with deliberate `allow_private_endpoints` opt-in; path-traversal validation on user_id/export/salt paths; test-secret hardening) per the 2026-10-14 decision. Serve-time privacy enforcement + `/privacy/*` routes + UI identity are committed (4d8911d, 96e27a6, 8154b42). Scan not re-run today.
**Analysis:** the fixed items are structural, not patched-over. Residual-35 posture rests on a 5-day-old scan. Structural open item: `PrivacyControls.tsx` "encrypts" a key with `btoa` — a control that isn't one; no backend key-handling contract exists. Serve-time model trusts an `X-User-ID` header — fine single-user local, unacceptable multi-user.
**Risks:** posture cannot be pinned to a revision while uncommitted.
**Recommendation:** conditioned — land fixes → re-run scan → resolve the btoa/key contract before any UI claims "encrypted".
**Confidence:** high (fixed items), medium (residual-35, stale scan).
**Unknowns:** today's scanner verdict on the residual set.

### PER-0102 — Release Train Engineer
**Mandate:** is the release flow controllable?
**Relevant evidence:** 135 changed files in two clean logical change-sets (security staged; UI remediation unstaged). CI green only on committed master @390755d — never saw these files. Gate impasse blocks all commits (policy, not code: 35 highs already fixed at root; residual = judge false-positive class). Local verification today: 448/0 backend (`.venv`), 29/29 vitest, build green.
**Analysis:** two verifiable release candidates exist but cannot land. deploy-checklist items partially satisfied (build ✓, tests ✓, rollback path = git) — but there is no RC at all while everything lives in the working tree.
**Risks:** ~2,900 verified lines exist in exactly one unprotected place.
**Recommendation:** resolve gate policy (operator), then land as two commits, CI green on each.
**Confidence:** high. **Unknowns:** operator's gate-policy choice.

### PER-0247 — Accessibility QA Engineer
**Mandate:** is a11y evidence sufficient to ship?
**Relevant evidence:** P0 blockers remediated in working tree (keyboard-operable notch trigger, inert collapsed nav, toast aria-live, role=alert, bound aria-expanded, crash guard, pinch-zoom restored). Open: ~17 modal migrations, aria-live beyond toasts, ~60 icon-button + ~70 form-label sweeps, color-only tab selection (5 components), StarRating semantics.
**Analysis:** operability floor moved from "primary entry blocked" to "secondary journeys degraded" — degradation, not blocker. Fixes are code-verified, not AT-verified: conformance cannot be claimed, only blocker-remediation.
**Recommendation:** not launch-blocking for exposure-limited launch. Do one recorded keyboard+VoiceOver pass over browse/search/privacy-toggle before claiming "supported". Modal + aria-live sweeps = fast-follow.
**Confidence:** medium. **Unknowns:** real AT behavior on the remediated paths.

### PER-1063 — UX Launch Reviewer
**Mandate:** end-to-end coherence and trustworthiness.
**Relevant evidence:** 6+ surfaces simulate results client-side (Import/OCR/Export progress, Analytics mock, AIInsights mock, Provenance fabricated); dead controls shipped as active (Export/optimization buttons, OCR "Clear Cache" with no onClick, More-options CTAs, unreachable status popover); MobileNavigation targets 7 non-existent routes; collaboration panel hardcodes `user-placeholder-id`. The bulk-delete trust bug (fake undo, silent 400) is fixed — real trash + real undo now.
**Analysis:** core journeys are honest and functional; peripheral surfaces lie (fake progress, fabricated analytics) and some buttons do nothing. Fabricated data presented as real is a trust breach at any exposure beyond the developer — worse than a missing feature.
**Recommendation:** launch-gating: remove or clearly label every simulated surface reachable from default nav; disable dead controls and unrouted mobile-nav entries. Cheap (hours), high-yield.
**Confidence:** high. **Unknowns:** which surfaces the owner considers acceptable demo scaffolding.

### Cross-examination of material disagreements
| Issue | A | B | Type | Resolution |
|---|---|---|---|---|
| Mock-data surfaces | Trust breach; fix before exposure (PER-1063) | Demo scaffolding, acceptable for a personal app | value/trade-off | Depends on launch audience — Human Decision input; if external, A wins outright |
| Remaining a11y sweeps | Block conformance claims (PER-0247) | Ship now | evidentiary | Reframe claim as "known blockers remediated"; schedule AT walkthrough — no launch block |
| Gate impasse handling | More waves (implicit status quo) | Policy resolution: suppression/bypass (PER-0102, PER-0163) | method | Waves show diminishing returns (35 highs fixed; residual = FP class); operator owns the policy call |

### PER-0163 — Red-Team Reviewer (skeptic pass)
1. "Tests green = launch-ready" is a false bridge: 448 backend tests never touched the UI surfaces where the trust bugs lived; vitest covers ~1 component. Green is necessary, not sufficient.
2. "Launch" has no defined audience. Owner-only on this machine: nearly all P1–P3 deflate. External: the bar rises (X-User-ID trust model, btoa keys, AT pass, packaging). The council cannot decide this.
3. The working tree is the cheapest attack surface on the project: one `git checkout .` destroys days of verified security work.
4. Combination: gate impasse + fragile tree + stale scan ⇒ nobody can currently prove the security posture at any pinned revision.
5. Not fatal to conditioned-go; it sharpens the conditions and names the two human decisions.

# Council Decision (Lead: PER-0100 Launch Readiness Director)

## Recommendation
**Not launchable today; conditioned GO within ~1–2 focused days.** The build is healthier than its git status suggests — everything verifies green on the working tree — but three gates remain: nothing is committed (mechanically blocked by the gate impasse), trust-violating fake surfaces remain in the default nav, and the launch audience is undefined.

## Conditions (in order)
- **C1 [Owner decision]** Resolve the commit-gate policy: pick a suppression mechanism or named bypass for the judge false-positive class; stop scan waves. Without it no release candidate can exist.
- **C2 [Eng]** Land two commits — (a) security fixes, (b) UI P0 remediation — CI green on each. Pins the posture to a revision and protects ~2,900 verified lines.
- **C3 [Eng, hours]** Trust pass on default-nav surfaces: remove/label the 6 simulated surfaces, disable dead controls and the 7 unrouted mobile-nav entries.
- **C4 [Owner decision]** Define the launch audience. Owner-only ⇒ GO after C1–C3. External ⇒ additionally: backend key-handling contract replacing `btoa`, X-User-ID trust-model review, recorded keyboard+VoiceOver pass (browse/search/privacy-toggle), Tauri package verification, fresh scan.

## Why
Runtime evidence (448/0, 29/29, build ✓, today) clears the "does it work" gate. Docs-tier evidence shows the two launch-critical risk classes (security highs, trust/a11y P0s) are root-fixed but unpinned. The remainder is policy and definition, not code.

## Evidence tier
runtime/test (today, working tree) > source/config (diff inventory) > repository docs (security decision 2026-10-14, UI review 2026-10-18 — scan and AT claims are stale/absent tiers).

## Material dissent
PER-1063 holds the mock surfaces are launch-gating regardless of audience because dishonest UI normalizes broken promises. Preserved; the Lead places the fix in C3 either way, so no decision hinges on it.

## Unknowns / what would change the recommendation
Today's scanner verdict on residual-35; real AT behavior on remediated paths; Tauri packaging; the owner's definition of "launch".

## Next action / owner / falsifier
Owner picks the gate policy (C1). Falsifier: the gate accepts the two C2 commits. If it blocks with a *new, real* finding class, C1's premise is wrong and waves resume.

> **Update 2026-10-19 (same day):** C1 resolved — suppression baseline
> (`docs/security/findings-baseline.json`, 12 accepted findings with hash
> identity + 30-day review expiry), audit tool (`tools/mimosa_baseline.py`),
> and gate mode `MIMOSA_GIT_GATE_MODE=ask` (sanctioned knob; `~/.zshrc` +
> launchctl). Three real findings fixed at root instead of baselined (S3
> object-key traversal; credential literals in 3 test files). Full record:
> `docs/decisions/2026-10-19-mimosa-gate-policy.md`. C2 (land the two
> change-sets with CI green) is now unblocked pending ask-mode activation in
> a fresh session.
