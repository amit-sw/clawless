# Clawless

Clawless is a Telegram-only, Python-only assistant with tracks, tools, and a Streamlit control panel. It supports:

- Single-user Telegram bot with implicit `#track:<name>` routing
- File read/edit tools constrained to a shared directory
- Shared logs directory under `shared_root/logs/` with date-based folders
- Skills (optional, loaded from the internal root)
- Remote MCP tool invocation (Bearer auth)
- Global scheduling and OpenClaw-style heartbeat checks
- Streamlit onboarding + configuration

## Quickstart

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[llm,test]"
```

To enable Gmail integration, add the `gmail` extra:

```bash
pip install -e ".[llm,gmail,test]"
```

2. Start the Streamlit UI to configure the bot:

```bash
clawless-ui
```

3. Configure:

- Telegram bot token
- Owner Telegram user ID
- LLM connection string and API key
- Root directories

4. Run the bot:

```bash
clawless-bot
```

## Configuration

Configuration lives in `~/.clawless/config.json` (fixed location).

See `docs/CONFIG.md` for schema details.

## Gmail Integration (Optional)

Clawless can read your Gmail inbox (read-only) and answer questions about your email, generate to-do lists, and more.

### Setup

1. Create a Google Cloud project and enable the **Gmail API**.
2. Create an **OAuth Desktop App** credential (APIs & Services > Credentials > OAuth Client ID > Desktop app).
3. Download the credentials JSON and save it as `~/.clawless/gmail_credentials.json`.
4. Set `gmail.enabled` to `true` in `~/.clawless/config.json`:
   ```json
   {
     "gmail": {
       "enabled": true
     }
   }
   ```
5. On first use, a browser window opens for OAuth consent. The refresh token is saved to `~/.clawless/gmail_token.json` automatically.

Only the `gmail.readonly` scope is requested — the bot cannot send, delete, or modify emails.

**Security:** `gmail_credentials.json` and `gmail_token.json` are listed in `.gitignore` and must never be committed.

### Available Tools

| Tool | Description |
|------|-------------|
| `gmail_list` | Fetch all emails from a time period with full content and reply status |
| `gmail_read` | Read a specific email by message ID |
| `gmail_search` | Search emails using Gmail query syntax |

## Heartbeat

Heartbeat runs every 30 minutes by default. If `shared_root/HEARTBEAT.md` exists, it is included in the prompt. If the model responds with `HEARTBEAT_OK`, the message is suppressed.

## Skills

Skills are loaded from `internal_root/skills/<skill>/skill.json`.

See `docs/ARCHITECTURE.md` for the full layout.

## Track Commands

Use `/track` commands in Telegram:

- `/track list`
- `/track set <name>`
- `/track rename <old> <new>`
- `/track archive <name>`

## Testing

```bash
pytest
```

## License

MIT
