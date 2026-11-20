---
name: operator-pass-list
description: List all available JMC API tools with their slugs, descriptions, and input schemas. Hits the live catalog endpoint so the list is always current. Loaded by the main operator-pass skill when the user asks "what tools are available" or "list the API tools".
user-invocable: false
allowed-tools: Read Bash
license: MIT

---

# Operator Pass List — sub-skill

Lists the current JMC API tool catalog with each tool's slug,
description, and input schema. Hits the live catalog endpoint so the
list is always current.

## Activation

Loaded by `operator-pass` on:
- "What tools are available"
- "List the API tools"
- "/operator-pass list"
- "Show me the catalog"

## Workflow

### 1. Validate the API key (lightweight)

The catalog endpoint is authenticated; require a valid key.

### 2. Fetch the catalog

```bash
python3 scripts/op_api.py list
```

The list comes from the member MCP tool list (the API has no catalog
route). Each entry has a `name` (the slug), a `description` and an
`inputSchema`. There is no category field: group by the sections below
only for tools you recognise, and list any other tool under "Other".

### 3. Format the list

Group by category. Don't dump full schemas inline — surface slug +
description + a "see schema with `--detail`" hint.

```markdown
# JMC API tools — <N> available

## Outbound + cold email
- **`cold-email-linter`** — Per-email score + line-level rewrite
- **`linkedin-post-critic`** — Critique + 3 register-varied rewrites
- **`linkedin-hook-grader`** — First-line hook scoring
- **`nurture-sequence-planner`** — 5-email nurture stream

## Foundation + targeting
- **`evp-generator`** — Schwartz-awareness EVP variants
- **`evp-brief-generator`** — Structured 3-tier EVP brief
- **`persona-from-crm`** — CSV → clusters → PSPs
- **`offer-lever-scorer`** — 5-lever offer score
- **`buyer-journey-mapper`** — ICP+pains → 5-stage Schwartz

## Demand + content
- **`geo-visibility-audit`** — URL → AI-visibility 5-dim score
- **`competitive-teardown`** — URL → 6-bullet teardown
- **`paid-media-teardown`** — 5-lever ad creative teardown
- **`ad-creative-scorer`** — JMC creative framework score
- **`pricing-page-lab`** — Tiers + decoy → rendered mock

## Revenue + math
- **`cohort-economics-modeler`** — LTV/payback/cohort contribution
- **`channel-matrix-scorer`** — Volume × ACV × Accessibility ranker
- **`blended-gtm-dashboard`** — 11-slider modeler
- **`gtm-architecture-diagrammer`** — Canvas + AI coherence audit

## Total: <N> tools
```

### 4. Per-tool detail mode

If user asks "schema for cold-email-linter" or "detail on
<slug>", fetch:

```bash
python3 scripts/op_api.py schema <slug>
```

And pretty-print the required + optional inputs.

## Caching

Cache the catalog response for 5 minutes per session — the catalog
doesn't change often, and rate limits matter on the user's quota.
