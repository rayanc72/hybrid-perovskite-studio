"""Sidebar catalog extracted from the current Streamlit app."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SidebarSection:
    title: str
    items: tuple[str, ...]


SIDEBAR_SECTIONS: tuple[SidebarSection, ...] = (
    SidebarSection(
        title="Structure Analysis",
        items=(
            "Symmetrize structure",
            "Find center of mass",
            "Calculate dipole moment",
            "Calculate polarization direction",
            "Calculate atomic distances",
            "Calculate octahedral distortions",
            "Calculate percentage deviation",
            "Anisotropic displacement parameters",
            "PDF analysis",
            "Charge analysis",
        ),
    ),
    SidebarSection(
        title="Structure Transformations",
        items=(
            "Rotation",
            "Reflection",
            "Translation",
            "Deletion",
            "Standard interpolation",
        ),
    ),
    SidebarSection(
        title="Electronic Analysis",
        items=(
            "Plot polarization",
            "Plot partial density of states (PDOS)",
            "Plot bandstructure",
            "Plot spin texture",
            "Plot 3D spin texture",
            "Plot absorption spectra",
        ),
    ),
    SidebarSection(
        title="Dynamics Analysis",
        items=(
            "Analyze AIMS MD output",
            "Trajectory analysis",
        ),
    ),
    SidebarSection(
        title="Experimental",
        items=(
            "Run your own script",
            "Plot Data",
        ),
    ),
)
