"""Structure metric workflow renderers and table-building helpers."""

from __future__ import annotations

import io
from collections.abc import Callable, Sequence
from typing import Any

import pandas as pd
import streamlit as st
from pymatgen.io.ase import AseAtomsAdaptor

from hps.domain.md_analysis import calculate_ellipsoid_volumes
from hps.domain.structure_manager import (
    calculate_angle_variance,
    calculate_bond_distance_variance,
    calculate_bond_distance_variance_v2,
    calculate_in_out_planes,
    calculate_mc_2D,
    calculate_mc_2D_proj,
    calculate_off_centering,
    calculate_off_centering_proj,
    calculate_unique_ABA_angles,
    extract_Uij_from_cif,
    filter_atoms_by_symbols_and_extend,
    filter_unique_distances,
    find_matching_distances,
    find_third_atom_distances_with_cutoff,
    handle_bridging_angles,
    handle_in_out_deviations,
    identify_AB_groups,
    process_uploaded_files,
)

LATTICE_PARAMETER_LABELS = (
    "a (Å)",
    "b (Å)",
    "c (Å)",
    "alpha (°)",
    "beta (°)",
    "gamma (°)",
    "volume (Å^3)",
)
LATTICE_PARAMETER_KEYS = ("a", "b", "c", "alpha", "beta", "gamma", "volume")


def build_lattice_deviation_table(initial_lattice: Any, final_lattice: Any) -> pd.DataFrame:
    """Build initial/final lattice values and percentage deviations."""

    initial = [float(getattr(initial_lattice, key)) for key in LATTICE_PARAMETER_KEYS]
    final = [float(getattr(final_lattice, key)) for key in LATTICE_PARAMETER_KEYS]
    deviations = [
        (final_value - initial_value) / initial_value * 100.0
        for initial_value, final_value in zip(initial, final)
    ]
    return pd.DataFrame(
        zip(LATTICE_PARAMETER_LABELS, initial, final, deviations),
        columns=("Lattice Parameter", "Initial Value", "Final Value", "Deviation (%)"),
    )


def distortion_function_map() -> dict[str, Callable[..., Any]]:
    """Return the supported distortion calculations in display order."""

    return {
        "Bond distance variance": calculate_bond_distance_variance,
        "Bond distance variance simplified (x 1e-05)": calculate_bond_distance_variance_v2,
        "Metal off-centering": calculate_off_centering,
        "2D projected Metal off-centering": calculate_off_centering_proj,
        "2D Metal off-centering": calculate_mc_2D,
        "2D projected 2D off-centering": calculate_mc_2D_proj,
        "Angle variance": calculate_angle_variance,
        "Bridging angle(s)": calculate_unique_ABA_angles,
        "In and out deviations": calculate_in_out_planes,
    }


def render_adp_table(
    uploaded_structure_bytes: bytes,
    *,
    render_section_header: Callable[..., None],
) -> None:
    render_section_header("Extract ADP from CIF", kicker="Structure Workspace")
    try:
        table = extract_Uij_from_cif(io.BytesIO(uploaded_structure_bytes))
        table = calculate_ellipsoid_volumes(table, ignore_atoms=None)
        st.dataframe(table, hide_index=True, use_container_width=True)
    except ValueError as exc:
        st.error(f"An error occurred when trying to extract the ADP values: {exc}")


def render_atomic_distances(
    modified_atoms: Any,
    *,
    render_section_header: Callable[..., None],
) -> None:
    render_section_header("Calculate atomic distances", kicker="Structure Workspace")
    first_atom = st.text_input("Enter the symbol of the first atom (A):", value="Pb")
    second_atom = st.text_input("Enter the symbol of the second atom (B):", value="I")
    min_cutoff, max_cutoff = st.slider(
        "Set cut-off range for searching the atoms",
        min_value=0.0,
        max_value=10.0,
        value=(0.0, 3.5),
        step=0.1,
    )
    if st.button("Calculate"):
        distances = find_third_atom_distances_with_cutoff(
            modified_atoms,
            first_atom,
            second_atom,
            min_cutoff,
            max_cutoff,
        )
        st.dataframe(distances, use_container_width=True, hide_index=True)


def _format_distortion_result(
    name: str,
    result: Any,
    periodic_image_dict: dict[Any, Any],
) -> list[tuple[str, str]]:
    if name == "Bridging angle(s)":
        return handle_bridging_angles(result, periodic_image_dict)
    if name == "In and out deviations":
        return handle_in_out_deviations(result)
    return [(name, ", ".join(result))]


def render_distortions(
    modified_atoms: Any,
    *,
    render_section_header: Callable[..., None],
) -> None:
    render_section_header("Calculate distortion parameters", kicker="Structure Workspace")
    center_atom = st.text_input("Enter the symbol of the center atom (A):", value="Pb")
    surrounding_atom = st.text_input(
        "Enter the symbol of the surrounding atoms (B):",
        value="I",
    )
    selectable = (
        "all",
        "Bond distance variance",
        "Angle variance",
        "Bridging angle(s)",
        "In and out deviations",
    )
    distortion_type = st.selectbox("Select the type of distortion to calculate:", selectable)
    with st.expander("Optional parameters"):
        center_atom_2 = st.text_input(
            "Enter the symbol of a second center atom, if available (useful for double perovskites):",
            value=None,
        )
        bond_relaxation = st.number_input(
            "Relax the bond distance limit (useful for chloride-based systems):",
            value=0.0,
        )
        distortion_relaxation = st.number_input(
            "Relax the octahedron distortion limit (useful for highly distorted systems):",
            value=0.0,
        )
        supercell_size = st.number_input(
            "Modify the supercell size (useful for checking convergence):",
            value=3,
        )
    if not st.button("Calculate"):
        return

    try:
        super_atoms, periodic_images, second_center_indices = filter_atoms_by_symbols_and_extend(
            modified_atoms,
            A=center_atom,
            B=surrounding_atom,
            A2=center_atom_2,
            s_size=supercell_size,
        )
        octahedra, distances = identify_AB_groups(
            super_atoms,
            center_atom,
            surrounding_atom,
            b=bond_relaxation,
            c=distortion_relaxation,
        )
        unique_distances = filter_unique_distances(distances)
        octahedral_distances = find_matching_distances(
            modified_atoms,
            center_atom,
            surrounding_atom,
            unique_distances,
            A2_indices=second_center_indices,
            A2_symbol=center_atom_2,
        )
        st.markdown(f"**Distance of {center_atom} - {surrounding_atom} bonds in octahedra**")
        st.dataframe(octahedral_distances, use_container_width=True, hide_index=True)

        functions = distortion_function_map()
        selected: Sequence[tuple[str, Callable[..., Any]]]
        selected = (
            list(functions.items())
            if distortion_type == "all"
            else [(distortion_type, functions[distortion_type])]
        )
        output: list[tuple[str, str]] = []
        for name, function in selected:
            result = function(
                octahedra,
                super_atoms,
                periodic_images,
                b=bond_relaxation,
                A2_indices=second_center_indices,
                A2_symbol=center_atom_2,
            )
            output.extend(_format_distortion_result(name, result, periodic_images))
        st.dataframe(
            pd.DataFrame(output, columns=("Distortion Parameter", "Value")),
            use_container_width=True,
            hide_index=True,
        )
    except Exception as exc:
        st.error(exc)
        st.write(
            """
            If you see an error message `['A_index'] not found in axis`, try increasing
            the bond-distance limit (for example, to 0.5) and octahedron-distortion
            limit (for example, to 0.3). For a double perovskite, also provide the
            second center-atom label under Optional parameters.
            """
        )


def render_percentage_deviation(
    *,
    render_section_header: Callable[..., None],
) -> None:
    render_section_header("Calculate deviation", kicker="Structure Workspace")
    initial_file = st.file_uploader(
        "Upload an initial structure file (AIMS or CIF)",
        type=[".in", ".cif"],
        key="deviation_initial_file",
    )
    final_file = st.file_uploader(
        "Upload a final structure file (AIMS or CIF)",
        type=[".in", ".cif"],
        key="deviation_final_file",
    )
    if initial_file is None or final_file is None:
        return
    initial_atoms, final_atoms, _, _ = process_uploaded_files(initial_file, final_file)
    if initial_atoms is None or final_atoms is None:
        return
    initial = AseAtomsAdaptor.get_structure(initial_atoms)
    final = AseAtomsAdaptor.get_structure(final_atoms)
    table = build_lattice_deviation_table(initial.lattice, final.lattice)
    st.dataframe(table, use_container_width=True, hide_index=True)
