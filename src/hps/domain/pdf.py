"""PDF-analysis wrappers."""

from __future__ import annotations

from hps.domain import pdf_analysis as _impl


def calculate_pdf(*args, **kwargs):
    return _impl.calculate_pdf(*args, **kwargs)


def compute_pcc(*args, **kwargs):
    return _impl.compute_pcc(*args, **kwargs)


def compute_rdf_weighted(*args, **kwargs):
    return _impl.compute_rdf_weighted(*args, **kwargs)


def compute_pdf_from_rdf_df(*args, **kwargs):
    return _impl.compute_pdf_from_rdf_df(*args, **kwargs)


def plot_rdf_pdf(*args, **kwargs):
    return _impl.plot_rdf_pdf(*args, **kwargs)


def load_or_create_plot_config(*args, **kwargs):
    return _impl.load_or_create_plot_config(*args, **kwargs)


def load_or_create_plot_config_matplotlib(*args, **kwargs):
    return _impl.load_or_create_plot_config_matplotlib(*args, **kwargs)


def plot_rdf_pdf_matplotlib(*args, **kwargs):
    return _impl.plot_rdf_pdf_matplotlib(*args, **kwargs)
