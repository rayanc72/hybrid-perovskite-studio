"""Band and spin-texture tool wrappers."""

from __future__ import annotations

from hpame.tools import plot_band as _plot_band
from hpame.tools import scan_cbm as _scan_cbm


def plot_band_module():
    return _plot_band


def scan_cbm_module():
    return _scan_cbm
