# Implementation status

This change closes a shared-review authorization gap and adds a first portable workflow for reviewing actual mechanical comparison output. It does not promote draft review notes into approved requirements.

## Implemented

- Sign-off withdrawal checks the review lens or lead role and the original signer. A refused withdrawal changes no revision or event. Decision changes still clear sign-offs transactionally.
- Prototype withdrawal controls match signer ownership. Scrollable navigation and resolve containers no longer add implicit Firefox tab stops; the keyboard test has an explicit end-of-page boundary.
- `tools/review/build.py` recomputes and validates comparison output against its datasets, then builds a portable workspace from the reference dataset component and a separate comparison view model. It refuses existing output folders and outputs inside source folders.
- The workspace shows source wording, rule explanations and coverage limits. It supports reasoned review notes, draft download and restore, and input fingerprints. Source validation must finish before review controls open; choosing another dataset hides comparison controls.
- `tools/doctor.py` reports missing local tools and configuration without printing environment values. Core, browser and release profiles distinguish their requirements. The diagnostic does not contact services or certify an external setup.
- `docs/capabilities.json` is the source for the generated [capability table](CAPABILITIES.md). Onboarding now distinguishes sample prototype content, shared decisions and source-bound comparison review.

## Validation

The full Python suite passed 1,264 tests on Python 3.12. Targeted checks cover all fourteen contract dataset shapes. The GUI probe passed 552 checks through each of URL and folder-input loading. The comparison workspace passed draft download/restore, invalid-file refusal, damaged-source refusal, mobile layout and dataset-switch checks in Chromium; its source scan reported zero errors and warnings.

Prototype browser tests for dispositions, single requirements, accessibility and shared projects passed at 1440, 900 and 390 px (12 runs). Firefox's accessibility run passed at 1440 px after the keyboard fixes. Screenshots were regenerated and inspected. Server, review and Firefox mutation checks document the regressions they deliberately restore; run them from [tools/mutation](../tools/mutation/).

The wider repository checks passed 433 tests with 80 optional checks skipped in the initial run. The changed documentation, preview freshness, mutation patterns and setup checks were rerun separately. These are local checks; this branch has not run in hosted CI.

## Remaining work

1. Configure the GitHub `DENYLIST` secret with an actual private-term list. The current missing-list failure must remain visible until configured. No secret value is fabricated or committed.
2. Register imported datasets and comparisons in reference-server projects, binding shared decisions to their source fingerprint. The portable review workspace currently saves draft files, independently of the prototype's sample-based shared decisions.
3. Define a versioned completion-policy contract and enforce it on the server before authoritative approval or release export. The current reference server enforces individual authorization rules, not the full client completion policy.
4. Add token expiry or company sign-in, a TLS reverse proxy, backup/restore verification and deployment checks before broader shared use. No container engine was available in this environment.
5. Evaluate with two human labellers and an approved corpus outside this repository. No real requirement set or live source system was tested; semantic matching, full SysML parsing and source-system write-back remain outside the current implementation.
6. Add a dependency lock and repeat the complete supported Python/browser matrix for this branch. The latest hosted run used the earlier commit; local browser success does not certify a deployment.

## Try the new workflow

See [tools/review/README.md](../tools/review/README.md). Generated workspaces contain source text and belong outside the repository. The prototype remains a generated design sample; do not copy its markup into real screens.
