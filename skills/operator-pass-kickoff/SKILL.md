---
name: operator-pass-kickoff
description: Router for the Operator Pass API skill pack. Checks state (key set and valid, brand-config present, quota left, recent calls) and picks the next step. Use when the pack is invoked with no clear task, or the user asks for Operator Pass status or where to start. Not for first-time setup when brand-config.json or SOUL.md is missing (use operator-pass-onboarding), listing tools (use operator-pass-list), or running a named tool (use operator-pass-call).
user-invocable: false
allowed-tools: Read Bash
  - Grep
license: MIT

---

# Operator Pass Kickoff — adaptive router

## Activation

Loaded by `operator-pass` on bare invocation, or:
- "Operator Pass status"
- "Where do I start with the API"

## State detection

```python
state = {
    "env_var_set":       bool(os.environ.get("OPERATOR_PASS_API_KEY")),
    "has_brand_config":  file_exists("brand-config.json"),
    "has_soul":          file_exists("SOUL.md"),
    "key_valid":         authenticated MCP tools/list succeeds,
    "quota_remaining":   unknown unless explicitly returned,
    "cache_dir_exists":  file_exists(".operator-pass-cache"),
    "recent_calls":      count of entries in usage.jsonl from last 7 days,
}
```

| State | Route to |
|---|---|
| `!env_var_set` | "Set OPERATOR_PASS_API_KEY. Subscribe at jaymountconsulting.com/operator-pass." |
| `env_var_set AND !key_valid` | "Key invalid or expired. Renew at jaymountconsulting.com/operator-pass." |
| `key_valid AND !has_brand_config OR !has_soul` | `operator-pass-onboarding` |
| Known quota below `usage.warn_at_remaining_quota_percent` | "⚠ Only X% quota remaining. Proceed carefully or upgrade." |
| `recent_calls == 0` | "No calls in the last 7 days. Want to try a sample call? `/operator-pass call cold-email-linter`" |
| else | "API discovery ready. Quota unknown unless returned. <N> recent calls." |
```

## Welcome flow

```
> /operator-pass

[Detected: OPERATOR_PASS_API_KEY not set]

You need an Operator Pass subscription + API key to use this skill.

→ Subscribe: https://jaymountconsulting.com/operator-pass
   - Includes every tool in the API + the full build guide catalog
   - Free browser versions of every tool: https://jaymountconsulting.com/tools

Once you have a key:
  export OPERATOR_PASS_API_KEY="jmc_live_..."

Then re-run /operator-pass and I'll walk you through setup.
```

## Status mode

`/operator-pass status`:

```
# Operator Pass status

API key:           ✓ Authenticated discovery (key never displayed)
Plan:              Unknown
Quota remaining:   Unknown (discovery returns no quota)
Brand config:      ✓ brand-config.json (5 preferred tools)
SOUL:              ✓ SOUL.md
Cache:             ✓ .operator-pass-cache (catalog cached 2 minutes ago)
Recent calls:      14 in the last 7 days

Recent tool usage:
  cold-email-linter      6 calls (Wed batch)
  competitive-teardown   4 calls (Mon prospect research)
  evp-generator          2 calls
  geo-visibility         2 calls

Recommended next:
- Continue your batch: `/operator-pass call cold-email-linter`
- Or run the live catalog: `/operator-pass list`
```

## References

- `../operator-pass-onboarding/SKILL.md`
- `../operator-pass-call/SKILL.md`
- `../operator-pass-list/SKILL.md`
