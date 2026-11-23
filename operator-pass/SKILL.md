---
name: operator-pass
description: >
  Operator Pass API skill for Claude Code. Wraps the JMC tools API at
  api.jaymountconsulting.com/v1/tools/<slug> for cross-runtime agent use —
  Cold Email Linter, EVP Generator, Pipeline Calculator, GEO Visibility
  Audit, Competitive Teardown, Paid Media Teardown, Blended GTM Dashboard,
  GTM Data Atlas search and dossiers, plus more multi-input modelers and
  generators. Bring your own Operator
  Pass API key (env var OPERATOR_PASS_API_KEY); subscribe at
  jaymountconsulting.com/operator-pass. Triggers on: "lint this cold email",
  "generate an EVP via API", "run the pipeline calculator", "GEO audit",
  "competitive teardown", "operator pass tool", "JMC API", "subscription
  tool", "agent-callable tool", "data atlas", "which data source covers",
  "compare data vendors", "pick an enrichment source".
allowed-tools: Read Bash WebFetch
  - Write
license: MIT

---

# Operator Pass — API Skill

Wraps the **JMC tools API** for use inside any Claude Code agent —
or any MCP-aware runtime. Each tool is a server-side, schema-validated,
real-result endpoint (not a prompt). Use them in your Claude / Cursor /
Codex / Gemini flows the same way you'd use a built-in tool.

## Bring your own key

This skill calls the JMC API. You need an active **Operator Pass**
subscription and an API key, exposed via env var:

```bash
export OPERATOR_PASS_API_KEY="jmc_live_..."
```

The skill detects a missing or invalid key and tells the user how to
subscribe:

> → Get an API key at https://jaymountconsulting.com/operator-pass

No key, no calls. The skill won't call the API anonymously.

## Quick reference

| Slash | What it does |
|---|---|
| `/operator-pass` | Interactive — detect intent, route to a tool |
| `/operator-pass list` | List all available tools + their input schemas |
| `/operator-pass call <slug>` | Call a specific tool with JSON inputs |
| `/operator-pass status` | Check API key validity + remaining quota |

## Available tools (current catalog)

The JMC tools API exposes multi-input modelers, generators, and
auditors. Each one is server-side, schema-validated, and returns
structured JSON (not LLM-narrated prose).

### Outbound + cold email

| Tool slug | What it does |
|---|---|
| `cold-email-linter` | Per-email score + line-level rewrite recommendations |
| `linkedin-post-critic` | Critique + 3 register-varied rewrites |
| `linkedin-hook-grader` | First-line hook scoring across 5 archetypes |
| `nurture-sequence-planner` | 5-email nurture stream with route-to-sales triggers |

### Foundation + targeting

| Tool slug | What it does |
|---|---|
| `evp-generator` | Schwartz-awareness EVP variants by tier |
| `evp-brief-generator` | Structured 3-tier EVP brief |
| `persona-from-crm` | CSV → AI clusters → PSPs per cluster |
| `offer-lever-scorer` | 5-lever offer score + rewrite |
| `buyer-journey-mapper` | ICP+pains → 5-stage Schwartz template |

### Demand + content

| Tool slug | What it does |
|---|---|
| `geo-visibility` | URL → 5-dim AI-visibility score + ranked fixes |
| `competitive-teardown` | URL → 6-bullet positioning teardown |
| `paid-media-teardown` | 5-lever ad creative teardown |
| `ad-creative-scorer` | Score against the JMC creative framework |
| `pricing-page-lab` | Tiers + decoy → rendered mock + rationale |

### Revenue + math

| Tool slug | What it does |
|---|---|
| `cohort-economics-modeler` | LTV/payback/cohort contribution + verdict |
| `channel-matrix-scorer` | Volume × ACV × Accessibility ranker |
| `blended-gtm-dashboard` | 11-slider dashboard, marquee modeler |
| `gtm-architecture-diagrammer` | Canvas + AI coherence audit |

### Data sources (GTM Data Atlas)

| Tool slug | What it does |
|---|---|
| `data-atlas-search` | Find data sources by text, tag or category. Returns a short list of slugs |
| `data-atlas-dossier` | The full dossier for one source: coverage, who it fits, pricing reality, what it pairs with, compliance, citations |
| `data-atlas-evidence` | The Atlas's stored publisher claim receipts for one named source: up to 5 excerpts with links and check dates |

(Full catalog + per-tool input schema at runtime via `/operator-pass list`.)

## Workflow

### 1. Validate the API key

On first call, validate:

```bash
curl -s https://api.jaymountconsulting.com/v1/me \
  -H "Authorization: Bearer $OPERATOR_PASS_API_KEY"
```

If 401 or 403, surface:

> Your Operator Pass API key is missing / expired / invalid.
> Get or renew at https://jaymountconsulting.com/operator-pass.

### 2. Route to the right tool

Detect intent from the user's request:

| User says | Route to |
|---|---|
| "Lint this cold email" | `cold-email-linter` |
| "Critique this LinkedIn post" | `linkedin-post-critic` |
| "Generate an EVP" | `evp-generator` |
| "Build an EVP brief" | `evp-brief-generator` |
| "GEO audit on <URL>" | `geo-visibility` |
| "Competitive teardown of <URL>" | `competitive-teardown` |
| "Run the pipeline math" | `blended-gtm-dashboard` |
| "Score this ad creative" | `ad-creative-scorer` |
| "Which data source covers <need>?" | `data-atlas-search`, then `data-atlas-dossier` |
| "Tell me about <data source>" | `data-atlas-dossier` |
| "What evidence has the Atlas stored for <data source>?" | `data-atlas-evidence` with its `source_slug` from `data-atlas-search` |

If intent is ambiguous, ask one clarifying question. Don't list tools
unless the user asks.

### 3. Gather the inputs per tool schema

Each tool publishes its input schema at:

```
GET https://api.jaymountconsulting.com/v1/tools/<slug>/schema
```

Fetch the schema, validate the user's inputs against it, and ask for
any missing required fields.

### 4. Call the tool

```bash
curl -s -X POST "https://api.jaymountconsulting.com/v1/tools/<slug>" \
  -H "Authorization: Bearer $OPERATOR_PASS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '<inputs>'
```

### 5. Surface the result

Each tool returns structured JSON. Pretty-print the result, then offer
"the next step" — usually:

- For audit tools (`geo-visibility`, `cold-email-linter`,
  `competitive-teardown`): "Want me to draft the fix for the top
  issue?"
- For generator tools (`evp-generator`, `nurture-sequence-planner`):
  "Want me to A/B test these variants against your existing copy?"
- For modeler tools (`blended-gtm-dashboard`,
  `cohort-economics-modeler`): "Want me to run a sensitivity analysis
  on the top 2 levers?"

## Data Atlas: search, dossier, evidence

Use these tools when you are choosing where data comes from: a list
source, an enrichment vendor, a signal feed. Search first, read the
dossier for the two or three best matches, then inspect stored claim
receipts for a named source with `data-atlas-evidence`. It does not search
outside commentary or reviews. All three are read-only. Follow the
one-call-per-request confirmation rule before calling another tool.

### `data-atlas-search`

Inputs (all optional):

| Field | Type | Notes |
|---|---|---|
| `query` | string, up to 200 chars | Free text, matched against name, summary, category and tags |
| `tag` | string | A data type, play or segment slug, e.g. `cold-email` |
| `category` | string | Exact category name, case-insensitive, e.g. `Enrichment` |
| `limit` | integer 1-100 | Default 25 |
| `offset` | integer, 0 or more | For paging |

Output:

```
{
  "total": <every match>,
  "limit": 25,
  "offset": 0,
  "results": [
    { "slug": "...", "name": "...", "summary": "...", "category": "...", "tags": ["..."], "url": "..." }
  ]
}
```

`total` counts every match, so page with `offset` when it is larger
than `limit`. `url` opens the same source in the JMC app.

### `data-atlas-dossier`

Input: `{ "slug": "<slug from data-atlas-search>" }`

Output when the source has a dossier: `found: true`, the
source's name, summary, coverage strengths and gaps, pricing model,
`tags`, `citations`, `related` sources, and `sections` with nine keys:

`overview`, `coverage_deep_dive`, `icp_segment`, `operator_moves`,
`gtm_engineering`, `pricing_reality`, `pairs_with`,
`practitioner_reality`, `compliance`.

When the slug has no dossier yet, or does not exist, the call
still returns HTTP 200:

```json
{ "found": false, "slug": "...", "message": "..." }
```

Treat that as "not in the Atlas yet". Say so, and go back to
`data-atlas-search` for another match. Do not fill in a dossier
yourself.

### `data-atlas-evidence`

Inputs:

| Field | Type | Notes |
|---|---|---|
| `query` | string, 3-200 chars after trimming, required | The data need or question; ranks stored claim receipts for the named source |
| `source_slug` | string, optional in the schema, up to 120 chars | A slug from `data-atlas-search`, matching `^[a-z0-9][a-z0-9-]*$` (lowercase letters, digits and hyphens; first character must be a letter or digit) |

Without `source_slug`, the API abstains: obtain a slug from
`data-atlas-search` before expecting passages. Only the two fields above
are accepted; additional input fields are rejected.

Output (illustrative successful response, not a live result):

```json
{
  "query": "...",
  "passages": [
    { "excerpt": "...", "title": "Source name", "url": "https://example.com/source", "source_type": "publisher", "published_at": null, "checked_at": "YYYY-MM-DD" }
  ],
  "note": "Excerpts the Atlas stored for this source, each with its link and the date it was checked. Read the page before relying on it.",
  "summary": "1 stored excerpt(s) for Source name.",
  "status": "ok",
  "confidence": { "value": null, "basis": "unmeasured" },
  "abstain": null,
  "unknowns": [],
  "assumptions": [],
  "evidence": [
    { "text": "...", "url": "https://example.com/source", "date": "YYYY-MM-DD", "verified": false }
  ],
  "limits": ["Excerpts are as recorded on the check date; the page may have changed. Shape-checked, not re-read on each call."],
  "next_action": null,
  "receipt": { "tool": "data-atlas-evidence", "version": "1", "as_of": "YYYY-MM-DD" }
}
```

Up to 5 passages, ranked by query word overlap with stored receipts.
Each `excerpt` is 300 characters or less. The current implementation emits
`source_type: publisher`, the source's name as `title`, and
`published_at: null`. `checked_at` is the recorded check date, not a
publication date; the schema allows it to be absent or null, and allows
`source_type` and `published_at` to be null.

Receipts were recorded on their check date and are not re-read on each call;
the page may have changed. Read the linked page before relying on it.
Quote the excerpt with its link and retain the check date; do not present
it as JMC's view or expand it into claims the excerpt does not make.

The response envelope includes `summary`, `status`, `confidence`, `abstain`,
`unknowns`, `assumptions`, `evidence`, `limits`, `next_action` and `receipt`.
Success uses `status: ok`; confidence is unmeasured, and evidence entries
have `verified: false`. On success, `receipt.as_of` is the latest stored
claim check date, not evidence of a fresh page read.

Empty `passages` with `status: abstain` can mean a missing slug, an unknown source,
or no stored receipts for that source. Surface the returned `abstain.reason`,
`abstain.to_collect`, `unknowns` and `next_action` guidance. For a missing or
unknown slug, obtain a valid slug from `data-atlas-search`; for no stored
receipts, consult `data-atlas-dossier` and the source's own site. Ask before
another tool call. Do not infer that no evidence exists about the question.

### Example

```bash
python3 scripts/op_api.py call data-atlas-search --input '{"query":"job change signals","limit":5}'
python3 scripts/op_api.py call data-atlas-dossier --input '{"slug":"<slug>"}'
python3 scripts/op_api.py call data-atlas-evidence --input '{"query":"how accurate is its job change data","source_slug":"<slug>"}'
```

## Sub-skills

- [`skills/operator-pass-call`](../skills/operator-pass-call) — invoke a specific tool by slug
- [`skills/operator-pass-list`](../skills/operator-pass-list) — list available tools + schemas

## Rate limits + costs

Each tool's API cost is included in your Operator Pass subscription.
Per-tool rate limits and any per-call cost are documented at:

→ https://jaymountconsulting.com/operator-pass/api

The skill respects rate-limit headers and tells the user when they're
throttled.

## Plugs into

Pairs especially well with:

- **[claude-cold-email](https://github.com/cmj-hub/claude-cold-email)** — `cold-email-linter` validates drafts; `linkedin-hook-grader` scores hooks
- **[claude-psp](https://github.com/cmj-hub/claude-psp)** — `persona-from-crm` clusters real prospect data into PSPs
- **[claude-evp](https://github.com/cmj-hub/claude-evp)** — `evp-generator` produces variants; `evp-brief-generator` produces full briefs

The free framework skills give you the frameworks. The API gives you
the deterministic execution layer.

## Operator Pass

[Operator Pass](https://jaymountconsulting.com/operator-pass) is the
all-access subscription to:

- The full build guide catalog
- The tool API (this skill wraps it)
- Live office hours

→ [jaymountconsulting.com/operator-pass](https://jaymountconsulting.com/operator-pass)
