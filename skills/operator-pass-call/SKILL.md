---
name: operator-pass-call
description: Invoke a specific JMC API tool by slug. Validates the API key, fetches the per-tool input schema, validates the user's inputs, makes the POST call, and pretty-prints the structured response. Loaded by the main operator-pass skill when the user knows which tool they want.
user-invocable: false
allowed-tools: Read Bash
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

Then check the key is accepted (this goes through the member MCP,
the only place the API answers a key check):

```bash
python3 scripts/op_api.py whoami
```

Exit code 0 means accepted. The API does not report plan, quota or
expiry, so treat those as unknown. If it fails with 401/403, exit with
the subscribe link.

### 2. Fetch the tool's input schema

```bash
python3 scripts/op_api.py schema <slug>
```

Prints the tool's JSON Schema (read from the member MCP tool list). An unknown slug exits 1 with "unknown tool"; do not guess a schema. It is a JSON Schema describing required inputs. Parse it, compare
to what the user supplied, and ask for any missing required fields.

### 3. Validate inputs against the schema

Walk the schema's `required` array; ensure each is present in the
user's input. Validate types where the schema is strict.

If any required input is missing, ask:

> The `<tool-slug>` tool needs `<field>` (`<type>`, `<description>`).
> What should I use?

### 4. Call the API

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
| 400 | Bad input | Surface the validation error + retry with corrected input |
| 401 | Invalid key | Tell user to renew via /operator-pass |
| 402 | Subscription expired | Tell user to renew |
| 429 | Rate-limited | Surface the retry-after header value |
| 5xx | API error | Surface the message; suggest retry |

### 6. Pretty-print + offer next step

Don't dump raw JSON unless asked. Convert to a human-readable summary:

```markdown
# <Tool name> result

<one-paragraph summary of what was returned>

## Key findings
<bulleted list>

## Suggested next step
<one specific action — e.g., "Want me to draft the fix?" or "Want to
run the same call with <variation>?">
```

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
