---
name: operator-pass-onboarding
description: First-run interactive setup for the Operator Pass API skill pack. Validates the OPERATOR_PASS_API_KEY env var, fetches the live tool catalog, captures the operator's preferred tools + won't-call list + failure handling preferences + quota awareness. Writes brand-config.json + SOUL.md. Loaded automatically when either file is missing.
user-invocable: false
allowed-tools: Read Write Bash
  - WebFetch
license: MIT

---

# Operator Pass Onboarding — first-run setup

10 minutes of setup that connects this pack to the real JMC API,
captures your usage preferences, and writes the config files all
downstream sub-skills load.

## Activation

Loaded automatically by `operator-pass` on missing brand-config.json
or SOUL.md.

Also user-invocable: "Set up Operator Pass", "Configure operator-pass API".

## Workflow

### Step 1 — API key check

```
First — do you have an Operator Pass subscription?

This pack calls api.jaymountconsulting.com — without a key, it
can't do anything. Subscribe at jaymountconsulting.com/operator-pass.
Every tool also has a free browser version at jaymountconsulting.com/tools.

Once you have a key, set it as an env var:
  export OPERATOR_PASS_API_KEY="jmc_live_..."

Then come back and run onboarding.
```

If env var is missing, **stop here** with the subscribe link. Don't
continue setup.

### Step 2 — Validate the key

```bash
curl -s https://api.jaymountconsulting.com/v1/me \
  -H "Authorization: Bearer $OPERATOR_PASS_API_KEY"
```

If 401/403, surface: "Key invalid or expired. Renew at
jaymountconsulting.com/operator-pass." Stop.

If 200, parse `{ user_id, plan, rate_limit_remaining }` and continue.

### Step 3 — Fetch the live tool catalog

```bash
curl -s https://api.jaymountconsulting.com/v1/tools \
  -H "Authorization: Bearer $OPERATOR_PASS_API_KEY"
```

Show the operator the catalog grouped by category:

```
# Operator Pass API tools — <N> available

## Outbound
  cold-email-linter      Per-email score + line-level rewrite
  linkedin-post-critic   Critique + 3 register-varied rewrites
  ...

## Foundation
  evp-generator          Schwartz-tier EVP variants
  ...

(<full live catalog>)
```

### Step 4 — Preferred tools

```
Which tools will you call most often? (Mark all that apply — these
get priority in routing suggestions.)

The skill defaults the most-popular operator picks. Override as needed:
- cold_email_validation: cold-email-linter
- evp_generation: evp-generator
- competitive_research: competitive-teardown
- geo_audit: geo-visibility
- pricing_lab: pricing-page-lab
```

Save to `brand-config.preferred_tools`.

### Step 5 — Won't-call list

```
Any tools you specifically don't want auto-invoked? (Common reasons:
expensive ones, long-running, schema you haven't locked.)
```

Save to `SOUL.md`.

### Step 6 — Failure handling preferences

```
How should the skill handle failures?

  429 (rate-limited):     Retry once (default) / Retry twice / Surface immediately
  402 (sub-expired):      Surface + stop (always — non-overridable)
  401 (key invalid):      Surface + stop (always — non-overridable)
  5xx (API error):        Log + skip / Retry once / Surface immediately
  Network timeout:        Retry once / Skip
```

Save to `brand-config.api` + `SOUL.md`.

### Step 7 — Quota awareness

```
Your Operator Pass has a usage quota. Want a warning when you're
running low?

  Warn at: 20% remaining (default) / 10% / 30% / Never warn

Where to log usage:
  Default: .operator-pass-cache/usage.jsonl (per-call timestamp + tool + result)
```

Save to `brand-config.usage`.

### Step 8 — Cache settings

```
Tool catalog and schemas don't change often. Cache them to save quota.

  Catalog TTL:  300s (default) / 60s / 3600s / no-cache
  Schema TTL:   3600s (default) / 600s / 86400s / no-cache
  Cache dir:    .operator-pass-cache (default — gitignored)
```

Save to `brand-config.cache`.

### Step 9 — Write files + smoke test

```
✓ brand-config.json — API config + preferred tools + cache + usage
✓ SOUL.md — won't-call list + failure handling preferences

Quick smoke test:
> /operator-pass list

Should return the live tool catalog (cached for 5min).
```

### Step 10 — Refresh

```
Re-run onboarding if:
- Your API key rotates
- You upgrade / downgrade tier
- New tools ship to the catalog

Refresh: `/operator-pass onboarding refresh`
```
