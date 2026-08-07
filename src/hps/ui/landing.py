"""Fallback landing page for environments missing optional dependencies."""

from __future__ import annotations

import streamlit as st

from hps.services.runtime import (
    dependency_status_by_group,
    full_install_command,
    pdf_install_command,
)
from hps.ui.sidebar import SIDEBAR_SECTIONS


def render_bootstrap_page() -> None:
    st.set_page_config(page_title="Hybrid Perovskite Studio", layout="wide")
    st.markdown(
        """
        <style>
        :root {
            --hp-text:#10232a;
            --hp-muted:#5a6b72;
            --hp-accent:#007a8a;
            --hp-border:rgba(16,35,42,.14);
        }
        .stApp { background:#f4f7f7; color:var(--hp-text); }
        .block-container { padding-top:3rem; padding-bottom:4rem; }
        .bootstrap-brand { padding-bottom:2.6rem; border-bottom:1px solid var(--hp-border); }
        .bootstrap-kicker {
            color:var(--hp-accent);
            font-size:.72rem;
            font-weight:700;
            letter-spacing:.14em;
            text-transform:uppercase;
        }
        .bootstrap-title {
            max-width:48rem;
            margin:.7rem 0 .55rem;
            color:var(--hp-text);
            font-size:clamp(2.4rem,5vw,4.8rem);
            font-weight:720;
            letter-spacing:-.06em;
            line-height:.96;
        }
        .bootstrap-copy { max-width:42rem; color:var(--hp-muted); font-size:1rem; line-height:1.6; }
        h2, h3 { color:var(--hp-text); letter-spacing:-.035em; }
        hr { border-color:var(--hp-border) !important; }
        div[data-testid="stCode"] {
            border:1px solid var(--hp-border);
            border-radius:8px;
            box-shadow:none;
        }
        div[data-testid="stAlert"] {
            border:0;
            border-left:3px solid var(--hp-accent);
            border-radius:8px;
        }
        </style>
        <div class="bootstrap-brand">
            <div class="bootstrap-kicker">Hybrid Perovskite Studio</div>
            <div class="bootstrap-title">Complete the local setup.</div>
            <div class="bootstrap-copy">
                Install the analysis dependencies below to open the full materials workspace.
                PDF support remains optional.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        The standard dependency set enables structure, electronic, dynamics, and utility workflows.
        """
    )

    st.code(full_install_command())
    st.caption("Optional PDF support")
    st.code(pdf_install_command())

    st.subheader("Dependency status", divider="gray")
    for group in dependency_status_by_group():
        state = "Ready" if group["ready"] else "Missing"
        st.markdown(f"**{group['title']}** - {state}")
        if group["missing"]:
            st.write("Missing packages:", ", ".join(group["missing"]))
            st.code(group["install_hint"])

    st.subheader("Available workspaces", divider="gray")
    for section in SIDEBAR_SECTIONS:
        st.markdown(f"**{section.title}**")
        for item in section.items:
            st.write(f"- {item}")

    st.info(
        "Run `streamlit run src/hps/app.py` after installing `.[full]`. "
        "Add `.[pdf]` only if you need PDF analysis."
    )
