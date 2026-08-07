"""PDF-analysis wrappers."""

from __future__ import annotations

from importlib import import_module


def _implementation():
    return import_module("hps.domain.pdf_analysis")


def calculate_pdf(*args, **kwargs):
    return _implementation().calculate_pdf(*args, **kwargs)


def compute_pcc(*args, **kwargs):
    return _implementation().compute_pcc(*args, **kwargs)


def compute_rdf_weighted(*args, **kwargs):
    return _implementation().compute_rdf_weighted(*args, **kwargs)


def compute_pdf_from_rdf_df(*args, **kwargs):
    return _implementation().compute_pdf_from_rdf_df(*args, **kwargs)


def plot_rdf_pdf(*args, **kwargs):
    return _implementation().plot_rdf_pdf(*args, **kwargs)


def load_or_create_plot_config(*args, **kwargs):
    return _implementation().load_or_create_plot_config(*args, **kwargs)


def load_or_create_plot_config_matplotlib(*args, **kwargs):
    return _implementation().load_or_create_plot_config_matplotlib(*args, **kwargs)


def plot_rdf_pdf_matplotlib(*args, **kwargs):
    return _implementation().plot_rdf_pdf_matplotlib(*args, **kwargs)


def infer_rho0_from_cif(*args, **kwargs):
    return _implementation().infer_rho0_from_cif(*args, **kwargs)


def integrate_gr_window(*args, **kwargs):
    return _implementation().integrate_gr_window(*args, **kwargs)


def reduced_pdf_to_gr(*args, **kwargs):
    return _implementation().reduced_pdf_to_gr(*args, **kwargs)


def load_structure(*args, **kwargs):
    return _implementation().loadStructure(*args, **kwargs)
