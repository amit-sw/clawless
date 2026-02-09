# Configuration

Config file: `~/.clawless/config.json` (fixed location).

## Schema

```json
{
  "telegram": {
    "token": "...",
    "owner_user_id": 123456789
  },
  "llm": {
    "connection_string": "openai:gpt-4o",
    "api_key": "..."
  },
  "paths": {
    "config_root": "/home/user/.clawless",
    "internal_root": "/abs/path/internal",
    "shared_root": "/abs/path/shared"
  },
  "mcp_servers": [
    {
      "name": "server1",
      "url": "https://example.com/mcp",
      "bearer_token": "token",
      "list_method": "tools/list",
      "call_method": "tools/call"
    }
  ],
  "heartbeat": {
    "enabled": true,
    "interval_minutes": 30,
    "active_hours": "09:00-17:00",
    "prompt": "...",
    "checklist_path": "HEARTBEAT.md"
  }
}
```

## Connection Strings

- `openai:<model>` uses `langchain-openai` `ChatOpenAI`.
- `openrouter:<model>` uses OpenAI-compatible base URL `https://openrouter.ai/api/v1`.

## Gmail

```json
{
  "gmail": {
    "enabled": false
  }
}
```

Set `enabled` to `true` to register the Gmail tools (`gmail_list`, `gmail_read`, `gmail_search`). Requires:

1. A Google Cloud project with the Gmail API enabled.
2. An OAuth Desktop App credential saved as `~/.clawless/gmail_credentials.json`.
3. The `gmail` optional dependencies installed: `pip install -e ".[gmail]"`.

On first use the OAuth consent flow opens a browser window. The refresh token is saved to `~/.clawless/gmail_token.json` for subsequent runs. Only the `gmail.readonly` scope is requested — the bot cannot send, delete, or modify emails.

**Security:** Never commit `gmail_credentials.json` or `gmail_token.json`. Both are listed in `.gitignore`.

## MCP

`mcp_servers` is a list of MCP endpoints with Bearer auth. `list_method` and `call_method` can be customized to match server JSON-RPC method names.

## Logs

Logs are written under `shared_root/logs/YYYY/MM/DD/file<start-timestamp>.log`.
