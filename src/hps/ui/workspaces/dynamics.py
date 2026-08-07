"""Dynamics workspace renderers."""

from __future__ import annotations

import base64
import os
import tempfile
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from ase import Atoms

from hps.domain.md_analysis import (
    average_structure_to_cif,
    build_universe_from_dir,
    calculate_ellipsoid_volumes,
    create_probability_distribution_plots_plotly,
    create_variance_dataframe,
    create_violin_plots_plotly,
    get_ADP,
    get_atom_frame_positions_dataframe,
    handle_distance_analysis,
    handle_rdf_analysis,
    hydrogen_bond_analysis,
    plot_atom_volumes_violinplot,
    plot_data,
    plot_hbond_data,
    replace_indices_with_original,
    run_perl_script,
)
from hps.domain.structure_manager import (
    calculate_angle_variance,
    calculate_bond_distance_variance,
    calculate_in_out_planes,
    calculate_unique_ABA_angles,
    filter_atoms_by_symbols_and_extend,
    identify_AB_groups,
)
from hps.io.archives import UnsafeArchiveError, safe_extract_zip
from hps.io.paths import APP_TMP_DIR
from hps.services.backend_client import BackendClientError, get_artifact_content
from hps.ui.backend_workflows import get_workflow_state, named_file_payload, run_workflow


def _workflow_registry():
    if "backend_workflows" not in st.session_state:
        st.session_state.backend_workflows = {}
    return st.session_state.backend_workflows


def _run_backend_workflow(workflow, payload, state_key, *, start=False, poll_timeout=6.0):
    return run_workflow(
        _workflow_registry(), workflow, payload, state_key,
        start=start, poll_timeout=poll_timeout,
    )


def _get_backend_workflow_state(state_key):
    return get_workflow_state(_workflow_registry(), state_key)


def _backend_named_file_payload(uploaded_files):
    return named_file_payload(uploaded_files)

def handle_h_bond_analysis(u):
    donor_atom = st.text_input("Enter donor atom (e.g., O)")
    acceptor_atom = st.text_input("Enter acceptor atom (e.g., Br)")
    da_cutoff = st.number_input("Enter donor-acceptor cutoff", min_value=0.0, max_value=10.0, step=0.1)
    angle_cutoff = st.number_input("Enter angle cutoff", min_value=0, max_value=180, step=1)

    if st.button('Do H-bond analysis'):
        try:
            # st.write("Building universe...")
            # u = build_universe_from_dir('frames_dir', timestep=timestep)
            st.write("Running hydrogen bond analysis...")
            h = hydrogen_bond_analysis(u, donor_atom, acceptor_atom, da_cutoff, angle_cutoff)
            st.write("Plotting hydrogen bond distances...")
            _, _, counts_fig = plot_hbond_data(h, u)

            st.plotly_chart(counts_fig, use_container_width=True)

            # col1, col2, col3 = st.columns(3)
            # Create 2x2 grid using Streamlit's column feature
            # col1, col_space, col2 = st.columns([1, 0.1, 1])
            # # col1, col2 = st.columns(2)
            # col3, col_space, col4 = st.columns([1, 0.1, 1])
            # with col1:
            #     st.plotly_chart(distances_fig)
            # with col2:
            #     st.plotly_chart(counts_fig)
            # with col3:
            #     st.plotly_chart(angles_fig)

        except Exception as e:
            st.write(f"Error: {str(e)}")
    pass




def handle_distortion_analysis(u):
    # User input for atomic symbols
    center_atom = st.text_input('Enter the symbol of the center atom (A):', value="Pb")
    surrounding_atoms = st.text_input('Enter the symbol of the surrounding atoms (B):', value="I")

    with st.expander("Optional parameters"):
        # Experimental
        center_atom_2 = st.text_input(
            'Enter the symbol of a second center atom, if available (useful for double perovskites):', value=None)
        b_parameter = st.number_input("Relax the bond distance limit (useful for chloride-based systems):",
                                      value=0.50)
        c_paramter = st.number_input("Relax the octahedron distortion limit:",
                                     value=0.30)

    step = st.number_input('Enter the step value for skipping frames:', min_value=1, max_value=1000, value=100)

    min_time = 0.0
    max_time = u.trajectory[-1].time

    # Input for time window
    ti_range = st.slider("Select the time range for analysis (ps):",
                         min_value=min_time,
                         max_value=max_time,
                         value=(min_time, max_time),
                         step=0.1)

    start_time = ti_range[0]
    end_time = ti_range[1]

    # Generate atom group with the atom_indices
    atom_group = u.select_atoms(f'name {center_atom} or name {surrounding_atoms}')
    # Add a button to trigger calculations
    if st.button('Do Analysis'):

        progress_bar = st.progress(0,text="Calculating...")

        # Determine the frames to analyze based on step value
        frame_indices = [ts.frame for ts in u.trajectory if start_time <= ts.time <= end_time]
        frames_to_analyze = frame_indices[::step]
        total_frames = len(frames_to_analyze)
        frame_counter = 0

        # Initialize lists to store data for each DataFrame
        results_df1 = []
        bdv_lists = []
        av_lists = []

        # Loop through the trajectory
        for ts in u.trajectory:
            if ts.frame in frames_to_analyze:
                symbols = [atom.name for atom in atom_group]
                positions = atom_group.positions
                atoms = Atoms(symbols=symbols, positions=positions, pbc=True, cell=u.dimensions)
                new_atoms, periodic_image_dict, A2_indices = filter_atoms_by_symbols_and_extend(atoms, center_atom, surrounding_atoms, A2=center_atom_2)
                AB6_octahedra, AB_distances = identify_AB_groups(new_atoms, center_atom, surrounding_atoms, b=b_parameter, c=c_paramter)

                result_angle = calculate_unique_ABA_angles(AB6_octahedra, new_atoms)
                result_iop = calculate_in_out_planes(AB6_octahedra, new_atoms)
                result_bdv = calculate_bond_distance_variance(AB6_octahedra, new_atoms, periodic_image_dict,A2_indices=A2_indices, A2_symbol=center_atom_2)
                result_av = calculate_angle_variance(AB6_octahedra, new_atoms, periodic_image_dict,A2_indices=A2_indices, A2_symbol=center_atom_2)

                # Update progress bar
                frame_counter += 1
                progress = frame_counter / total_frames
                progress_bar.progress(progress,text=f"{int(progress * 100)} % completed")

                # Append data for DataFrame 1
                for i, (angle, atoms) in enumerate(result_angle[0].items()):
                    beta_value = result_angle[1][i]
                    iop_data = result_iop[angle]
                    results_df1.append({
                        'Time': ts.time,
                        'Atoms': atoms,
                        'Angle': angle,
                        'In-Plane': iop_data['in_plane'],
                        'Out-Plane': iop_data['out_plane'],
                        'Beta': beta_value
                    })

                    # Store bond distance and angle variance lists for later processing
                    bdv_lists.append((ts.time, result_bdv))
                    av_lists.append((ts.time, result_av))
        # Finalize progress bar
        progress_bar.empty()

        # Convert to DataFrames
        df1 = pd.DataFrame(results_df1)
        df1_mod = replace_indices_with_original(periodic_image_dict, df1)
        df2 = create_variance_dataframe(bdv_lists)
        df3 = create_variance_dataframe(av_lists)

        # Return the DataFrame
        return df1_mod, df2, df3

def build_universe_and_analyze(timestep):
    st.write("Building universe...")
    u = build_universe_from_dir('frames_dir', timestep=timestep)
    return u


@st.cache_resource(show_spinner="Building MDA universe", ttl=600, max_entries=1)
def create_universe(file_bytes, timestep):
    APP_TMP_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hps-trajectory-", dir=APP_TMP_DIR) as tmpdir:
        safe_extract_zip(BytesIO(file_bytes), Path(tmpdir))
        timestep = timestep / 1000
        return build_universe_from_dir(tmpdir, timestep=timestep)


def _render_backend_download(export, *, label):
    try:
        content, content_type = get_artifact_content(str(export["artifact_id"]))
    except BackendClientError as exc:
        st.error(f"Could not retrieve backend export: {exc}")
        return
    st.download_button(
        label=label,
        data=content,
        file_name=str(export["file_name"]),
        mime=str(export.get("content_type") or content_type),
    )




def render_dynamics_workspace(
    *, MD_option: bool, MDanalysis_option: bool, render_section_header
) -> None:
    if MD_option:
        render_section_header("Analyze AIMS Molecular Dynamics (MD) Output files", kicker="Dynamics Workspace")

        file_buffer_md = st.file_uploader("Upload MD output files", type=[".out"], accept_multiple_files=True,
                                          key="file_buffer_md")

        if file_buffer_md:
            md_parse_result = _run_backend_workflow(
                "md_parse",
                {"files": _backend_named_file_payload(file_buffer_md)},
                "md_parse_outputs",
                start=True,
                poll_timeout=8.0,
            )
            md_parse_state = _get_backend_workflow_state("md_parse_outputs")
            if md_parse_result is None:
                if md_parse_state.get("error"):
                    st.error(f"MD parsing failed: {md_parse_state['error']}")
                else:
                    st.info("MD output parsing is still running in the backend. Re-run shortly if the plots do not appear immediately.")
                st.stop()

            df = pd.DataFrame(md_parse_result["table"], columns=md_parse_result.get("columns"))
            plot_data(df)


            data_export = md_parse_result.get("exports", {}).get("data_csv")
            if data_export:
                _render_backend_download(data_export, label="Download data as CSV")
            else:
                st.download_button(
                    label="Download data as CSV",
                    data=df.to_csv(index=False),
                    file_name="md_output.csv",
                    mime="text/csv",
                )

            # Button to generate files
            if st.button("Generate files"):
                # zip_file, spt_file, movie_file = run_perl_script(file_buffer_md)
                zip_file, spt_file = run_perl_script(file_buffer_md)

                # Provide native download option for zip_file
                with open(zip_file, "rb") as f:
                    zip_data = f.read()
                st.download_button(
                    label=f"Download {zip_file}",
                    data=zip_data,
                    file_name="geometries.zip",
                    mime="application/zip"
                )

                # Remove the files after they have been downloaded
                os.remove(zip_file)
                os.remove(spt_file)
                # os.remove("joined_file.out")
                # os.remove(movie_file)




    if MDanalysis_option:
        render_section_header("Analysis on MD Trajectory", kicker="Dynamics Workspace")
        timestep = st.number_input("Enter timestep in fs (dt)", min_value=0.0, max_value=50.0, step=0.1)
        file_buffer_md = st.file_uploader("Upload zipped directory", type=["zip"], key="file_buffer_zip")


        if file_buffer_md is not None and timestep > 0:

            trajectory_result = _run_backend_workflow(
                "md_trajectory_prepare",
                {
                    "file_name": file_buffer_md.name,
                    "file_bytes_b64": base64.b64encode(file_buffer_md.getvalue()).decode("utf-8"),
                    "timestep_fs": timestep,
                },
                "md_trajectory_prepare",
                start=True,
                poll_timeout=10.0,
            )
            trajectory_state = _get_backend_workflow_state("md_trajectory_prepare")
            if trajectory_result is None:
                if trajectory_state.get("error"):
                    st.error(f"Trajectory validation failed: {trajectory_state['error']}")
                else:
                    st.info("Trajectory validation is still running in the backend.")
                st.stop()
            st.caption(
                f"Validated {trajectory_result['frame_count']} frames "
                f"({trajectory_result['estimated_duration_ps']:.3f} ps estimated duration)."
            )
            trajectory_exports = trajectory_result.get("exports", {})
            if trajectory_exports:
                with st.expander("Trajectory exports"):
                    _render_backend_download(
                        trajectory_exports["metrics_csv"],
                        label="Download frame metrics (CSV)",
                    )
                    _render_backend_download(
                        trajectory_exports["first_frame"],
                        label="Download first structure",
                    )
                    _render_backend_download(
                        trajectory_exports["last_frame"],
                        label="Download last structure",
                    )

            try:
                u = create_universe(file_buffer_md.getvalue(), timestep)
            except UnsafeArchiveError as exc:
                st.error(f"Could not open trajectory archive: {exc}")
                st.stop()

            analysis_type = st.selectbox("Select Analysis Type", ("H-Bond Analysis", "Distance Analysis", "Average Structure", "Distortion Analysis", "Pair Distribution Function","Anisotropic Displacement Parameter"))

            if analysis_type == "H-Bond Analysis":
                handle_h_bond_analysis(u)

            elif analysis_type == "Distance Analysis":
                handle_distance_analysis(u)

            elif analysis_type == "Distortion Analysis":
                try:
                    dist_df1, dist_df2, dist_df3 = handle_distortion_analysis(u)
                    if dist_df1 is not None:
                        with st.expander("Download data"):
                            st.subheader("Bridging Angles and Deviations")
                            st.dataframe(dist_df1, hide_index=True, use_container_width=True)
                            st.subheader("Bond Distance Variance")
                            st.dataframe(dist_df2, hide_index=True, use_container_width=True)
                            st.subheader("Angle Variance")
                            st.dataframe(dist_df3, hide_index=True, use_container_width=True)

                        # Generate plots
                        f1, f2, f3, f4 = create_violin_plots_plotly(dist_df1,
                                                                    dist_df2,
                                                                    dist_df3)
                        f5, f6, f7, f8 = create_probability_distribution_plots_plotly(dist_df1,
                                                                                      dist_df2,
                                                                                      dist_df3,
                                                                                      bin_size=30)

                        # Create a 2x2 grid for plots
                        col1, col2 = st.columns(2)
                        with col1:
                            # st.pyplot(f1)
                            # st.pyplot(f3)
                            st.plotly_chart(f1)
                            st.plotly_chart(f2)
                            st.plotly_chart(f3)
                            st.plotly_chart(f4)

                        with col2:
                            st.plotly_chart(f5)
                            st.plotly_chart(f6)
                            st.plotly_chart(f7)
                            st.plotly_chart(f8)


                except TypeError:
                    pass

                except Exception as e:
                    # st.warning("Click on the analysis button")
                    st.error(e)

            elif analysis_type == "Average Structure":
                start_time = st.number_input("Enter time (ps) to set first frame: ", min_value=0.00, max_value=100.0, step=0.0001)

                if start_time is not None and st.button("Generate Average Structure"):
                    cif_file = average_structure_to_cif(u, start_time)

                    with open(cif_file, "rb") as f:
                        st.download_button(
                            label="Download Average Structure",
                            data=f,
                            file_name="Average_structure.in"
                        )
                    os.remove("Average_structure.in")

            elif analysis_type == "Pair Distribution Function":
                min_time = 0.0
                max_time = u.trajectory[-1].time

                ti_range = st.slider("Select the time range for analysis (ps):",
                                    min_value=min_time,
                                    max_value=max_time,
                                    value=(min_time, max_time),
                                    step=0.1)
                handle_rdf_analysis(u, ti_range)

            elif analysis_type == "Anisotropic Displacement Parameter":
                st.subheader("Analysis of Anisotropic Displacement Parameter")
                start_time = st.number_input("Enter time (ps) to set first frame: ", min_value=0.00, max_value=100.0, step=0.0001)
                start_frame_no = np.round(start_time*1000 / timestep)

                if start_time is not None and st.button("Get ADP values"):
                    atom_frame_pos_df = get_atom_frame_positions_dataframe(u, start_frame_no)
                    ADP_values = get_ADP(u, atom_frame_pos_df)
                    ADP_values_w_vol = calculate_ellipsoid_volumes(ADP_values, ignore_atoms=None)

                    with st.expander("View ADP data"):
                        st.dataframe(ADP_values_w_vol, use_container_width=True, hide_index=True)

                    elp_vol_plot = plot_atom_volumes_violinplot(ADP_values_w_vol)
                    st.plotly_chart(elp_vol_plot, use_container_width=True)
