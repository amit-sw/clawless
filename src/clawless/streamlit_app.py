from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from clawless.config import AppConfig, ConfigManager, coerce_config_roots, ensure_paths
from clawless.db import connect, init_db
from clawless.tracks import TrackManager

DEFAULT_CONFIG_ROOT = Path("./config")


def _load_config() -> tuple[ConfigManager, AppConfig]:
    config_root = Path(os.environ.get("CLAWLESS_CONFIG_ROOT", str(DEFAULT_CONFIG_ROOT))).expanduser().resolve()
    manager = ConfigManager(config_root)
    config = manager.load()
    config = coerce_config_roots(config)
    return manager, config


def main() -> None:
    st.set_page_config(page_title="Clawless", layout="wide")
    manager, config = _load_config()

    st.title("Clawless Control Panel")

    tabs = st.tabs(["Onboarding", "Tracks", "Jobs", "MCP", "Heartbeat"])

    with tabs[0]:
        st.subheader("Configuration")
        with st.form("config_form"):
            st.write("Telegram")
            token = st.text_input("Telegram Bot Token", value=config.telegram.token, type="password")
            owner_id = st.text_input("Owner User ID", value=str(config.telegram.owner_user_id))

            st.write("LLM")
            connection_string = st.text_input(
                "Connection String (scheme:model)",
                value=config.llm.connection_string,
            )
            api_key = st.text_input("API Key", value=config.llm.api_key, type="password")

            st.write("Paths")
            config_root = st.text_input("Config Root", value=str(config.paths.config_root))
            internal_root = st.text_input("Internal Root", value=str(config.paths.internal_root))
            shared_root = st.text_input("Shared Root", value=str(config.paths.shared_root))

            save = st.form_submit_button("Save")
            if save:
                config.telegram.token = token
                config.telegram.owner_user_id = int(owner_id or 0)
                config.llm.connection_string = connection_string
                config.llm.api_key = api_key
                config.paths.config_root = Path(config_root)
                config.paths.internal_root = Path(internal_root)
                config.paths.shared_root = Path(shared_root)
                ensure_paths(config.paths)
                new_manager = ConfigManager(Path(config_root).expanduser().resolve())
                new_manager.save(config)
                st.success("Saved configuration.")

    with tabs[1]:
        st.subheader("Tracks")
        if config.paths.internal_root:
            db_path = Path(config.paths.internal_root) / "clawless.db"
            conn = connect(db_path)
            init_db(conn)
            tracks = TrackManager(conn)
            items = tracks.list_tracks()
            if not items:
                st.info("No tracks yet.")
            else:
                track_names = [t.name for t in items]
                selected = st.selectbox("Track", options=track_names)
                track = tracks.get_by_name(selected)
                if track:
                    st.write(f"Summary: {track.summary or '(empty)'}")
                    messages = tracks.recent_messages(track.id, limit=50)
                    for msg in messages:
                        st.write(f"{msg['role']}: {msg['content']}")

    with tabs[2]:
        st.subheader("Jobs")
        db_path = Path(config.paths.internal_root) / "clawless.db"
        conn = connect(db_path)
        init_db(conn)
        rows = conn.execute("SELECT id, cron_spec, payload, enabled FROM jobs").fetchall()
        if not rows:
            st.info("No jobs scheduled.")
        else:
            for row in rows:
                st.write(f"#{row['id']} | {row['cron_spec']} | enabled={bool(row['enabled'])}")
                st.code(row["payload"], language="json")

        st.markdown("---")
        st.write("Add new job")
        with st.form("new_job"):
            cron_spec = st.text_input("Cron Spec", value="0 * * * *")
            prompt = st.text_area("Prompt")
            submit = st.form_submit_button("Add Job")
            if submit:
                payload = json.dumps({"prompt": prompt})
                conn.execute(
                    "INSERT INTO jobs (cron_spec, payload, enabled) VALUES (?, ?, 1)",
                    (cron_spec, payload),
                )
                conn.commit()
                st.success("Job added.")

    with tabs[3]:
        st.subheader("MCP Servers")
        st.write("Configured servers:")
        for srv in config.mcp_servers:
            st.write(f"{srv.name} -> {srv.url}")
        st.markdown("---")
        st.write("Add server")
        with st.form("mcp_form"):
            name = st.text_input("Name")
            url = st.text_input("URL")
            token = st.text_input("Bearer Token", type="password")
            add = st.form_submit_button("Add")
            if add and name and url:
                from clawless.config import MCPServerConfig

                config.mcp_servers.append(MCPServerConfig(name=name, url=url, bearer_token=token))
                manager.save(config)
                st.success("MCP server added.")

    with tabs[4]:
        st.subheader("Heartbeat")
        with st.form("heartbeat_form"):
            enabled = st.checkbox("Enabled", value=config.heartbeat.enabled)
            interval = st.number_input("Interval Minutes", min_value=5, value=config.heartbeat.interval_minutes)
            active_hours = st.text_input(
                "Active Hours (HH:MM-HH:MM)",
                value=config.heartbeat.active_hours or "",
            )
            prompt = st.text_area("Prompt", value=config.heartbeat.prompt)
            checklist = st.text_input("Checklist Path", value=config.heartbeat.checklist_path)
            save_heartbeat = st.form_submit_button("Save Heartbeat")
            if save_heartbeat:
                config.heartbeat.enabled = enabled
                config.heartbeat.interval_minutes = int(interval)
                config.heartbeat.active_hours = active_hours or None
                config.heartbeat.prompt = prompt
                config.heartbeat.checklist_path = checklist
                manager.save(config)
                st.success("Heartbeat updated.")


if __name__ == "__main__":
    main()
