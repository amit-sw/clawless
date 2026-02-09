# Architecture

## Runtime Processes

- `bot_service`: Telegram polling, message routing, tool execution, scheduling, heartbeat.
- `streamlit_ui`: Onboarding/config, track viewing, job editor, MCP server list.

Both processes share a SQLite database in `internal_root/clawless.db`.

## Core Modules

- `clawless.telegram.adapter`: Telegram polling and message send.
- `clawless.router`: Implicit `#track:<name>` parsing.
- `clawless.tracks`: Track state + message history.
- `clawless.agent`: Prompt assembly + LangChain invocation + tool execution.
- `clawless.tools`: Tool registry and built-ins (files, skills, MCP, Gmail).
- `clawless.tools.gmail_tools`: Read-only Gmail access (list, read, search).
- `clawless.mcp`: JSON-RPC MCP client wrapper.
- `clawless.scheduler`: Cron-style scheduled jobs.
- `clawless.heartbeat`: Periodic OpenClaw-style check.

## Track Flow

- Telegram update arrives.
- Router extracts `#track:<name>` if present.
- TrackManager chooses track (explicit or last active).
- Messages and responses are stored in SQLite.
- `/track` commands allow list/set/rename/archive.

## Tool Flow

- The system prompt lists tools and required JSON format.
- If the LLM returns a tool call, the tool is executed.
- The tool result is injected into a follow-up LLM call.

## Gmail Tools

When `gmail.enabled` is `true` in config, three tools are registered:

- `gmail_list`: Fetches all emails from a time period with full body content and reply status. Paginates automatically with no cap on results.
- `gmail_read`: Reads a single email by message ID.
- `gmail_search`: Searches emails using Gmail query syntax (e.g. `from:boss subject:urgent`).

Reply detection checks each email's thread for messages sent by the authenticated user. Unread status is derived from Gmail labels. The batch API is used for efficient bulk fetching.

OAuth credentials are stored in `~/.clawless/` and are never committed to the repository.

## File Sandbox

All file tools are constrained to the `shared_root` directory, with path resolution enforcing that requests do not escape the root.

## Logs

Runtime logs are stored in `shared_root/logs/YYYY/MM/DD/file<start-timestamp>.log` for troubleshooting.

## Heartbeat

- Runs on a fixed interval (default 30 minutes).
- Reads `shared_root/HEARTBEAT.md` if present.
- Suppresses output when response is exactly `HEARTBEAT_OK`.
