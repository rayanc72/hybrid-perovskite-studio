"""Electronic-analysis wrappers."""

from __future__ import annotations

from hps.domain import electronic_property as _impl


def plot_pdos_streamlit(*args, **kwargs):
    return _impl.plot_pdos_streamlit(*args, **kwargs)


def process_input_files(*args, **kwargs):
    return _impl.process_input_files(*args, **kwargs)


def process_geometry_file(*args, **kwargs):
    return _impl.process_geometry_file(*args, **kwargs)


def process_control_file(*args, **kwargs):
    return _impl.process_control_file(*args, **kwargs)


def plot_bands(*args, **kwargs):
    return _impl.plot_bands(*args, **kwargs)
