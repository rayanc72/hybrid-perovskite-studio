"""Backend-backed symmetry workflow renderer."""

from __future__ import annotations

import base64
import os
from collections.abc import Callable, MutableMapping
from typing import Any

import streamlit as st
from pymatgen.io.cif import CifWriter

from hps.domain.structure_manager import (
    extract_symprec_from_string,
    generate_symmetrized_structure,
)
from hps.ui.backend_workflows import get_workflow_state, run_workflow


def build_symmetry_payload(
    file_name: str,
    file_bytes: bytes,
    symprec_lower: float,
    symprec_upper: float,
    angle_tol: float,
) -> dict[str, object]:
    return {
        "file_name": file_name,
        "file_bytes_b64": base64.b64encode(file_bytes).decode("utf-8"),
        "symprec_lower": float(symprec_lower),
        "symprec_upper": float(symprec_upper),
        "angle_tol": float(angle_tol),
    }


def symmetry_output_filename(file_name: str | None) -> str:
    root = os.path.splitext(file_name or "structure")[0]
    return f"{root}_high_symm.cif"


def render_symmetry_analysis(
    state: MutableMapping[str, Any],
    registry: MutableMapping[str, dict[str, Any]],
    uploaded_structure_bytes: bytes,
    modified_atoms: Any,
    *,
    render_section_header: Callable[..., None],
) -> None:
    render_section_header("Symmetrize structure", kicker="Structure Workspace")
    with st.form(key="symmetry_form"):
        symprec_lower = st.number_input(
            "Enter the lower bound for tolerance",
            value=1e-3,
            step=1e-3,
            format="%.4f",
        )
        symprec_upper = st.number_input(
            "Enter the upper bound for tolerance",
            value=1e-1,
            step=1e-3,
            format="%.4f",
        )
        angle_tol = st.number_input(
            "Enter a tolerance for angles",
            value=5.0,
            step=1e-3,
            format="%.4f",
        )
        valid_range = symprec_lower <= symprec_upper
        if not valid_range:
            st.error("Lower bound should be less than or equal to the upper bound.")
        form_submitted = st.form_submit_button("Get Space Groups")

    payload = build_symmetry_payload(
        state["file_name"],
        uploaded_structure_bytes,
        symprec_lower,
        symprec_upper,
        angle_tol,
    )
    state_key = f"structure_symmetry::{state['file_name']}"
    result = run_workflow(
        registry,
        "structure_symmetry",
        payload,
        state_key,
        start=form_submitted and valid_range,
    )
    workflow_state = get_workflow_state(registry, state_key)
    if (
        form_submitted
        and result is None
        and workflow_state.get("status") not in {"failed", "cancelled"}
    ):
        st.info(
            "Computing symmetry candidates in the backend. Re-run this action in a moment "
            "if they do not appear immediately."
        )
    if workflow_state.get("error"):
        st.error(f"Symmetry analysis failed: {workflow_state['error']}")

    if not result or not result.get("space_groups"):
        return

    selected = st.selectbox(
        "Select the desired space group",
        options=[entry["label"] for entry in result["space_groups"]],
        index=0,
    )
    if not st.button("Generate CIF"):
        return

    try:
        selected_symprec = extract_symprec_from_string(selected)
        structure = generate_symmetrized_structure(
            modified_atoms,
            selected_symprec,
            angle_tol,
        )
        content = str(
            CifWriter(
                structure,
                symprec=selected_symprec,
                angle_tolerance=angle_tol,
            )
        )
        st.download_button(
            "Download symmetrized CIF",
            data=content,
            file_name=symmetry_output_filename(state.get("file_name")),
            mime="chemical/x-cif",
            key="symmetry_cif_download",
        )
    except ValueError as exc:
        st.error(f"An error occurred when processing the selected space group: {exc}")
    except Exception as exc:
        st.error(f"An unexpected error occurred: {exc}")
