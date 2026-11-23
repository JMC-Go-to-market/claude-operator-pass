# Member MCP discovery and Atlas guidance

Closes #26.

- Wire the plugin to the authenticated member `/mcp` using an environment placeholder.
- Replace nonexistent REST discovery endpoints with stateless JSON-RPC `tools/list`.
- `whoami` is an authentication/discovery check, never an invented identity or quota.
- Select `inputSchema` by exact tool name, follow pagination, fail on protocol errors.
- Keep REST execution as the fallback; schemas come from the MCP catalog.
- Present the server envelope summary first, preserve all fields, never derive status or routing from model self-report.
- Match the published result envelope: additive result fields, statuses `ok`, `partial`, `abstain`, `error`; confidence may be null with basis `unmeasured`; evidence uses `text`, `url`, `date`, `verified`; receipt requires `tool`, `version`, `as_of`.
- No local envelope synthesis or vendored package types.
- Atlas search/dossier use the member surface only. No other server connection is shipped. When the member catalog has no evidence tool, report evidence unavailable.
- Discovery accepts both `application/json` and `text/event-stream` responses: the client reads SSE events, skips notifications and returns the JSON-RPC response whose id matches the request; no matching response is a protocol error.
- This repository is public: tracked files outside `.github/` carry no private repository, issue, server or rollout references (`tests/test_public_content.py`).

Offline tests mock every request. Production verification is outside this repository.
