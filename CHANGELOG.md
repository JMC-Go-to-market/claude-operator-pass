# Changelog

## [Unreleased]

### Added
- `data-atlas-search` and `data-atlas-dossier` documented in `operator-pass/SKILL.md`: when to use them, inputs, outputs, and the `found: false` case. Usage lines in `scripts/op_api.py`.

## [0.2.1] — 2026-05-24

Marketplace-submission compliance pass. No functional changes.

### Fixed
- `plugin.json` `author` field now an object `{ "name": "..." }` per Claude Code plugin manifest schema. `claude plugin validate` now passes.

## [0.2.0] — 2026-05-23

Polish pass matching the v0.2 family.

### Added
- 3-tier config: brand-config.example.json + SOUL.md + AGENTS.md
- skills/operator-pass-onboarding (10-min setup w/ live key validation) + skills/operator-pass-kickoff (state router)
- scripts/op_api.py — zero-dep Python client: whoami / list / schema / call. Handles 401/402/429/5xx per brand-config rules.
- README rewrite: cost-replacement positioning, mermaid

### Verified
- Without API key: graceful error + subscribe URL
- Validates via /me before any tool call
- Catalog cached per brand-config.cache.tool_catalog_ttl_seconds

## [0.1.0] — 2026-05-23

Initial release.
