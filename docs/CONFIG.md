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

## MCP

`mcp_servers` is a list of MCP endpoints with Bearer auth. `list_method` and `call_method` can be customized to match server JSON-RPC method names.

## Logs

Logs are written under `shared_root/logs/YYYY/MM/DD/file<start-timestamp>.log`.
