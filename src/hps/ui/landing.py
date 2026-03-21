"""Fallback landing page for environments missing optional dependencies."""

from __future__ import annotations

import streamlit as st

from hps.services.runtime import dependency_status_by_group, full_install_command
from hps.ui.sidebar import SIDEBAR_SECTIONS


def render_bootstrap_page() -> None:
    st.set_page_config(page_title="Hybrid Perovskite Studio", layout="wide")
    st.title("Hybrid Perovskite Studio")
    st.caption("Packaged entrypoint for Hybrid Perovskite Studio")

    st.markdown(
        """
        This packaged launcher keeps the legacy Streamlit app intact while moving installation and runtime checks
        into a more reproducible structure. Install the full dependency set to run the complete legacy UI.
        """
    )

    st.code(full_install_command())

    st.subheader("Dependency status")
    for group in dependency_status_by_group():
        state = "Ready" if group["ready"] else "Missing"
        st.markdown(f"**{group['title']}** - {state}")
        if group["missing"]:
            st.write("Missing packages:", ", ".join(group["missing"]))
            st.code(group["install_hint"])

    st.subheader("Current app sections")
    for section in SIDEBAR_SECTIONS:
        st.markdown(f"**{section.title}**")
        for item in section.items:
            st.write(f"- {item}")

    st.info(
        "Run `streamlit run src/hps/app.py` after installing `.[full]` to execute the complete legacy interface."
    )
