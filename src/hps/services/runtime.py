"""Dependency inspection for the packaged app bootstrap."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec


@dataclass(frozen=True)
class DependencyGroup:
    name: str
    title: str
    install_hint: str
    modules: dict[str, str]


DEPENDENCY_GROUPS: tuple[DependencyGroup, ...] = (
    DependencyGroup(
        name="core",
        title="Core analysis",
        install_hint="pip install -e '.[core]'",
        modules={
            "ase": "ase",
            "matplotlib": "matplotlib",
            "natsort": "natsort",
            "networkx": "networkx",
            "numpy": "numpy",
            "pandas": "pandas",
            "PIL": "pillow",
            "plotly": "plotly",
            "pymatgen": "pymatgen",
            "requests": "requests",
            "scipy": "scipy",
            "spglib": "spglib",
            "yaml": "pyyaml",
        },
    ),
    DependencyGroup(
        name="md",
        title="Molecular dynamics",
        install_hint="pip install -e '.[md]'",
        modules={
            "MDAnalysis": "mdanalysis",
            "seaborn": "seaborn",
        },
    ),
    DependencyGroup(
        name="pdf",
        title="PDF analysis",
        install_hint="pip install -e '.[pdf]'",
        modules={
            "diffpy.pdffit2": "diffpy.pdffit2",
            "diffpy.structure": "diffpy.structure",
        },
    ),
    DependencyGroup(
        name="viz",
        title="Visualization and widgets",
        install_hint="pip install -e '.[viz]'",
        modules={
            "bokeh": "bokeh",
            "colorcet": "colorcet",
            "holoviews": "holoviews",
            "ipyspeck": "ipyspeck",
            "mpld3": "mpld3",
            "streamlit_bokeh_events": "streamlit-bokeh-events",
            "streamlit_extras": "streamlit-extras",
            "streamlit_ketcher": "streamlit-ketcher",
            "streamlit_lottie": "streamlit-lottie",
        },
    ),
    DependencyGroup(
        name="auth",
        title="Authentication",
        install_hint="pip install -e '.[auth]'",
        modules={
            "streamlit_authenticator": "streamlit-authenticator",
        },
    ),
)


def _is_available(module_name: str) -> bool:
    try:
        return find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False


def grouped_missing_modules() -> dict[str, list[str]]:
    missing: dict[str, list[str]] = {}
    for group in DEPENDENCY_GROUPS:
        absent = [pkg_name for module_name, pkg_name in group.modules.items() if not _is_available(module_name)]
        if absent:
            missing[group.name] = absent
    return missing


def dependency_status_by_group() -> list[dict[str, object]]:
    status: list[dict[str, object]] = []
    missing = grouped_missing_modules()
    for group in DEPENDENCY_GROUPS:
        status.append(
            {
                "name": group.name,
                "title": group.title,
                "install_hint": group.install_hint,
                "missing": missing.get(group.name, []),
                "ready": group.name not in missing,
            }
        )
    return status


def legacy_app_is_runnable() -> bool:
    missing = grouped_missing_modules()
    missing.pop("pdf", None)
    return not missing


def full_install_command() -> str:
    return "pip install -e '.[full]'"


def pdf_install_command() -> str:
    return "pip install -e '.[pdf]'"
