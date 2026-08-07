"""Structure rotation workflow renderer."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from hps.domain.molecule_builder import get_molecule_object
from hps.domain.structure_manager import (
    align_vector_with_plane,
    atoms_to_speck,
    create_aims_download_file,
    create_labelled_download_file,
    create_zip_with_rotated_structures,
    crystal_direction_v3,
    get_dm_direction,
    rotate_molecules_v2,
    rotate_molecules_v3,
    rotate_molecules_v4,
    rotate_molecules_v5,
    rotation_axis_and_angle_from_matrix_v2,
)

ROTATION_TYPES = (
    "Rotate Individual Molecules",
    "Rotate Multiple Molecules",
    "Random Rotation",
    "Interpolate by Rotation",
    "Rotate Part of Molecules",
    "Rotate by Dipole Moment",
)


def render_rotation(
    modified_atoms: Any,
    molecules: list[list[int]],
    file_name: str,
    *,
    render_section_header: Callable[..., None],
) -> Any:
    """Render rotation controls and return the possibly updated structure."""

    render_section_header("Rotation", kicker="Structure Workspace")

    rotate_type = st.selectbox("Select Rotation Type", ROTATION_TYPES)

    if rotate_type == "Rotate Individual Molecules":
        # Gather user inputs for rotation using Streamlit widgets
        molecule_indices = st.multiselect(
            "Select molecule indices", options=range(1, len(molecules) + 1)
        )

        if molecule_indices is not None:
            if "rotation_parameters" not in st.session_state:
                st.session_state.rotation_parameters = [None] * len(molecules)

            for i in molecule_indices:
                st.subheader(f"Molecule {i}")

                with st.form(key=f"molecule_{i}_form"):
                    axis_input = st.text_input(
                        "Enter crystal direction as h, k, l separated by spaces"
                    )

                    angle = st.number_input("Enter rotation angle in degrees", step=1.0)

                    if st.form_submit_button(f"Set Parameters for Molecule {i}"):
                        hkl = np.array([int(val) for val in axis_input.split()])
                        lattice_vectors = modified_atoms.get_cell()
                        axis = np.dot(hkl, lattice_vectors)
                        axis /= np.linalg.norm(axis)

                        st.session_state.rotation_parameters[i - 1] = (axis, angle)

            if st.button("Apply Multiple Rotations"):
                chosen_molecules = [molecules[i - 1] for i in molecule_indices]
                chosen_rotation_parameters = [
                    st.session_state.rotation_parameters[i - 1] for i in molecule_indices
                ]

                for molecule, (axis, angle) in zip(chosen_molecules, chosen_rotation_parameters):
                    modified_atoms = rotate_molecules_v2(modified_atoms, molecule, axis, angle)

                # Save modified atoms to temporary files
                output_suffix = "_rotated"
                file_name = os.path.splitext(st.session_state.file_name)[0]

                create_aims_download_file(modified_atoms, file_name, output_suffix)

                create_labelled_download_file(modified_atoms, file_name, output_suffix)

    if rotate_type == "Rotate Multiple Molecules":
        st.header("Rotate Molecules (Same operation for all chosen molecules)")
        # Gather user inputs for rotation using Streamlit widgets
        molecule_indices = st.multiselect(
            "Select molecule indices", options=range(1, len(molecules) + 1)
        )

        axis_option = st.selectbox(
            "Choose axis option", options=["Cartesian axis", "Crystal direction", "Custom axis"]
        )
        axis_input = None
        if axis_option == "Cartesian axis":
            axis_input = st.selectbox("Select rotation axis", options=["x", "y", "z"])
        elif axis_option == "Crystal direction":
            axis_input = st.text_input("Enter crystal direction as h, k, l separated by spaces")
        elif axis_option == "Custom axis":
            axis_input = st.text_input("Enter custom axis as x, y, z separated by spaces")

        # Add the centroid option selection
        centroid_option = st.selectbox(
            "Choose centroid option",
            options=[("1: Center of mass", 1), ("2: Custom", 2), ("3: Center of unit cell", 3)],
            format_func=lambda o: o[0],
        )[1]

        custom_centroid = None
        if centroid_option == 2:
            custom_centroid = st.text_input("Enter custom centroid as x, y, z separated by spaces")
        angle = st.number_input("Enter rotation angle in degrees", step=1.0)

        if st.button("Apply Rotation") and axis_input:
            if axis_option == "Cartesian axis":
                axis_dict = {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}
                axis = axis_dict[axis_input]
            elif axis_option == "Crystal direction":
                hkl = np.array([int(val) for val in axis_input.split()])
                lattice_vectors = modified_atoms.get_cell()
                axis = np.dot(hkl, lattice_vectors)
                axis /= np.linalg.norm(axis)
            elif axis_option == "Custom axis":
                axis = np.array([float(val) for val in axis_input.split()])

            # Pass custom centroid if centroid_option is 2, otherwise pass None
            custom_centroid = (
                np.array([float(val) for val in custom_centroid.split()])
                if centroid_option == 2
                else None
            )

            modified_atoms = rotate_molecules_v3(
                modified_atoms,
                molecules,
                molecule_indices,
                axis,
                angle,
                centroid_option,
                custom_centroid,
            )

            # Save modified atoms to temporary files
            output_suffix = "_rotated"
            file_name = os.path.splitext(st.session_state.file_name)[0]

            create_aims_download_file(modified_atoms, file_name, output_suffix)

            create_labelled_download_file(modified_atoms, file_name, output_suffix)

        with st.expander("See structure"):
            with st.form(key="structure_viz"):
                if st.form_submit_button("Update Strcuture"):
                    atoms_to_speck(modified_atoms, "rotation")
                else:
                    atoms_to_speck(modified_atoms, "rotation")

    if rotate_type == "Random Rotation":
        st.subheader("Random Rotation")

        mode = st.radio(
            "Choose mode",
            options=["Symmetric Random Rotation", "Asymmetric Random Rotation"],
            horizontal=False,
            index=0,
            key="random_rotation_mode",
        )

        # helpers
        def _random_axis_from_cell(
            cell,
            max_index=3,
            reduce_colinear=True,
            fixed_h=None,
            fixed_k=None,
            fixed_l=None,
        ):
            """
            Pick a random crystal direction with Miller indices in [-max_index, max_index],
            excluding (0,0,0). Optionally fix one or two Miller indices.

            Returns
            -------
            axis : ndarray (3,)
                Unit vector of chosen axis in Cartesian space.
            hkl : (h, k, l) as ints
            """
            low, high = -int(max_index), int(max_index)

            while True:
                # draw randoms, respecting fixed values
                h = fixed_h if fixed_h is not None else np.random.randint(low, high + 1)
                k = fixed_k if fixed_k is not None else np.random.randint(low, high + 1)
                l_index = fixed_l if fixed_l is not None else np.random.randint(low, high + 1)

                # avoid (0,0,0)
                if h == 0 and k == 0 and l_index == 0:
                    continue

                hkl = np.array([h, k, l_index], dtype=int)

                if reduce_colinear:
                    g = np.gcd.reduce(np.abs(hkl))
                    if g > 1:
                        hkl = (hkl // g).astype(int)

                axis = np.dot(hkl, cell)
                n = np.linalg.norm(axis)
                if n > 0:
                    return axis / n, (int(hkl[0]), int(hkl[1]), int(hkl[2]))
                # degenerate (shouldn't happen with valid cells); retry

        def _random_angle():
            return float(np.random.uniform(0.0, 180.0))

        def _log_table_to_df(log_rows):
            import pandas as pd

            # log_rows: list of dicts
            cols = [
                "structure_id",
                "mode",
                "molecule_index",
                "h",
                "k",
                "l",
                "axis_x",
                "axis_y",
                "axis_z",
                "angle_deg",
            ]
            df = pd.DataFrame(log_rows)[cols]
            return df

        lattice_vectors = modified_atoms.get_cell()

        # ---- Axis constraints (optional) ----
        with st.expander("Axis constraints (optional): fix one or two Miller indices"):
            # how many indices to fix?
            fix_choice = st.radio(
                "Do you want to fix one or two Miller indices?",
                options=["No", "Fix one", "Fix two"],
                horizontal=True,
                index=0,
                key="axis_fix_choice",
            )

            # choose which indices to fix
            fixed_h = fixed_k = fixed_l = None
            max_index = st.number_input(
                "Max |index| for random draw (controls range [-N, N])",
                min_value=1,
                max_value=6,
                value=2,
                step=1,
                key="axis_max_index",
            )

            if fix_choice == "Fix one":
                which_one = st.selectbox(
                    "Choose index to fix", ["h", "k", "l"], key="fix_one_which"
                )
                val = st.number_input(
                    "Value",
                    min_value=-max_index,
                    max_value=max_index,
                    value=0,
                    step=1,
                    key="fix_one_val",
                )
                if which_one == "h":
                    fixed_h = int(val)
                elif which_one == "k":
                    fixed_k = int(val)
                else:
                    fixed_l = int(val)

            elif fix_choice == "Fix two":
                which_two = st.multiselect(
                    "Choose two indices to fix",
                    ["h", "k", "l"],
                    max_selections=2,
                    key="fix_two_which",
                )
                if len(which_two) == 2:
                    v1 = st.number_input(
                        f"Value for {which_two[0]}",
                        min_value=-max_index,
                        max_value=max_index,
                        value=0,
                        step=1,
                        key="fix_two_val1",
                    )
                    v2 = st.number_input(
                        f"Value for {which_two[1]}",
                        min_value=-max_index,
                        max_value=max_index,
                        value=0,
                        step=1,
                        key="fix_two_val2",
                    )
                    if "h" in which_two:
                        fixed_h = int(v1 if which_two[0] == "h" else v2)
                    if "k" in which_two:
                        fixed_k = int(v1 if which_two[0] == "k" else v2)
                    if "l" in which_two:
                        fixed_l = int(v1 if which_two[0] == "l" else v2)

        # ---------- Mode-specific selection UIs ----------
        if mode == "Symmetric Random Rotation":
            st.markdown(
                "Define **partner pairs** (two molecule indices per pair). "
                "Assuming input symmetric configuration, each pair receives equal rotations to preserve symmetry."
            )

            if "sym_pairs" not in st.session_state:
                st.session_state.sym_pairs = []

            # Pair builder UI
            with st.form("add_partner_pair_form"):
                st.markdown(
                    "Add a **single pair** manually or **upload a CSV** with two columns of indices."
                )

                c1, c2 = st.columns([1, 1])
                with c1:
                    pair = st.multiselect(
                        "Select exactly two molecule indices to form a partner pair",
                        options=range(1, len(molecules) + 1),
                        max_selections=2,
                        key="sym_pair_builder",
                    )
                with c2:
                    uploaded_csv = st.file_uploader(
                        "Or upload CSV (two columns = indices)",
                        type=["csv"],
                        key="sym_pair_uploader",
                    )
                    csv_has_header = st.checkbox(
                        "CSV has header row", value=True, key="sym_csv_has_header"
                    )

                add_pair = st.form_submit_button("Add Pair(s)")

                if add_pair:
                    new_pairs = []
                    issues = []

                    # 1) From manual selection
                    if len(pair) > 0:
                        if len(pair) != 2:
                            issues.append("Manual selection: please select exactly two indices.")
                        elif pair[0] == pair[1]:
                            issues.append(
                                f"Manual selection: indices must be different (got {pair[0]}, {pair[1]})."
                            )
                        elif not (
                            1 <= pair[0] <= len(molecules) and 1 <= pair[1] <= len(molecules)
                        ):
                            issues.append(
                                f"Manual selection: indices out of range 1..{len(molecules)}."
                            )
                        else:
                            new_pairs.append(tuple(sorted(pair)))

                    # 2) From CSV (optional)
                    if uploaded_csv is not None:
                        try:
                            df = pd.read_csv(uploaded_csv, header=0 if csv_has_header else None)
                            if df.shape[1] < 2:
                                issues.append(
                                    "CSV must have at least two columns (first two are used)."
                                )
                            else:
                                idx_df = df.iloc[:, :2]
                                for i, row in idx_df.iterrows():
                                    a, b = row.iloc[0], row.iloc[1]
                                    # Try to coerce to integers
                                    try:
                                        a = int(a)
                                        b = int(b)
                                    except Exception:
                                        issues.append(
                                            f"Row {i + 1}: values must be integers (got {row.iloc[0]!r}, {row.iloc[1]!r})."
                                        )
                                        continue
                                    # Validate values
                                    if a == b:
                                        issues.append(
                                            f"Row {i + 1}: indices must be different (got {a}, {b})."
                                        )
                                        continue
                                    if not (1 <= a <= len(molecules) and 1 <= b <= len(molecules)):
                                        issues.append(
                                            f"Row {i + 1}: indices out of range 1..{len(molecules)} (got {a}, {b})."
                                        )
                                        continue
                                    new_pairs.append(tuple(sorted((a, b))))
                        except Exception as e:
                            issues.append(f"Failed to read CSV: {e}")

                    # De-duplicate within the submission
                    new_pairs = list(
                        dict.fromkeys(new_pairs)
                    )  # preserves order, removes duplicates

                    # Filter out pairs already present
                    existing = set(st.session_state.sym_pairs)
                    to_add = [p for p in new_pairs if p not in existing]

                    # Report overlaps (not added because already present)
                    already = [p for p in new_pairs if p in existing]

                    # Apply additions
                    if to_add:
                        st.session_state.sym_pairs.extend(to_add)
                        st.success(
                            f"Added {len(to_add)} new pair(s): {', '.join(map(str, to_add))}"
                        )

                    if already:
                        st.info(
                            f"Skipped {len(already)} duplicate pair(s): {', '.join(map(str, already))}"
                        )

                    if issues:
                        st.warning("Some issues were found:\n- " + "\n- ".join(issues))

            # Optional seed
            seed_col1, seed_col2 = st.columns(2)
            with seed_col1:
                use_seed = st.checkbox("Use random seed (optional)")
            with seed_col2:
                seed_val = st.number_input("Seed", value=0, step=1) if use_seed else None
            if use_seed:
                np.random.seed(int(seed_val))

            # How many structures?
            num_structs = st.number_input(
                "How many structures should be generated?",
                min_value=1,
                max_value=32,
                value=1,
                step=1,
            )

            if st.button("Apply Symmetric Random Rotations"):
                if not st.session_state.sym_pairs:
                    st.warning("Add at least one partner pair first.")
                else:
                    import copy
                    import io
                    import tempfile
                    import zipfile

                    from ase.io import write as ase_write

                    base_atoms = modified_atoms  # keep original reference
                    all_logs = []
                    generated_atoms = []
                    used_signatures = set()

                    # Generate num_structs unique sets
                    for s_idx in range(1, int(num_structs) + 1):
                        # Make a working copy of atoms
                        work_atoms = copy.deepcopy(base_atoms)
                        struct_logs = []

                        # Build a uniqueness signature for this set
                        sig_parts = []

                        for a, b in st.session_state.sym_pairs:
                            mol_a = molecules[a - 1]
                            mol_b = molecules[b - 1]

                            axis, hkl = _random_axis_from_cell(
                                lattice_vectors,
                                max_index=max_index,
                                reduce_colinear=True,
                                fixed_h=fixed_h,
                                fixed_k=fixed_k,
                                fixed_l=fixed_l,
                            )
                            angle = _random_angle()

                            # signature part (rounded angle avoids float jitter)
                            sig_parts.append((tuple(sorted((a, b))), hkl, round(angle, 3)))

                            # Apply +θ to first, −θ to second
                            work_atoms = rotate_molecules_v2(work_atoms, mol_a, axis, angle)
                            work_atoms = rotate_molecules_v2(work_atoms, mol_b, axis, angle)

                            # log both applications
                            struct_logs.append(
                                {
                                    "structure_id": s_idx,
                                    "mode": "symmetric",
                                    "molecule_index": a,
                                    "h": hkl[0],
                                    "k": hkl[1],
                                    "l": hkl[2],
                                    "axis_x": float(axis[0]),
                                    "axis_y": float(axis[1]),
                                    "axis_z": float(axis[2]),
                                    "angle_deg": float(angle),
                                }
                            )
                            struct_logs.append(
                                {
                                    "structure_id": s_idx,
                                    "mode": "symmetric",
                                    "molecule_index": b,
                                    "h": hkl[0],
                                    "k": hkl[1],
                                    "l": hkl[2],
                                    "axis_x": float(axis[0]),
                                    "axis_y": float(axis[1]),
                                    "axis_z": float(axis[2]),
                                    "angle_deg": float(angle),
                                }
                            )

                        sig = tuple(sig_parts)
                        # (Practically always unique; retry would require a loop. Here we accept near-certain uniqueness.)
                        used_signatures.add(sig)

                        generated_atoms.append(work_atoms)
                        all_logs.extend(struct_logs)

                    # Show logs in a table
                    df = _log_table_to_df(all_logs)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    file_name = os.path.splitext(st.session_state.file_name)[0]

                    if int(num_structs) == 1:
                        # Single file output via your helper, preserve prior suffix style
                        output_suffix = "_rand_sym"
                        create_aims_download_file(generated_atoms[0], file_name, output_suffix)
                        st.success("Symmetric random rotation applied and file generated.")
                    else:
                        # Batch ZIP
                        buf = io.BytesIO()
                        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                            for s_idx, atoms_obj in enumerate(generated_atoms, start=1):
                                fname = f"{file_name}_rand_sym_{s_idx:02d}.in"
                                tmp_path = os.path.join(tempfile.gettempdir(), fname)
                                ase_write(tmp_path, atoms_obj, format="aims")
                                zf.write(tmp_path, arcname=fname)
                        buf.seek(0)
                        st.download_button(
                            "Download ZIP of symmetric random-rotated structures",
                            data=buf,
                            file_name=f"{file_name}_rand_sym_batch.zip",
                            mime="application/zip",
                        )
                        st.success(
                            f"Generated {int(num_structs)} symmetric random-rotated structures."
                        )

        elif mode == "Asymmetric Random Rotation":
            st.markdown("Select any molecules; each gets its **own** random axis and angle.")

            target_indices = st.multiselect(
                "Select molecule indices for asymmetric random rotation",
                options=range(1, len(molecules) + 1),
                key="pure_random_indices",
            )

            # Optional seed
            seed_col1, seed_col2 = st.columns(2)
            with seed_col1:
                use_seed = st.checkbox("Use random seed (optional)", key="pure_use_seed")
            with seed_col2:
                seed_val = (
                    st.number_input("Seed", value=0, step=1, key="pure_seed_val")
                    if use_seed
                    else None
                )
            if use_seed:
                np.random.seed(int(seed_val))

            # How many structures?
            num_structs = st.number_input(
                "How many structures should be generated?",
                min_value=1,
                max_value=32,
                value=1,
                step=1,
                key="pure_num_structs",
            )

            if st.button("Apply Asymmetric Random Rotations"):
                if not target_indices:
                    st.warning("Please select at least one molecule.")
                else:
                    import copy
                    import io
                    import tempfile
                    import zipfile

                    from ase.io import write as ase_write

                    base_atoms = modified_atoms
                    all_logs = []
                    generated_atoms = []
                    used_signatures = set()

                    for s_idx in range(1, int(num_structs) + 1):
                        work_atoms = copy.deepcopy(base_atoms)
                        struct_logs = []
                        sig_parts = []

                        for idx in target_indices:
                            molecule = molecules[idx - 1]
                            axis, hkl = _random_axis_from_cell(
                                lattice_vectors,
                                max_index=max_index,
                                reduce_colinear=True,
                                fixed_h=fixed_h,
                                fixed_k=fixed_k,
                                fixed_l=fixed_l,
                            )
                            angle = _random_angle()
                            work_atoms = rotate_molecules_v2(work_atoms, molecule, axis, angle)

                            struct_logs.append(
                                {
                                    "structure_id": s_idx,
                                    "mode": "asym",
                                    "molecule_index": idx,
                                    "h": hkl[0],
                                    "k": hkl[1],
                                    "l": hkl[2],
                                    "axis_x": float(axis[0]),
                                    "axis_y": float(axis[1]),
                                    "axis_z": float(axis[2]),
                                    "angle_deg": float(angle),
                                }
                            )

                            # uniqueness signature component
                            sig_parts.append((idx, hkl, round(angle, 3)))

                        sig = tuple(sorted(sig_parts, key=lambda x: x[0]))
                        used_signatures.add(sig)

                        generated_atoms.append(work_atoms)
                        all_logs.extend(struct_logs)

                    # Show logs in a table
                    df = _log_table_to_df(all_logs)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    file_name = os.path.splitext(st.session_state.file_name)[0]

                    if int(num_structs) == 1:
                        output_suffix = "_rand_pure"
                        create_aims_download_file(generated_atoms[0], file_name, output_suffix)
                        st.success("Asymmetric random rotations applied and file generated.")
                    else:
                        buf = io.BytesIO()
                        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                            for s_idx, atoms_obj in enumerate(generated_atoms, start=1):
                                fname = f"{file_name}_rand_pure_{s_idx:02d}.in"
                                tmp_path = os.path.join(tempfile.gettempdir(), fname)
                                ase_write(tmp_path, atoms_obj, format="aims")
                                zf.write(tmp_path, arcname=fname)
                        buf.seek(0)
                        st.download_button(
                            "Download ZIP of pure random-rotated structures",
                            data=buf,
                            file_name=f"{file_name}_rand_asym_batch.zip",
                            mime="application/zip",
                        )
                        st.success(
                            f"Generated {int(num_structs)} asymmetric random-rotated structures."
                        )

    if rotate_type == "Interpolate by Rotation":
        st.header("Create a Series of Structures")

        # Gather user inputs for rotation using Streamlit widgets
        molecule_indices = st.multiselect(
            "Select molecule indices", options=range(1, len(molecules) + 1)
        )

        if molecule_indices is not None:
            if "rotation_parameters" not in st.session_state:
                st.session_state.rotation_parameters = [None] * len(molecules)

            angle_range = st.slider(
                "Enter rotation angle range (min, max) in degrees",
                min_value=0,
                max_value=360,
                value=(0, 180),
            )
            num_structures = st.number_input(
                "Enter the number of structures to generate",
                min_value=2,
                value=2,
                step=1,
            )

            for i in molecule_indices:
                st.subheader(f"Molecule {i}")

                with st.form(key=f"molecule_{i}_form"):
                    axis_input = st.text_input(
                        "Enter crystal direction as h, k, l separated by spaces"
                    )

                    if st.form_submit_button(f"Set Parameters for Molecule {i}"):
                        hkl = np.array([int(val) for val in axis_input.split()])
                        lattice_vectors = modified_atoms.get_cell()
                        axis = np.dot(hkl, lattice_vectors)
                        axis /= np.linalg.norm(axis)

                        st.session_state.rotation_parameters[i - 1] = axis

            if st.button("Apply Multiple Rotations"):
                chosen_molecules = [molecules[i - 1] for i in molecule_indices]
                chosen_rotation_axes = [
                    st.session_state.rotation_parameters[i - 1] for i in molecule_indices
                ]

                angle_step = (angle_range[1] - angle_range[0]) / (num_structures - 1)
                rotation_angles = [angle_range[0] + angle_step * i for i in range(num_structures)]

                rotated_structures_list = []

                for angle in rotation_angles:
                    temp_atoms = modified_atoms.copy()
                    for molecule, axis in zip(chosen_molecules, chosen_rotation_axes):
                        temp_atoms = rotate_molecules_v2(temp_atoms, molecule, axis, angle)
                    rotated_structures_list.append((temp_atoms, angle))

                file_name = os.path.splitext(st.session_state.file_name)[0]

                create_zip_with_rotated_structures(rotated_structures_list, file_name)

    if rotate_type == "Rotate Part of Molecules":
        st.header("Rotate Atoms in Molecule")

        # Gather user inputs for rotation using Streamlit widgets
        # molecules is a list of lists where each list contains indices from the atoms object that define a molecule
        molecule_indices = st.multiselect(
            "Select molecule indices", options=range(1, len(molecules) + 1)
        )

        if "rotation_parameters" not in st.session_state:
            st.session_state.rotation_parameters = [None] * len(molecules)
        if molecule_indices is not None:
            for i in molecule_indices:
                st.subheader(f"Molecule {i}")

                with st.form(key=f"molecule_{i}_form"):
                    atoms_to_rotate = st.multiselect(
                        "Enter the atom indices that require rotation",
                        options=[idx + 1 for idx in molecules[i - 1]],
                    )

                    axis_input = st.text_input(
                        "Enter crystal direction as h, k, l separated by spaces"
                    )

                    pivot_point = st.selectbox(
                        "Select the pivot point atom", options=[idx + 1 for idx in molecules[i - 1]]
                    )
                    angle = st.number_input("Enter rotation angle in degrees", step=1.0)

                    if st.form_submit_button(f"Set Parameters for Molecule {i}"):
                        hkl = np.array([int(val) for val in axis_input.split()])
                        lattice_vectors = modified_atoms.get_cell()
                        axis = np.dot(hkl, lattice_vectors)
                        axis /= np.linalg.norm(axis)

                        atoms_to_rotate_indices = [
                            molecules[i - 1].index(atom - 1) for atom in atoms_to_rotate
                        ]
                        pivot_point_index = molecules[i - 1].index(pivot_point - 1)

                        st.session_state.rotation_parameters[i - 1] = (
                            atoms_to_rotate_indices,
                            axis,
                            pivot_point_index,
                            angle,
                        )

        if st.button("Apply Rotations"):
            chosen_molecules = [molecules[i - 1] for i in molecule_indices]
            chosen_rotation_parameters = [
                st.session_state.rotation_parameters[i - 1] for i in molecule_indices
            ]

            for molecule, (atoms_to_rotate_indices, axis, pivot_point_index, angle) in zip(
                chosen_molecules, chosen_rotation_parameters
            ):
                modified_atoms = rotate_molecules_v5(
                    modified_atoms,
                    molecule,
                    axis,
                    angle,
                    pivot_point_index,
                    atoms_to_rotate_indices,
                )

            # Save modified atoms to temporary files
            output_suffix = "_rotated_some_atoms"
            file_name = os.path.splitext(st.session_state.file_name)[0]

            create_aims_download_file(modified_atoms, file_name, output_suffix)

            create_labelled_download_file(modified_atoms, file_name, output_suffix)

    if rotate_type == "Rotate by Dipole Moment":
        # This option aligns a molecule's dipole moment to a chosen crystal plane by rotating the molecule around its centroid
        st.header("Rotate Molecules to align with planes")

        # Gather user inputs for rotation using Streamlit widgets
        molecule_indices = st.multiselect(
            "Select molecule indices", options=range(1, len(molecules) + 1)
        )

        if molecule_indices is not None:
            if "alignment_planes" not in st.session_state:
                st.session_state.alignment_planes = [None] * len(molecules)

            for i in molecule_indices:
                st.subheader(f"Molecule {i}")

                with st.form(key=f"molecule_{i}_alg_form"):
                    plane_input = st.text_input(
                        "Enter crystal plane as h, k, l separated by spaces"
                    )

                    if st.form_submit_button(f"Set Parameters for Molecule {i}"):
                        hkl = np.array([int(val) for val in plane_input.split()])
                        st.session_state.alignment_planes[i - 1] = hkl

            if st.button("Apply Alignments"):
                chosen_molecules = [molecules[i - 1] for i in molecule_indices]
                chosen_alignment_planes = [
                    st.session_state.alignment_planes[i - 1] for i in molecule_indices
                ]
                lattice_vectors = modified_atoms.get_cell()

                for molecule, miller_indices in zip(chosen_molecules, chosen_alignment_planes):
                    # calculate the dm
                    mol_obj = get_molecule_object(modified_atoms, molecule)
                    dm_vector, com = get_dm_direction(mol_obj)
                    # get the rotation matrix
                    rot_mat = align_vector_with_plane(dm_vector, lattice_vectors, miller_indices)
                    # get the axis
                    rot_ax, rot_ang = rotation_axis_and_angle_from_matrix_v2(rot_mat)
                    rot_ax_cr = crystal_direction_v3(rot_ax, lattice_vectors)
                    st.write(rot_ax_cr)
                    # supply it to the rotate_molecules
                    modified_atoms = rotate_molecules_v4(modified_atoms, molecule, mol_obj, rot_mat)

                # Save modified atoms to temporary files
                output_suffix = "_rotated_aligned"
                file_name = os.path.splitext(st.session_state.file_name)[0]

                create_aims_download_file(modified_atoms, file_name, output_suffix)

                create_labelled_download_file(modified_atoms, file_name, output_suffix)

    return modified_atoms
