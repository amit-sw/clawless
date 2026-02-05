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
- `clawless.tools`: Tool registry and built-ins (files, skills, MCP).
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

## File Sandbox

All file tools are constrained to the `shared_root` directory, with path resolution enforcing that requests do not escape the root.

## Logs

Runtime logs are stored in `shared_root/logs/YYYY/MM/DD/file<start-timestamp>.log` for troubleshooting.

## Heartbeat

- Runs on a fixed interval (default 30 minutes).
- Reads `shared_root/HEARTBEAT.md` if present.
- Suppresses output when response is exactly `HEARTBEAT_OK`.
