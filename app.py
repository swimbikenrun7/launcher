"""Launcher home page: one card per app in apps.yaml, with running/stopped status."""

from pathlib import Path

import streamlit as st

from launcher.apps import AppsFileError, is_running, load_apps

APPS_FILE = Path(__file__).parent / "apps.yaml"

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
        else:
            st.warning(f"Stopped (port {app.port})")
