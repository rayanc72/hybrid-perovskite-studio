"""Molecular-dynamics wrappers."""

from __future__ import annotations

from hps.domain import md_analysis as _impl


def process_streams(*args, **kwargs):
    return _impl.process_streams(*args, **kwargs)


def build_universe_from_dir(*args, **kwargs):
    return _impl.build_universe_from_dir(*args, **kwargs)


def hydrogen_bond_analysis(*args, **kwargs):
    return _impl.hydrogen_bond_analysis(*args, **kwargs)


def plot_and_return_min_distances(*args, **kwargs):
    return _impl.plot_and_return_min_distances(*args, **kwargs)


def average_structure_to_cif(*args, **kwargs):
    return _impl.average_structure_to_cif(*args, **kwargs)


def calculate_rdf_mda(*args, **kwargs):
    return _impl.calculate_rdf_mda(*args, **kwargs)


def get_ADP(*args, **kwargs):
    return _impl.get_ADP(*args, **kwargs)


def handle_rdf_analysis(*args, **kwargs):
    return _impl.handle_rdf_analysis(*args, **kwargs)


def handle_distance_analysis(*args, **kwargs):
    return _impl.handle_distance_analysis(*args, **kwargs)
