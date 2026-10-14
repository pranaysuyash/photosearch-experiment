# Jev (TypeSafe) Intent-Routing Exploration — 2026-10-13

**Status:** exploration complete; deterministic router fixed; advisory Jev tier implemented (default OFF)
**HEAD pinned:** master `f65a551` (clean tree at session start); implementation is uncommitted working-tree state on top of it
**Scope executed:** L0 docs/research + L1 experiment artifacts + L2 bounded live provider calls (17 + 3 + 2 requests, pinned model, approved credential store) + L1 product implementation (§9) and tests
**Authorization:** operator request 2026-10-13 — "use jev on the product right now, identify how it can help us, check online how people have been using it and document, then run … explore, document, use it."
**Canonical Jev surfaces:** runbook `/Users/pranay/Projects/runbooks/jev-typesafe.md`, skill `/Users/pranay/Projects/.agents/skills/typesafe-ai/SKILL.md`, living map `/Users/pranay/Projects/exploration_maps/jev/EXPLORATION_MAP.md`.

---

## 1. What Jev is and why it fits this product

Jev is TypeSafe's "System One" model: it takes structured **state** plus typed **questions** and returns **calibrated probabilities and choices**, not generated text. Three primitives map directly onto decisions this product makes on every search:

| Primitive | Meaning | Photosearch decision |
|---|---|---|
| `Choice` | pick one of a defined set | which search capability a query means (the 12-intent router) |
| `Noul` | probability that a yes/no holds | does this query need face-search privacy gating? does it need multi-mode fusion? |
| `Score` | position on ordered levels | result relevance for reranking; result-quality gates |

Code stays in control: candidate lists, thresholds, fallbacks, side effects. This matches the runbook invariant ("Jev recommends or verifies; code owns permissions, thresholds, side effects").

## 2. The decision-heavy surface we measured

`src/intent_recognition.py` (`IntentDetector`) routes every natural-language query to one of 12 capabilities (camera/date/location/people/object/scene/event/technical/color/emotion/activity/generic) using keyword + regex scoring, and feeds hybrid-search weighting, suggestions, and UI badges.

**Observed production defects (independent of Jev — these are real product bugs):**

1. **No-signal and tie cases fall through to `camera`.** When all intent scores are zero (or tied at the top), `max()` over the dict returns the first key, which is `camera`, never `generic`. Verified: `"zzz qwerty florb"` → `camera`.
2. **Substring keyword matching causes false positives.** `"park"` (location) is contained in `"parking"`; verified: `"parking garage"` → `location`.
3. **Bare years are invisible to date detection.** The date pattern requires full `YYYY-MM-DD` shapes; `"summer 2023"` → `camera` (defect 1).

Fix recommendation (product, no Jev required): word-boundary keyword matching, explicit zero-score → `generic` fallback, and a bare-year pattern. This belongs in a separate small PR; this exploration did not touch the file.

## 3. How people are using Jev (online research, 2026-10-13)

Sources consulted live: [docs index](https://docs.typesafe.ai/llms.txt), [intent-routing pattern](https://docs.typesafe.ai/patterns/intent-routing.md), [skill-suggestion cookbook](https://docs.typesafe.ai/cookbooks/skill_suggestion.md), [jev-1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md), Hacker News (Algolia API), plus workspace prior experiments.

- **Launch and reception:** "Introducing System One Models and Jev" — 1,989 points / 520 comments ([HN, 2026-09-15](https://news.ycombinator.com/item?id=49717558)); TechCrunch: ChatGPT/RLHF inventor's new model kind "thrilling developers" ([2026-09-18](https://techcrunch.com/2026/09/18/a-new-kind-of-ai-model-from-a-chatgpt-inventor-is-thrilling-developers/)).
- **Competitive response:** OpenAI answered with a Decision API built on Luna ([The New Stack, 2026-09-29](https://news.ycombinator.com/item?id=49896979)) — decision-style models are becoming a category.
- **Real documented integrations** (TypeSafe cookbooks, all follow the same shape: code owns control flow, Jev owns one narrow judgment):
  - [Skill suggestion](https://docs.typesafe.ai/cookbooks/skill_suggestion.md): routes agent turns to 1 of 182 Hermes skills — one `Choice` ranks all skills, then reranks the top 3 with a companion Noul. The direct precedent for our intent router.
  - [Reranking](https://docs.typesafe.ai/cookbooks/rerank_typesafe.md): BM25 shortlist + one judgment per query-candidate pair raised legal-search top-1 from 5%→18%, top-10 from 38%→62% — the pattern for reranking photosearch results.
  - [Intent routing](https://docs.typesafe.ai/patterns/intent-routing.md): Choice intent + Score complexity + confidence gates routing between deterministic code / specialist LLM / human.
  - Others: Twitch chat moderation filter, citation checking, RAG-passage classification, entity alignment, LLM guardrails, date extraction.
- **Ecosystem:** open-source reproductions and alternatives are proliferating — "von" (sub-15ms local alternative, [HN](https://news.ycombinator.com/item?id=49781612)), "onesie" CLI ([HN](https://news.ycombinator.com/item?id=49876472)), a 70-reproduction Decision Index ([HF space](https://news.ycombinator.com/item?id=49934879)) — evidence the decision-model shape is validated, and that a local fallback path exists if provider dependence ever matters.
- **Known limits (jaggedness page + community):** literal reading (write exact criteria), no reliable counting/math/dates (keep in code), context rot (send only what the question needs), **choice-option-order sensitivity** (reorder to verify), and no vision/generation — Jev cannot look at photos (it routes and judges over text descriptions only).

## 4. Experiment: measured head-to-head on the product's router

**Artifacts** (canonical experiment location, following the map's per-experiment pattern): `/Users/pranay/Projects/exploration_maps/jev/experiments/photo_intent_router/` — `fixture.json` (17 synthetic, labeled cases), `photo_intent_probe.py`, `results_baseline.json`, `results_live.json`.

Design points that differ from the earlier skill-router experiment:
- The offline baseline runs the **production** `IntentDetector` imported live from this checkout (not a toy comparator), and candidate intent names/descriptions are read from the product at runtime, so the fixture cannot drift from the product.
- The live payload carries one `Choice` (primary intent) plus two companion Nouls (needs-multi-mode; privacy gate) per case — the same 3-question batch shape the living map validated as safe for narrow routing sets.
- Intent descriptions in state are the product's own strings; state stays small (query + 12 one-line descriptions) per the context-rot jaggedness rule.

### Results (17 cases, 2026-10-13)

| Metric | Production keyword router (offline) | Jev `jev-1.13.0` (live) |
|---|---|---|
| Primary intent agreement with product-UX labels | **52.9%** | **88.2%** |
| Needs-multi-mode accuracy | 52.9% | 82.4% (Brier 0.137) |
| Privacy-gate accuracy | 94.1% | 94.1% (**Brier 0.048** — well calibrated) |
| Latency | n/a (in-process) | mean 311 ms / p95 346 ms |
| Cost for the full run | — | 16,703 in / 2,380 out tokens |

Live receipts: 17/17 HTTP 200, served `model` field = `jev-1.13.0` in every response (version anchor recorded per runbook). Option-order spot check (documented jaggedness): 3/3 consistent with reversed candidate order.

**Jev agreed with the production router on only 9/17 cases** — it corrected 8 cases the keyword router gets wrong (including all three defect classes in §2) while disagreeing on 2, both pre-flagged ambiguous:

- `amb_002` "beach sunset with the whole family" → Jev said `scene`, label says `people`. Genuine judgment call; either defensible.
- `loc_002` "landscapes of Iceland" → Jev said `scene`, label says `location`. Common-sense place-seeking; keyword router also says `scene`.

Disagreements should be reviewed case-by-case, not folded into an aggregate; both are recorded in `results_live.json` with notes.

### Evidence tiers

- Baseline numbers: **Observed** (S1 — ran the real router on the fixture; no mutation-grade falsification performed).
- Live numbers: **Observed** (Tier 2 — synthetic labeled replay, HTTP receipts + served-version anchor; not production calibration).
- Production defect root causes: **Verified** by direct behavioral checks + static reading of `src/intent_recognition.py` (S1).
- "Jev beats the keyword router on real user queries": **Unknown** — this fixture is synthetic. The exact next check is Tier 3: replay real (redacted) query logs.

## 5. Where Jev can help this product (ranked)

1. **Query intent routing — measured.** Advisory `Choice` behind the existing router: run keyword router (free, instant); when it is low-confidence or no-signal, ask Jev; act on Jev's answer only above a confidence threshold (docs recommend ≥0.5 gate; calibrate on real queries). This alone fixes the `camera`-fallback class of misroutes measured at 47% of this fixture.
2. **Face-search privacy gating — measured equivalent, cheap.** The privacy `Noul` matched labels at 94.1% with the best calibration in the run (Brier 0.048) and catches person-queries that the keyword router misroutes away from `people` (e.g. "my daughter at school"). It should gate the face-search path regardless of which router wins.
3. **Multi-mode fusion hint — measured 82.4%.** Decides when to blend semantic + metadata + OCR search instead of single-mode. Threshold-sensitive; needs real-data calibration.
4. **Result reranking — proposed, unmeasured.** The cookbook's biggest wins (top-1 5%→18%) are in reranking; apply `Score` per candidate for top-K search results.
5. **Duplicate-detection confirmation — proposed.** `Noul` over flagged near-duplicate pairs before destructive merges (product has duplicate surfaces with db sprawl; a calibrated confirm step fits).
6. **Kept out by model shape:** anything visual (Jev cannot see photos — VLM lane owns that), exact date/size filtering (code owns arithmetic), anything requiring generation.

## 6. Integration shape (Proposed — not implemented)

```
query ──> keyword router (deterministic, free)
             │ score == 0 OR confidence < threshold
             ▼
         Jev Choice (pinned jev-1.13.0, 3-question batch, ~311 ms, ~1k tok)
             │ confidence >= gate
             ▼
         route + badges  ◄── Jev result is advisory; keyword router remains the fallback
```

- Privacy `Noul` runs in the same call and gates face-search before any results render.
- Offline/failure behavior: provider error or timeout → deterministic route (never block search on Jev).
- Cost: ~1k input tokens per low-confidence query; with a keyword-first gate, only the hard tail pays.
- Needs before any production claim: real-query replay (Tier 3), privacy review for sending query text to a hosted provider (queries are user content; the runbook's redaction rule applies), and a threshold calibration pass.

## 7. Open questions

- Do real user queries shift the 88.2% (synthetic-fixture) number? Replay logs when available.
- Should the two `scene`-vs-`location`/`people` disagreement shapes adjust the product's dominant-intent convention, or the label convention? Owner call.
- Is there volume for Jev at all (query rate × tail fraction × 1k tokens), or is the deterministic fix in §2 sufficient alone? The deterministic fixes are worth shipping regardless.

## 8. Implementation (same session, operator: "start and do all and document")

All changes are uncommitted working-tree edits on top of `f65a551`. Nothing is wired to send data externally by default.

### 9.1 Deterministic router fixes — `src/intent_recognition.py`

Four defects fixed (the three from §2 plus one the test run exposed):

1. **Word-boundary keyword matching** — `"parking"` no longer matches the `park` location keyword; brand boost also word-bounded.
2. **No-signal/tie fallthrough** — when every intent scores zero the router now returns `generic` (confidence 0) instead of `camera`. True ties (all > 0) remain deterministic first-key behavior; this residual limit is pinned by a test and is what the advisory tier is for.
3. **Date patterns** — added month names (excluding the ambiguous standalone `may`/`mar`), 3-letter abbreviations, and bare years (`19xx`/`20xx`).
4. **Camera double-count removed** — the camera intent's pattern list duplicated its keyword list verbatim, scoring each camera word at 2.75 (1.25 keyword + 1.5 pattern) and biasing camera over all other intents (this is why "grandma smiling at the camera" misrouted). Pattern list emptied; keyword scoring unchanged.
5. **Family-relation keywords added to the people intent** (grandma, daughter, mother, father, mom, dad, wife, husband, brother, sister, cousin, baby, child, children, kid, kids, colleague, coworker, grandpa, son) — relation words users actually name carried no signal before.

**Measured on the same 17-case labeled fixture:** primary-intent agreement **52.9% → 76.5%**; needs-multi-mode 52.9% → 70.6%. The 4 remaining disagreements are exactly the semantic tail (`loc_001` "Kyoto Japan" and `loc_002` "Iceland" — no keyword can express geography; `ppl_001` camera/people tie; `act_001` people-vs-activity boundary), and Jev answered all four correctly in the earlier live run. The layers are complementary: keyword router free/instant for the clear majority, Jev for the tail.

### 9.2 Advisory Jev tier — `src/jev_intent_advisor.py` (new)

`JevIntentAdvisor` wraps `IntentDetector` with the identical public interface (`detect_intent` / `get_search_badges` / `get_search_suggestions` / `get_all_intents`), so all existing consumers (`server/api/routers/intent.py`, `search.py`, `advanced_intent_search.py`) keep one canonical path — no new routes, no parallel system.

- **Default OFF.** Enabled only with `JEV_INTENT_ADVISOR_ENABLED=1` **and** a `TYPESAFE_API_KEY` in the environment; otherwise a pure pass-through that cannot make a network call. The API key is read from the process environment only — product code never reads `~/Projects/.env.local` (that injection is an operator action).
- **Two escalation triggers** (corpus-measured): `low_confidence` when keyword confidence is below `JEV_INTENT_TAIL_THRESHOLD` (default 0.5), and `contested_margin` when the top two intents finish within `JEV_INTENT_MARGIN_THRESHOLD` (default 2.0) — the confidently-wrong shape (pattern-boosted winner over a keyword runner-up) that confidence alone cannot see. On the 2,290-case corpus this lifts wrong-case escalation coverage from 50.1% to 69.5% at a 44.2% call rate. The active trigger is recorded in `advisor.escalation`. Verified live: "photos of my daughter at school" (single keyword hit, no runner-up) still costs zero provider calls.
- **Batch shape:** one request — `Choice` (primary intent over the detector's own intent descriptions, read at call time so definitions cannot drift) + two `Noul`s (needs-multi-mode; privacy gate). Pinned `JEV_MODEL`, default `jev-1.13.0`; timeout `JEV_INTENT_TIMEOUT_S` (default 4 s).
- **Gating and validation:** the returned choice must be in the candidate set (Jev cannot invent a capability) and its confidence must clear `JEV_INTENT_CHOICE_GATE` (default 0.5) before it overrides routing; on override, suggestions and badges are re-derived through new public delegates on the detector (`generate_suggestions` / `generate_badges`, thin wrappers over the existing private methods).
- **Never breaks search:** any transport, parsing, validation, or merge failure falls back to the deterministic result. The result dict gains an additive `advisor` metadata block: `{enabled, source: keyword|jev|keyword_fallback, model, latency_ms, privacy_gate, needs_multiple_modes, jev_choice, jev_confidence, error}`. API responses keep working (v2 route projects explicit fields; OpenAPI schemas allow additional properties).
- **Authorization boundary:** `advisor.privacy_gate` is an advisory signal for face-search UX. Per the runbook invariant, Jev output is never a permission decision; the product's face-privacy controls remain the authority.
- **Known limitation:** the privacy Noul rides the escalation path, so it is `null` when the keyword router is already confident. Queries confident enough to skip Jev are routed to `people` by the router itself, which is the signal face-search actually consumes today.

### 9.3 Wiring — `server/core/bootstrap.py`

`init_stores` now constructs `JevIntentAdvisor.from_env(IntentDetector())` for the state's `intent_detector`. Disabled by default; server behavior is unchanged unless the operator opts in via environment.

### 9.4 Verification evidence

- **Tests:** `tests/test_intent_recognition.py` (15 cases — regression coverage for each fix, including a pinned tie-behavior test and public-delegate parity) + `tests/test_jev_intent_advisor.py` (14 cases — disabled pass-through, no-key, high-confidence skip, escalation+merge, invalid-choice rejection, below-gate fallback, transport error fallback, malformed response fallback, interface parity, env configuration). **36 passed** after the trigger-hardening pass (§9.3 addendum). The fallback path has S2-grade evidence: a signature-mismatch bug introduced during development surfaced as `keyword_fallback` in tests rather than a crash — the never-break-search invariant held on its first real fault.
- **Hooks:** all 8 pre-commit hooks pass on the five changed files (ruff, ruff-format, file-size limits included).
- **Fixture replay (offline, zero credit):** `results_baseline_post_fix.json` in the experiment dir — 76.5% post-fix vs 52.9% pre-fix, full disagreement list retained.
- **Live smoke through the product module (2 calls, HTTP 200, served `jev-1.13.0`):** "landscapes of Iceland" escalated (306 ms; Jev routed `scene` at 0.81 — the known flagged scene-vs-location disagreement, recorded as-is, not fit to the label) and "photos of my daughter at school" resolved by the router at confidence 1.0 with no escalation. Both advisor paths exercised end-to-end in the real codebase.
- **Not yet established (stays Unknown):** accuracy on real user queries (needs redacted log replay), threshold calibration on production traffic, and any production claim — the tier ships off by default.

### 9.5 Operator configuration reference

```bash
# Enable the advisory tier (per-process env; key never stored in config files)
export JEV_INTENT_ADVISOR_ENABLED=1
export TYPESAFE_API_KEY=...          # from your secret store
export JEV_MODEL=jev-1.13.0          # optional; pinned default
export JEV_INTENT_TAIL_THRESHOLD=0.5   # optional: escalate below this keyword confidence
export JEV_INTENT_MARGIN_THRESHOLD=2.0 # optional: escalate when top-2 intents finish within this margin
export JEV_INTENT_CHOICE_GATE=0.5    # optional: accept Jev routing above this confidence
export JEV_INTENT_TIMEOUT_S=4        # optional: provider timeout; timeout = fallback
```

Rollback: unset `JEV_INTENT_ADVISOR_ENABLED` (advisor becomes a pass-through) or revert the bootstrap line to `IntentDetector()`; the detector fixes are independent and safe to keep in either case.

## 9. Persona council at corpus scale (same session, operator: "simulate, get personas created, use council... run on queries, thousands of them")

Artifacts: `/Users/pranay/Projects/exploration_maps/jev/experiments/photo_persona_council/` — `personas.json`, `generate_corpus.py`, `corpus.json`, `persona_council_probe.py`, `results_offline.json`, `results_council_live.json`.

### 9.1 Simulated personas (documented fixtures, deliberately outside the registry)

Four synthetic user-lens personas were created for this experiment — full mandates, ambiguity preferences, privacy sensitivity, and weights in `personas.json`:

| ID | Lens | Routing bias | Privacy |
|---|---|---|---|
| SIM-AVA | Family Archivist | people > event | high |
| SIM-MARCUS | Working Photographer | camera/technical | low |
| SIM-PRIYA | Privacy-Conscious Parent | people/location/date; owns the privacy Noul | maximum |
| SIM-DARIO | Visual Curator | color/scene/emotion | medium |

**Governance (council-orchestrator compliant):** these are bounded speciality/user-lens fixtures, not canonical personas. They are deliberately **not** added to the Master Persona Registry (`~/Downloads/Understanding_Personas_24sep`, resolved canonical, read-only) — that registry holds workspace decision personas, not simulated product users. They live only in the experiment directory and are never presented as real identities. The council vote here is a product mechanic under test (simulated users adjudicating search routing), measured against labels, not workspace decision-making.

### 9.2 Corpus — 2,290 deterministic labeled queries

`generate_corpus.py` (seed 20261013; byte-identical on re-run) expands the 17-case fixture's families into **2,290** unique labeled queries across 21 families (12 simple intent families + 9 combined-signal families + generic). Labels inherit the fixture convention; **label_source is template-family**, which is lower epistemic strength than hand labels, and four combined families (camera+date, color+date, event+people, emotion+scene) are convention-dependent — recorded as such.

### 9.3 Findings

**Offline, full corpus (free, ~seconds):** fixed router agreement **39.4%** (vs 76.5% on the 17-case fixture — the fixture under-represented the families keywords structurally cannot express: geography 0%, scene nouns 8%, tech jargon 10%). People routing is perfect (100% on its families) and the privacy side has recall 1.0 / precision 0.69 / F1 0.82 — over-gating toward people, the safe direction.

**Calibration gap (product-relevant beyond this experiment):** router confidence is score share, not calibration — median confidence is **1.0** while 60.6% of cases are wrong; 668 of 1,387 wrong cases carry confidence ≥ 0.5. The shipped advisor's tail trigger (`conf < 0.5`) therefore catches 736 wrongs (the no-signal half, where median confidence on wrongs is 0.0) but is structurally blind to the confidently-wrong half. Recommended follow-up: escalate on `generic`-with-content and ties as well, and consider a calibrated trigger; recorded as an open item on the shipped advisor. **Addendum (same session, implemented):** the advisor now also escalates on a small top-two margin (`contested_margin`), and the camera keyword list gained the devices users actually name (gopro, drone, webcam, pixel, leica, fuji, fujifilm, olympus, dji). Measured on the corpus: wrong-case escalation coverage **50.1% → 69.5%** at a 44.2% call rate (margin default 2.0 chosen by threshold sweep — coverage plateaus at 2.0–2.5 while over-escalation grows at 3.0+), and router agreement rose **39.4% → 42.2%**. Residual: ~30% of wrongs are single-signal confident-wrong (one pattern-boosted keyword, no runner-up) — structurally invisible to any deterministic trigger; the calibrated-trigger idea stays open.

**Deterministic persona-prior council: no measurable lift.** Personas vote over the router's top-2; on the votable tail (13 cases) 12 were ties and nothing changed. Root cause: priors can only arbitrate between candidates the router already produced — they cannot recover a capability that is absent from top-2. Verified negative result; the layer that recovers misses is semantic.

**Live Jev persona council (bounded: 35 calls, HTTP 200 ×35, served `jev-1.13.0`):** one call per case, four persona-conditioned `Choice` questions (independent, parallel — the documented fan-out pattern) plus one privacy `Noul` under SIM-PRIYA's mandate; weighted vote aggregated in code. On the stratified router-miss sample the council reaches **71.4% agreement vs the router's 0% on the same cases** — 27 overrides. Mean 309 ms; 67.1k in / 14.9k out tokens total (mean 1,917 in/call).

**Honest reading of the 10 remaining council misses:** ~7 are label-convention disputes, not routing errors — e.g. "gopro photos from december 2023" (council unanimously `date`, template label `camera`), "the engagement with my cousin" (`people` vs `event`), "chaotic rainy day moments" (`scene` vs `emotion`). Review-judged agreement is materially higher than strict-label agreement; the strict number is the one reported. One clean model miss: "black and white bicycle photos" → `object` (B&W reads as a color mode).

**Full-scale cost model (documented, not run):** all 1,387 misses through the live council ≈ **2.66M input tokens** (~1,917 in/call measured). A production shape would not council every miss — gate on the escalation set (736 at `conf<0.5`), tighten triggers per the calibration finding, or council only user-visible failures. Any full-scale run needs a fresh explicit cap per the runbook.

### 9.4 What the council architecture buys

The personas convert routing from single-model classification into an *owner-perspective adjudication* with three practical properties: (1) disagreement is data — a split vote flags a genuinely ambiguous query for the product's "did you mean" UX instead of silently picking; (2) SIM-PRIYA makes privacy sensitivity a first-class vote, surfacing person-adjacent queries the router routed away from `people`; (3) the aggregation weights are a product knob (a family-photos release can weight SIM-AVA up). None of this requires the personas to be real; it requires them to be explicit, documented, and measured — which is what `personas.json` is for.

## 10. Real-query availability check (2026-10-14) — Tier-3 replay resolved: no corpus exists yet

The one remaining "Unknown" from §4 — accuracy on real user queries — was chased to ground:

- **Capture is wired**: the search route logs every query to `saved_searches.db:search_history` by default (`server/api/routers/search.py:155,863`), and it logs through the state's detector, so once the advisor is enabled, recorded intents reflect Jev routing.
- **The corpus is effectively empty**: 5 rows total, 3 usable, all single words (`sunset`, `food`, `people`), from December 2025. No meaningful replay is possible; the synthetic corpus remains the evidence base.
- **The tiny history still paid off**: `food` was recorded with `intent=camera` on 2025-12-15 — the pre-fix no-signal fallthrough bug, confirmed in real recorded data. Replayed through the fixed router: `food` → `generic` (changed), `sunset` → `scene` and `people` → `people` (both unchanged, both correct).
- **Path forward**: let `search_history` accumulate real traffic (≥50 distinct non-trivial queries), then replay offline through the deterministic layer (free) and run a capped live pass. Until then, real-query accuracy stays Unknown — not by omission but by absence of data.

## 11. Artifacts and provenance (updated)

- Intent-routing experiment: `/Users/pranay/Projects/exploration_maps/jev/experiments/photo_intent_router/` (fixture, probe, pre-fix and post-fix result files, live results, order-check receipt)
- Persona-council experiment: `/Users/pranay/Projects/exploration_maps/jev/experiments/photo_persona_council/` (personas.json, corpus generator + 2,290-case corpus, probe, offline and live council results)
- Living map entries: receipts six (exploration), seven (implementation), and eight (persona council at scale), 2026-10-13, in `/Users/pranay/Projects/exploration_maps/jev/EXPLORATION_MAP.md`
- Changed product files (uncommitted): `src/intent_recognition.py` (fixes), `src/jev_intent_advisor.py` (new), `server/core/bootstrap.py` (wiring), `tests/test_intent_recognition.py` (new), `tests/test_jev_intent_advisor.py` (new), this doc
- Production surface pinned pre-change: `src/intent_recognition.py` at `f65a551`
- Credential handling: exploration probes read the key in-process from `/Users/pranay/Projects/.env.local` (mode 600); the product module reads `TYPESAFE_API_KEY` from the process environment only. Never printed, never persisted in any case.
