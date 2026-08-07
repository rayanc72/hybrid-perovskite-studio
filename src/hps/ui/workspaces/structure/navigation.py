"""Typed navigation state for the Structure workspace."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from hps.ui.navigation import group_names, tool_options, view_names


@dataclass(frozen=True)
class StructureSelection:
    mode: str
    group: str | None = None
    tool: str | None = None

    @property
    def symmetry(self) -> bool:
        return self.tool == "Symmetrize structure"

    @property
    def center_of_mass(self) -> bool:
        return self.tool == "Find center of mass"

    @property
    def dipole_moment(self) -> bool:
        return self.tool == "Calculate dipole moment"

    @property
    def polarization(self) -> bool:
        return self.tool == "Calculate polarization direction"

    @property
    def atomic_distances(self) -> bool:
        return self.tool == "Calculate atomic distances"

    @property
    def distortions(self) -> bool:
        return self.tool == "Calculate octahedral distortions"

    @property
    def percentage_deviation(self) -> bool:
        return self.tool == "Calculate percentage deviation"

    @property
    def adp_table(self) -> bool:
        return self.tool == "Anisotropic displacement parameters"

    @property
    def pxrd(self) -> bool:
        return self.mode == "Analysis" and self.group == "PXRD Analysis"

    @property
    def pdf(self) -> bool:
        return self.mode == "Analysis" and self.group == "PDF Analysis"

    @property
    def charge_analysis(self) -> bool:
        return self.tool == "Charge analysis"

    @property
    def rotation(self) -> bool:
        return self.mode == "Transformations" and self.tool == "Rotation"

    @property
    def reflection(self) -> bool:
        return self.mode == "Transformations" and self.tool == "Reflection"

    @property
    def translation(self) -> bool:
        return self.mode == "Transformations" and self.tool == "Translation"

    @property
    def deletion(self) -> bool:
        return self.mode == "Transformations" and self.tool == "Deletion"

    @property
    def labelling(self) -> bool:
        return self.mode == "Transformations" and self.tool == "Labelling"

    @property
    def interpolation(self) -> bool:
        return self.mode == "Transformations" and self.tool == "Interpolation"


def render_structure_navigation() -> StructureSelection:
    mode = st.radio("View", options=view_names("Structure"), horizontal=True)

    if mode == "Overview":
        st.info("Review the current structure, then move into analysis or transformations as needed.")
        return StructureSelection(mode=mode)

    if mode == "Analysis":
        group = st.radio(
            "Group",
            options=group_names("Structure", "Analysis"),
            horizontal=True,
        )
        label = "Tool" if group in {"Symmetry", "Molecules", "Structure Metrics"} else "Workflow"
        tool = st.selectbox(
            label,
            options=tool_options("Structure", "Analysis", group),
        )
        return StructureSelection(mode=mode, group=group, tool=tool)

    group = st.radio(
        "Group",
        options=group_names("Structure", "Transformations"),
        horizontal=True,
    )
    tool = st.selectbox(
        "Tool",
        options=tool_options("Structure", "Transformations", group),
    )
    if tool == "Interpolation":
        st.caption("Interpolation uses its own file-upload workflow inside lattice operations.")
    return StructureSelection(mode=mode, group=group, tool=tool)
