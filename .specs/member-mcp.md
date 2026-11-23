# Member MCP discovery and Atlas guidance

Closes #26.

- Wire the plugin to the authenticated member `/mcp` using an environment placeholder.
- Replace nonexistent REST discovery endpoints with stateless JSON-RPC `tools/list`.
- `whoami` is an authentication/discovery check, never an invented identity or quota.
- Select `inputSchema` by exact tool name, follow pagination, fail on protocol errors.
- Keep REST execution as the fallback; schemas come from the MCP catalog.
- Present the server envelope summary first, preserve all fields, never derive status or routing from model self-report.
- Match the current jmc-packages#422 shape: additive result fields, statuses `ok`, `partial`, `abstain`, `error`; confidence may be null with basis `unmeasured`; evidence uses `text`, `url`, `date`, `verified`; receipt requires `tool`, `version`, `as_of`.
- No local envelope synthesis or vendored package types. Server rollout depends on the #422 release; no vendor sync is applicable here.
- Atlas search/dossier use the member surface only; evidence moves to the knowledge pack. No internal server connection is shipped. Specs, concepts and dated claims come first; wiki pages wait for their leak check.

Offline tests mock every request. Production verification and the knowledge pack backend are outside this repository.
