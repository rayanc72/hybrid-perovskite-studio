"""Molecule-oriented Structure workspace renderers."""

from __future__ import annotations

import io
import os
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from hps.domain.molecule_builder import get_molecule_object
from hps.domain.structure_manager import (
    create_3d_scatter_plot,
    find_closest_partners,
    generate_symmetrized_structure,
    get_crystal_direction,
    get_distance_matrix,
    get_dm_direction,
    normalize_fractional_direction,
    plot_dipole_moment_vectors,
)
from hps.ui.workspaces.structure.analysis.charge import (
    parse_bader_integrated_atomic_properties,
    parse_id_field,
)


def render_molecule_analysis(
    *,
    polarization_option: bool,
    charge_analysis_option: bool,
    com_option: bool,
    dm_option: bool,
    modified_atoms,
    molecules,
    render_section_header,
) -> None:
        if polarization_option:
            render_section_header("Calculated Polarization direction", kicker="Structure Workspace")
            pymatgen_structure = generate_symmetrized_structure(modified_atoms, 0.001,5.0)
            analyzer = SpacegroupAnalyzer(pymatgen_structure)
            structure = analyzer.get_conventional_standard_structure()
            pos_atoms, neg_atoms = [["Pb"], ["I"]]

            # Extract fractional positions
            pos_coords = np.array([site.frac_coords for site in structure if site.species_string in pos_atoms])
            neg_coords = np.array([site.frac_coords for site in structure if site.species_string in neg_atoms])

            if len(pos_coords) == 0 or len(neg_coords) == 0:
                raise ValueError("Specified charged atoms not found in the structure.")

            L = structure.lattice.matrix

            # get cartesian coordinates
            pos_cart = pos_coords @ L
            neg_cart = neg_coords @ L

            dipole_cart = ((pos_cart.mean(axis=0))*2) - neg_cart.mean(axis=0)

            # convert that vector back to fractional
            dipole_frac = np.linalg.solve(L.T, dipole_cart)


            miller_direction = normalize_fractional_direction(dipole_frac)

            st.write(miller_direction)


        if charge_analysis_option:
            render_section_header("Analyze charge differences", kicker="Structure Workspace")

            uploaded = st.file_uploader("Upload Bader charge analysis output (.out)", type=["out", "txt", "dat"])
            if uploaded is not None:
                try:
                    text = uploaded.read().decode("utf-8", errors="ignore")
                    df_all = parse_bader_integrated_atomic_properties(text)
                except Exception as e:
                    st.error(f"Failed to parse file: {e}")
                    st.stop()

                with st.expander("Preview parsed atomic properties", expanded=False):
                    st.dataframe(df_all, use_container_width=True, hide_index=True)

                colA, colB = st.columns(2)
                with colA:
                    ids_a_str = st.text_input(
                        "Atom IDs – Set A",
                        placeholder="e.g., 1, 3, 4 or 5:10",
                        key="charge_ids_A"
                    )
                with colB:
                    ids_b_str = st.text_input(
                        "Atom IDs – Set B",
                        placeholder="e.g., 2, 6:9",
                        key="charge_ids_B"
                    )

                ids_a = parse_id_field(ids_a_str)
                ids_b = parse_id_field(ids_b_str)

                if ids_a or ids_b:
                    # Subset
                    df_a = df_all[df_all["Id"].isin(ids_a)].copy() if ids_a else pd.DataFrame(columns=df_all.columns)
                    df_b = df_all[df_all["Id"].isin(ids_b)].copy() if ids_b else pd.DataFrame(columns=df_all.columns)

                    # Sums and counts
                    sum_a = float(df_a["PartialCharge"].sum()) if not df_a.empty else 0.0
                    sum_b = float(df_b["PartialCharge"].sum()) if not df_b.empty else 0.0
                    n_a = int(len(df_a))
                    n_b = int(len(df_b))

                    # Differences (net and normalized by group size)
                    diff_ab = sum_a - sum_b  # A - B
                    avg_a = (sum_a / n_a) if n_a > 0 else float("nan")
                    avg_b = (sum_b / n_b) if n_b > 0 else float("nan")
                    diff_avg = (avg_a - avg_b) if (n_a > 0 and n_b > 0) else float("nan")

                    # Per-atom view
                    df_a_view = df_a[["Id", "Name", "PartialCharge"]].copy()
                    df_a_view.insert(0, "Set", "A")
                    df_b_view = df_b[["Id", "Name", "PartialCharge"]].copy()
                    df_b_view.insert(0, "Set", "B")
                    df_view = pd.concat([df_a_view, df_b_view], ignore_index=True)

                    # Summary rows (keep original summary table format)
                    summary_rows = pd.DataFrame([
                        {"Set": "A", "Id": "", "Name": "SUM(A)", "PartialCharge": sum_a},
                        {"Set": "B", "Id": "", "Name": "SUM(B)", "PartialCharge": sum_b},
                        {"Set": "A−B", "Id": "", "Name": "DIFF (A − B)", "PartialCharge": diff_ab},
                        {"Set": "A¯", "Id": "", "Name": "MEAN(A)=SUM(A)/N", "PartialCharge": avg_a},
                        {"Set": "B¯", "Id": "", "Name": "MEAN(B)=SUM(B)/N", "PartialCharge": avg_b},
                        {"Set": "Δ¯", "Id": "", "Name": "DIFF MEAN (A − B)", "PartialCharge": diff_avg},
                    ])
                    df_out = pd.concat([df_view, summary_rows], ignore_index=True)

                    # Compact stats table
                    stats = pd.DataFrame([
                        {"Set": "A", "N": n_a, "Sum": sum_a, "Mean": avg_a},
                        {"Set": "B", "N": n_b, "Sum": sum_b, "Mean": avg_b},
                        {"Set": "Diffs", "N": "", "Sum": diff_ab, "Mean": diff_avg},
                    ])

                    st.subheader("Charge summary")
                    st.dataframe(df_out, use_container_width=True, hide_index=True)

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Σ PartialCharge (A)", f"{sum_a:.6f}")
                    c2.metric("Σ PartialCharge (B)", f"{sum_b:.6f}")
                    c3.metric("Δ Net (A − B)", f"{diff_ab:.6f}")

                    c4, c5 = st.columns(2)
                    c4.metric("Mean(A) = ΣA / NA", f"{avg_a:.6f}" if n_a > 0 else "—")
                    c5.metric("Mean(B) = ΣB / NB", f"{avg_b:.6f}" if n_b > 0 else "—")

                    st.metric("Δ Mean (A − B)", f"{diff_avg:.6f}" if (n_a > 0 and n_b > 0) else "—")

                    with st.expander("Group stats (N, Sum, Mean)", expanded=False):
                        st.dataframe(stats, use_container_width=True, hide_index=True)

                    # Download button for the results CSV (per-atom + summaries)
                    csv_bytes = df_out.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Download results as CSV",
                        data=csv_bytes,
                        file_name="charge_difference_results.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("Enter one or both ID sets above to compute charge sums, means, and their differences.")

        if com_option:
            render_section_header("Get center of mass of molecules", kicker="Structure Workspace")
            # scale_choice = st.checkbox("Scaled (Fractional) co-ordinates")
            scale_choice = False
            df_centroids, df_distance_matrix, lattice_vectors, df_merged = get_distance_matrix(modified_atoms, molecules)


            # Print the distances
            st.dataframe(df_merged, use_container_width=True)


            # Generate 3D plot using Plotly
            fig = px.scatter_3d(df_centroids, x='a', y='b', z='c', text=df_centroids.index, color=df_centroids.index,
                                opacity=0.7, hover_name=df_centroids.index)
            fig.update_layout(scene=dict(xaxis_title='a', yaxis_title='b', zaxis_title='c'), title='Centroids 3D Plot',
                              width=600, height=600)

            # Draw the unit cell box
            scaled_lattice_vectors = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
            # Create the centroids and distance matrix plots
            box_vectors = scaled_lattice_vectors if scale_choice else lattice_vectors
            centroids_fig = create_3d_scatter_plot(df_centroids, 'Centroids', box_vectors)
            # distance_matrix_fig = create_3d_scatter_plot(df_distance_matrix, 'Distance Matrix', box_vectors)

            # Use Streamlit column containers to display the plots
            st.plotly_chart(centroids_fig, use_container_width=True)
            # col1, col2 = st.columns(2)
            # with col1:
            #     st.plotly_chart(centroids_fig, use_container_width=True)
            # with col2:
            #     st.plotly_chart(distance_matrix_fig, use_container_width=True)

            # Call the function with the new method
            sym_part = st.button("Search for Symmetric Partners")

            if sym_part:
                try:
                    symmetric_partners = find_closest_partners(df_centroids, lattice_vectors, initial_threshold=1e-3, max_iterations=1000)
                    for key, value in symmetric_partners.items():
                        st.markdown(value)

                except Exception as e:
                    st.error(f"Error: {e}")


            # translations_to_restore_symmetry, symmetry_output = find_translation_to_restore_symmetry(df_centroids,
            #                                                                                          lattice_vectors)
            # st.write("Translations required to restore inversion symmetry:", translations_to_restore_symmetry)
            # for line in symmetry_output:
            #     st.write(line)

            # col1, col2 = st.columns(2)
            # col1.plotly_chart(fig1, use_container_width=True)
            # col2.plotly_chart(fig2, use_container_width=True)

        if dm_option:
            render_section_header("Get dipole moment direction", kicker="Structure Workspace")

            # Gather user inputs for rotation using Streamlit widgets
            all_options = list(range(1, len(molecules) + 1))
            options_with_all = ["Select All"] + all_options

            molecule_indices = st.multiselect(
                "Select molecule indices",
                options=options_with_all,
            )

            # If "Select All" is chosen, override with all indices
            if "Select All" in molecule_indices:
                molecule_indices = all_options

            # ---- Optional charge inputs ----
            use_charges = st.checkbox(
                "Set custom charges to compute dipole magnitude (optional)",
                value=False,
                help="Choose per-element or per-atom input. Unspecified atoms default to 0."
            )

            charge_input_mode = None
            charge_map = {}  # per-element charges, e.g., {'N': +1, 'O': -1}

            if use_charges:
                charge_input_mode = st.radio(
                    "Charge input mode",
                    options=["Per-element (e.g., N: +1, O: -1)", "Per-atom (index, charge)"],
                    index=0,
                    help="Per-atom indices are 1-based within each selected molecule."
                )

                if charge_input_mode.startswith("Per-element"):
                    # Show which elements are present in selected molecules (for convenience)
                    if molecule_indices:
                        selected_atoms = []
                        for i in molecule_indices:
                            selected_atoms.extend(get_molecule_object(modified_atoms, molecules[i - 1]))
                        unique_elements = sorted({str(a.specie) for a in selected_atoms})
                        st.caption(f"Elements in selected molecules: {', '.join(unique_elements)}")

                    charges_text = st.text_area(
                        "Enter per-element charges (one per line, e.g., `N: +1`)",
                        value="",
                        help="Format: ElementSymbol: charge (e.g., H: +0.1)\nUnspecified elements default to 0."
                    )
                    if charges_text.strip():
                        entries = re.split(r"[\n,;]+", charges_text.strip())
                        for entry in entries:
                            m = re.match(r"^\s*([A-Za-z][a-z]?)\s*:\s*([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)\s*$", entry)
                            if m:
                                elem = m.group(1)
                                val = float(m.group(2))
                                charge_map[elem] = val
                            else:
                                st.warning(f"Could not parse charge entry: '{entry.strip()}'")

                else:
                    st.caption(
                        "Provide per-atom charges using GLOBAL 1-based indices (matching the full ASE structure). "
                        "Example:\n1 0.933196\n2 -0.614332\n3 -0.597291"
                    )

                    uploaded_out = st.file_uploader(
                        "Optionally upload a .out file with charge analysis (will auto-extract from the last analysis block)",
                        type=["out"],
                        accept_multiple_files=False
                    )

                    charges_by_global_1b_text = st.text_area(
                        "Or paste index–charge pairs (1-based global indices; whitespace/comma/tab separated per line).",
                        value=""
                    )

                    global_charge_map_1b = {}


                    def _parse_pairs_1b(text: str) -> dict:
                        m = {}
                        for line in re.split(r"[\n;]+", text.strip()):
                            if not line.strip():
                                continue
                            parts = re.split(r"[,\s]+", line.strip())
                            if len(parts) >= 2:
                                try:
                                    idx_1b = int(parts[0])
                                    q = float(parts[1])
                                    if idx_1b < 1 or idx_1b > len(modified_atoms):
                                        st.warning(
                                            f"Global atom index {idx_1b} out of range [1, {len(modified_atoms)}]; skipped.")
                                        continue
                                    m[idx_1b] = q
                                except ValueError:
                                    st.warning(f"Could not parse line: '{line.strip()}'")
                            else:
                                st.warning(f"Incomplete entry (need index and charge): '{line.strip()}'")
                        return m


                    def _parse_out_block_from_bottom(buf) -> dict:
                        """Search from the bottom for the last 'Summary of the per-atom charge analysis:' block and parse it."""
                        try:
                            content = buf.read().decode("utf-8", errors="replace")
                        except Exception:
                            st.error("Failed to read uploaded .out file as UTF-8.")
                            return {}

                        lines = content.splitlines()
                        start = None
                        # scan upward so the FIRST hit is the last block in the file
                        for i in range(len(lines) - 1, -1, -1):
                            if "Summary of the per-atom charge analysis:" in lines[i]:
                                start = i
                                break
                        if start is None:
                            st.warning("No 'Summary of the per-atom charge analysis:' block found in the uploaded file.")
                            return {}

                        charges = {}
                        # parse forward from header; rows look like: "|    1   electrons   charge  l=0 ..."
                        row_re = re.compile(
                            r"^\s*\|\s*(\d+)\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
                        )
                        for line in lines[start + 1:]:
                            if re.match(r"^\s*\|\s*Total\b", line):
                                break
                            m = row_re.match(line)
                            if m:
                                idx_1b = int(m.group(1))
                                charge = float(m.group(3))  # third numeric column is 'charge'
                                if 1 <= idx_1b <= len(modified_atoms):
                                    charges[idx_1b] = charge
                            # tolerate header/blank/separator lines; continue until Total or end
                        if not charges:
                            st.warning("Found the analysis block, but could not parse any per-atom charges.")
                        return charges

                    # Build the 1-based global charge map (upload takes precedence if both given)
                    if uploaded_out is not None:
                        global_charge_map_1b = _parse_out_block_from_bottom(uploaded_out)
                        # Reset file pointer in case you need to re-read elsewhere
                        uploaded_out.seek(0)
                        with st.expander("see extracted charges"):
                            if global_charge_map_1b:
                                rows = []
                                for idx_1b, charge in sorted(global_charge_map_1b.items()):
                                    # ASE atoms are 0-based, so subtract 1
                                    symbol = modified_atoms[idx_1b - 1].symbol
                                    rows.append((idx_1b, symbol, charge))

                                charges_df = pd.DataFrame(rows, columns=["Atom Index (1-based)", "Element", "Charge (e)"])
                                st.subheader("Extracted per-atom charges", divider="gray")
                                st.dataframe(charges_df, hide_index=True, use_container_width=True)
                            else:
                                st.info("No per-atom charges were parsed from the uploaded file.")
                    elif charges_by_global_1b_text.strip():
                        global_charge_map_1b = _parse_pairs_1b(charges_by_global_1b_text.strip())

            # Camera position
            x_pos = st.number_input("Camera X position", value=0.0)
            y_pos = st.number_input("Camera Y position", value=0.0)
            z_pos = st.number_input("Camera Z position", value=0.0)

            if st.button("Get direction"):
                chosen_molecules = [molecules[i - 1] for i in molecule_indices]
                direction_records = []

                for mol_index, mol_atoms in zip(molecule_indices, chosen_molecules):
                    mol_obj = get_molecule_object(modified_atoms, mol_atoms)

                    dipole_moment_debye = None

                    if use_charges:
                        if use_charges and charge_input_mode.startswith("Per-atom") and global_charge_map_1b:
                            # 'mol_atoms' is the list of GLOBAL indices (0-based) for this molecule
                            # Convert to per-atom charges aligned to mol_obj by looking up (gidx + 1)
                            per_atom_charges = [float(global_charge_map_1b.get(gidx + 1, 0.0)) for gidx in mol_atoms]

                            # Optional info for visibility
                            missing = [g for g in mol_atoms if (g + 1) not in global_charge_map_1b]
                            if global_charge_map_1b and missing:
                                st.info(f"[Mol {mol_index}] {len(missing)} atoms had no provided charge; defaulted to 0.0.")

                            dm_vector, dipole_moment_debye, com = get_dm_direction(mol_obj, charges=per_atom_charges)

                        elif charge_input_mode and charge_input_mode.startswith("Per-element") and len(charge_map) > 0:
                            # Per-element charges, default 0 for unspecified elements
                            per_atom_charges = [float(charge_map.get(str(atom.specie), 0.0)) for atom in mol_obj]
                            dm_vector, dipole_moment_debye, com = get_dm_direction(mol_obj, charges=per_atom_charges)

                        else:
                            # Charges requested but none parsed: fall back to direction-only
                            dm_vector, com = get_dm_direction(mol_obj)

                    else:
                        # Original behavior (no charges)
                        dm_vector, com = get_dm_direction(mol_obj)

                    # Crystal direction
                    crystal_dir, fract_com = get_crystal_direction(dm_vector, modified_atoms, com)

                    rec = {
                        'Molecule Index': mol_index,
                        'Center of Mass': com,
                        'Dipole Moment Vector': dm_vector,
                        'Crystal Direction': crystal_dir
                    }
                    if dipole_moment_debye is not None:
                        rec['Dipole Moment (Debye)'] = dipole_moment_debye

                    direction_records.append(rec)

                # DataFrame + display
                direction_df = pd.DataFrame(direction_records)
                st.dataframe(direction_df, hide_index=True, use_container_width=True)

                # Plot
                camera_pos = [x_pos, y_pos, z_pos]
                dm_plot = plot_dipole_moment_vectors(direction_df, modified_atoms, chosen_molecules, camera_pos)
                st.plotly_chart(dm_plot)

                png_buffer = io.BytesIO()

                png_bytes = pio.to_image(dm_plot, format="png", scale=3)  # higher resolution

                png_buffer.write(png_bytes)

                png_buffer.seek(0)

                base_name = os.path.splitext(st.session_state.file_name or "structure")[0]
                st.download_button(
                    label="📥 Download as PNG",
                    data=png_buffer,
                    file_name=f"{base_name}.png",
                    mime="image/png",
                )
