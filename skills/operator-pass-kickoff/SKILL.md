---
name: operator-pass-kickoff
description: Adaptive router for the Operator Pass API skill pack. Detects state (API key set? brand-config? key still valid? quota remaining? recent calls?) and picks the next-best step. Loaded by the main operator-pass skill on bare invocation.
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
    "key_valid":         api_get("/me") returns 200,
    "quota_remaining":   parse from /me response,
    "cache_dir_exists":  file_exists(".operator-pass-cache"),
    "recent_calls":      count of entries in usage.jsonl from last 7 days,
}
```

| State | Route to |
|---|---|
| `!env_var_set` | "Set OPERATOR_PASS_API_KEY. Subscribe at jaymountconsulting.com/operator-pass." |
| `env_var_set AND !key_valid` | "Key invalid or expired. Renew at jaymountconsulting.com/operator-pass." |
| `key_valid AND !has_brand_config OR !has_soul` | `operator-pass-onboarding` |
| `quota_remaining < 20%` | "⚠ Only X% quota remaining. Proceed carefully or upgrade." |
| `recent_calls == 0` | "No calls in the last 7 days. Want to try a sample call? `/operator-pass call cold-email-linter`" |
| else | "API ready. <quota>% quota. <N> recent calls. What do you want to do?" |
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

API key:           ✓ Valid (jmc_live_xxxxxx_xxxx... — last 4)
Plan:              Operator Pass
Quota remaining:   847 / 1000 calls this month (84.7%)
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
