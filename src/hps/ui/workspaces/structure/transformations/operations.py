"""Structure reflection, translation, deletion, labelling, and interpolation UI."""

from __future__ import annotations

import os
from collections.abc import Callable, MutableMapping, Sequence
from typing import Any

import numpy as np
import streamlit as st
from pymatgen.analysis.structure_matcher import StructureMatcher
from pymatgen.io.ase import AseAtomsAdaptor

from hps.domain.molecule_builder import get_molecule_object
from hps.domain.structure_manager import (
    atoms_to_speck,
    build_molecule_label_overrides,
    create_aims_download_file,
    create_custom_geometry_download_file,
    create_interpolated_structures_zip,
    create_labelled_download_file,
    delete_molecules,
    find_local_indices,
    generate_labelled_cif,
    get_atom_labels,
    get_file_format,
    plane_params_from_hkl,
    process_uploaded_files,
    reflect_molecules,
    translate_molecule,
)

TRANSLATION_AXES = ("x", "y", "z", "xy", "xz", "yz", "xyz", "custom")


def structure_file_root(file_name: str | None) -> str:
    """Return a stable output root for the active structure."""

    return os.path.splitext(file_name or "structure")[0]


def parse_atom_indices(value: str) -> list[int]:
    """Parse comma- or whitespace-separated atom indices."""

    return [int(token) for token in value.replace(",", " ").split()]


def render_reflection(
    modified_atoms: Any,
    molecules: Sequence[Sequence[int]],
    file_name: str | None,
    *,
    render_section_header: Callable[..., None],
) -> Any:
    render_section_header("Reflect molecules on a plane", kicker="Structure Workspace")
    selected = st.multiselect(
        "Select molecule indices",
        options=range(1, len(molecules) + 1),
    )
    if "reflection_parameters" not in st.session_state:
        st.session_state.reflection_parameters = [None] * len(molecules)
    for index in selected:
        st.subheader(f"Molecule {index}")
        with st.form(key=f"reflection_molecule_{index}_form"):
            plane_input = st.text_input("Enter crystal plane as h, k, l separated by spaces")
            atom_labels = get_atom_labels(modified_atoms, molecules[index - 1])
            excluded = st.multiselect(
                "Select atom indices not to reflect (Optional)",
                options=atom_labels,
                format_func=lambda item: item[1],
            )
            if st.form_submit_button(f"Set Parameters for Molecule {index}"):
                hkl = np.array([int(value) for value in plane_input.split()])
                local_indices = find_local_indices(
                    molecules[index - 1],
                    [atom_index for atom_index, _ in excluded],
                )
                st.session_state.reflection_parameters[index - 1] = (hkl, local_indices)

    if not st.button("Apply Reflections"):
        return modified_atoms
    parameters = [st.session_state.reflection_parameters[index - 1] for index in selected]
    if not selected or any(parameter is None for parameter in parameters):
        st.warning("Set reflection parameters for every selected molecule first.")
        return modified_atoms
    for index, (hkl, excluded) in zip(selected, parameters):
        molecule = molecules[index - 1]
        molecule_object = get_molecule_object(modified_atoms, molecule)
        normal, origin = plane_params_from_hkl(modified_atoms, hkl)
        modified_atoms = reflect_molecules(
            modified_atoms,
            molecule,
            molecule_object,
            normal,
            origin,
            excluded,
        )
    root = structure_file_root(file_name)
    create_aims_download_file(modified_atoms, root, "_reflected")
    create_labelled_download_file(modified_atoms, root, "_reflected")
    return modified_atoms


def _translation_parameters(key_prefix: str) -> tuple[str, dict[Any, float]]:
    axes = st.selectbox(
        "Enter the axes for translation",
        TRANSLATION_AXES,
        key=f"{key_prefix}_axes",
    )
    if axes == "custom":
        raw_axis = st.text_input(
            "Enter custom axis as x, y, z separated by spaces",
            key=f"{key_prefix}_custom_axis",
        )
        axis = tuple(float(value) for value in raw_axis.split())
        distance = st.number_input(
            "Enter the translation distance",
            step=0.1,
            key=f"{key_prefix}_custom_distance",
        )
        return axes, {axis: distance}
    distances = {
        axis: st.number_input(
            f"Enter the translation distance along {axis}-axis",
            key=f"{key_prefix}_{axis}_distance",
            step=0.1,
        )
        for axis in axes
    }
    return axes, distances


def render_translation(
    modified_atoms: Any,
    molecules: Sequence[Sequence[int]],
    file_name: str | None,
    *,
    render_section_header: Callable[..., None],
) -> Any:
    render_section_header("Translation", kicker="Structure Workspace")
    translation_type = st.selectbox("Select Translation Type", ("Molecules", "Atoms"))
    if translation_type == "Molecules":
        scope = "molecules"
        selected = st.multiselect(
            "Select molecule indices to translate",
            range(1, len(molecules) + 1),
        )
    else:
        scope = "atoms"
        raw_indices = st.text_input(
            "Enter atom indices to translate (separated by spaces or commas)"
        )
        try:
            selected = parse_atom_indices(raw_indices) if raw_indices else []
        except ValueError:
            st.error("Atom indices must be integers separated by spaces or commas.")
            return modified_atoms

    with st.form(key=f"translation_{scope}_form"):
        try:
            axes, distances = _translation_parameters(f"translation_{scope}")
        except ValueError:
            st.error("A custom axis must contain numeric components.")
            return modified_atoms
        submitted = st.form_submit_button("Apply Translation")
    if submitted:
        modified_atoms = translate_molecule(
            modified_atoms,
            molecules,
            scope,
            selected,
            axes,
            distances,
        )
        root = structure_file_root(file_name)
        create_aims_download_file(modified_atoms, root, "_translated")
        create_labelled_download_file(modified_atoms, root, "_translated")
    with st.expander("See structure"):
        atoms_to_speck(modified_atoms, f"translation_{scope}")
    return modified_atoms


def render_deletion(
    modified_atoms: Any,
    molecules: Sequence[Sequence[int]],
    file_name: str | None,
    *,
    render_section_header: Callable[..., None],
) -> Any:
    render_section_header("Delete Molecules", kicker="Structure Workspace")
    with st.form(key="delete_form"):
        selected = st.multiselect(
            "Select molecule indices to delete",
            range(1, len(molecules) + 1),
        )
        submitted = st.form_submit_button("Apply Deletion")
    if submitted:
        modified_atoms = delete_molecules(modified_atoms, molecules, selected)
        root = structure_file_root(file_name)
        create_aims_download_file(modified_atoms, root, "_deleted")
        create_labelled_download_file(modified_atoms, root, "_deleted")
    with st.expander("See structure"):
        atoms_to_speck(modified_atoms, "deletion")
    return modified_atoms


def render_labelling(
    modified_atoms: Any,
    molecules: Sequence[Sequence[int]],
    current_labels: Sequence[str],
    state: MutableMapping[str, Any],
    *,
    render_section_header: Callable[..., None],
) -> None:
    render_section_header("Label Molecule Atoms", kicker="Structure Workspace")
    selected = st.multiselect(
        "Select molecules",
        options=range(1, len(molecules) + 1),
        format_func=lambda index: f"Molecule {index}",
    )
    overrides: dict[int, str] = {}
    parts: list[str] = []
    for index in selected:
        molecule = molecules[index - 1]
        labels = [current_labels[atom_index] for atom_index in molecule]
        st.caption(f"Molecule {index} current labels: {', '.join(labels)}")
        suffix = st.text_input(
            f"Label suffix for Molecule {index}",
            value="",
            key=f"molecule_label_suffix_{index}",
        ).strip()
        if not suffix:
            continue
        try:
            molecule_overrides = build_molecule_label_overrides(
                modified_atoms,
                molecule,
                suffix,
            )
        except ValueError as exc:
            st.error(f"Molecule {index}: {exc}")
            continue
        overrides.update(molecule_overrides)
        parts.append(f"molecule_{index}_{suffix}")
        preview = [molecule_overrides[atom_index] for atom_index in molecule]
        st.caption(f"Molecule {index} preview: {', '.join(preview)}")
    if not overrides:
        return

    original_content = None
    uploaded_name = state.get("uploaded_structure_name")
    uploaded_bytes = state.get("uploaded_structure_bytes")
    if uploaded_name and uploaded_bytes is not None and get_file_format(uploaded_name) == "aims":
        original_content = uploaded_bytes.decode("utf-8")
    create_custom_geometry_download_file(
        modified_atoms,
        "geometry.in",
        "_" + "_".join(parts),
        atom_label_overrides=overrides,
        original_content=original_content,
        download_label="Download custom-labelled geometry.in",
    )


def render_interpolation(*, render_section_header: Callable[..., None]) -> None:
    render_section_header("Interpolate Structures", kicker="Structure Workspace")
    initial_file = st.file_uploader(
        "Upload an initial structure file (AIMS or CIF)",
        type=[".in", ".cif"],
        key="interpolation_initial_file",
    )
    final_file = st.file_uploader(
        "Upload a final structure file (AIMS or CIF)",
        type=[".in", ".cif"],
        key="interpolation_final_file",
    )
    if initial_file is None or final_file is None:
        return
    initial_atoms, final_atoms, initial_name, final_name = process_uploaded_files(
        initial_file,
        final_file,
    )
    if initial_atoms is None or final_atoms is None:
        return
    image_count = st.number_input(
        "Enter the number of interpolated structures to generate:",
        min_value=1,
        step=1,
    )
    initial = AseAtomsAdaptor.get_structure(initial_atoms)
    final = AseAtomsAdaptor.get_structure(final_atoms)
    reordered_final = StructureMatcher(primitive_cell=False).get_s2_like_s1(initial, final)
    if reordered_final is None:
        st.error("The final structure could not be matched to the initial structure.")
        return
    if st.checkbox("Do you want labelled atoms for checking?"):
        generate_labelled_cif(initial, f"{initial_name}_labelled")
        generate_labelled_cif(reordered_final, f"{final_name}_reordered_labelled")
    if not st.button("Generate Interpolated Structures"):
        return
    try:
        structures = initial.interpolate(
            reordered_final,
            nimages=image_count,
            autosort_tol=0.5,
            interpolate_lattices=True,
        )
        atoms = [AseAtomsAdaptor.get_atoms(structure) for structure in structures]
        create_interpolated_structures_zip(atoms)
    except Exception as exc:
        st.error(f"Error: {exc}")
