"""Upload and current-structure rendering for the Structure workspace."""

from __future__ import annotations

from collections.abc import Callable, MutableMapping, Sequence
from typing import Any

import streamlit as st

from hps.domain.structure_manager import (
    atoms_to_speck,
    create_aims_download_file,
    create_labelled_download_file,
    get_file_format,
    print_space_group,
)
from hps.ui.workspaces.structure.state import (
    clear_loaded_structure,
    prime_summary_job,
    refresh_summary_status,
    store_upload,
)


def render_structure_upload_panel(
    state: MutableMapping[str, Any],
    *,
    debug_log: Callable[[str], None] | None = None,
) -> None:
    log = debug_log or (lambda _message: None)
    st.caption(
        "Upload or replace the active structure from anywhere inside the Structure workspace."
    )
    structure_upload = st.file_uploader(
        "Upload a structure file (aims geometry, CIF, or next_step)",
        type=["in", "cif", "next_step"],
        key=f"structure_workspace_uploader_{state['structure_uploader_key']}",
    )
    log("structure workspace: file_uploader rendered")

    if structure_upload is not None:
        uploaded_bytes = structure_upload.getvalue()
        store_upload(state, structure_upload.name, uploaded_bytes)
        prime_summary_job(state, structure_upload.name, uploaded_bytes)
        log(
            f"structure workspace: stored upload file={structure_upload.name} "
            f"bytes={len(uploaded_bytes)}"
        )
        st.success(f"Loaded `{structure_upload.name}` into the current workspace.")
    elif state["uploaded_structure_name"] is None:
        st.caption("No structure loaded yet.")
    else:
        st.caption(f"Current structure: `{state['uploaded_structure_name']}`")
        if st.button("Remove current structure", key="remove_structure_workspace"):
            clear_loaded_structure(state)
            st.rerun()

    uploaded_name = state.get("uploaded_structure_name")
    uploaded_bytes = state.get("uploaded_structure_bytes")
    if uploaded_name and uploaded_bytes is not None:
        prime_summary_job(state, uploaded_name, uploaded_bytes)
        refresh_summary_status(state)
        _render_summary_status(state)


def _render_summary_status(state: MutableMapping[str, Any]) -> None:
    status = state.get("structure_summary_status")
    error = state.get("structure_summary_error")
    if status in {"queued", "running"}:
        st.caption("Backend cache is preparing a structure summary in the background.")
    elif status == "completed":
        st.caption("Backend cache is ready for the current structure.")
    elif error:
        st.warning(f"Backend summary unavailable: {error}")


def render_current_structure_card(
    state: MutableMapping[str, Any],
    current_atoms: Any,
    current_molecules: Sequence[Sequence[int]],
    current_modified_symbols: Sequence[str],
) -> None:
    summary = state.get("structure_summary_data")
    file_name = state["file_name"]

    with st.container():
        st.markdown("### Current Structure")
        meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
        meta_col1.metric("File", file_name)
        meta_col2.metric("Format", get_file_format(file_name))
        meta_col3.metric(
            "Atoms",
            summary.get("atom_count", len(current_atoms)) if summary else len(current_atoms),
        )
        meta_col4.metric(
            "Molecule Groups",
            summary.get("molecule_group_count", len(current_molecules))
            if summary
            else len(current_molecules),
        )

        if summary:
            st.caption(
                "Backend summary: "
                f"{summary.get('formula', 'Unknown formula')} | "
                f"{summary.get('space_group', 'Unknown space group')}"
            )

        action_col1, action_col2, action_col3 = st.columns(3)
        with action_col1:
            create_aims_download_file(current_atoms, file_name, "")
        with action_col2:
            create_labelled_download_file(current_atoms, file_name, "")
        with action_col3:
            if st.button(
                "Remove current structure",
                key="remove_structure_context",
                use_container_width=True,
            ):
                clear_loaded_structure(state)
                st.rerun()

        if st.checkbox("Show structure details", value=False, key="show_structure_details"):
            _render_structure_details(current_atoms, current_molecules, current_modified_symbols)

        with st.expander("3D structure viewer", expanded=False):
            load_viewer = st.checkbox(
                "Load 3D structure viewer",
                value=False,
                key="load_initial_structure_viewer",
            )
            if load_viewer:
                try:
                    atoms_to_speck(current_atoms, "initialization")
                except Exception as exc:
                    st.error(f"Error rendering structure viewer: {exc}")
            else:
                st.caption("Enable the viewer only when needed.")

        st.divider()


def _render_structure_details(
    current_atoms: Any,
    current_molecules: Sequence[Sequence[int]],
    current_modified_symbols: Sequence[str],
) -> None:
    space_group = print_space_group(current_atoms)
    with st.expander("Symmetry information", expanded=False):
        st.markdown(f"```\n{space_group}\n```")

    molecule_lines = []
    for index, molecule in enumerate(current_molecules, 1):
        labels = [current_modified_symbols[atom_index] for atom_index in molecule]
        molecule_lines.append(f"Molecule {index}: {', '.join(labels)}")
    molecule_text = "\n".join(molecule_lines)
    with st.expander("Detected molecules", expanded=False):
        st.markdown(f"```\n{molecule_text}\n```")
