# Connect the Operator Pass MCP server

Endpoint: `https://api.jaymountconsulting.com/mcp`. It uses Streamable HTTP and needs your Operator Pass key as a Bearer token. It carries the Operator Pass tools, including the member Data Atlas (`data-atlas-search`, `data-atlas-dossier`).

Keep the key in an environment variable named `OPERATOR_PASS_API_KEY`. Never paste it into a file that is committed, and never into a shared config.

```
export OPERATOR_PASS_API_KEY="jmc_live_..."
```

Get a key at https://jaymountconsulting.com/operator-pass. Check it works:

```
python3 scripts/op_api.py whoami
```

## Claude Code

If you installed this repository's plugin, the server is already configured and reads `OPERATOR_PASS_API_KEY`. Start Claude Code from a shell where the variable is set. To add it by hand:

```
claude mcp add --transport http operator-pass https://api.jaymountconsulting.com/mcp --header "Authorization: Bearer ${OPERATOR_PASS_API_KEY}"
```

Or in `.mcp.json` (the variable is expanded when Claude Code starts):

```json
{
  "mcpServers": {
    "operator-pass": {
      "type": "http",
      "url": "https://api.jaymountconsulting.com/mcp",
      "headers": { "Authorization": "Bearer ${OPERATOR_PASS_API_KEY}" }
    }
  }
}
```

## Codex

In `~/.codex/config.toml`. Codex reads the token from the named variable:

```toml
[mcp_servers.operator-pass]
url = "https://api.jaymountconsulting.com/mcp"
bearer_token_env_var = "OPERATOR_PASS_API_KEY"
```

## Cursor

`.cursor/mcp.json` in the project, or `~/.cursor/mcp.json` for every project:

```json
{
  "mcpServers": {
    "operator-pass": {
      "url": "https://api.jaymountconsulting.com/mcp",
      "headers": { "Authorization": "Bearer ${env:OPERATOR_PASS_API_KEY}" }
    }
  }
}
```

## Claude Desktop

If your build only takes local servers in `claude_desktop_config.json`, bridge the remote server over stdio. The key is read from the environment of the app:

```json
{
  "mcpServers": {
    "operator-pass": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://api.jaymountconsulting.com/mcp", "--header", "Authorization:${AUTH_HEADER}"],
      "env": { "AUTH_HEADER": "Bearer <your key>" }
    }
  }
}
```

This file holds the key in plain text. Keep it out of version control. Restart the app fully after editing.

## Any other MCP client

- Transport: Streamable HTTP
- URL: `https://api.jaymountconsulting.com/mcp`
- Header: `Authorization: Bearer $OPERATOR_PASS_API_KEY`

If your client cannot send a header, use the command line instead: `python3 scripts/op_api.py call <slug> --input '<json>'`.

## Errors

- 401: key missing, malformed or not recognised. Check the variable is set in the environment the agent was started from.
- 403: key suspended, revoked or expired. Renew at https://jaymountconsulting.com/operator-pass.
- 429: rate limited. Wait for the `Retry-After` seconds, then retry once.
