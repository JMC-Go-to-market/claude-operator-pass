---
name: operator-pass-list
description: List all available JMC API tools with their slugs, descriptions, and input schemas. Hits the live catalog endpoint so the list is always current. Loaded by the main operator-pass skill when the user asks "what tools are available" or "list the API tools".
user-invocable: false
allowed-tools: Bash WebFetch
  - Read
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

Use the connected member MCP's `tools/list`, or:

```bash
python3 scripts/op_api.py list
```

Discovery uses authenticated `POST /mcp` JSON-RPC `tools/list` and follows
`nextCursor`. Each entry has `name`, `description`, `inputSchema`, and optionally
`outputSchema`. Load brand-config and SOUL first; missing setup routes to
onboarding. Cache the catalog in-session for `cache.tool_catalog_ttl_seconds`;
never reuse an authenticated catalog across keys or users.

### 3. Format the list

Group by category only if returned; otherwise list by name. Don't dump full schemas inline — surface slug +
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
- **`geo-visibility`** — URL → AI-visibility 5-dim score
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

If the user asks for a tool's schema, select its exact `name` from the
cached catalog and display `inputSchema`, or run:

```bash
python3 scripts/op_api.py schema <slug>
```

Missing tool/schema or a discovery error is a failure; never guess a schema.
