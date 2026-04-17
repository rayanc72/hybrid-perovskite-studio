"""Electronic-analysis wrappers."""

from __future__ import annotations

from hps.domain import electronic_property as _impl


def plot_pdos_streamlit(*args, **kwargs):
    return _impl.plot_pdos_streamlit(*args, **kwargs)


def detect_pdos_file_roles(*args, **kwargs):
    return _impl.detect_pdos_file_roles(*args, **kwargs)


def parse_pdos_uploads(*args, **kwargs):
    return _impl.parse_pdos_uploads(*args, **kwargs)


def build_pdos_table(*args, **kwargs):
    return _impl.build_pdos_table(*args, **kwargs)


def get_pdos_trace_options(*args, **kwargs):
    return _impl.get_pdos_trace_options(*args, **kwargs)


def add_pdos_combinations(*args, **kwargs):
    return _impl.add_pdos_combinations(*args, **kwargs)


def get_pdos_combination_labels(*args, **kwargs):
    return _impl.get_pdos_combination_labels(*args, **kwargs)


def add_pdos_combination_traces(*args, **kwargs):
    return _impl.add_pdos_combination_traces(*args, **kwargs)


def process_input_files(*args, **kwargs):
    return _impl.process_input_files(*args, **kwargs)


def process_geometry_file(*args, **kwargs):
    return _impl.process_geometry_file(*args, **kwargs)


def process_control_file(*args, **kwargs):
    return _impl.process_control_file(*args, **kwargs)


def plot_bands(*args, **kwargs):
    return _impl.plot_bands(*args, **kwargs)


def plot_spin_quivers_3D(*args, **kwargs):
    return _impl.plot_spin_quivers_3D(*args, **kwargs)
