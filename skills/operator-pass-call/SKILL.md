---
name: operator-pass-call
description: Call one JMC API tool by its slug. It checks the key, fetch the tool's input schema, check the inputs, POST the call and print the result. Use when the user names the tool to run, such as "run the cold-email-linter on this draft" or "call evp-generator with these inputs". Not for finding which tool exists or fits (use operator-pass-list), first-time setup (use operator-pass-onboarding), or an unclear ask (use operator-pass-kickoff).
user-invocable: false
allowed-tools: Read Bash WebFetch
license: MIT

---

# Operator Pass Call — sub-skill

Invokes a specific JMC API tool by slug.

## Activation

Loaded by `operator-pass` when intent is clear:
- "Run the cold-email-linter on <draft>"
- "Call evp-generator with <inputs>"
- "Use the pipeline calculator"

## Workflow

### 1. Validate the API key

```bash
if [ -z "${OPERATOR_PASS_API_KEY:-}" ]; then
  echo "OPERATOR_PASS_API_KEY env var is not set."
  echo "Get a key at https://jaymountconsulting.com/operator-pass"
  exit 1
fi
```

On first setup run `python3 scripts/op_api.py whoami`: authenticated
MCP discovery, with no tool execution. Stop on failure. Account identity
and quota stay unknown unless explicitly returned. Load `brand-config.json`
and `SOUL.md`, routing to onboarding if missing. Respect the won't-call list
and confirm before sending customer data.

### 2. Fetch the tool's input schema

Use the connected member MCP catalog, or the REST fallback helper:

```bash
python3 scripts/op_api.py schema <slug>
```

This reads `inputSchema` from `/mcp` `tools/list`, selecting the exact name.
Stop if the tool or schema is absent. Cache discovery per brand-config TTLs.

### 3. Validate inputs against the schema

Walk the schema's `required` array; ensure each is present in the
user's input. Validate types where the schema is strict.

If any required input is missing, ask:

> The `<tool-slug>` tool needs `<field>` (`<type>`, `<description>`).
> What should I use?

### 4. Call the API

Prefer the connected member MCP tool. REST fallback:

```bash
curl -sS -X POST "https://api.jaymountconsulting.com/v1/tools/<slug>" \
  -H "Authorization: Bearer $OPERATOR_PASS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '<inputs JSON>'
```

### 5. Handle the response

| Status | Meaning | Action |
|---|---|---|
| 200 | Success | Pretty-print the JSON result + offer next step |
| 400 | Bad input | Surface validation error; ask before a corrected call |
| 401 | Invalid key | Tell user to renew via /operator-pass |
| 402 | Subscription expired | Tell user to renew |
| 429 | Rate-limited | Surface the retry-after header value |
| 5xx | API error | Surface the message; suggest retry |

### 6. Pretty-print + offer next step

Follow the result presentation contract in `operator-pass/SKILL.md`:
summary first, preserve server status, confidence basis, unknowns, assumptions,
evidence, limits and receipt, then the single returned next_action. Never
route from model_self_report or invent missing fields. CLI defaults to readable
output; `--raw` preserves the response when requested. Ask before an additional
execution call; do not automatically retry validation failures.

## Common errors + their handling

| Error | User-facing message |
|---|---|
| Missing env var | "Set `OPERATOR_PASS_API_KEY`. Get a key at /operator-pass." |
| Key invalid (401) | "API key invalid or expired. Renew at /operator-pass." |
| Sub expired (402) | "Operator Pass subscription expired. Renew at /operator-pass." |
| Schema mismatch (400) | "Missing field `<x>` — please provide." |
| Rate-limited (429) | "Rate-limited. Retry in <X seconds> per the API." |
| Unknown slug (404) | "Tool `<slug>` doesn't exist. Run `/operator-pass list`." |

## Discipline

- **Never** invent tool results. If the API call fails, say so.
- **Never** call the API anonymously — always require a key.
- **Never** retry on 401/402 — those need user action.
- **Always** show the raw JSON if the user asks (`--raw` flag style).
