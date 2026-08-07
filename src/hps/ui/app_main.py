import io
import json
import tempfile
from io import BytesIO
import numpy as np
import pandas as pd

from ase import Atoms
from hps.core.expressions import evaluate_math_expression
from hps.domain.electronic_property import (
    add_pdos_combination_traces,
    build_brillouin_zone_figure,
    calculate_scaling_factors,
    create_absorption_graphs,
    create_dataframe_from_absorption_out_files,
    get_file_uploads,
    get_pdos_combination_labels,
    get_state_range,
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
from hps.domain.molecule_builder import get_molecule_object
from hps.domain.structure_manager import (
    calculate_angle_variance,
    calculate_bond_distance_variance,
    calculate_in_out_planes,
    calculate_unique_ABA_angles,
    create_3d_scatter_plot,
    data_download_links,
    extract_polarization,
    extract_totalenergy,
    filter_atoms_by_symbols_and_extend,
    find_closest_partners,
    generate_symmetrized_structure,
    get_crystal_direction,
    get_distance_matrix,
    get_dm_direction,
    identify_AB_groups,
    normalize_fractional_direction,
    plot_dipole_moment_vectors,
    plot_pol_figure,
)
from hps.io.archives import UnsafeArchiveError, safe_extract_zip
from hps.io.paths import APP_TMP_DIR
from hps.ui.backend_workflows import (
    get_workflow_state,
    named_file_payload,
    run_workflow,
)
from hps.ui.workspaces.structure.overview import (
    render_current_structure_card,
    render_structure_upload_panel,
)
from hps.ui.workspaces.structure.navigation import render_structure_navigation
from hps.ui.workspaces.structure.analysis.charge import (
    parse_bader_integrated_atomic_properties,
    parse_id_field,
)
from hps.ui.workspaces.structure.analysis.metrics import (
    render_adp_table,
    render_atomic_distances,
    render_distortions,
    render_percentage_deviation,
)
from hps.ui.workspaces.structure.analysis.pdf import render_pdf_analysis
from hps.ui.workspaces.structure.analysis.pxrd import render_pxrd_analysis
from hps.ui.workspaces.structure.analysis.symmetry import render_symmetry_analysis
from hps.ui.workspaces.structure.transformations.operations import (
    render_deletion,
    render_interpolation,
    render_labelling,
    render_reflection,
    render_translation,
)
from hps.ui.workspaces.structure.transformations.rotation import render_rotation
from hps.ui.workspaces.structure.state import (
    initialize_state as initialize_structure_workspace_state,
    load_active_structure,
)
from hps.ui.navigation import (
    build_feature_tree,
    render_tree_lines,
    tool_options,
    view_names,
    workspace_descriptions,
    workspace_names,
)

def _debug_log(message):
    APP_TMP_DIR.mkdir(exist_ok=True)
    with open(APP_TMP_DIR / "upload_debug.log", "a", encoding="utf-8") as fh:
        fh.write(f"{message}\n")


def _parse_uploaded_json(uploaded_file):
    if uploaded_file is None:
        return {}
    try:
        return json.loads(uploaded_file.getvalue().decode("utf-8"))
    except Exception as exc:
        st.error(f"Could not read preset file: {exc}")
        return {}


PDOS_COLOR_PREFERENCES_PATH = APP_TMP_DIR / "pdos_trace_colors.json"


def _load_pdos_color_preferences():
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

    return detected, duplicate_types, unclassified_files


_debug_log("startup: entered hps.ui.app_main")


_debug_log("startup: loaded explicit packaged dependencies")

import plotly.express as px
import plotly.io as pio
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
import streamlit as st
import os
import shutil
from pathlib import Path
# from streamlit_ketcher import st_ketcher
from streamlit_extras.jupyterlite import jupyterlite
import matplotlib as mpl
import matplotlib.pyplot as plt
# from scipy.optimize import minimize
# from scipy.stats import pearsonr
# import tempfile
# from ase import Atoms
# from pathlib import Path
# from diffpy.srreal.structureadapter import loadStructure
# from diffpy.srreal.pdfcalculator import DebyePDFCalculator
# from pymatgen.io.cif import CifWriter
mpl.rcParams['pdf.fonttype'] = 42
mpl.rcParams['ps.fonttype'] = 42
mpl.rcParams["font.family"] = "Arial"


def render_section_header(title, kicker=None, subtitle=None):
    kicker_html = f'<div class="section-kicker">{kicker}</div>' if kicker else ""
    subtitle_html = f'<div class="workspace-card-copy">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="workspace-card">
            {kicker_html}
            <div class="workspace-card-title">{title}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

st.set_page_config(page_title="Hybrid Perovskite Studio", layout="wide")
_debug_log("startup: page config set")

st.markdown(
    """
    <div class="app-brand-wrap">
        <div class="app-brand-title">Hybrid <span>Perovskite Studio</span></div>
        <div class="app-brand-subtitle">
            Analyze, transform, and visualize hybrid perovskite structures and simulation outputs in one workspace.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
_debug_log("startup: title rendered")

# st.divider()
# st.latex(r'''\rm Download\; a\;  structure\;  file\;  from\;  HybriD^3:''')
# with st.expander("Expand for options"):
#
#     col1, col2, col3 = st.columns([3,0.5,3])


    # conn = st.connection("1107_dump", type="sql", autocommit=True) ## Updated database on 08/28/2024
    # systems = conn.query("select * from materials_system")
    #
    # # Taking user input for the search string, system ID, and dataset ID
    # user_input = st.text_input("Enter search string (e.g., BA2PbI4):")
    # system_id = st.text_input("Enter system ID:")
    # dataset_id = st.text_input("Enter dataset ID:")
    #
    # structure_file_path = None
    #
    # if dataset_id:  # If dataset ID is provided, it takes precedence
    #     try:
    #         zip_url = f"https://materials.hybrid3.duke.edu/materials/datasets/{dataset_id}/files"
    #         response = requests.get(zip_url, stream=True)
    #         response.raise_for_status()
    #
    #         # Writing the zip file to a temporary location and allowing the user to download
    #         zip_data = response.content
    #         file_content, file_extension = extract_structure_file(zip_data)
    #         if file_content:
    #             # Use st.download_button to allow the user to download the file
    #             st.download_button(
    #                 label=f"Download {dataset_id}{file_extension}",
    #                 data=file_content,
    #                 file_name=f"{dataset_id}{file_extension}",
    #                 mime=f"text/{file_extension[1:]}"  # assuming mime type to be text/in or text/cif
    #             )
    #
    #
    #     except requests.exceptions.RequestException as err:
    #         st.write(f"Error fetching dataset: {err}")
    #
    #
    # elif system_id:  # Next priority is system ID
    #
    #     try:
    #
    #         matched_df = systems[systems['id'] == int(system_id)][['id', 'compound_name', 'formula']]
    #
    #         if not matched_df.empty:
    #
    #             st.write(f"Information for ID '{system_id}':")
    #
    #             st.dataframe(matched_df, hide_index=True, use_container_width=True)
    #
    #             dataset_results = fetch_materials_datasets(conn, int(system_id))
    #
    #             # Safely format the list of integers for the SQL query
    #
    #             ref_ids = dataset_results['reference_id'].tolist()
    #
    #             ref_ids_string = ','.join(
    #                 map(str, ref_ids))  # Converts each id to a string and then joins them with commas
    #
    #             # Formulate the SQL query with the ref_ids_string
    #
    #             reference_query = f"SELECT `id`,`title`, `year`, `doi_isbn` FROM materials_reference WHERE `id` IN ({ref_ids_string})"
    #
    #             reference_data = conn.query(reference_query)
    #
    #             # Convert the result to a DataFrame
    #
    #             reference_df = pd.DataFrame(reference_data, columns=['id', 'title', 'year', 'doi_isbn'])
    #             reference_df.rename(columns={'id': 'reference_id'}, inplace=True)
    #
    #
    #             # Merge the dataframes on 'reference_id'
    #
    #             merged_results = pd.merge(dataset_results, reference_df, on='reference_id',
    #                                       how='left')
    #
    #
    #             st.write("Associated structure datasets with DOIs:")
    #
    #             st.dataframe(merged_results[['id', 'space_group', 'title', 'year', 'doi_isbn']], hide_index=True,
    #                          use_container_width=True)
    #
    #         else:
    #
    #             st.write(f"No results found for ID '{system_id}'.")
    #
    #     except ValueError:
    #
    #         st.write("Please enter a valid ID.")
    # elif user_input:  # Only check for search string if ID is not provided
    #     matched_ids = search_database(systems, user_input)
    #     matched_df = systems[systems['id'].isin(matched_ids)][['id', 'compound_name', 'formula']]
    #
    #     # Initiate a column in matched_df "Structure exists" with values "No"
    #     matched_df['Structure exists'] = 'No'
    #
    #     # for each id in matched_df run fetch_materials_datasets to get results. If result is not empty, update the "Structure exists" value to "Yes"
    #     for index, row in matched_df.iterrows():
    #         # Fetch materials datasets using the provided ID and check if any data exists
    #         result = fetch_materials_datasets(conn, row['id'])
    #         # If the result is not empty, update the "Structure exists" column for this row to "Yes"
    #         if not result.empty:
    #             matched_df.at[index, 'Structure exists'] = 'Yes'
    #
    #     st.write(f"Information for matched IDs with '{user_input}':")
    #     st.dataframe(matched_df, hide_index=True, use_container_width=True)



current_atoms = None
current_molecules = None
current_modified_symbols = None

initialize_structure_workspace_state(st.session_state)
if "pdos_file_uploader_key" not in st.session_state:
    st.session_state.pdos_file_uploader_key = 0
if "pdos_table" not in st.session_state:
    st.session_state.pdos_table = None
if "pdos_figure" not in st.session_state:
    st.session_state.pdos_figure = None
if "pdos_roles" not in st.session_state:
    st.session_state.pdos_roles = None
if "pdos_file_signature" not in st.session_state:
    st.session_state.pdos_file_signature = None
if "pdos_saved_trace_colors" not in st.session_state:
    st.session_state.pdos_saved_trace_colors = _load_pdos_color_preferences()
symmetry_option = False
com_option = False
dm_option = False
polarization_option = False
distance_option = False
distortion_option = False
deviation_calculation_option = False
ADP_table_option = False
PXRD_option = False
PDF_option = False
PDF_workflow = None
charge_analysis_option = False
rotate_option = False
reflect_option = False
translation_option = False
delete_option = False
labelling_option = False
interpolate_option = False
plot_polarization_option = False
plot_pdos_option = False
plot_bs_option = False
plot_spin_option = False
plot_spin_v2_option = False
plot_absorption_option = False
MD_option = False
MDanalysis_option = False
script_option = False
xy_plot_option = False

workspace_descriptions = workspace_descriptions()
workspace_tree = build_feature_tree()

st.markdown(
    """
    <style>
    :root {
        --hp-bg-soft: #f5f8f9;
        --hp-surface: rgba(255, 255, 255, 0.96);
        --hp-surface-strong: rgba(255, 255, 255, 0.99);
        --hp-text: #16202a;
        --hp-text-muted: #556371;
        --hp-text-subtle: #677787;
        --hp-border: rgba(49, 51, 63, 0.12);
        --hp-border-strong: rgba(0, 83, 155, 0.38);
        --hp-accent: #00539B;
        --hp-accent-soft: rgba(0, 83, 155, 0.1);
        --hp-shadow-sm: 0 8px 20px rgba(15, 23, 42, 0.05);
        --hp-shadow-md: 0 14px 30px rgba(15, 23, 42, 0.07);
        --hp-shadow-lg: 0 18px 38px rgba(15, 23, 42, 0.08);
        --hp-radius-sm: 14px;
        --hp-radius-md: 18px;
        --hp-radius-lg: 24px;
    }
    .block-container {
        padding-top: 3.5rem;
        padding-bottom: 2.5rem;
    }
    .app-brand-wrap {
        width: 100%;
        max-width: 56rem;
        text-align: center;
        padding: 0.85rem 1rem 1.35rem 1rem;
        margin: 0 auto;
        box-sizing: border-box;
        overflow: hidden;
    }
    .app-brand-title {
        display: block;
        width: 100%;
        font-size: clamp(1.65rem, 3.4vw, 2.45rem);
        font-weight: 700;
        letter-spacing: -0.02em;
        color: var(--hp-text);
        line-height: 1.18;
        max-width: 100%;
        margin: 0 auto;
        white-space: normal;
        overflow-wrap: break-word;
        word-break: normal;
        box-sizing: border-box;
    }
    .app-brand-title span {
        color: var(--hp-accent);
    }
    .app-brand-subtitle {
        margin: 0.65rem auto 0 auto;
        max-width: 48rem;
        font-size: 1rem;
        line-height: 1.55;
        color: var(--hp-text-muted);
    }
    h2, h3 {
        letter-spacing: -0.02em;
        color: var(--hp-text);
    }
    div[data-testid="stMarkdownContainer"] p {
        color: var(--hp-text-muted);
    }
    div[data-testid="stCaptionContainer"] {
        color: var(--hp-text-subtle);
    }
    div[data-testid="stAlert"] {
        border-radius: var(--hp-radius-sm);
        border: 1px solid var(--hp-border);
        box-shadow: var(--hp-shadow-sm);
    }
    div[data-testid="stRadio"] > label[data-testid="stWidgetLabel"] p {
        font-size: 0.95rem;
        font-weight: 600;
        letter-spacing: 0.01em;
        color: var(--hp-text);
    }
    div[data-testid="stRadio"] div[role="radiogroup"] {
        gap: 0.65rem;
        padding: 0.25rem 0 0.1rem 0;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label {
        border: 1px solid var(--hp-border);
        border-radius: 999px;
        padding: 0.55rem 1rem;
        background: linear-gradient(180deg, var(--hp-surface-strong), rgba(245, 247, 250, 0.95));
        box-shadow: var(--hp-shadow-sm);
        transition: all 0.2s ease;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
        border-color: var(--hp-border-strong);
        box-shadow: 0 10px 22px rgba(0, 83, 155, 0.12);
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
        background: linear-gradient(135deg, rgba(233, 243, 252, 1), rgba(219, 234, 248, 1));
        border-color: rgba(0, 83, 155, 0.62);
        box-shadow: 0 12px 26px rgba(0, 83, 155, 0.16);
    }
    div[data-testid="stSelectbox"] > label p,
    div[data-testid="stFileUploader"] > label p,
    div[data-testid="stTextInput"] > label p,
    div[data-testid="stNumberInput"] > label p,
    div[data-testid="stMultiSelect"] > label p,
    div[data-testid="stCheckbox"] label p {
        color: var(--hp-text);
        font-weight: 600;
    }
    div[data-testid="stFileUploader"] section,
    div[data-testid="stSelectbox"] > div[data-baseweb="select"],
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stTextArea"] textarea {
        border-radius: var(--hp-radius-sm);
    }
    div[data-testid="stButton"] > button,
    div[data-testid="stDownloadButton"] > button {
        border-radius: 999px;
        border: 1px solid var(--hp-border);
        background: linear-gradient(180deg, var(--hp-surface-strong), rgba(244, 247, 249, 0.98));
        color: var(--hp-text);
        font-weight: 600;
        box-shadow: var(--hp-shadow-sm);
        transition: all 0.18s ease;
    }
    div[data-testid="stButton"] > button:hover,
    div[data-testid="stDownloadButton"] > button:hover {
        border-color: var(--hp-border-strong);
        color: var(--hp-accent);
        transform: translateY(-1px);
        box-shadow: var(--hp-shadow-md);
    }
    .workspace-card {
        border-radius: var(--hp-radius-md);
        padding: 1rem 1rem 0.95rem 1rem;
        min-height: 8.6rem;
        border: 1px solid var(--hp-border);
        background: linear-gradient(180deg, var(--hp-surface-strong), rgba(246, 248, 251, 0.96));
        box-shadow: var(--hp-shadow-md);
    }
    .workspace-card.active {
        border-color: rgba(0, 83, 155, 0.52);
        background: linear-gradient(135deg, rgba(236, 244, 252, 1), rgba(223, 235, 248, 1));
        box-shadow: 0 16px 30px rgba(0, 83, 155, 0.14);
    }
    .workspace-card-title {
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 0.35rem;
        color: var(--hp-text);
    }
    .workspace-card-body {
        font-size: 0.9rem;
        line-height: 1.45;
        color: var(--hp-text-muted);
    }
    .workspace-card-body strong {
        color: var(--hp-accent);
        font-weight: 700;
    }
    .workspace-header {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--hp-text-subtle);
        margin-bottom: 0.15rem;
    }
    .landing-panel {
        border-radius: var(--hp-radius-lg);
        padding: 1.35rem 1.45rem;
        margin: 0.35rem 0 1.1rem 0;
        border: 1px solid var(--hp-border);
        background: linear-gradient(135deg, rgba(252, 253, 255, 1), rgba(241, 247, 246, 1));
        box-shadow: var(--hp-shadow-lg);
    }
    .landing-eyebrow {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--hp-text-subtle);
        margin-bottom: 0.35rem;
    }
    .landing-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: var(--hp-text);
        margin-bottom: 0.35rem;
    }
    .landing-copy {
        font-size: 0.98rem;
        line-height: 1.6;
        color: var(--hp-text-muted);
        max-width: 44rem;
    }
    .landing-copy a,
    .feature-map-panel a {
        color: var(--hp-accent);
        font-weight: 600;
        text-decoration: none;
        border-bottom: 1px solid rgba(0, 83, 155, 0.28);
    }
    .landing-copy a:hover,
    .feature-map-panel a:hover {
        border-bottom-color: rgba(0, 83, 155, 0.65);
    }
    .feature-map-panel {
        border-radius: var(--hp-radius-lg);
        padding: 1.35rem 1.45rem;
        margin: 0.35rem 0 1.1rem 0;
        border: 1px solid var(--hp-border);
        background: linear-gradient(180deg, var(--hp-surface-strong), rgba(246, 249, 250, 0.98));
        box-shadow: var(--hp-shadow-lg);
    }
    .feature-map-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: var(--hp-text);
        margin-bottom: 0.35rem;
    }
    div[data-testid="stExpander"] details {
        border-radius: var(--hp-radius-sm);
        border: 1px solid var(--hp-border);
        background: linear-gradient(180deg, var(--hp-surface), rgba(247, 249, 251, 0.98));
        box-shadow: var(--hp-shadow-sm);
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, var(--hp-surface-strong), rgba(247, 249, 251, 0.98));
        border: 1px solid var(--hp-border);
        border-radius: var(--hp-radius-sm);
        padding: 0.85rem 1rem;
        box-shadow: var(--hp-shadow-sm);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "primary_section" not in st.session_state:
    st.session_state.primary_section = None

def clear_pdos_results():
    st.session_state.pdos_table = None
    st.session_state.pdos_figure = None
    st.session_state.pdos_roles = None

feature_map_view = st.query_params.get("view") == "feature-map"
primary_section = st.session_state.primary_section
start_page_clicked = False

if feature_map_view:
    st.markdown(
        """
        <div class="feature-map-panel">
            <div class="landing-eyebrow">Feature Map</div>
            <div class="feature-map-title">Hybrid Perovskite Studio Feature Map</div>
            <div class="landing-copy">
                This page shows the current workspace and tool tree. <a href="?" target="_self">Return to the main app</a>.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("\n".join(render_tree_lines(workspace_tree)))
    st.stop()

if primary_section is None:
    st.markdown(
        """
        <div class="landing-panel">
            <div class="landing-eyebrow">Start Here</div>
            <div class="landing-title">Pick the workspace that matches your task.</div>
            <div class="landing-copy">
                Start with Structure when you need to upload or prepare a model. Electronic, Dynamics, and Utilities stay available once you want to move into plotting, trajectory analysis, or supporting tools. You can also open the <a href="?view=feature-map" target="_blank">feature map</a> in a new tab for a full tree view.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

workspace_columns = st.columns(4)
for column, workspace_name in zip(workspace_columns, workspace_names()):
    card_class = (
        "workspace-card active"
        if workspace_name == primary_section
        else "workspace-card"
    )
    with column:
        st.markdown(
            f"""
            <div class="{card_class}">
                <div class="workspace-card-title">{workspace_name}</div>
                <div class="workspace-card-body">{workspace_descriptions[workspace_name]}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        button_label = (
            f"Open {workspace_name}"
            if primary_section != workspace_name
            else f"{workspace_name} Selected"
        )
        if st.button(
            button_label,
            key=f"workspace_select_{workspace_name.lower()}",
            use_container_width=True,
            disabled=primary_section == workspace_name,
        ):
            primary_section = workspace_name
            st.session_state.primary_section = workspace_name
            st.rerun()

toolbar_col1, toolbar_col2 = st.columns([6, 1.4])
with toolbar_col1:
    st.markdown('<div class="workspace-header">Navigation</div>', unsafe_allow_html=True)
    if primary_section is None:
        st.subheader("Choose a Workspace")
    else:
        st.subheader(f"{primary_section} Workspace")
with toolbar_col2:
    if primary_section is not None:
        st.write("")
        start_page_clicked = st.button(
            "Start Page",
            use_container_width=True,
            key="workspace_back_to_start",
        )

if start_page_clicked:
    primary_section = None
    st.session_state.primary_section = None

if primary_section is not None:
    st.caption("Switch workspaces at any time, or return to the start page for a clean overview.")

if primary_section == "Structure":
    render_structure_upload_panel(st.session_state, debug_log=_debug_log)
    structure_selection = render_structure_navigation()
    symmetry_option = structure_selection.symmetry
    com_option = structure_selection.center_of_mass
    dm_option = structure_selection.dipole_moment
    polarization_option = structure_selection.polarization
    distance_option = structure_selection.atomic_distances
    distortion_option = structure_selection.distortions
    deviation_calculation_option = structure_selection.percentage_deviation
    ADP_table_option = structure_selection.adp_table
    PXRD_option = structure_selection.pxrd
    PDF_option = structure_selection.pdf
    PDF_workflow = structure_selection.tool if PDF_option else None
    charge_analysis_option = structure_selection.charge_analysis
    rotate_option = structure_selection.rotation
    reflect_option = structure_selection.reflection
    translation_option = structure_selection.translation
    delete_option = structure_selection.deletion
    labelling_option = structure_selection.labelling
    interpolate_option = structure_selection.interpolation

elif primary_section == "Electronic":
    electronic_group = st.radio(
        "View",
        options=view_names("Electronic"),
        horizontal=True,
    )
    electronic_tool = st.radio(
        "Tool",
        options=tool_options("Electronic", electronic_group),
        horizontal=True,
    )
    plot_polarization_option = electronic_tool == "Plot polarization"
    plot_pdos_option = electronic_tool == "Plot partial density of states (PDOS)"
    plot_bs_option = electronic_tool == "Plot bandstructure"
    plot_spin_option = electronic_tool == "Plot spin texture"
    plot_spin_v2_option = electronic_tool == "Plot 3D spin texture"
    plot_absorption_option = electronic_tool == "Plot absorption spectra"

elif primary_section == "Dynamics":
    dynamics_tool = st.radio(
        "View",
        options=view_names("Dynamics"),
        horizontal=True,
    )
    MD_option = dynamics_tool == "Analyze AIMS MD output"
    MDanalysis_option = dynamics_tool == "Trajectory analysis"

elif primary_section == "Utilities":
    utility_tool = st.radio(
        "View",
        options=view_names("Utilities"),
        horizontal=True,
    )
    script_option = utility_tool == "Run your own script"
    xy_plot_option = utility_tool == "Plot Data"


uploaded_structure_name = st.session_state.uploaded_structure_name
uploaded_structure_bytes = st.session_state.uploaded_structure_bytes
if uploaded_structure_name and uploaded_structure_bytes is not None and primary_section == "Structure":
    try:
        _debug_log(f"upload: before initialize_structure file={uploaded_structure_name}")
        current_atoms, current_molecules, current_modified_symbols = load_active_structure(
            st.session_state
        )
        _debug_log(
            f"upload: after initialize_structure atoms={len(current_atoms)} molecules={len(current_molecules)}"
        )
    except Exception as e:
        _debug_log(f"upload: exception {type(e).__name__}: {e}")
        st.error(f"Error loading the current structure: {str(e)}")
        current_atoms = None
        current_molecules = None
        current_modified_symbols = None

structure_tool_selected = any(
    [
        symmetry_option,
        com_option,
        dm_option,
        polarization_option,
        distance_option,
        distortion_option,
        deviation_calculation_option,
        ADP_table_option,
        PXRD_option,
        PDF_option,
        charge_analysis_option,
        rotate_option,
        reflect_option,
        translation_option,
        delete_option,
        labelling_option,
        interpolate_option,
    ]
)
if current_atoms is None and structure_tool_selected:
    st.warning("Load a structure from Structure -> Overview before using structure-dependent tools.")
    symmetry_option = False
    com_option = False
    dm_option = False
    polarization_option = False
    distance_option = False
    distortion_option = False
    deviation_calculation_option = False
    ADP_table_option = False
    PXRD_option = False
    PDF_option = False
    PDF_workflow = None
    charge_analysis_option = False
    rotate_option = False
    reflect_option = False
    translation_option = False
    delete_option = False
    labelling_option = False
    interpolate_option = False


if current_atoms is not None and primary_section == "Structure":
    render_current_structure_card(
        st.session_state,
        current_atoms,
        current_molecules,
        current_modified_symbols,
    )

    modified_atoms = current_atoms.copy()
    molecules = current_molecules.copy()
if current_atoms is not None:
    modified_atoms = current_atoms.copy()
    molecules = current_molecules.copy()
    if rotate_option:
        modified_atoms = render_rotation(
            modified_atoms,
            molecules,
            st.session_state.file_name,
            render_section_header=render_section_header,
        )

    if reflect_option:
        modified_atoms = render_reflection(
            modified_atoms,
            molecules,
            st.session_state.file_name,
            render_section_header=render_section_header,
        )

    if translation_option:
        modified_atoms = render_translation(
            modified_atoms,
            molecules,
            st.session_state.file_name,
            render_section_header=render_section_header,
        )

    if delete_option:
        modified_atoms = render_deletion(
            modified_atoms,
            molecules,
            st.session_state.file_name,
            render_section_header=render_section_header,
        )

    if labelling_option:
        render_labelling(
            modified_atoms,
            molecules,
            current_modified_symbols,
            st.session_state,
            render_section_header=render_section_header,
        )

    if symmetry_option:
        render_symmetry_analysis(
            st.session_state,
            _get_backend_workflow_registry(),
            uploaded_structure_bytes,
            modified_atoms,
            render_section_header=render_section_header,
        )

    if ADP_table_option:
        render_adp_table(
            uploaded_structure_bytes,
            render_section_header=render_section_header,
        )

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

    if PXRD_option:
        render_pxrd_analysis(
            st.session_state,
            _get_backend_workflow_registry(),
            uploaded_structure_bytes,
            render_section_header=render_section_header,
        )

    if PDF_option:
        render_pdf_analysis(
            PDF_workflow,
            modified_atoms,
            render_section_header=render_section_header,
        )


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

    import re

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
        charges_by_index = None  # per-atom charges {1: q1, 2: q2, ...} 1-based per molecule

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

    if distance_option:
        render_atomic_distances(
            modified_atoms,
            render_section_header=render_section_header,
        )

    if distortion_option:
        render_distortions(
            modified_atoms,
            render_section_header=render_section_header,
        )


if interpolate_option:
    render_interpolation(render_section_header=render_section_header)

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
        min_state, max_state = get_state_range(uploaded_file)

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



if deviation_calculation_option:
    render_percentage_deviation(render_section_header=render_section_header)

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


        # Convert the DataFrame to a CSV string
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name="md_output.csv",
            mime="text/csv"
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


@st.cache_data(show_spinner="Building MDA universe")
def create_universe(file_buffer_md, timestep):
    file_buffer_md.seek(0)
    APP_TMP_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hps-trajectory-", dir=APP_TMP_DIR) as tmpdir:
        safe_extract_zip(file_buffer_md, Path(tmpdir))
        timestep = timestep / 1000
        return build_universe_from_dir(tmpdir, timestep=timestep)


previous_file_buffer = None

if MDanalysis_option:
    render_section_header("Analysis on MD Trajectory", kicker="Dynamics Workspace")
    timestep = st.number_input("Enter timestep in fs (dt)", min_value=0.0, max_value=50.0, step=0.1)
    file_buffer_md = st.file_uploader("Upload zipped directory", type=["zip"], key="file_buffer_zip")


    if file_buffer_md is not None and timestep is not None:

        # Check if the new file is uploaded, then remove the existing 'frames_dir'
        if file_buffer_md != previous_file_buffer:
            if os.path.exists('frames_dir'):
                shutil.rmtree('frames_dir')
            previous_file_buffer = file_buffer_md


        try:
            u = create_universe(file_buffer_md, timestep)
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
                    btn = st.download_button(
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


if script_option:
    render_section_header(
        "Run your own python script!",
        kicker="Utilities Workspace",
        subtitle="This feature uses JupyterLite and runs entirely in your browser. It does not currently have access to previously uploaded files.",
    )
    jupyterlite(900, 1600)

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
        min_state, max_state = get_state_range(uploaded_file)

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


from matplotlib.ticker import MultipleLocator


def format_subscripts(text):
    """Convert any _X to $_{X}$ (e.g., A_2BC_4 → A$_{2}$BC$_{4}$)"""
    return re.sub(r'_(\w)', r'$_{\1}$', text)


def _option_index(options, value, default=0):
    return options.index(value) if value in options else default


# def convert_underscores_to_subscripts(text):
#     return re.sub(r'_(\w)', r'$_{\1}$', text)

def modify_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    st.subheader("🔧 Dataset Modification via Math Expressions")

    # Build alias map and safe namespace
    alias_map = {}
    constants = {
        'pi': np.pi,
        'e': np.e,
    }
    functions = {
        'sin': np.sin,
        'cos': np.cos,
        'tan': np.tan,
        'log': np.log,
        'sqrt': np.sqrt,
        'abs': np.abs,
        'exp': np.exp
    }
    local_vars = {}

    # Map each column to a Python-safe variable name
    for col in df.columns:
        safe_col = re.sub(r'\W|^(?=\d)', '_', col)
        alias_map[safe_col] = col
        local_vars[safe_col] = df[col]

    # Show the alias map as a table
    st.markdown("### 🧭 Column Alias Mapping")
    st.dataframe(pd.DataFrame.from_dict(alias_map, orient='index', columns=["Original Column"]).rename_axis("Safe Name"))

    # Expression input area
    st.markdown("### 🧮 Enter one or more expressions below:")
    st.markdown("*Each line should be in the format: `new_col = expression`*")
    st.markdown("*(Use safe names from the left column. Functions like `sqrt`, `log`, `pi`, etc. are available.)*")

    expressions = st.text_area("Math expressions", height=200, value="")

    if st.button("✅ Apply Expressions"):
        success = True
        for line in expressions.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            if "=" not in line:
                st.warning(f"Skipping invalid line: `{line}` (missing '=')")
                continue

            new_col, formula = [s.strip() for s in line.split("=", 1)]
            try:
                result = evaluate_math_expression(
                    formula,
                    variables=local_vars,
                    functions=functions,
                    constants=constants,
                )
                df[new_col] = result
                # Update local_vars so it can be reused in later expressions
                safe_new_col = re.sub(r'\W|^(?=\d)', '_', new_col)
                local_vars[safe_new_col] = df[new_col]
                alias_map[safe_new_col] = new_col
                st.success(f"✅ Created column: `{new_col}`")

            except Exception as e:
                success = False
                st.error(f"❌ Error evaluating `{line}`: {e}")

        if success:
            st.markdown("### 🔄 Updated DataFrame Preview")
            st.dataframe(df.head())

    return df

if xy_plot_option:
    st.header("Plot Generator")
    import matplotlib as mpl
    mpl.rcParams["pdf.fonttype"] = 42

    # 1) upload (allow any text table)
    uploaded_file = st.file_uploader("Upload Data File", type=None)

    # 2) optional config
    uploaded_config = st.file_uploader(
        "Optionally, Upload Saved Plot Config (JSON)", type=["json"]
    )
    config_data = None
    if uploaded_config:
        try:
            config_data = json.load(uploaded_config)
            st.success("Configuration loaded.")
        except Exception as e:
            st.error(f"Failed to load config: {e}")

    if uploaded_file:
        try:
            # A) UI controls for parsing
            skip_rows = st.number_input(
                "Number of header/comment lines to skip",
                min_value=0, value=1, step=1
            )
            use_header = st.checkbox(
                "Treat first non-skipped row as header",
                value=True
            )

            manual_columns = None
            if not use_header:
                col_str = st.text_input(
                    "Enter column names (comma-separated)",
                    placeholder="e.g. time, intensity"
                )
                if col_str:
                    manual_columns = [c.strip() for c in col_str.split(",")]

            # B) let user peek at raw text
            with st.expander("📄 View raw data file (as text)"):
                text = uploaded_file.read().decode("utf-8", errors="ignore")
                st.text_area("Raw File Content", text, height=300)
                uploaded_file.seek(0)

            # C) decide if we need to re-parse
            current_params = {
                "name": uploaded_file.name,
                "skip_rows": skip_rows,
                "use_header": use_header,
                "manual_columns": manual_columns,
            }
            last_params = st.session_state.get("last_parse_params")
            if current_params != last_params:
                # detect delimiter
                content = uploaded_file.read().decode("utf-8", errors="ignore")
                uploaded_file.seek(0)
                if "\t" in content:
                    delim = "\t"
                elif "," in content:
                    delim = ","
                elif ";" in content:
                    delim = ";"
                else:
                    delim = r"\s+"

                # parse!
                df = pd.read_csv(
                    uploaded_file,
                    delimiter=delim,
                    skiprows=skip_rows,
                    header=0 if use_header else None,
                    names=manual_columns if not use_header else None,
                    engine="python" if delim == r"\s+" else "c"
                )

                # store
                st.session_state.original_df = df
                st.session_state.modified_df = df.copy()
                st.session_state.last_parse_params = current_params
                st.success("File uploaded and parsed.")

            # D) now work with the parsed DataFrame
            df = st.session_state.modified_df
            st.dataframe(df.head())

            if st.checkbox("🧪 Modify datasets?"):
                st.session_state.modified_df = modify_dataframe(df.copy())
                st.success("Dataset modified.")

            # E) your downstream plotting UI
            df = st.session_state.modified_df
            columns = df.columns.tolist()
            with st.expander("🗂 Dataset Configuration"):
                num_datasets = st.number_input(
                    "Number of Datasets to Plot",
                    min_value=1, max_value=10,
                    value=config_data.get("num_datasets", 1) if config_data else 1
                )
                shared_x = st.checkbox(
                    "All datasets share the same X-axis",
                    value=config_data.get("shared_x", True) if config_data else True
                )

            dataset_info = []
            plot_type_options = ["Line", "Scatter", "Line + Scatter"]
            marker_options = ["None", "o", "s", "D", "^", "x", "*"]
            linestyle_options = ["solid", "dashed", "dashdot", "dotted"]
            for i in range(num_datasets):
                with st.expander(f"📊 Dataset {i + 1}"):
                    ds_cfg = config_data["datasets"][i] if config_data and "datasets" in config_data and i < len(
                        config_data["datasets"]) else {}

                    x_col = st.selectbox("X-axis column", columns, key=f"x{i}",
                                         index=columns.index(ds_cfg.get("x", columns[0])) if ds_cfg.get(
                                             "x") in columns else 0)
                    y_col = st.selectbox("Y-axis column", columns, key=f"y{i}",
                                         index=columns.index(ds_cfg.get("y", columns[0])) if ds_cfg.get(
                                             "y") in columns else 0)

                    label = st.text_input(f"Label for Dataset {i + 1} (use _ for subscript)",
                                          value=ds_cfg.get("label", f"Data_{i + 1}"), key=f"label{i}")

                    color = st.color_picker(f"Color for Dataset {i + 1}", value=ds_cfg.get("color", "#1f77b4"),
                                            key=f"color{i}")
                    plot_type = st.selectbox(
                        f"Plot Type for Dataset {i + 1}",
                        plot_type_options,
                        index=_option_index(plot_type_options, ds_cfg.get("plot_type", "Line")),
                        key=f"plot_type{i}"
                    )
                    marker = st.selectbox(f"Marker for Dataset {i + 1}", marker_options,
                                          index=_option_index(marker_options, ds_cfg.get("marker", "o")),
                                          key=f"marker{i}")
                    marker_size = st.slider(
                        f"Marker Size for Dataset {i + 1}",
                        10,
                        200,
                        value=int(ds_cfg.get("marker_size", 45)),
                        step=5,
                        key=f"marker_size{i}"
                    )
                    linestyle = st.selectbox(f"Line Style for Dataset {i + 1}",
                                             linestyle_options,
                                             index=_option_index(
                                                 linestyle_options,
                                                 ds_cfg.get("linestyle", "solid")
                                             ), key=f"linestyle{i}")

                    dataset_info.append({
                        "x": x_col,
                        "y": y_col,
                        "label": format_subscripts(label),
                        "color": color,
                        "plot_type": plot_type,
                        "marker": None if marker == "None" else marker,
                        "marker_size": marker_size,
                        "linestyle": linestyle
                    })

            with st.expander("🧾 Labels and Title"):
                x_label = st.text_input(
                    "X-axis Label (use _ for subscript)",
                    value=config_data.get("x_label", dataset_info[0]["x"]) if config_data else dataset_info[0]["x"]
                )
                y_label = st.text_input(
                    "Y-axis Label (use _ for subscript)",
                    value=config_data.get("y_label", "Y") if config_data else "Y"
                )
                plot_title_raw = st.text_input(
                    "Plot Title (use _ for subscript)",
                    value=config_data.get("plot_title", "My_Plot") if config_data else "My_Plot"
                )

            with st.expander("📐 Axis Range and Ticks"):
                x_min = st.number_input(
                    "X min",
                    value=config_data.get("x_min", float(df[dataset_info[0]["x"]].min())) if config_data else float(
                        df[dataset_info[0]["x"]].min())
                )
                x_max = st.number_input(
                    "X max",
                    value=config_data.get("x_max", float(df[dataset_info[0]["x"]].max())) if config_data else float(
                        df[dataset_info[0]["x"]].max())
                )
                x_tick_gap = st.number_input(
                    "X-axis Tick Interval",
                    min_value=0.0,
                    value=config_data.get("x_tick_gap", 1.0) if config_data else np.around((df[dataset_info[0]["x"]].max() - df[dataset_info[0]["x"]].min())/5),
                    step=0.1
                )

                y_min = st.number_input(
                    "Y min",
                    value=config_data.get("y_min", float(df[dataset_info[0]["y"]].min())) if config_data else float(
                        df[dataset_info[0]["y"]].min()), format="%0.4f"
                )
                y_max = st.number_input(
                    "Y max",
                    value=config_data.get("y_max", float(df[dataset_info[0]["y"]].max())) if config_data else float(
                        df[dataset_info[0]["y"]].max()), format="%0.4f"
                )
                y_tick_gap = st.number_input(
                    "Y-axis Tick Interval",
                    min_value=0.0,
                    value=config_data.get("y_tick_gap", 1.0) if config_data else 1.0,
                    step=0.001, format="%0.4f"
                )

            with st.expander("🖋️ Text Customization"):
                font_options = ["sans-serif", "serif", "monospace", "cursive", "fantasy"]
                default_font = config_data.get("font_family", "sans-serif") if config_data else "sans-serif"
                font_family = st.selectbox("Font Family", font_options, index=font_options.index(default_font))

                title_size = st.slider(
                    "Plot Title Font Size", 8, 32,
                    value=config_data.get("title_size", 18) if config_data else 14
                )
                title_weight = st.selectbox(
                    "Title Weight", ["normal", "bold", "heavy"],
                    index=["normal", "bold", "heavy"].index(
                        config_data.get("title_weight", "bold") if config_data else "normal")
                )
                title_loc = st.selectbox(
                    "Title Alignment", ["center", "left", "right"],
                    index=["center", "left", "right"].index(
                        config_data.get("title_loc", "center") if config_data else "center")
                )

                label_size = st.slider(
                    "Axis Label Font Size", 8, 28,
                    value=config_data.get("label_size", 14) if config_data else 14
                )
                label_weight = st.selectbox(
                    "Label Weight", ["normal", "bold", "heavy"],
                    index=["normal", "bold", "heavy"].index(
                        config_data.get("label_weight", "normal") if config_data else "normal")
                )

                tick_size = st.slider(
                    "Tick Label Font Size", 6, 20,
                    value=config_data.get("tick_size", 12) if config_data else 12
                )

            with st.expander("📏 Border (Spine) Thickness"):
                spine_width = st.slider(
                    "Axes Line Width", 0.5, 5.0,
                    value=config_data.get("spine_width", 1.0) if config_data else 1.0
                )

            with st.expander("⚙️ Additional Plot Settings"):
                grid_on = st.checkbox(
                    "Show Grid", value=config_data.get("grid_on", True) if config_data else True
                )
                show_legend = st.checkbox(
                    "Show Legend", value=config_data.get("show_legend", True) if config_data else True
                )

            if st.button("Generate Plot"):
                plt.style.use('classic')
                fig, ax = plt.subplots(figsize=(8, 6))


                for ds in dataset_info:
                    label = ds["label"] if show_legend else None
                    if ds["plot_type"] == "Scatter":
                        ax.scatter(
                            df[ds["x"]],
                            df[ds["y"]],
                            color=ds["color"],
                            marker=ds["marker"] or "o",
                            s=ds["marker_size"],
                            label=label,
                        )
                    elif ds["plot_type"] == "Line + Scatter":
                        ax.plot(df[ds["x"]], df[ds["y"]],
                                color=ds["color"],
                                linewidth=2.0,
                                marker=ds["marker"] or "o",
                                markersize=np.sqrt(ds["marker_size"]),
                                linestyle=ds["linestyle"],
                                label=label)
                    else:
                        ax.plot(df[ds["x"]], df[ds["y"]],
                                color=ds["color"],
                                linewidth=2.0,
                                marker=ds["marker"],
                                linestyle=ds["linestyle"],
                                label=label)

                ax.set_xlabel(format_subscripts(x_label), fontsize=label_size, weight=label_weight, family=font_family)
                ax.set_ylabel(format_subscripts(y_label), fontsize=label_size, weight=label_weight, family=font_family)
                ax.set_title(format_subscripts(plot_title_raw),
                             fontsize=title_size, weight=title_weight, loc=title_loc, family=font_family)

                ax.set_xlim(x_min, x_max)
                ax.set_ylim(y_min, y_max)
                ax.tick_params(axis='both', labelsize=tick_size)

                for label in ax.get_xticklabels() + ax.get_yticklabels():
                    label.set_family(font_family)

                if x_tick_gap > 0:
                    ax.xaxis.set_major_locator(MultipleLocator(x_tick_gap))
                if y_tick_gap > 0:
                    ax.yaxis.set_major_locator(MultipleLocator(y_tick_gap))

                for spine in ax.spines.values():
                    spine.set_linewidth(spine_width)

                if grid_on:
                    ax.grid(True)
                if show_legend:
                    ax.legend(fontsize=label_size)

                st.pyplot(fig)


                def save_plot_bytes(fmt):
                    buf = BytesIO()
                    fig.savefig(buf, format=fmt, bbox_inches='tight')
                    buf.seek(0)
                    return buf


                pdf_bytes = save_plot_bytes("pdf")
                png_bytes = save_plot_bytes("png")

                st.download_button("Download Plot as PDF", data=pdf_bytes, file_name="plot.pdf", mime="application/pdf")
                st.download_button("Download Plot as PNG", data=png_bytes, file_name="plot.png", mime="image/png")

                config_out = {
                    "num_datasets": num_datasets,
                    "shared_x": shared_x,
                    "datasets": [
                        {
                            "x": ds["x"],
                            "y": ds["y"],
                            "label": ds["label"].replace("$_{", "_").replace("}$", ""),
                            # Convert back to original input
                            "color": ds["color"],
                            "plot_type": ds["plot_type"],
                            "marker": ds["marker"] if ds["marker"] else "None",
                            "marker_size": ds["marker_size"],
                            "linestyle": ds["linestyle"]
                        }
                        for ds in dataset_info
                    ],
                    "x_label": x_label,
                    "y_label": y_label,
                    "plot_title": plot_title_raw,
                    "x_min": x_min,
                    "x_max": x_max,
                    "x_tick_gap": x_tick_gap,
                    "y_min": y_min,
                    "y_max": y_max,
                    "y_tick_gap": y_tick_gap,
                    "font_family": font_family,
                    "title_size": title_size,
                    "title_weight": title_weight,
                    "title_loc": title_loc,
                    "label_size": label_size,
                    "label_weight": label_weight,
                    "tick_size": tick_size,
                    "spine_width": spine_width,
                    "grid_on": grid_on,
                    "show_legend": show_legend
                }

                # Create a JSON file in memory
                config_json = json.dumps(config_out, indent=4)
                config_bytes = BytesIO(config_json.encode("utf-8"))

                # Download button for config
                st.download_button(
                    label="📥 Download Plot Config (JSON)",
                    data=config_bytes,
                    file_name="plot_config.json",
                    mime="application/json"
                )

        except Exception as e:
            st.error(f"Failed to read file: {e}")
