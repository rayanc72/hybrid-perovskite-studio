"""UI helpers for the packaged app."""

from .sidebar import SIDEBAR_SECTIONS

__all__ = ["SIDEBAR_SECTIONS", "render_bootstrap_page"]


def render_bootstrap_page():
    from .landing import render_bootstrap_page as _render_bootstrap_page

    return _render_bootstrap_page()
