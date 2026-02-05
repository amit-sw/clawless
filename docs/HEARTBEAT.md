# Heartbeat

Heartbeat is a periodic check that surfaces actionable items without spamming.

## Behavior

- Runs every `interval_minutes`.
- Reads `shared_root/HEARTBEAT.md` if it exists.
- Suppresses output if the model returns `HEARTBEAT_OK`.
- Optional active-hours window via `active_hours`.

## Checklist

Place a checklist in `shared_root/HEARTBEAT.md` to guide the model.
