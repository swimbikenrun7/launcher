"""Launcher home page: one card per app in apps.yaml, with status and a Start button."""

from pathlib import Path

import streamlit as st

from launcher.apps import (
    AppsFileError,
    AppStartError,
    is_running,
    load_apps,
    log_path,
    start_app,
    tail,
    wait_until_running,
)

HERE = Path(__file__).parent
APPS_FILE = HERE / "apps.yaml"
LOGS_DIR = HERE / "logs"

st.set_page_config(page_title="Launcher", page_icon="🚀", layout="wide")
st.title("🚀 Launcher")

try:
    apps = load_apps(APPS_FILE)
except AppsFileError as e:
    st.error(str(e))
    st.stop()

if st.button("Refresh status"):
    st.rerun()

columns = st.columns(3)
for i, app in enumerate(apps):
    with columns[i % 3], st.container(border=True):
        st.subheader(f"{app.icon} {app.name}")
        st.caption(app.description)
        if is_running(app.port):
            st.success(f"Running on port {app.port}")
            st.link_button("Open", app.url)
            continue

        st.warning(f"Stopped (port {app.port})")
        if not st.button("Start", key=f"start-{app.port}"):
            continue
        try:
            with st.spinner(f"Starting {app.name}…"):
                proc = start_app(app, LOGS_DIR)
                started = wait_until_running(app, proc)
        except AppStartError as e:
            st.error(str(e))
            continue
        if started:
            st.rerun()
        log = log_path(app, LOGS_DIR)
        st.error(f"{app.name} didn't come up. Last lines of {log}:")
        st.code(tail(log) or "(no output)")
