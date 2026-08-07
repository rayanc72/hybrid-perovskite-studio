"""Electronic workspace renderers."""

from __future__ import annotations

import io
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.io as pio
import streamlit as st

from hps.domain.electronic_property import (
    add_pdos_combination_traces,
    build_brillouin_zone_figure,
    calculate_scaling_factors,
    create_absorption_graphs,
    create_dataframe_from_absorption_out_files,
    get_file_uploads,
    get_pdos_combination_labels,
    parse_label_offset_map,
    parse_out_file,
    parse_segment_selection,
    plot_all_bands,
    plot_pdos_streamlit,
    plot_spin_quivers,
    plot_spin_quivers_3D,
    process_files,
    scale_data,
    set_custom_labels,
)
from hps.domain.structure_manager import (
    data_download_links,
    extract_polarization,
    extract_totalenergy,
    plot_pol_figure,
)
from hps.io.paths import APP_TMP_DIR
from hps.ui.backend_workflows import get_workflow_state, named_file_payload, run_workflow


def clear_pdos_results() -> None:
    st.session_state.pdos_table = None
    st.session_state.pdos_figure = None
    st.session_state.pdos_roles = None


def _parse_uploaded_json(uploaded_file):
    if uploaded_file is None:
        return {}
    try:
        return json.loads(uploaded_file.getvalue().decode("utf-8"))
    except Exception as exc:
        st.error(f"Could not read preset file: {exc}")
        return {}


PDOS_COLOR_PREFERENCES_PATH = APP_TMP_DIR / "pdos_trace_colors.json"


def load_pdos_color_preferences():
    if not PDOS_COLOR_PREFERENCES_PATH.exists():
        return {}
    try:
        data = json.loads(PDOS_COLOR_PREFERENCES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        str(trace_name): str(color)
        for trace_name, color in data.items()
        if isinstance(trace_name, str) and isinstance(color, str)
    }


def _save_pdos_color_preferences(trace_colors):
    APP_TMP_DIR.mkdir(exist_ok=True)
    PDOS_COLOR_PREFERENCES_PATH.write_text(
        json.dumps(trace_colors, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _clear_pdos_color_picker_state():
    for key in list(st.session_state.keys()):
        if str(key).startswith("pdos_trace_color_"):
            del st.session_state[key]


def _get_backend_workflow_registry():
    if "backend_workflows" not in st.session_state:
        st.session_state.backend_workflows = {}
    return st.session_state.backend_workflows


def _backend_named_file_payload(uploaded_files):
    return named_file_payload(uploaded_files)


def _run_backend_workflow(workflow, payload, state_key, *, start=False, poll_timeout=6.0):
    return run_workflow(
        _get_backend_workflow_registry(),
        workflow,
        payload,
        state_key,
        start=start,
        poll_timeout=poll_timeout,
    )


def _get_backend_workflow_state(state_key):
    return get_workflow_state(_get_backend_workflow_registry(), state_key)



def render_electronic_workspace(
    *,
    plot_polarization_option: bool,
    plot_pdos_option: bool,
    plot_bs_option: bool,
    plot_spin_option: bool,
    plot_absorption_option: bool,
    render_section_header,
) -> None:
    if plot_polarization_option:
        render_section_header(
            "Polarization Analysis",
            kicker="Electronic Workspace",
            subtitle="Upload all `aims.out` files from the polarization calculation.",
        )

        uploaded_files = st.file_uploader("Upload one or more AIMS output files (.out)", accept_multiple_files=True,
                                          type=".out")

        if uploaded_files:
            # Create an empty DataFrame to store the extracted data
            data = pd.DataFrame(columns=["File", "Parameter", "Px", "Py", "Pz"])

            # Iterate over the uploaded files and collect the parameter values
            file_parameters = {}
            for uploaded_file in uploaded_files:
                parameter = st.number_input(f"Enter the parameter value for {uploaded_file.name}", step=1.0)
                file_parameters[uploaded_file.name] = parameter

            parameter_name = st.text_input("Enter the name of the parameter:")
            parameter_unit = st.text_input("Enter the unit of the parameter:")

            if st.button("Process Files"):
                # Iterate over the uploaded files and update the DataFrame
                for uploaded_file in uploaded_files:
                    file_content = uploaded_file.read().decode("utf-8")
                    parameter = file_parameters[uploaded_file.name]

                    # Extract the polarization values from the file content
                    px, py, pz = extract_polarization(file_content)

                    #Extract the total energy values from the file content
                    Et = extract_totalenergy(file_content)

                    # Append the extracted data to the DataFrame
                    data = data.append({"File": uploaded_file.name, "Parameter": parameter, "Px": px, "Py": py, "Pz": pz, "Et": Et},
                                       ignore_index=True)


            flip_plot = st.checkbox("Flip plot")
            if flip_plot and not data.empty:
                data[["Px", "Py", "Pz"]] *= -1

            if not data.empty:
                data = data.sort_values("Parameter")
                with st.expander("See Datapoints"):
                    st.write(data)
                    csv_link, txt_link, tsv_link = data_download_links(data, 'datapoints')
                    st.markdown(csv_link, unsafe_allow_html=True)
                with st.expander("See Plots"):
                    plot_pol_figure(data, parameter_name, parameter_unit)


                # plot_pol_figure(data, parameter_name, parameter_unit)




                # if exp_option:
        # tab1, tab2, tab3 = st.tabs(["Cat", "Dog", "Owl"])
        #
        # with tab1:
        #     st.header("A cat")
        #     st.image("https://static.streamlit.io/examples/cat.jpg", width=200)
        #
        # with tab2:
        #     st.header("A dog")
        #     st.image("https://static.streamlit.io/examples/dog.jpg", width=200)
        #
        # with tab3:
        #     st.header("An owl")
        #     st.image("https://static.streamlit.io/examples/owl.jpg", width=200)

        # with st.container():
        #     st.write("This is inside the container")
        #
        #     # You can call any Streamlit command, including custom components:
        #     st.bar_chart(np.random.randn(50, 3))
        #
        # st.write("This is outside the container")

    if plot_pdos_option:
        render_section_header(
            "Plot PDOS",
            kicker="Electronic Workspace",
            subtitle='Upload all PDOS data files. To align the energy axis with the bandstructure, optionally provide the energy shift (Fermi level) from the "Band Structure Studio" module.',
        )

        # File uploader for all DOS files
        uploaded_files = st.file_uploader(
            "Upload Total DOS and element DOS files:",
            type=['dat', 'txt'],
            accept_multiple_files=True,
            key=f"pdos_file_uploader_{st.session_state.pdos_file_uploader_key}",
        )
        pdos_file_signature = tuple(file.name for file in uploaded_files or [])
        if pdos_file_signature != st.session_state.pdos_file_signature:
            clear_pdos_results()
            st.session_state.pdos_file_signature = pdos_file_signature

        pdos_payload = {
            "files": _backend_named_file_payload(uploaded_files),
            "combination_text": "",
        }
        pdos_preview_state_key = "electronic_pdos_preview"
        pdos_preview_result = _run_backend_workflow(
            "electronic_pdos",
            pdos_payload,
            pdos_preview_state_key,
            start=bool(uploaded_files),
        )
        preview_state = _get_backend_workflow_state(pdos_preview_state_key)
        roles = pdos_preview_result.get("roles", {"total": [], "projected": [], "unrecognized": []}) if pdos_preview_result else {"total": [], "projected": [], "unrecognized": []}
        if uploaded_files:
            st.markdown("**Detected files**")
            role_messages = []
            if roles["total"]:
                role_messages.append("Total DOS: " + ", ".join(f"`{name}`" for name in roles["total"]))
            if roles["projected"]:
                projected_labels = [
                    f"`{item['name']}` as `{item['element']}`" for item in roles["projected"]
                ]
                role_messages.append("Element DOS: " + ", ".join(projected_labels))
            if roles["unrecognized"]:
                role_messages.append("Ignored: " + ", ".join(f"`{name}`" for name in roles["unrecognized"]))
            for message in role_messages:
                st.caption(message)
        else:
            st.info("Upload `KS_DOS_total.dat` and one or more `*_l_proj_dos.dat` files.")

        pdos_trace_options = []
        pdos_trace_preview_error = None
        if uploaded_files:
            if pdos_preview_result is not None:
                pdos_trace_options = pdos_preview_result.get("trace_options", [])
            elif preview_state.get("error"):
                pdos_trace_preview_error = preview_state["error"]

        st.markdown("**Plot controls**")
        control_col1, control_col2 = st.columns(2)
        with control_col1:
            shift = float(st.number_input("Energy shift (eV):", value=0.00, key="pdos_shift"))
            plot_range = st.slider(
                "Energy range (eV):",
                min_value=-30.0,
                max_value=30.0,
                value=(-2.0, 5.0),
                step=1.0,
                key="pdos_energy_range",
            )
        with control_col2:
            use_dos_range = st.checkbox("Set DOS axis range", value=False, key="pdos_use_dos_range")
            dos_range = None
            if use_dos_range:
                dos_min_col, dos_max_col = st.columns(2)
                with dos_min_col:
                    dos_min = st.number_input("DOS min:", value=0.0, key="pdos_dos_min")
                with dos_max_col:
                    dos_max = st.number_input("DOS max:", value=50.0, key="pdos_dos_max")
                if dos_min < dos_max:
                    dos_range = (dos_min, dos_max)
                else:
                    st.warning("DOS min must be smaller than DOS max.")
            figure_height = st.slider(
                "Figure height:",
                min_value=500,
                max_value=1200,
                value=850,
                step=50,
                key="pdos_figure_height",
            )
            plot_width_choice = st.selectbox(
                "Plot area width:",
                options=["Full", "Wide", "Medium", "Narrow"],
                index=0,
                key="pdos_plot_width_choice",
                on_change=clear_pdos_results,
            )
        smooth_pdos_traces = st.checkbox(
            "Smooth traces",
            value=False,
            key="pdos_smooth_traces",
            on_change=clear_pdos_results,
        )
        smoothing_window = None
        if smooth_pdos_traces:
            smoothing_window = st.slider(
                "Smoothing window:",
                min_value=3,
                max_value=51,
                value=9,
                step=2,
                help="Applies a centered moving average to DOS values while keeping the energy grid unchanged.",
                key="pdos_smoothing_window",
                on_change=clear_pdos_results,
            )
        show_pdos_table = st.checkbox("Show parsed data table", value=True, key="pdos_show_table")
        if pdos_trace_options:
            selected_pdos_traces = st.multiselect(
                "Contributions to plot",
                options=pdos_trace_options,
                default=pdos_trace_options,
                help="Select the parsed total/species/orbital traces to include in the plot.",
                key=f"pdos_selected_traces_{st.session_state.pdos_file_signature}",
            )
        else:
            selected_pdos_traces = []
            if pdos_trace_preview_error:
                st.caption(f"Contribution selection is unavailable: {pdos_trace_preview_error}")
        custom_pdos_combinations = st.text_area(
            "Custom contribution formulas",
            value="",
            placeholder="PbI = Pb(s) + Pb(p) + I\nI without p = I - I(p)",
            help="Use one formula per line. Terms must match parsed table columns, with + or - between terms.",
            key="pdos_custom_combinations",
        )
        pdos_color_defaults = [
            "#000000",
            "#8a2be2",
            "#5f9ea0",
            "#dc143c",
            "#228b22",
            "#ff7f50",
            "#4169e1",
            "#b8860b",
        ]
        custom_pdos_labels = get_pdos_combination_labels(custom_pdos_combinations)
        pdos_color_labels = list(dict.fromkeys([*selected_pdos_traces, *custom_pdos_labels]))
        pdos_trace_colors = {}
        if pdos_color_labels:
            with st.expander("Trace colors"):
                st.caption("Saved colors are reused for matching trace names in later sessions.")
                color_columns = st.columns(2)
                for color_index, trace_name in enumerate(pdos_color_labels):
                    default_color = pdos_color_defaults[color_index % len(pdos_color_defaults)]
                    if trace_name == "Total DOS":
                        default_color = "#000000"
                    default_color = st.session_state.pdos_saved_trace_colors.get(
                        trace_name,
                        default_color,
                    )
                    with color_columns[color_index % 2]:
                        pdos_trace_colors[trace_name] = st.color_picker(
                            trace_name,
                            value=default_color,
                            key=f"pdos_trace_color_{trace_name}",
                        )
                save_color_col, reset_color_col = st.columns(2)
                with save_color_col:
                    if st.button("Save trace colors", key="pdos_save_trace_colors", use_container_width=True):
                        saved_trace_colors = dict(st.session_state.pdos_saved_trace_colors)
                        saved_trace_colors.update(pdos_trace_colors)
                        _save_pdos_color_preferences(saved_trace_colors)
                        st.session_state.pdos_saved_trace_colors = saved_trace_colors
                        st.success("Trace colors saved.")
                with reset_color_col:
                    if st.button("Reset saved colors", key="pdos_reset_trace_colors", use_container_width=True):
                        if PDOS_COLOR_PREFERENCES_PATH.exists():
                            PDOS_COLOR_PREFERENCES_PATH.unlink()
                        st.session_state.pdos_saved_trace_colors = {}
                        _clear_pdos_color_picker_state()
                        st.success("Saved trace colors reset.")
                        st.rerun()
        st.session_state.shift = shift

        # Plot and file-reset controls
        plot_col, clean_col = st.columns(2)
        with plot_col:
            plot_button = st.button("Plot", key="plot_pdos_button", use_container_width=True)
        with clean_col:
            clean_files_button = st.button("Clean files", key="clean_pdos_files_button", use_container_width=True)

        if clean_files_button:
            clear_pdos_results()
            st.session_state.pdos_file_signature = None
            st.session_state.pdos_file_uploader_key += 1
            st.rerun()

        if plot_button:
            if uploaded_files:
                pdos_result = _run_backend_workflow(
                    "electronic_pdos",
                    {
                        "files": _backend_named_file_payload(uploaded_files),
                        "combination_text": custom_pdos_combinations,
                    },
                    "electronic_pdos_plot",
                    start=True,
                )
                pdos_state = _get_backend_workflow_state("electronic_pdos_plot")
                if pdos_result is None:
                    clear_pdos_results()
                    if pdos_state.get("error"):
                        st.error(str(pdos_state["error"]))
                    else:
                        st.info("PDOS parsing is still running in the backend. Re-run the plot action if the figure does not appear immediately.")
                else:
                    try:
                        dos_data = {
                            element: np.asarray(data)
                            for element, data in pdos_result["dos_data"].items()
                        }
                        pdos_table = pd.DataFrame(pdos_result["pdos_table"], columns=pdos_result.get("pdos_columns"))
                        roles = pdos_result["roles"]
                        combination_columns = pdos_result.get("combination_columns", [])
                        fig = plot_pdos_streamlit(
                            dos_data,
                            st.session_state.shift,
                            plot_range,
                            dos_range=dos_range,
                            figure_height=figure_height,
                            selected_trace_names=selected_pdos_traces,
                            trace_colors=pdos_trace_colors,
                            smoothing_window=smoothing_window,
                        )
                        if combination_columns:
                            add_pdos_combination_traces(
                                fig,
                                pdos_table,
                                combination_columns,
                                st.session_state.shift,
                                trace_colors=pdos_trace_colors,
                                smoothing_window=smoothing_window,
                            )

                        if not fig.data:
                            clear_pdos_results()
                            st.warning("Select at least one contribution or add a valid custom formula.")
                        else:
                            st.session_state.pdos_table = pdos_table
                            st.session_state.pdos_figure = fig
                            st.session_state.pdos_roles = roles
                    except Exception as exc:
                        clear_pdos_results()
                        st.error(str(exc))
            else:
                clear_pdos_results()
                st.warning("Upload PDOS files before plotting.")

        if st.session_state.pdos_figure is not None:
            if show_pdos_table and st.session_state.pdos_table is not None:
                st.dataframe(st.session_state.pdos_table, hide_index=True, use_container_width=True)

            if plot_width_choice == "Full":
                st.plotly_chart(st.session_state.pdos_figure, use_container_width=True)
            else:
                width_ratios = {
                    "Wide": [1, 6, 1],
                    "Medium": [1, 4, 1],
                    "Narrow": [2, 3, 2],
                }
                _, plot_area_col, _ = st.columns(width_ratios[plot_width_choice])
                with plot_area_col:
                    st.plotly_chart(st.session_state.pdos_figure, use_container_width=True)
            st.markdown("**Export**")
            csv_data = st.session_state.pdos_table.to_csv(index=False)
            html_data = pio.to_html(
                st.session_state.pdos_figure,
                include_plotlyjs="cdn",
                full_html=True,
            )
            export_col1, export_col2 = st.columns(2)
            with export_col1:
                st.download_button(
                    label="CSV",
                    data=csv_data,
                    file_name="pdos_data.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with export_col2:
                st.download_button(
                    label="HTML",
                    data=html_data,
                    file_name="pdos_plot.html",
                    mime="text/html",
                    use_container_width=True,
                )
            if st.checkbox("Prepare PNG/PDF exports", value=False, key="pdos_prepare_static_exports"):
                try:
                    png_bytes = pio.to_image(st.session_state.pdos_figure, format="png", scale=3)
                    pdf_bytes = pio.to_image(st.session_state.pdos_figure, format="pdf")
                    static_export_col1, static_export_col2 = st.columns(2)
                    with static_export_col1:
                        st.download_button(
                            label="PNG",
                            data=png_bytes,
                            file_name="pdos_plot.png",
                            mime="image/png",
                            use_container_width=True,
                        )
                    with static_export_col2:
                        st.download_button(
                            label="PDF",
                            data=pdf_bytes,
                            file_name="pdos_plot.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                except Exception as exc:
                    st.info(f"PNG/PDF export needs Kaleido: {exc}")

    if plot_bs_option:
        st.markdown(
            """
            <div class="workspace-card">
                <div class="section-kicker">Electronic Workspace</div>
                <div class="workspace-card-title">Band Structure Studio</div>
                <div class="workspace-card-copy">
                    Band plots require <code>band*.out</code>. Brillouin-zone plots require <code>geometry.in</code>, and path labels additionally require <code>control.in</code>.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("**Inputs**")
        num_data_sets = st.number_input(
            "How many plot data sets do you want to provide?",
            min_value=1,
            max_value=10,
            value=1,
        )
        default_colors = ['crimson', 'blue', 'green', 'red', 'cyan', 'magenta', 'yellow', 'black', 'orange', 'purple', 'brown']

        uploaded_files_list, user_defined_colors, user_defined_legends, user_defined_eshifts, dataset_summaries = get_file_uploads(num_data_sets, default_colors)

        if dataset_summaries:
            with st.expander("Loaded Data Sets", expanded=False):
                for start in range(0, len(dataset_summaries), 3):
                    row = dataset_summaries[start:start + 3]
                    columns = st.columns(len(row))
                    for col, summary in zip(columns, row):
                        geometry_status = "Yes" if summary["has_geometry"] else "No"
                        control_status = "Yes" if summary["has_control"] else "No"
                        band_gap_text = f"{summary['band_gap']:.3f} eV" if summary["band_gap"] is not None else "Not detected"
                        vbm_text = (
                            f"State {summary['vbm_state']} @ {summary['vbm_coordinate']}<br>"
                            f"{summary['vbm_energy']:.3f} eV"
                            if summary["vbm_energy"] is not None
                            else "Not detected"
                        )
                        cbm_text = (
                            f"State {summary['cbm_state']} @ {summary['cbm_coordinate']}<br>"
                            f"{summary['cbm_energy']:.3f} eV"
                            if summary["cbm_energy"] is not None
                            else "Not detected"
                        )
                        with col:
                            st.markdown(
                                f"""
                                <div class="workspace-card">
                                    <div class="workspace-card-title">{summary['legend_label']}</div>
                                    <div class="workspace-card-copy">
                                        <strong>Color:</strong> <span style="color:{summary['color']};">{summary['color']}</span><br>
                                        <strong>Band files:</strong> {summary['band_file_count']}<br>
                                        <strong>geometry.in:</strong> {geometry_status}<br>
                                        <strong>control.in:</strong> {control_status}<br>
                                        <strong>VBM:</strong><br>{vbm_text}<br>
                                        <strong>CBM:</strong><br>{cbm_text}<br>
                                        <strong>Band gap:</strong> {band_gap_text}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

        band_tab, bz_tab = st.tabs(["Band Structure", "Brillouin Zone"])

        with band_tab:
            st.markdown("**Plot Settings**")
            plot_range = st.slider(
                "Select plot range for Energy axis (eV):",
                min_value=-10.0,
                max_value=10.0,
                value=(-2.0, 5.0),
                step=0.1,
            )
            ymin, ymax = plot_range

            with st.expander("Advanced"):
                selected_segment_text = st.text_input(
                    "K-path segments to plot (optional)",
                    value="",
                    help="Use one-based segment indices like 1,3,5-6. Leave blank to plot all segments.",
                )
                label_offset_text = st.text_input(
                    "X-axis label offsets (optional)",
                    value="",
                    help="Adjust selected x-axis labels with entries like 2:-0.08, 5:-0.15.",
                )
                apply_scaling = st.checkbox("Scale x-axis to match the first dataset?") if num_data_sets > 1 else False

            plot_button = st.button("Generate Band Structure")

            if uploaded_files_list:
                if plot_button:
                    try:
                        for dataset_index, dataset_files in enumerate(uploaded_files_list):
                            parse_result = _run_backend_workflow(
                                "electronic_band",
                                {
                                    "files": _backend_named_file_payload(dataset_files),
                                    "energy_shift": user_defined_eshifts[dataset_index],
                                },
                                f"electronic_band_{dataset_index}",
                                start=True,
                                poll_timeout=10.0,
                            )
                            parse_state = _get_backend_workflow_state(
                                f"electronic_band_{dataset_index}"
                            )
                            if parse_result is None:
                                raise ValueError(
                                    parse_state.get("error")
                                    or "Band parsing is still running in the backend."
                                )
                        fig, ax = plt.subplots(figsize=(16, 12))
                        plt.rcParams["font.family"] = "Arial"
                        plt.rcParams.update({'font.size': 24})
                        for spine in ['bottom', 'left', 'top', 'right']:
                            ax.spines[spine].set_linewidth(2)

                        selected_segments = parse_segment_selection(selected_segment_text)
                        label_offset_map = parse_label_offset_map(label_offset_text)

                        all_data = process_files(
                            uploaded_files_list,
                            user_defined_colors,
                            user_defined_legends,
                            user_defined_eshifts,
                            selected_segments=selected_segments,
                        )
                        if apply_scaling:
                            scaling_factors = calculate_scaling_factors(all_data)
                            all_data = scale_data(all_data, scaling_factors)

                        plot_all_bands(ax, all_data, apply_scaling, num_data_sets)
                        set_custom_labels(ax, all_data, apply_scaling, num_data_sets, label_offset_map=label_offset_map)

                        plt.ylabel('Energy (eV)')
                        plt.axis([0, max([abs(i) for data in all_data for i in data["xvals"][-1]]), ymin, ymax])
                        if num_data_sets > 1:
                            ax.legend(
                                frameon=True,
                                facecolor='white',
                                edgecolor='lightgray',
                                framealpha=0.95,
                                fontsize=14,
                                loc='upper right',
                                borderpad=0.4,
                                labelspacing=0.3,
                                handlelength=1.6,
                            )
                        plt.tight_layout()
                        st.pyplot(fig)

                        buf = io.BytesIO()
                        fig.savefig(buf, format='png', transparent=True)
                        buf.seek(0)

                        pdf_buf = io.BytesIO()
                        fig.savefig(pdf_buf, format='pdf', transparent=True)
                        pdf_buf.seek(0)
                        st.markdown("**Export**")
                        export_col1, export_col2 = st.columns(2)
                        with export_col1:
                            st.download_button(
                                label="PNG",
                                data=buf,
                                file_name="band_structure.png",
                                mime="application/png",
                                use_container_width=True,
                            )
                        with export_col2:
                            st.download_button(
                                label="PDF",
                                data=pdf_buf,
                                file_name="band_structure.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                            )

                    except ValueError as exc:
                        st.error(str(exc))
            else:
                st.info("Upload at least one dataset above to generate a band-structure plot.")

        with bz_tab:
            if uploaded_files_list:
                st.markdown("**Inputs**")
                bz_dataset_options = [f"Data set {index + 1}" for index in range(len(uploaded_files_list))]
                bz_dataset_label = st.selectbox(
                    "Brillouin-zone dataset",
                    options=bz_dataset_options,
                    index=0,
                    help="Choose which uploaded dataset to use for the Brillouin-zone plot.",
                )
                bz_plot_button = st.button("Generate Brillouin Zone")
                if bz_plot_button:
                    try:
                        bz_index = bz_dataset_options.index(bz_dataset_label)
                        bz_fig = build_brillouin_zone_figure(
                            uploaded_files_list[bz_index],
                            dataset_label=user_defined_legends[bz_index] if bz_index < len(user_defined_legends) else bz_dataset_label,
                        )
                        st.plotly_chart(bz_fig, use_container_width=True)

                        bz_png = pio.to_image(bz_fig, format="png", scale=3)
                        bz_pdf = pio.to_image(bz_fig, format="pdf")
                        st.markdown("**Export**")
                        bz_col1, bz_col2 = st.columns(2)
                        with bz_col1:
                            st.download_button(
                                label="PNG",
                                data=bz_png,
                                file_name="brillouin_zone.png",
                                mime="application/png",
                                use_container_width=True,
                            )
                        with bz_col2:
                            st.download_button(
                                label="PDF",
                                data=bz_pdf,
                                file_name="brillouin_zone.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                            )
                    except ValueError as exc:
                        st.error(str(exc))
            else:
                st.info("Upload a dataset with `geometry.in` to generate a Brillouin-zone plot.")

        remove_button = st.button("Clear files")
        if uploaded_files_list and remove_button:
            st.session_state["file_uploader_key"] += 1
            st.rerun()

    if plot_spin_option:
        render_section_header(
            "Plot Spin Texture",
            kicker="Electronic Workspace",
            subtitle='Upload `spin_texture.dat`. Optionally include `aims.out` to show related band-edge information.',
        )

        # File uploader
        uploaded_file = st.file_uploader("Upload spin_texture.dat", type=['dat'], accept_multiple_files=False)

        # File uploader for .out file
        uploaded_out_file = st.file_uploader("Upload .out file from spin texture calculation (optional)", type=['out'], accept_multiple_files=False)

        if uploaded_out_file is not None:
            uploaded_out_file.seek(0)  # Reset file pointer
            out_df = parse_out_file(uploaded_out_file)
            st.dataframe(out_df, hide_index=True, use_container_width=True)

        if uploaded_file is not None:
            # Get the range of available states
            spin_result = _run_backend_workflow(
                "electronic_spin",
                {"files": _backend_named_file_payload([uploaded_file])},
                "electronic_spin_2d",
                start=True,
                poll_timeout=8.0,
            )
            spin_state = _get_backend_workflow_state("electronic_spin_2d")
            if spin_result is None:
                if spin_state.get("error"):
                    st.error(f"Spin-texture parsing failed: {spin_state['error']}")
                else:
                    st.info("Spin-texture parsing is still running in the backend.")
                st.stop()
            min_state, max_state = spin_result["state_range"]

            # Display the range of available states
            st.markdown(f"Range of available states for spin texture plot: {min_state} to {max_state}")

            # Input for states
            state_input = st.text_input("Enter states (separated by commas, max 8):")

            # Input for energy shift
            shift_e = st.number_input("Enter the energy shift:")

            # Input for k-plane
            k_plane = st.selectbox("k-plane for texture", ['xy', 'yz', 'xz'])

            #Input for spin direction
            spin_direction = st.selectbox("Spin direction", ['x', 'y', 'z'])

            # Scale for the arrows
            scale_param = st.number_input("Scale parameter for the spin arrows (optional)", value=15)

            # Axis range for the texture
            axis_limits = st.text_input("Enter axis limits (xmin, xmax, ymin, ymax):", "")
            # Initialize limits to None
            if axis_limits.strip():
                try:
                    values = axis_limits.split(',')
                    # Ensure there are exactly 4 values or fill missing ones with None
                    x_min, x_max, y_min, y_max = [float(v.strip()) if v.strip() else None for v in values] + [None] * (
                                4 - len(values))
                except ValueError:
                    st.error("Please enter the limits in the correct format: xmin, xmax, ymin, ymax")
            else:
                # Default to None if no input is provided
                x_min, x_max, y_min, y_max = [None] * 4

            # Process the input states
            if state_input:
                states = [int(s.strip()) for s in state_input.split(',') if s.strip().isdigit()]
                states = states[:8]  # Limit to maximum 8 states

                if all(min_state <= state <= max_state for state in states):
                    if st.button("Plot spin texture"):

                        # Create a 2x2 grid of columns
                        cols = st.columns(2)
                        col_index = 0  # To keep track of which column to use

                        for state in states:
                            uploaded_file.seek(0)
                            try:
                                fig = plot_spin_quivers(uploaded_file, state, spin_direction, k_plane, shift_e, scale=scale_param, axis_limits= [x_min, x_max, y_min, y_max])

                                buf = io.BytesIO()
                                fig.savefig(buf, format='pdf', transparent=True)
                                buf.seek(0)

                                # Display plot in the grid
                                with cols[col_index % 2]:
                                    st.markdown(f"### State {state}")
                                    st.pyplot(fig)

                                    st.download_button(
                                        label="Download plot as PDF",
                                        data=buf,
                                        file_name=f"plot_state_{state}.pdf",
                                        mime="application/pdf"
                                    )

                                col_index += 1

                            except Exception as e:
                                st.error(f"An error occurred while plotting: {e}")
                else:
                    st.error("Entered states are out of the available range.")

    if plot_absorption_option:
        render_section_header("Plot absorption spectra", kicker="Electronic Workspace")

        uploaded_abs_files = st.file_uploader("Upload absorption output files", type=['out'], accept_multiple_files=True)
        exponent_y_user = st.checkbox('y-axis logarithmic?')

        if uploaded_abs_files:
            energy, data = create_dataframe_from_absorption_out_files(uploaded_abs_files)
            grid_fig, overlaid_fig = create_absorption_graphs(energy, data, exponent_y_user)
            # Display plots in Streamlit
            st.plotly_chart(grid_fig, use_container_width=True)

            st.plotly_chart(overlaid_fig, use_container_width=True)


def _detect_spin_texture_bundle_files(uploaded_files):
    detected = {
        "spin_texture": None,
        "geometry": None,
        "out": None,
        "preset": None,
    }
    duplicate_types = []
    unclassified_files = []

    for bundle_file in uploaded_files or []:
        name = bundle_file.name.lower()
        file_type = None
        if name.endswith(".json"):
            file_type = "preset"
        elif name.endswith(".out"):
            file_type = "out"
        elif name.endswith(".dat") or "spin_texture" in name:
            file_type = "spin_texture"
        elif name.endswith(".in"):
            file_type = "geometry"

        if file_type is None:
            unclassified_files.append(bundle_file.name)
        elif detected[file_type] is None:
            detected[file_type] = bundle_file
        else:
            duplicate_types.append(bundle_file.name)



def render_spin_texture_3d(*, plot_spin_v2_option: bool, render_section_header) -> None:
    if plot_spin_v2_option:
        render_section_header(
            "Plot 3D Spin Texture",
            kicker="Electronic Workspace",
            subtitle='Upload files in one batch. `spin_texture.dat` is required; `geometry.in`, `aims.out`, and a preset `.json` are optional.',
        )

        uploaded_bundle = st.file_uploader(
            "Upload spin-texture files",
            type=['dat', 'in', 'out', 'json'],
            accept_multiple_files=True,
        )

        detected_files, duplicate_types, unclassified_files = _detect_spin_texture_bundle_files(uploaded_bundle)
        uploaded_file = detected_files["spin_texture"]
        uploaded_geometry_file = detected_files["geometry"]
        uploaded_out_file = detected_files["out"]
        preset_file = detected_files["preset"]

        if uploaded_bundle:
            mapped_files = []
            if uploaded_file is not None:
                mapped_files.append(f"`spin_texture.dat`: {uploaded_file.name}")
            if uploaded_geometry_file is not None:
                mapped_files.append(f"`geometry.in`: {uploaded_geometry_file.name}")
            if uploaded_out_file is not None:
                mapped_files.append(f"`.out` metadata: {uploaded_out_file.name}")
            if preset_file is not None:
                mapped_files.append(f"`preset.json`: {preset_file.name}")
            if mapped_files:
                st.caption("Detected files: " + " | ".join(mapped_files))
            if duplicate_types:
                st.warning("Ignored extra files with duplicate roles: " + ", ".join(duplicate_types))
            if unclassified_files:
                st.warning("Could not classify these files: " + ", ".join(unclassified_files))

        if uploaded_out_file is not None:
            uploaded_out_file.seek(0)
            out_df = parse_out_file(uploaded_out_file)
            st.dataframe(out_df, hide_index=True, use_container_width=True)

        if uploaded_file is not None:
            uploaded_file.seek(0)
            spin_result = _run_backend_workflow(
                "electronic_spin",
                {"files": _backend_named_file_payload([uploaded_file])},
                "electronic_spin_3d",
                start=True,
                poll_timeout=8.0,
            )
            spin_state = _get_backend_workflow_state("electronic_spin_3d")
            if spin_result is None:
                if spin_state.get("error"):
                    st.error(f"Spin-texture parsing failed: {spin_state['error']}")
                else:
                    st.info("Spin-texture parsing is still running in the backend.")
                st.stop()
            min_state, max_state = spin_result["state_range"]

            st.markdown(f"Range of available states for spin texture plot: {min_state} to {max_state}")
            preset_data = _parse_uploaded_json(preset_file)

            state_default = preset_data.get("states", [])
            if isinstance(state_default, list):
                state_default_text = ", ".join(str(state) for state in state_default)
            else:
                state_default_text = ""
            spin_default = preset_data.get("spin_direction", "z")
            plane_default = preset_data.get("plane", "xy")
            colorscale_options = {
                "Red-Blue": "RdBu",
                "Red-Yellow-Blue": "RdYlBu",
                "Spectral": "Spectral",
                "Brown-Green": "BrBG",
                "Portland": "Portland",
                "Picnic": "Picnic",
                "Viridis": "Viridis",
                "Cividis": "Cividis",
                "Turbo": "Turbo",
            }
            colorscale_names = list(colorscale_options.keys())
            colorscale_value_to_label = {value: label for label, value in colorscale_options.items()}
            colorscale_default_label = colorscale_value_to_label.get(preset_data.get("colorscale_name", "RdBu"), "Red-Blue")
            color_mode_options = {
                "Normalized component": "normalized_component",
                "Raw component": "raw_component",
                "Spin magnitude": "magnitude",
            }
            color_mode_labels = list(color_mode_options.keys())
            color_mode_value_to_label = {value: label for label, value in color_mode_options.items()}
            color_mode_default_label = color_mode_value_to_label.get(
                preset_data.get("color_mode", "normalized_component"),
                "Normalized component",
            )

            state_input = st.text_input("Enter states (separated by commas, max 8):", value=state_default_text)
            col0, col1, col2, col3 = st.columns(4)
            with col0:
                plane = st.selectbox(
                    "k-plane for texture",
                    ['xy', 'yz', 'xz'],
                    index=['xy', 'yz', 'xz'].index(plane_default) if plane_default in ['xy', 'yz', 'xz'] else 0,
                )
            with col1:
                spin_direction = st.selectbox(
                    "Spin direction",
                    ['x', 'y', 'z'],
                    index=['x', 'y', 'z'].index(spin_default) if spin_default in ['x', 'y', 'z'] else 2,
                )
            with col2:
                gridsize = st.slider(
                    "Surface grid size",
                    min_value=25,
                    max_value=500,
                    value=int(preset_data.get("gridsize", 250)),
                    step=25,
                )
            with col3:
                state_energy_offset = st.number_input(
                    "Energy offset between states",
                    value=float(preset_data.get("energy_shift_m", 2.0)),
                    step=0.1,
                    format="%.2f",
                )
            control_col1, control_col2, control_col3, control_col4 = st.columns(4)
            with control_col1:
                colorscale_label = st.selectbox(
                    "Colormap",
                    colorscale_names,
                    index=colorscale_names.index(colorscale_default_label),
                )
            with control_col2:
                color_mode_label = st.selectbox(
                    "Surface color mode",
                    color_mode_labels,
                    index=color_mode_labels.index(color_mode_default_label),
                )
            with control_col3:
                text_size = st.slider("Text size", min_value=10, max_value=28, value=int(preset_data.get("text_size", 18)), step=1)
            with control_col4:
                show_background_grid = st.toggle("Show background grid", value=bool(preset_data.get("show_background_grid", True)))
            energy_axis_default = preset_data.get("energy_axis_range")
            if isinstance(energy_axis_default, list) and len(energy_axis_default) == 2:
                energy_axis_default_text = f"{energy_axis_default[0]}, {energy_axis_default[1]}"
            else:
                energy_axis_default_text = ""
            energy_axis_text = st.text_input("Energy axis range (min, max)", value=energy_axis_default_text)

            if state_input:
                states = [int(s.strip()) for s in state_input.split(',') if s.strip().isdigit()]
                states = states[:8]
                preset_opacities = preset_data.get("state_opacities")
                if isinstance(preset_opacities, list) and preset_opacities:
                    default_opacity_text = ", ".join(str(value) for value in preset_opacities)
                else:
                    default_opacity_text = ", ".join(["0.18"] * len(states)) if states else "0.18"
                state_opacity_text = st.text_input(
                    "State opacities (comma-separated, one per selected state)",
                    value=default_opacity_text,
                )

                if all(min_state <= state <= max_state for state in states):
                    try:
                        state_opacities = [float(value.strip()) for value in state_opacity_text.split(",") if value.strip()]
                    except ValueError:
                        st.error("State opacities must be numeric values between 0 and 1.")
                        state_opacities = None

                    if state_opacities is not None:
                        if len(state_opacities) == 1 and len(states) > 1:
                            state_opacities = state_opacities * len(states)
                        elif len(state_opacities) != len(states):
                            st.error("Provide either one opacity value or one value for each selected state.")
                            state_opacities = None

                    if state_opacities is not None and any(opacity < 0 or opacity > 1 for opacity in state_opacities):
                        st.error("Each state opacity must be between 0 and 1.")
                        state_opacities = None

                    energy_axis_range = None
                    if energy_axis_text.strip():
                        try:
                            energy_bounds = [float(value.strip()) for value in energy_axis_text.split(",") if value.strip()]
                            if len(energy_bounds) != 2:
                                st.error("Provide the energy axis range as two comma-separated values: min, max.")
                            elif energy_bounds[0] >= energy_bounds[1]:
                                st.error("Energy axis minimum must be smaller than the maximum.")
                            else:
                                energy_axis_range = energy_bounds
                        except ValueError:
                            st.error("Energy axis range values must be numeric.")

                    current_preset = {
                        "states": states,
                        "plane": plane,
                        "spin_direction": spin_direction,
                        "gridsize": gridsize,
                        "energy_shift_m": state_energy_offset,
                        "state_opacities": state_opacities,
                        "energy_axis_range": energy_axis_range,
                        "colorscale_name": colorscale_options[colorscale_label],
                        "color_mode": color_mode_options[color_mode_label],
                        "text_size": text_size,
                        "show_background_grid": show_background_grid,
                    }

                    if state_opacities is not None and st.button("Plot 3D spin texture"):
                        uploaded_file.seek(0)
                        if uploaded_geometry_file is not None:
                            uploaded_geometry_file.seek(0)
                        try:
                            fig = plot_spin_quivers_3D(
                                uploaded_file,
                                states,
                                spin_direction,
                                plane,
                                geometry_file=uploaded_geometry_file,
                                gridsize=gridsize,
                                energy_shift_m=state_energy_offset,
                                state_opacities=state_opacities,
                                energy_axis_range=energy_axis_range,
                                colorscale_name=colorscale_options[colorscale_label],
                                color_mode=color_mode_options[color_mode_label],
                                text_size=text_size,
                                show_background_grid=show_background_grid,
                                figure_height=1050,
                            )
                            html = pio.to_html(fig, include_plotlyjs="cdn", full_html=True)
                            preset_json = json.dumps(current_preset, indent=2)

                            st.markdown(f"### State {states}")
                            st.plotly_chart(fig, use_container_width=True, theme=None)

                            download_col1, download_col2 = st.columns(2)
                            with download_col1:
                                st.download_button(
                                    label="Download interactive plot as HTML",
                                    data=html,
                                    file_name=f"plot_state_{states}.html",
                                    mime="text/html"
                                )
                            with download_col2:
                                st.download_button(
                                    label="Download view preset",
                                    data=preset_json,
                                    file_name=f"plot_state_{states}_preset.json",
                                    mime="application/json",
                                )

                        except Exception as e:
                            st.error(f"An error occurred while plotting: {e}")
                else:
                    st.error("Entered states are out of the available range.")
