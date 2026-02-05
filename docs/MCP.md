# MCP Integration

Clawless connects to remote MCP servers over JSON-RPC 2.0.

## Expected Methods

By default, Clawless calls:

- `tools/list` to discover tools
- `tools/call` to execute a tool

You can override these in `config.json` per server.

## Tool Naming

Tools are registered as:

```
mcp:<server_name>:<tool_name>
```

## Bearer Authentication

If `bearer_token` is set, requests include:

```
Authorization: Bearer <token>
```
