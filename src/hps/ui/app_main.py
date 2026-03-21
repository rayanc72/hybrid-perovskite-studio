import copy

from hps.domain import pdf_analysis as pdf_analysis_module
from hps.domain import electronic_property as electronic_property_module
from hps.domain import md_analysis as md_analysis_module
from hps.domain import molecule_builder as molecule_builder_module
from hps.domain import structure_manager as structure_manager_module
from hps.io.paths import APP_TMP_DIR
from hps.ui.navigation import (
    build_feature_tree,
    group_names,
    render_tree_lines,
    tool_options,
    view_names,
    workspace_descriptions,
    workspace_names,
)


def _inject_public_names(module):
    for name in dir(module):
        if not name.startswith("_"):
            globals().setdefault(name, getattr(module, name))


def _debug_log(message):
    APP_TMP_DIR.mkdir(exist_ok=True)
    with open(APP_TMP_DIR / "upload_debug.log", "a", encoding="utf-8") as fh:
        fh.write(f"{message}\n")


_debug_log("startup: entered hps.ui.app_main")


for _module in (
    structure_manager_module,
    molecule_builder_module,
    electronic_property_module,
    md_analysis_module,
    pdf_analysis_module,
):
    _inject_public_names(_module)

_debug_log("startup: injected public names from packaged modules")

import plotly.express as px
import plotly.io as pio
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.io.cif import CifWriter
from pymatgen.core.structure import Structure
from contextlib import redirect_stdout
import streamlit as st
import subprocess
import os
import shutil
from pathlib import Path
from diffpy.structure import loadStructure
from diffpy.pdffit2 import PdfFit
import requests
from PIL import Image
from streamlit_lottie import st_lottie
# from streamlit_ketcher import st_ketcher
from streamlit_extras.mention import mention
from streamlit_extras.jupyterlite import jupyterlite
import matplotlib as mpl
from itertools import combinations_with_replacement
import matplotlib.pyplot as plt
# import io
# import numpy as np
# import pandas as pd
# import plotly.graph_objects as go
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

if "file_name" not in st.session_state:
    st.session_state.file_name = None
if "uploaded_structure_name" not in st.session_state:
    st.session_state.uploaded_structure_name = None
if "uploaded_structure_bytes" not in st.session_state:
    st.session_state.uploaded_structure_bytes = None
if "structure_uploader_key" not in st.session_state:
    st.session_state.structure_uploader_key = 0

symmetry_option = False
com_option = False
dm_option = False
polarization_option = False
distance_option = False
distortion_option = False
deviation_calculation_option = False
ADP_table_option = False
PDF_option = False
charge_analysis_option = False
rotate_option = False
reflect_option = False
translation_option = False
delete_option = False
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
        --hp-border-strong: rgba(12, 135, 122, 0.4);
        --hp-accent: #0c877a;
        --hp-accent-soft: rgba(12, 135, 122, 0.1);
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
        box-shadow: 0 10px 22px rgba(12, 135, 122, 0.12);
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
        background: linear-gradient(135deg, rgba(230, 246, 243, 1), rgba(214, 240, 236, 1));
        border-color: rgba(12, 135, 122, 0.65);
        box-shadow: 0 12px 26px rgba(12, 135, 122, 0.18);
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
        border-color: rgba(12, 135, 122, 0.55);
        background: linear-gradient(135deg, rgba(232, 247, 244, 1), rgba(220, 241, 237, 1));
        box-shadow: 0 16px 30px rgba(12, 135, 122, 0.14);
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
        border-bottom: 1px solid rgba(12, 135, 122, 0.28);
    }
    .landing-copy a:hover,
    .feature-map-panel a:hover {
        border-bottom-color: rgba(12, 135, 122, 0.65);
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

def clear_loaded_structure():
    st.session_state.uploaded_structure_name = None
    st.session_state.uploaded_structure_bytes = None
    st.session_state.file_name = None
    st.session_state.structure_uploader_key += 1
    st.session_state.show_structure_details = False
    st.session_state.load_initial_structure_viewer = False

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
    st.caption("Upload or replace the active structure from anywhere inside the Structure workspace.")
    structure_upload = st.file_uploader(
        "Upload a structure file (aims geometry, CIF, or next_step)",
        type=["in", "cif", "next_step"],
        key=f"structure_workspace_uploader_{st.session_state.structure_uploader_key}",
    )
    _debug_log("structure workspace: file_uploader rendered")
    if structure_upload is not None:
        st.session_state.uploaded_structure_name = structure_upload.name
        st.session_state.uploaded_structure_bytes = structure_upload.getvalue()
        st.session_state.file_name = structure_upload.name
        _debug_log(
            f"structure workspace: stored upload file={structure_upload.name} bytes={len(st.session_state.uploaded_structure_bytes)}"
        )
        st.success(f"Loaded `{structure_upload.name}` into the current workspace.")
    elif st.session_state.uploaded_structure_name is None:
        st.caption("No structure loaded yet.")
    else:
        st.caption(f"Current structure: `{st.session_state.uploaded_structure_name}`")
        if st.button("Remove current structure", key="remove_structure_workspace"):
            clear_loaded_structure()
            st.rerun()

    structure_mode = st.radio(
        "View",
        options=view_names("Structure"),
        horizontal=True,
    )

    if structure_mode == "Overview":
        st.info("Review the current structure, then move into analysis or transformations as needed.")

    elif structure_mode == "Analysis":
        analysis_group = st.radio(
            "Group",
            options=group_names("Structure", "Analysis"),
            horizontal=True,
        )

        if analysis_group == "Symmetry":
            analysis_tool = st.selectbox(
                "Tool",
                options=tool_options("Structure", "Analysis", analysis_group),
            )
        elif analysis_group == "Molecules":
            analysis_tool = st.selectbox(
                "Tool",
                options=tool_options("Structure", "Analysis", analysis_group),
            )
        elif analysis_group == "Structure Metrics":
            analysis_tool = st.selectbox(
                "Tool",
                options=tool_options("Structure", "Analysis", analysis_group),
            )
        else:
            st.markdown("**PDF Analysis**")
            st.caption("Run pair distribution function analysis for the currently loaded structure.")
            analysis_tool = tool_options("Structure", "Analysis", analysis_group)[0]

        symmetry_option = analysis_tool == "Symmetrize structure"
        com_option = analysis_tool == "Find center of mass"
        dm_option = analysis_tool == "Calculate dipole moment"
        polarization_option = analysis_tool == "Calculate polarization direction"
        distance_option = analysis_tool == "Calculate atomic distances"
        distortion_option = analysis_tool == "Calculate octahedral distortions"
        deviation_calculation_option = analysis_tool == "Calculate percentage deviation"
        ADP_table_option = analysis_tool == "Anisotropic displacement parameters"
        PDF_option = analysis_tool == "PDF analysis"
        charge_analysis_option = analysis_tool == "Charge analysis"

    elif structure_mode == "Transformations":
        transform_group = st.radio(
            "Group",
            options=group_names("Structure", "Transformations"),
            horizontal=True,
        )
        transform_tool = st.selectbox(
            "Tool",
            options=tool_options("Structure", "Transformations", transform_group),
        )
        rotate_option = transform_tool == "Rotation"
        reflect_option = transform_tool == "Reflection"
        translation_option = transform_tool == "Translation"
        delete_option = transform_tool == "Deletion"
        if transform_tool == "Interpolation":
            st.caption("Interpolation uses its own file-upload workflow inside lattice operations.")
        interpolate_option = transform_tool == "Interpolation"

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
if uploaded_structure_name and uploaded_structure_bytes is not None:
    structure_buffer = io.BytesIO(uploaded_structure_bytes)
    structure_buffer.name = uploaded_structure_name
    try:
        _debug_log(f"upload: before initialize_structure file={uploaded_structure_name}")
        current_atoms, current_molecules, current_modified_symbols = initialize_structure(
            structure_buffer,
            file_format=get_file_format(uploaded_structure_name),
            file_name=uploaded_structure_name,
            exceptions=[("F", "I")],
            b_p=0,
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
        PDF_option,
        charge_analysis_option,
        rotate_option,
        reflect_option,
        translation_option,
        delete_option,
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
    PDF_option = False
    charge_analysis_option = False
    rotate_option = False
    reflect_option = False
    translation_option = False
    delete_option = False
    interpolate_option = False


if current_atoms is not None and primary_section == "Structure":
    output_suffix = ""
    context_box = st.container()
    with context_box:
        st.markdown("### Current Structure")
        meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
        meta_col1.metric("File", st.session_state.file_name)
        meta_col2.metric("Format", get_file_format(st.session_state.file_name))
        meta_col3.metric("Atoms", len(current_atoms))
        meta_col4.metric("Molecule Groups", len(current_molecules))

        action_col1, action_col2, action_col3 = st.columns(3)
        with action_col1:
            create_aims_download_file(current_atoms, st.session_state.file_name, output_suffix)
        with action_col2:
            create_labelled_download_file(current_atoms, st.session_state.file_name, output_suffix)
        with action_col3:
            if st.button("Remove current structure", key="remove_structure_context", use_container_width=True):
                clear_loaded_structure()
                st.rerun()

        show_structure_details = st.checkbox(
            "Show structure details",
            value=False,
            key="show_structure_details",
        )
        if show_structure_details:
            space_group = print_space_group(current_atoms)
            with st.expander("Symmetry information", expanded=False):
                st.markdown(f"```\n{space_group}\n```")

            molecule_list = []
            for i, molecule in enumerate(current_molecules, 1):
                molecule_labels = [current_modified_symbols[mol_atom] for mol_atom in molecule]
                molecule_list.append(f"Molecule {i}: {', '.join(molecule_labels)}")

            molecule_list_formatted = "\n".join(molecule_list)
            with st.expander("Detected molecules", expanded=False):
                st.markdown(f"```\n{molecule_list_formatted}\n```")

        with st.expander("3D structure viewer", expanded=False):
            load_structure_viewer = st.checkbox(
                "Load 3D structure viewer",
                value=False,
                key="load_initial_structure_viewer",
            )
            if load_structure_viewer:
                try:
                    atoms_to_speck(current_atoms, "initialization")
                except Exception as e:
                    st.error(f"Error rendering structure viewer: {str(e)}")
            else:
                st.caption("Enable the viewer only when needed.")

        st.divider()

    modified_atoms = current_atoms.copy()
    molecules = current_molecules.copy()
if current_atoms is not None:
    modified_atoms = current_atoms.copy()
    molecules = current_molecules.copy()
    if rotate_option:
        render_section_header("Rotation", kicker="Structure Workspace")

        rotate_type = st.selectbox("Select Rotation Type", (
        "Rotate Individual Molecules", "Rotate Multiple Molecules", "Random Rotation", "Interpolate by Rotation", "Rotate Part of Molecules", "Rotate by Dipole Moment"))







        if rotate_type == "Rotate Individual Molecules":

            # Gather user inputs for rotation using Streamlit widgets
            molecule_indices = st.multiselect("Select molecule indices", options=range(1, len(molecules) + 1))

            if molecule_indices is not None:

                if "rotation_parameters" not in st.session_state:
                    st.session_state.rotation_parameters = [None] * len(molecules)

                for i in molecule_indices:
                    st.subheader(f"Molecule {i}")

                    with st.form(key=f"molecule_{i}_form"):

                        axis_input = st.text_input("Enter crystal direction as h, k, l separated by spaces")

                        angle = st.number_input("Enter rotation angle in degrees", step=1.0)

                        if st.form_submit_button(f"Set Parameters for Molecule {i}"):
                            hkl = np.array([int(val) for val in axis_input.split()])
                            lattice_vectors = modified_atoms.get_cell()
                            axis = np.dot(hkl, lattice_vectors)
                            axis /= np.linalg.norm(axis)

                            st.session_state.rotation_parameters[i - 1] = (axis, angle)


                if st.button("Apply Multiple Rotations"):
                    chosen_molecules = [molecules[i - 1] for i in molecule_indices]
                    chosen_rotation_parameters = [st.session_state.rotation_parameters[i - 1] for i in molecule_indices]

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
            molecule_indices = st.multiselect("Select molecule indices", options=range(1, len(molecules) + 1))


            axis_option = st.selectbox("Choose axis option", options=["Cartesian axis", "Crystal direction", "Custom axis"])
            axis_input = None
            if axis_option == "Cartesian axis":
                axis_input = st.selectbox("Select rotation axis", options=["x", "y", "z"])
            elif axis_option == "Crystal direction":
                axis_input = st.text_input("Enter crystal direction as h, k, l separated by spaces")
            elif axis_option == "Custom axis":
                axis_input = st.text_input("Enter custom axis as x, y, z separated by spaces")

            # Add the centroid option selection
            centroid_option = st.selectbox("Choose centroid option", options=[("1: Center of mass", 1),
                                                                              ("2: Custom", 2),
                                                                              ("3: Center of unit cell", 3)],
                                           format_func=lambda o: o[0])[1]

            custom_centroid = None
            if centroid_option == 2:
                custom_centroid = st.text_input("Enter custom centroid as x, y, z separated by spaces")
            angle = st.number_input("Enter rotation angle in degrees", step=1.0)

            if st.button("Apply Rotation") and axis_input:
                if axis_option == "Cartesian axis":
                    axis_dict = {'x': [1, 0, 0], 'y': [0, 1, 0], 'z': [0, 0, 1]}
                    axis = axis_dict[axis_input]
                elif axis_option == "Crystal direction":
                    hkl = np.array([int(val) for val in axis_input.split()])
                    lattice_vectors = modified_atoms.get_cell()
                    axis = np.dot(hkl, lattice_vectors)
                    axis /= np.linalg.norm(axis)
                elif axis_option == "Custom axis":
                    axis = np.array([float(val) for val in axis_input.split()])

                # Pass custom centroid if centroid_option is 2, otherwise pass None
                custom_centroid = np.array(
                    [float(val) for val in custom_centroid.split()]) if centroid_option == 2 else None

                modified_atoms = rotate_molecules_v3(modified_atoms, molecules, molecule_indices, axis, angle,
                                                  centroid_option, custom_centroid)


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
                    l = fixed_l if fixed_l is not None else np.random.randint(low, high + 1)

                    # avoid (0,0,0)
                    if h == 0 and k == 0 and l == 0:
                        continue

                    hkl = np.array([h, k, l], dtype=int)

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
                cols = ["structure_id", "mode", "molecule_index", "h", "k", "l", "axis_x", "axis_y", "axis_z",
                        "angle_deg"]
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
                    key="axis_fix_choice"
                )

                # choose which indices to fix
                fixed_h = fixed_k = fixed_l = None
                max_index = st.number_input(
                    "Max |index| for random draw (controls range [-N, N])",
                    min_value=1, max_value=6, value=2, step=1,
                    key="axis_max_index"
                )

                if fix_choice == "Fix one":
                    which_one = st.selectbox("Choose index to fix", ["h", "k", "l"], key="fix_one_which")
                    val = st.number_input("Value", min_value=-max_index, max_value=max_index, value=0, step=1,
                                          key="fix_one_val")
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
                        key="fix_two_which"
                    )
                    if len(which_two) == 2:
                        v1 = st.number_input(f"Value for {which_two[0]}", min_value=-max_index, max_value=max_index,
                                             value=0, step=1, key="fix_two_val1")
                        v2 = st.number_input(f"Value for {which_two[1]}", min_value=-max_index, max_value=max_index,
                                             value=0, step=1, key="fix_two_val2")
                        if "h" in which_two:
                            fixed_h = int(v1 if which_two[0] == "h" else v2)
                        if "k" in which_two:
                            fixed_k = int(v1 if which_two[0] == "k" else v2)
                        if "l" in which_two:
                            fixed_l = int(v1 if which_two[0] == "l" else v2)

            # ---------- Mode-specific selection UIs ----------
            if mode == "Symmetric Random Rotation":
                st.markdown("Define **partner pairs** (two molecule indices per pair). "
                            "Assuming input symmetric configuration, each pair receives equal rotations to preserve symmetry.")

                if "sym_pairs" not in st.session_state:
                    st.session_state.sym_pairs = []

                # Pair builder UI
                with st.form("add_partner_pair_form"):
                    st.markdown("Add a **single pair** manually or **upload a CSV** with two columns of indices.")

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
                        csv_has_header = st.checkbox("CSV has header row", value=True, key="sym_csv_has_header")

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
                                    f"Manual selection: indices must be different (got {pair[0]}, {pair[1]}).")
                            elif not (1 <= pair[0] <= len(molecules) and 1 <= pair[1] <= len(molecules)):
                                issues.append(f"Manual selection: indices out of range 1..{len(molecules)}.")
                            else:
                                new_pairs.append(tuple(sorted(pair)))

                        # 2) From CSV (optional)
                        if uploaded_csv is not None:
                            try:
                                df = pd.read_csv(uploaded_csv, header=0 if csv_has_header else None)
                                if df.shape[1] < 2:
                                    issues.append("CSV must have at least two columns (first two are used).")
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
                                                f"Row {i + 1}: values must be integers (got {row.iloc[0]!r}, {row.iloc[1]!r}).")
                                            continue
                                        # Validate values
                                        if a == b:
                                            issues.append(f"Row {i + 1}: indices must be different (got {a}, {b}).")
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
                        new_pairs = list(dict.fromkeys(new_pairs))  # preserves order, removes duplicates

                        # Filter out pairs already present
                        existing = set(st.session_state.sym_pairs)
                        to_add = [p for p in new_pairs if p not in existing]

                        # Report overlaps (not added because already present)
                        already = [p for p in new_pairs if p in existing]

                        # Apply additions
                        if to_add:
                            st.session_state.sym_pairs.extend(to_add)
                            st.success(f"Added {len(to_add)} new pair(s): {', '.join(map(str, to_add))}")

                        if already:
                            st.info(f"Skipped {len(already)} duplicate pair(s): {', '.join(map(str, already))}")

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
                    min_value=1, max_value=32, value=1, step=1
                )

                if st.button("Apply Symmetric Random Rotations"):
                    if not st.session_state.sym_pairs:
                        st.warning("Add at least one partner pair first.")
                    else:
                        import copy, io, zipfile, tempfile
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
                                struct_logs.append({
                                    "structure_id": s_idx, "mode": "symmetric",
                                    "molecule_index": a, "h": hkl[0], "k": hkl[1], "l": hkl[2],
                                    "axis_x": float(axis[0]), "axis_y": float(axis[1]), "axis_z": float(axis[2]),
                                    "angle_deg": float(angle)
                                })
                                struct_logs.append({
                                    "structure_id": s_idx, "mode": "symmetric",
                                    "molecule_index": b, "h": hkl[0], "k": hkl[1], "l": hkl[2],
                                    "axis_x": float(axis[0]), "axis_y": float(axis[1]), "axis_z": float(axis[2]),
                                    "angle_deg": float(angle)
                                })

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
                            st.success(f"Generated {int(num_structs)} symmetric random-rotated structures.")

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
                    seed_val = st.number_input("Seed", value=0, step=1, key="pure_seed_val") if use_seed else None
                if use_seed:
                    np.random.seed(int(seed_val))

                # How many structures?
                num_structs = st.number_input(
                    "How many structures should be generated?",
                    min_value=1, max_value=32, value=1, step=1,
                    key="pure_num_structs"
                )

                if st.button("Apply Asymmetric Random Rotations"):
                    if not target_indices:
                        st.warning("Please select at least one molecule.")
                    else:
                        import copy, io, zipfile, tempfile
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

                                struct_logs.append({
                                    "structure_id": s_idx, "mode": "asym",
                                    "molecule_index": idx, "h": hkl[0], "k": hkl[1], "l": hkl[2],
                                    "axis_x": float(axis[0]), "axis_y": float(axis[1]), "axis_z": float(axis[2]),
                                    "angle_deg": float(angle)
                                })

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
                            st.success(f"Generated {int(num_structs)} asymmetric random-rotated structures.")


        if rotate_type == "Interpolate by Rotation":
            st.header("Create a Series of Structures")

            # Gather user inputs for rotation using Streamlit widgets
            molecule_indices = st.multiselect("Select molecule indices", options=range(1, len(molecules) + 1))

            if molecule_indices is not None:

                if "rotation_parameters" not in st.session_state:
                    st.session_state.rotation_parameters = [None] * len(molecules)

                angle_range = st.slider("Enter rotation angle range (min, max) in degrees", min_value=0, max_value=360,
                                        value=(0, 180))
                num_structures = st.number_input("Enter the number of structures to generate", min_value=1, value=1, step=1)

                for i in molecule_indices:
                    st.subheader(f"Molecule {i}")

                    with st.form(key=f"molecule_{i}_form"):

                        axis_input = st.text_input("Enter crystal direction as h, k, l separated by spaces")

                        if st.form_submit_button(f"Set Parameters for Molecule {i}"):
                            hkl = np.array([int(val) for val in axis_input.split()])
                            lattice_vectors = modified_atoms.get_cell()
                            axis = np.dot(hkl, lattice_vectors)
                            axis /= np.linalg.norm(axis)

                            st.session_state.rotation_parameters[i - 1] = axis

                if st.button("Apply Multiple Rotations"):
                    chosen_molecules = [molecules[i - 1] for i in molecule_indices]
                    chosen_rotation_axes = [st.session_state.rotation_parameters[i - 1] for i in molecule_indices]

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
            molecule_indices = st.multiselect("Select molecule indices", options=range(1, len(molecules) + 1))

            if "rotation_parameters" not in st.session_state:
                st.session_state.rotation_parameters = [None] * len(molecules)
            if molecule_indices is not None:
                for i in molecule_indices:
                    st.subheader(f"Molecule {i}")

                    with st.form(key=f"molecule_{i}_form"):

                        atoms_to_rotate = st.multiselect("Enter the atom indices that require rotation",
                                                         options=[idx + 1 for idx in molecules[i - 1]])

                        axis_input = st.text_input("Enter crystal direction as h, k, l separated by spaces")

                        pivot_point = st.selectbox("Select the pivot point atom", options=[idx + 1 for idx in molecules[i - 1]])
                        angle = st.number_input("Enter rotation angle in degrees", step=1.0)

                        if st.form_submit_button(f"Set Parameters for Molecule {i}"):
                            hkl = np.array([int(val) for val in axis_input.split()])
                            lattice_vectors = modified_atoms.get_cell()
                            axis = np.dot(hkl, lattice_vectors)
                            axis /= np.linalg.norm(axis)

                            atoms_to_rotate_indices = [molecules[i - 1].index(atom - 1) for atom in atoms_to_rotate]
                            pivot_point_index = molecules[i - 1].index(pivot_point - 1)

                            st.session_state.rotation_parameters[i - 1] = (atoms_to_rotate_indices, axis, pivot_point_index, angle)

            if st.button("Apply Rotations"):
                chosen_molecules = [molecules[i - 1] for i in molecule_indices]
                chosen_rotation_parameters = [st.session_state.rotation_parameters[i - 1] for i in molecule_indices]

                for molecule, (atoms_to_rotate_indices, axis, pivot_point_index, angle) in zip(chosen_molecules,
                                                                                 chosen_rotation_parameters):
                    modified_atoms = rotate_molecules_v5(modified_atoms, molecule, axis, angle, pivot_point_index, atoms_to_rotate_indices)

                # Save modified atoms to temporary files
                output_suffix = "_rotated_some_atoms"
                file_name = os.path.splitext(st.session_state.file_name)[0]

                create_aims_download_file(modified_atoms, file_name, output_suffix)

                create_labelled_download_file(modified_atoms, file_name, output_suffix)

        if rotate_type == "Rotate by Dipole Moment":
            #This option aligns a molecule's dipole moment to a chosen crystal plane by rotating the molecule around its centroid
            st.header("Rotate Molecules to align with planes")

            # Gather user inputs for rotation using Streamlit widgets
            molecule_indices = st.multiselect("Select molecule indices", options=range(1, len(molecules) + 1))

            if molecule_indices is not None:



                if "alignment_planes" not in st.session_state:
                    st.session_state.alignment_planes = [None] * len(molecules)

                for i in molecule_indices:
                    st.subheader(f"Molecule {i}")

                    with st.form(key=f"molecule_{i}_alg_form"):

                        plane_input = st.text_input("Enter crystal plane as h, k, l separated by spaces")

                        if st.form_submit_button(f"Set Parameters for Molecule {i}"):
                            hkl = np.array([int(val) for val in plane_input.split()])
                            st.session_state.alignment_planes[i - 1] = hkl

                if st.button("Apply Alignments"):
                    chosen_molecules = [molecules[i - 1] for i in molecule_indices]
                    chosen_alignment_planes = [st.session_state.alignment_planes[i - 1] for i in molecule_indices]
                    lattice_vectors = modified_atoms.get_cell()

                    for molecule, miller_indices in zip(chosen_molecules, chosen_alignment_planes):
                        #calculate the dm
                        mol_obj = get_molecule_object(modified_atoms, molecule)
                        dm_vector, com = get_dm_direction(mol_obj)
                        #get the rotation matrix
                        rot_mat = align_vector_with_plane(dm_vector, lattice_vectors, miller_indices)
                        #get the axis
                        rot_ax, rot_ang = rotation_axis_and_angle_from_matrix_v2(rot_mat)
                        rot_ax_cr = crystal_direction_v3(rot_ax, lattice_vectors)
                        st.write(rot_ax_cr)
                        #supply it to the rotate_molecules
                        modified_atoms = rotate_molecules_v4(modified_atoms, molecule, mol_obj, rot_mat)

                    # Save modified atoms to temporary files
                    output_suffix = "_rotated_aligned"
                    file_name = os.path.splitext(st.session_state.file_name)[0]

                    create_aims_download_file(modified_atoms, file_name, output_suffix)

                    create_labelled_download_file(modified_atoms, file_name, output_suffix)

    if reflect_option:
        render_section_header("Reflect molecules on a plane", kicker="Structure Workspace")

        molecule_indices = st.multiselect("Select molecule indices", options=range(1, len(molecules) + 1))

        if "reflection_parameters" not in st.session_state:
            st.session_state.reflection_parameters = [None] * len(molecules)
        if molecule_indices is not None:
            for i in molecule_indices:
                st.subheader(f"Molecule {i}")

                with st.form(key=f"molecule_{i}_form"):

                    plane_input = st.text_input("Enter crystal plane as h, k, l separated by spaces")

                    # Add a multi-select list for atoms not to reflect
                    atom_labels = get_atom_labels(modified_atoms, molecules[i - 1])
                    atoms_not_to_reflect = st.multiselect("Select atom indices not to reflect (Optional)",
                                                          options=atom_labels, format_func=lambda x: x[1])

                    if st.form_submit_button(f"Set Parameters for Molecule {i}"):
                        hkl = np.array([int(val) for val in plane_input.split()])
                        local_indices = find_local_indices(molecules[i - 1],
                                                           [atom_idx for atom_idx, _ in atoms_not_to_reflect])
                        st.session_state.reflection_parameters[i - 1] = (hkl, local_indices)

                        # st.write(st.session_state.reflection_parameters[i - 1])

        if st.button("Apply Reflections"):
            chosen_molecules = [molecules[i - 1] for i in molecule_indices]
            chosen_reflection_parameters = [st.session_state.reflection_parameters[i - 1] for i in molecule_indices]

            for molecule, (hkl, not_to_reflect) in zip(chosen_molecules, chosen_reflection_parameters):
                mol_obj = get_molecule_object(modified_atoms, molecule)
                normal_vector, origin_point = plane_params_from_hkl(modified_atoms, hkl)
                modified_atoms = reflect_molecules(modified_atoms, molecule, mol_obj, normal_vector, origin_point,
                                                   not_to_reflect)

            # Save modified atoms to temporary files
            output_suffix = "_reflected"
            file_name = os.path.splitext(st.session_state.file_name)[0]

            create_aims_download_file(modified_atoms, file_name, output_suffix)

            create_labelled_download_file(modified_atoms, file_name, output_suffix)

    if translation_option:
        render_section_header("Translation", kicker="Structure Workspace")

        translate_type = st.selectbox("Select Translation Type", (
            "Molecules", "Atoms"))


        # scope_choice = st.selectbox("Do you want to translate molecules or atoms?", ("molecules", "atoms"))
        # st.session_state.scope_choice = scope_choice

        if translate_type == "Molecules":
            scope_choice = "molecules"
            selected_indices = st.multiselect("Select molecule indices to translate",
                                              range(1, len(molecules) + 1))

            with st.form(key="translation_form"):

                axes_choice = st.selectbox("Enter the axes for translation",
                                           ("x", "y", "z", "xy", "xz", "yz", "xyz", "custom"))

                if axes_choice == "custom":
                    custom_axis = st.text_input("Enter custom axis as x, y, z separated by spaces")
                    axis = np.array([float(val) for val in custom_axis.split()])
                    distance = st.number_input("Enter the translation distance", step=0.1)
                    translation_distances = {tuple(axis): distance}
                else:
                    translation_distances = {}
                    for axis in axes_choice:
                        distance = st.number_input(f"Enter the translation distance along {axis}-axis",
                                                   key=f"{axis}_translation", step=0.1)
                        translation_distances[axis] = distance

                if st.form_submit_button("Apply Translation"):
                    modified_atoms = translate_molecule(modified_atoms, molecules, scope_choice, selected_indices,
                                                        axes_choice,
                                                        translation_distances)

                    # Save modified atoms to temporary files
                    output_suffix = "_translated"

                    create_aims_download_file(modified_atoms, file_name, output_suffix)

                    create_labelled_download_file(modified_atoms, file_name, output_suffix)

                with st.expander("See structure"):
                    atoms_to_speck(modified_atoms, "translation")

        if translate_type == "Atoms":
            scope_choice = "atoms"
            selected_indices_string = st.text_input(
                "Enter atom indices to translate (separated by spaces or commas)")
            if selected_indices_string:
                selected_indices = [int(index.strip()) for index in
                                    selected_indices_string.replace(',', ' ').split() if index.strip()]

                with st.form(key="translation_form"):

                    axes_choice = st.selectbox("Enter the axes for translation",
                                               ("x", "y", "z", "xy", "xz", "yz", "xyz", "custom"))

                    if axes_choice == "custom":
                        custom_axis = st.text_input("Enter custom axis as x, y, z separated by spaces")
                        axis = np.array([float(val) for val in custom_axis.split()])
                        distance = st.number_input("Enter the translation distance", step=0.1)
                        translation_distances = {tuple(axis): distance}
                    else:
                        translation_distances = {}
                        for axis in axes_choice:
                            distance = st.number_input(f"Enter the translation distance along {axis}-axis",
                                                       key=f"{axis}_translation", step=0.1)
                            translation_distances[axis] = distance

                    if st.form_submit_button("Apply Translation"):
                        modified_atoms = translate_molecule(modified_atoms, molecules, scope_choice, selected_indices,
                                                            axes_choice,
                                                            translation_distances)

                        # Save modified atoms to temporary files
                        output_suffix = "_translated"

                        create_aims_download_file(modified_atoms, file_name, output_suffix)

                        create_labelled_download_file(modified_atoms, file_name, output_suffix)

                    with st.expander("See structure"):
                        atoms_to_speck(modified_atoms, "translation")

    if delete_option:
        render_section_header("Delete Molecules", kicker="Structure Workspace")
        with st.form(key="delete_form"):

            selected_indices = st.multiselect("Select molecule indices to delete",
                                              range(1, len(molecules) + 1))

            if st.form_submit_button("Apply Deletion"):
                modified_atoms = delete_molecules(modified_atoms, molecules, selected_indices)


                # Save modified atoms to temporary files
                output_suffix = "_deleted"

                create_aims_download_file(modified_atoms, file_name, output_suffix)

                create_labelled_download_file(modified_atoms, file_name, output_suffix)

            with st.expander("See structure"):
                atoms_to_speck(modified_atoms, "deletion")

    if symmetry_option:
        render_section_header("Symmetrize structure", kicker="Structure Workspace")
        with st.form(key="symmetry_form"):
            symprec_lower = st.number_input("Enter the lower bound for tolerance", value=1e-3, step=1e-3, format="%.4f")
            symprec_upper = st.number_input("Enter the upper bound for tolerance", value=1e-1, step=1e-3, format="%.4f")
            symprec_list = np.linspace(symprec_lower, symprec_upper, 6)
            angle_tol = st.number_input("Enter a tolerance for angles", value=5.0, step=1e-3, format="%.4f")

            if symprec_lower > symprec_upper:
                st.error("Lower bound should be less than or equal to the upper bound.")

            form_submitted = st.form_submit_button("Get Space Groups")

        # Update space groups if form_submitted is True or if space groups have not been calculated yet
        if form_submitted or 'space_groups' not in st.session_state:
            # Here, calculate_space_groups should return both symprec_list and space_groups
            st.session_state['symprec_list'], st.session_state['space_groups'] = calculate_space_groups(modified_atoms,
                                                                                                        symprec_lower,
                                                                                                        symprec_upper,
                                                                                                        angle_tol)
            st.session_state['space_group_strings'] = get_space_group_strings(st.session_state['symprec_list'],
                                                                              st.session_state['space_groups'])

        # Ensure that 'space_group_strings' and 'symprec_list' are available for the dropdown and button actions
        if 'space_group_strings' in st.session_state and 'symprec_list' in st.session_state:
            selected_string = st.selectbox("Select the desired space group",
                                          options=st.session_state.space_group_strings,
                                          index=0)

            if st.button("Generate CIF"):
                try:
                    file_name_m = os.path.splitext(file_name)[0]
                    output_cif_file = f"{file_name_m}_high_symm.cif"
                    selected_symprec = extract_symprec_from_string(selected_string)
                    pymatgen_structure = generate_symmetrized_structure(modified_atoms, selected_symprec, angle_tol)

                    cif_writer = CifWriter(pymatgen_structure, symprec=selected_symprec, angle_tolerance=angle_tol)

                    with tempfile.NamedTemporaryFile(mode="w+", suffix=".cif", delete=False) as output_file:
                        cif_writer.write_file(output_file.name)  # Write the content to the temporary file
                        output_file.seek(0)
                        output_content = output_file.read()
                        st.markdown(get_download_link(f"{output_cif_file}", output_content), unsafe_allow_html=True)
                except ValueError as e:
                    st.error(f"An error occurred when processing the selected space group: {e}")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")

    if ADP_table_option:
        render_section_header("Extract ADP from CIF", kicker="Structure Workspace")

        try:
            uij_df = extract_Uij_from_cif(file_buffer)
            uij_df_v = calculate_ellipsoid_volumes(uij_df, ignore_atoms=None)

            st.dataframe(uij_df_v, hide_index=True, use_container_width=True)
        except ValueError as e:
            st.error(f"An error occurred when trying to extract the ADP values: {e}")

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

    if PDF_option:
        render_section_header("Simulate pair distribution function", kicker="Structure Workspace")

        # -------------------------------------------------------------------------
        # 1) Parameter sliders
        # -------------------------------------------------------------------------
        qmin, qmax = st.slider("q (Å⁻¹)", 0, 25, (1, 20))
        rmin, rmax = st.slider("r (Å)", 0.0, 30.0, (0.1, 20.0))

        # -------------------------------------------------------------------------
        # 2) Build & write a clean CIF
        # -------------------------------------------------------------------------
        pymatgen_structure = generate_symmetrized_structure(modified_atoms, 0.01, 0.1)
        tmpdir = os.path.join(os.getcwd(), "pdfanalysis_temp")
        path = Path(tmpdir) / "structure_clean.cif"
        os.makedirs(tmpdir, exist_ok=True)
        CifWriter(pymatgen_structure).write_file(str(path))

        # -------------------------------------------------------------------------
        # 3) Compute the simulated PDF
        # -------------------------------------------------------------------------
        diffpy_structure = loadStructure(str(path))
        r1, g1 = calculate_pdf(
            diffpy_structure,
            diffpy_structure_attributes={"Uisoequiv": 0.01},
            pdf_calculator_kwargs={
                "qmin": qmin,
                "qmax": qmax,
                "rmin": rmin,
                "rmax": rmax,
                "qdamp": 0.06,
                "qbroad": 0.06
            }
        )

        # 4) DataFrame & expander
        df_pdf = pd.DataFrame({"r (Å)": r1, "G_sim(r)": g1})
        with st.expander("View simulated PDF data"):
            st.dataframe(df_pdf, use_container_width= True, hide_index = True)

        with st.expander("View simulated PDF"):
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_pdf["r (Å)"],
                y=df_pdf["G_sim(r)"],
                mode="lines",
                name="Simulated G(r)"
            ))

            fig.update_layout(
                xaxis_title="r (Å)", yaxis_title="G(r)",
                xaxis=dict(
                    range=[rmin, rmax],
                    tickfont=dict(size=20, color="black"),
                    title_font=dict(size=20, color="black")
                ),
                yaxis=dict(
                    tickfont=dict(size=20, color="black"),
                    title_font=dict(size=20, color="black")
                ),
                font=dict(color="black"),
                margin=dict(t=40, b=40, l=40, r=40),
                legend=dict(yanchor="top", y=0.99, xanchor="center", x=0.8)
            )

            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.subheader("Optional: plot Radial Distribution Function")

        # 1) Gather inputs
        rdf_atoms = st.text_input("Enter atom labels (comma-sep)", "Pb, I")
        atom_list = [a.strip() for a in rdf_atoms.split(",") if a.strip()]
        all_pairs = list(combinations_with_replacement(atom_list, 2))
        bins = st.slider("Number of bins", 50, 500, 200)
        rdf_w_weights = st.radio("Scale by atomic weights?",["True","False"])

        if rdf_w_weights == "True":
            weight = True
        else:
            weight=False

        # 2) Choose library
        lib = st.radio("Choose plotting library", ["Matplotlib", "Plotly"])

        # 3) Load the appropriate config UI
        if lib == "Matplotlib":
            config = load_or_create_plot_config_matplotlib(all_pairs)
        else:
            config = load_or_create_plot_config(all_pairs)

        # 4) Compute & display
        if st.button("Compute RDF"):
            if lib == "Matplotlib":
                fig, df_all = plot_rdf_pdf_matplotlib(
                    atom_list, modified_atoms, df_pdf, rmin, rmax, bins,
                    compute_rdf_weighted, config, weight
                )
                st.pyplot(fig)

                # Download buttons for Matplotlib
                buf_png = io.BytesIO()
                fig.savefig(buf_png, format='png', bbox_inches='tight')
                st.download_button(
                    "Download as PNG", buf_png.getvalue(),
                    file_name="rdf_plot.png", mime="image/png"
                )

                buf_pdf = io.BytesIO()
                fig.savefig(buf_pdf, format='pdf', bbox_inches='tight')
                st.download_button(
                    "Download as PDF", buf_pdf.getvalue(),
                    file_name="rdf_plot.pdf", mime="application/pdf"
                )

            else:  # Plotly
                fig_rdf, df_all = plot_rdf_pdf(
                    atom_list, modified_atoms, df_pdf, rmax, bins,
                    compute_rdf_weighted, config, weight
                )
                st.plotly_chart(fig_rdf, use_container_width=True)

                # # Download buttons for Plotly
                # png_bytes = fig_rdf.to_image(format="png")
                # st.download_button(
                #     "Download as PNG", png_bytes,
                #     file_name="rdf_plot.png", mime="image/png"
                # )
                #
                # pdf_bytes = fig_rdf.to_image(format="pdf")
                # st.download_button(
                #     "Download as PDF", pdf_bytes,
                #     file_name="rdf_plot.pdf", mime="application/pdf"
                # )

            # Show data table
            with st.expander("View simulated RDF data"):
                st.dataframe(df_all, use_container_width=True, hide_index=True)


        st.divider()
        st.subheader("Optional: Compare Experimental vs. Simulated PDF")


        # -------------------------------------------------------------------------
        # 5) Optionally load experimental .gr
        # -------------------------------------------------------------------------=
        # Choose normalization method
        norm_method = st.selectbox(
            "Normalize y-axis before fitting using:",
            ["Z-score (mean 0, std 1)", "Min-max [0,1]"],
            index=0,
            key="pdf_norm_method"
        )

        exp_file = st.file_uploader("Optionally upload experimental .gr file", type=["gr"], key="gr_uploader")
        if exp_file is not None:
            content = exp_file.read().decode("utf-8", errors="ignore").splitlines()
            idx = next((i for i, L in enumerate(content) if L.strip().startswith("#### start data")), None)
            if idx is None:
                st.error("Couldn't find '#### start data' in the .gr file.")
            else:
                data_lines = content[idx + 3:]
                df_exp = pd.read_csv(
                    io.StringIO("\n".join(data_lines)),
                    delim_whitespace=True, header=None, names=["r", "G_exp"]
                ).pipe(lambda d: d[(d.r >= rmin) & (d.r <= rmax)].reset_index(drop=True))

                # interpolate simulation onto experimental r-grid
                g_sim_interp = np.interp(df_exp.r, r1, g1)

                # -------------------------------
                # 1) Normalize y-data for fitting
                # -------------------------------
                eps = 1e-12

                if norm_method.startswith("Z-score"):
                    # stats for original (needed for back-transform)
                    mu_x, sig_x = float(np.mean(g_sim_interp)), float(np.std(g_sim_interp))
                    mu_y, sig_y = float(np.mean(df_exp.G_exp)), float(np.std(df_exp.G_exp))
                    sig_x = sig_x if sig_x > eps else eps
                    sig_y = sig_y if sig_y > eps else eps

                    x_norm = (g_sim_interp - mu_x) / sig_x
                    y_norm = (df_exp.G_exp - mu_y) / sig_y


                    # mapping from normalized fit back to original:
                    # y_fit = mu_y + sig_y * (a * (x - mu_x)/sig_x + b)
                    def back_transform(a_hat, b_hat, x_orig):
                        A_eff = (sig_y * a_hat) / sig_x
                        B_eff = mu_y + sig_y * b_hat - A_eff * mu_x
                        return A_eff, B_eff, A_eff * x_orig + B_eff

                else:  # Min-max
                    x_min, x_max = float(np.min(g_sim_interp)), float(np.max(g_sim_interp))
                    y_min, y_max = float(np.min(df_exp.G_exp)), float(np.max(df_exp.G_exp))
                    x_rng = (x_max - x_min) if (x_max - x_min) > eps else eps
                    y_rng = (y_max - y_min) if (y_max - y_min) > eps else eps

                    x_norm = (g_sim_interp - x_min) / x_rng
                    y_norm = (df_exp.G_exp - y_min) / y_rng


                    # mapping from normalized fit back to original:
                    # y_fit = y_min + y_rng * (a * (x - x_min)/x_rng + b)
                    def back_transform(a_hat, b_hat, x_orig):
                        A_eff = (y_rng * a_hat) / x_rng
                        B_eff = y_min + y_rng * b_hat - A_eff * x_min
                        return A_eff, B_eff, A_eff * x_orig + B_eff

                # ---------------------------------------
                # 2) Fit in normalized space: y' = a x' + b
                # ---------------------------------------
                from scipy.optimize import curve_fit


                def linear_model(G_sim_norm, a, b):
                    return a * G_sim_norm + b


                popt, pcov = curve_fit(linear_model, x_norm, y_norm, p0=[1.0, 0.0])
                a_norm, b_norm = map(float, popt)

                # ---------------------------------------
                # 3) Back-transform fit to original units
                # ---------------------------------------
                A_eff, B_eff, g_fit = back_transform(a_norm, b_norm, g_sim_interp)
                residual = df_exp.G_exp - g_fit

                # Compute correlations (both original and normalized, optional)
                pcc_value_orig = compute_pcc((df_exp.r, df_exp.G_exp), (df_exp.r, g_sim_interp))
                pcc_value_norm = compute_pcc((df_exp.r, y_norm), (df_exp.r, x_norm))

                # For reference, the normalized fitted values (if you want to display)
                g_fit_norm = linear_model(x_norm, a_norm, b_norm)

                df_combined = pd.DataFrame({
                    "r (Å)": df_exp.r,
                    "G_sim": g_sim_interp,
                    "G_exp": df_exp.G_exp,
                    "G_fit": g_fit,  # fit mapped back to original units
                    "Residual": residual,
                    "G_sim (norm)": x_norm,
                    "G_exp (norm)": y_norm,
                    "G_fit (norm)": g_fit_norm,
                })

                with st.expander("View combined PDF data"):
                    st.dataframe(df_combined, use_container_width=True, hide_index=True)

                # Optional: show fit parameters
                with st.expander("Fit details (normalized → original)"):
                    st.markdown(
                        f"- Normalized fit: y' = **{a_norm:.4f}** · x' + **{b_norm:.4f}**\n"
                        f"- Effective original-units mapping: y ≈ **{A_eff:.4f}** · x + **{B_eff:.4f}**\n"
                        f"- PCC (original): **{pcc_value_orig:.4f}**, PCC (normalized): **{pcc_value_norm:.4f}**"
                    )

        # --- 6) Plotting: customization, trigger button, downloads, and interactive Plotly ---
        # Load saved customization if provide
            with st.expander("Plot customization"):
                config_file = st.file_uploader("Upload plot customization config (.json)", type=["json"],
                                               key="config_uploader")
                if config_file:
                    import json

                    config = json.load(config_file)
                else:
                    config = {}

                sim_color = st.color_picker("Simulated line color", config.get("sim_color", "#1f77b4"))
                sim_width = st.slider("Simulated line width", 0.5, 5.0, config.get("sim_width", 2.0), step=0.1)
                sim_ls = st.selectbox("Simulated line style", ["-", "--", "-.", ":"],
                                      index=["-", "--", "-.", ":"].index(config.get("sim_ls", "-")))
                sim_opacity = st.slider("Simulated line opacity", 0.0, 1.0, config.get("sim_opacity", 1.0), step=0.05)
                exp_color = st.color_picker("Experimental line color", config.get("exp_color", "#ff7f0e"))
                exp_width = st.slider("Experimental line width", 0.5, 5.0, config.get("exp_width", 2.0), step=0.1)
                exp_ls = st.selectbox("Experimental line style", ["-", "--", "-.", ":"],
                                      index=["-", "--", "-.", ":"].index(config.get("exp_ls", "--")))
                exp_opacity = st.slider("Experimental line opacity", 0.0, 1.0, config.get("exp_opacity", 1.0), step=0.05)
                bar_color = st.color_picker("Residual bar color", config.get("bar_color", "#7f7f7f"))
                spline_width = st.slider("Fitted line width", 0.5, 5.0, config.get("spline_width", 1.5), step=0.1)
                text_size = st.slider("Text size", 8, 20, config.get("text_size", 12))
                text_style = st.selectbox("Text style", ["normal", "bold", "italic"],
                                          index=["normal", "bold", "italic"].index(config.get("text_style", "normal")))
                axis_lw = st.slider("Axis spine linewidth", 0.5, 5.0, config.get("axis_linewidth", 1.0), step=0.1)
                tick_lw = st.slider("Tick mark linewidth", 0.5, 5.0, config.get("tick_linewidth", 1.0), step=0.1)
                hide_legends   = st.checkbox("Hide legends", config.get("hide_legends", False))
                show_sim = st.checkbox("Show simulated data", config.get("show_sim", True))
                show_exp = st.checkbox("Show experimental data", config.get("show_exp", True))
                show_res = st.checkbox("Show residual data", config.get("show_res", True))
                aspect_opt = st.selectbox("Aspect ratio", ["auto", "equal", "custom"],
                                          index=["auto", "equal", "custom"].index(config.get("aspect_option", "equal")))
                aspect_val = config.get("aspect_val", 1.0)
                if aspect_opt == "custom":
                    aspect_val = st.number_input("Custom aspect ratio (y/x)", 0.1, 10.0, aspect_val, step=0.1)
                # axis limits & ticks
                x_min = st.number_input("X-axis min", value=config.get("x_min", rmin), step=0.1)
                x_max = st.number_input("X-axis max", value=config.get("x_max", rmax), step=0.1)
                y_min = st.number_input("Y-axis min", value=config.get("y_min", float(df_combined.G_sim.min()-1.5)), step=0.1)
                y_max = st.number_input("Y-axis max", value=config.get("y_max", float(df_combined.G_sim.max())), step=0.1)
                tick_gap_x = st.number_input("X-axis tick interval", value=config.get("tick_gap_x", (x_max - x_min) / 5),
                                             step=0.1)
                tick_gap_y = st.number_input("Y-axis tick interval", value=config.get("tick_gap_y", (y_max - y_min) / 5),
                                             step=0.1)
                plot_title = st.text_input("Plot title",
                                           value=config.get("plot_title", "PDF"))
                show_fit = st.checkbox("Plot fitted data", config.get("show_fit", False))

                # Download current customization as JSON
                config_out = {
                    "sim_color": sim_color, "sim_width": sim_width, "sim_ls": sim_ls, "sim_opacity": sim_opacity,
                    "exp_color": exp_color, "exp_width": exp_width, "exp_ls": exp_ls, "exp_opacity": exp_opacity,
                    "bar_color": bar_color, "spline_width": spline_width, "text_size": text_size, "text_style": text_style,
                    "axis_linewidth": axis_lw, "tick_linewidth": tick_lw, "hide_legends": hide_legends,
                    "show_sim": show_sim, "show_exp": show_exp, "show_res": show_res,
                    "aspect_option": aspect_opt, "aspect_val": aspect_val,
                    "x_min": x_min, "x_max": x_max, "y_min": y_min, "y_max": y_max,
                    "tick_gap_x": tick_gap_x, "tick_gap_y": tick_gap_y,
                    "plot_title": plot_title, "show_fit": show_fit
                }
                st.download_button(
                    "Download customization as JSON",
                    data=json.dumps(config_out, indent=2),
                    file_name="plot_config.json",
                    mime="application/json"
                )

            plot_btn = st.button("Generate Plot")
            if plot_btn:
                import matplotlib.style
                matplotlib.style.use('classic')
                import matplotlib.ticker as ticker

                fig, ax = plt.subplots()
                # apply spine & tick widths
                for s in ax.spines.values():
                    s.set_linewidth(axis_lw)
                ax.tick_params(width=tick_lw)

                # plot based on toggles
                if show_sim:
                    ax.plot(r1, g1, color=sim_color, linewidth=sim_width,
                            linestyle=sim_ls, alpha=sim_opacity, label="Simulated")
                if exp_file and show_exp:
                    ax.plot(df_combined["r (Å)"], df_combined["G_exp (norm)"],
                            color=exp_color, linewidth=exp_width,
                            linestyle=exp_ls, alpha=exp_opacity, label="Experimental")
                if exp_file and show_res:
                    baseline = min(np.min(g1), df_combined["G_exp"].min()) - 0.5
                    bar_w = (x_max - x_min) / (len(df_combined) * 1.5)
                    ax.bar(df_combined["r (Å)"], df_combined["Residual"],
                           width=bar_w, bottom=baseline, color=bar_color,
                           alpha=0.6, label="Residual")
                if exp_file and show_fit:
                    ax.plot(df_combined["r (Å)"], df_combined["G_fit"],
                            color="gray", linewidth=spline_width,
                            linestyle=":", alpha=0.8, label="Fitted")

                # axes limits, ticks, aspect
                ax.set_xlim(x_min, x_max);
                ax.set_ylim(y_min, y_max)
                ax.xaxis.set_major_locator(ticker.MultipleLocator(tick_gap_x))
                ax.yaxis.set_major_locator(ticker.MultipleLocator(tick_gap_y))
                ax.set_aspect(aspect_val)

                # labels & title
                title_kw = {"fontsize": text_size + 2}
                if text_style == "bold":   title_kw["fontweight"] = "bold"
                if text_style == "italic": title_kw["fontstyle"] = "italic"
                ax.set_title(plot_title, **title_kw)
                label_kw = {"fontsize": text_size}
                if text_style == "bold":   label_kw["fontweight"] = "bold"
                if text_style == "italic": label_kw["fontstyle"] = "italic"
                ax.set_xlabel(r"$r\ (\mathrm{\AA})$", **label_kw)
                ax.set_ylabel(r"$G(r)\ (\mathrm{\AA}^{-2})$", **label_kw)

                ax.annotate(
                    f"PCC = {pcc_value_norm:.2f}",
                    xy=(0.82, 0.1),
                    xycoords="axes fraction",
                    ha="center",
                    va="center",
                    fontsize=text_size,
                    fontweight="bold" if text_style == "bold" else "normal",
                    fontstyle="italic" if text_style == "italic" else "normal",
                    # bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", alpha=0.6)
                )

                ax.tick_params(labelsize=text_size)
                if not hide_legends:
                    ax.legend(fontsize=text_size)
                st.pyplot(fig)

                # downloads
                base_name = os.path.splitext(exp_file.name)[0]
                buf_pdf = io.BytesIO()
                fig.savefig(buf_pdf, format="pdf", dpi=300, bbox_inches="tight")
                buf_pdf.seek(0)
                st.download_button("Download PDF", buf_pdf, f"{base_name}.pdf", "application/pdf")
                buf_png = io.BytesIO()
                fig.savefig(buf_png, format="png", dpi=300, bbox_inches="tight")
                buf_png.seek(0)
                st.download_button("Download PNG", buf_png, f"{base_name}.png", "image/png")

        # Interactive Plotly chart
            if st.checkbox("Show interactive Plotly chart"):
                fig_int = go.Figure()
                fig_int.add_trace(go.Scatter(
                    x=df_combined["r (Å)"], y=df_combined["G_sim"],
                    mode="lines", name="Simulated G(r)",
                    line=dict(color=sim_color, width=sim_width, dash='solid'),
                    opacity=sim_opacity
                ))
                fig_int.add_trace(go.Scatter(
                    x=df_combined["r (Å)"], y=df_combined["G_exp"],
                    mode="lines", name="Experimental G(r)",
                    line=dict(color=exp_color, width=exp_width, dash='solid'),
                    opacity=exp_opacity
                ))
                fig_int.add_trace(go.Bar(
                    x=df_combined["r (Å)"], y=df_combined["Residual"],
                    base=(min(df_combined["G_sim"].min(), df_combined["G_exp"].min()) - 0.5), name="Residual",
                    marker_color=bar_color, opacity=0.6
                ))
                if show_fit:
                    fig_int.add_trace(go.Scatter(
                        x=df_combined["r (Å)"], y=df_combined["G_fit"],
                        mode="lines", name="Fitted G(r)",
                        line=dict(color="gray", width=spline_width, dash="dot"),
                        opacity=0.8
                    ))
                fig_int.update_layout(
                    xaxis_title="r (Å)", yaxis_title="G(r)",
                    xaxis=dict(
                        range=[x_min, x_max],
                        tickfont=dict(size=text_size+12, color="black"),
                        title_font=dict(size=text_size+12, color="black")
                    ),
                    yaxis=dict(
                        range=[y_min, y_max],
                        tickfont=dict(size=text_size+12, color="black"),
                        title_font=dict(size=text_size+12, color="black")
                    ),
                    font=dict(color="black"),
                    margin=dict(t=40, b=40, l=40, r=40),
                    legend=dict(yanchor="top", y=0.99, xanchor="center", x=0.8)
                )
                st.plotly_chart(fig_int, use_container_width=True)

        st.divider()
        st.subheader("Optional: Convert Reduced PDF to g(r)")

        exp_file2 = st.file_uploader(
            "Upload experimental .gr file",
            type=["gr"],
            key="gr_uploader2",
        )

        if exp_file2 is not None:
            content = exp_file2.read().decode("utf-8", errors="ignore").splitlines()
            idx = next((i for i, L in enumerate(content) if L.strip().startswith("#### start data")), None)

            if idx is None:
                st.error("Couldn't find '#### start data' in the .gr file.")
            else:
                data_lines = content[idx + 3:]

                try:
                    df_exp2 = pd.read_csv(
                        io.StringIO("\n".join(data_lines)),
                        sep=r"\s+",
                        header=None,
                        names=["r", "G_exp"],
                    ).pipe(lambda d: d[(d.r >= rmin) & (d.r <= rmax)].reset_index(drop=True))

                    fig_pdf = px.line(
                        df_exp2,
                        x="r",
                        y="G_exp",
                        labels={"r": "r (Å)", "G_exp": "G(r)"},
                        title="Uploaded Reduced PDF",
                    )
                    fig_pdf.update_layout(
                        height=450,
                        template="plotly_white",
                        margin=dict(l=20, r=20, t=50, b=20),
                    )
                    fig_pdf.update_traces(line=dict(width=2))
                    st.plotly_chart(fig_pdf, use_container_width=True)

                    st.markdown("### Number density, ρ₀")

                    cif_file = st.file_uploader(
                        "Optional: Upload CIF file to infer ρ₀ automatically",
                        type=["cif"],
                        key="cif_uploader_rho0",
                    )

                    rho0_auto = None
                    if cif_file is not None:
                        try:
                            rho0_auto, n_atoms, volume = infer_rho0_from_cif(cif_file.read())
                            st.success(
                                f"Inferred from CIF: ρ₀ = {rho0_auto:.6f} atoms/Å³ "
                                f"(N = {n_atoms}, V = {volume:.3f} Å³)"
                            )
                        except Exception as e:
                            st.warning(f"Could not infer ρ₀ from CIF: {e}")

                    use_auto_rho0 = st.checkbox(
                        "Use CIF-inferred ρ₀",
                        value=rho0_auto is not None,
                        disabled=rho0_auto is None,
                        key="use_auto_rho0_checkbox",
                    )

                    rho0_manual = st.number_input(
                        "Manual ρ₀ (atoms/Å³)",
                        min_value=0.0,
                        value=float(rho0_auto) if rho0_auto is not None else 0.05,
                        step=0.001,
                        format="%.6f",
                        key="rho0_input",
                    )

                    rho0 = rho0_auto if (use_auto_rho0 and rho0_auto is not None) else rho0_manual
                    st.info(f"Using ρ₀ = {rho0:.6f} atoms/Å³")

                    if st.button("Convert reduced PDF to g(r)", key="convert_pdf_to_gr"):
                        st.session_state["df_gr_converted"] = reduced_pdf_to_gr(df_exp2, rho0)
                        st.session_state["rho0_used_for_gr"] = rho0

                    if "df_gr_converted" in st.session_state:
                        df_gr = st.session_state["df_gr_converted"]
                        rho0_used = st.session_state.get("rho0_used_for_gr", rho0)

                        fig_gr = px.line(
                            df_gr,
                            x="r",
                            y="g_r",
                            labels={"r": "r (Å)", "g_r": "g(r)"},
                            title="Converted Radial Distribution Function",
                        )
                        fig_gr.update_layout(
                            height=450,
                            template="plotly_white",
                            margin=dict(l=20, r=20, t=50, b=20),
                        )
                        fig_gr.update_traces(line=dict(width=2))
                        st.plotly_chart(fig_gr, use_container_width=True)

                        st.markdown("### Integrate g(r) over an r-window")

                        c1, c2 = st.columns(2)
                        with c1:
                            r_int_min = st.number_input(
                                "Integration r min (Å)",
                                min_value=float(df_gr["r"].min()),
                                max_value=float(df_gr["r"].max()),
                                value=float(df_gr["r"].min()),
                                step=0.1,
                                key="gr_int_min",
                            )
                        with c2:
                            r_int_max = st.number_input(
                                "Integration r max (Å)",
                                min_value=float(df_gr["r"].min()),
                                max_value=float(df_gr["r"].max()),
                                value=min(float(df_gr["r"].min()) + 2.0, float(df_gr["r"].max())),
                                step=0.1,
                                key="gr_int_max",
                            )

                        if st.button("Integrate g(r)", key="integrate_gr_button"):
                            if r_int_max <= r_int_min:
                                st.warning("Integration r max must be greater than r min.")
                            else:
                                res = integrate_gr_window(df_gr, r_int_min, r_int_max, rho0=rho0_used)
                                if res is None:
                                    st.warning("Not enough points in the selected r-window for integration.")
                                else:
                                    st.write(
                                        f"**∫ g(r) dr** from {r_int_min:.3f} to {r_int_max:.3f} Å = "
                                        f"{res['integral_gdr']:.6f}"
                                    )
                                    st.write(
                                        f"**4πρ₀ ∫ r²g(r) dr** from {r_int_min:.3f} to {r_int_max:.3f} Å = "
                                        f"{res['coordination_like']:.6f}"
                                    )

                                    fig_window = px.line(
                                        df_gr,
                                        x="r",
                                        y="g_r",
                                        labels={"r": "r (Å)", "g_r": "g(r)"},
                                        title="g(r) with Integration Window",
                                    )
                                    fig_window.add_vrect(
                                        x0=r_int_min,
                                        x1=r_int_max,
                                        opacity=0.2,
                                        line_width=0,
                                    )
                                    fig_window.update_layout(
                                        height=450,
                                        template="plotly_white",
                                        margin=dict(l=20, r=20, t=50, b=20),
                                    )
                                    fig_window.update_traces(line=dict(width=2))
                                    st.plotly_chart(fig_window, use_container_width=True)

                        csv_data = df_gr.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "Download g(r) as CSV",
                            data=csv_data,
                            file_name="converted_gr.csv",
                            mime="text/csv",
                            key="download_gr_csv",
                        )

                except Exception as e:
                    st.error(f"Failed to parse or convert file: {e}")

    # if PDF_fit_option:
    #
    #     st.header("Fit simulated PDF to experimental data", divider="violet")
    #
    #     st.markdown(
    #         "Upload experimental PDF data (two columns: r(Å), G(r)). "
    #         "We'll perturb atomic coordinates to maximize Pearson correlation."
    #     )
    #
    #     uploaded_exp_pdf = st.file_uploader(
    #         "Experimental PDF file (.txt, .dat, .csv)",
    #         type=["txt", "dat", "csv"],
    #         accept_multiple_files=False,
    #     )
    #
    #     # Reuse sliders to enforce identical r/q ranges between sim and exp
    #     qmin_fit, qmax_fit = st.slider("q for fit (Å⁻¹)", 0, 25, (1, 20))
    #     rmin_fit, rmax_fit = st.slider("r for fit (Å)", 0.0, 30.0, (0.1, 20.0))
    #
    #     # Optimization controls
    #     max_disp = st.number_input(
    #         "Max |Δr| per Cartesian component (Å) for refinement bounds",
    #         min_value=0.01,
    #         max_value=1.0,
    #         value=0.2,
    #         step=0.01,
    #         help="Each x/y/z coord is allowed to move ± this amount from the starting structure.",
    #     )
    #
    #     n_iter_hint = st.number_input(
    #         "Max optimization iterations",
    #         min_value=10,
    #         max_value=500,
    #         value=80,
    #         step=10,
    #     )
    #
    #     run_fit = st.button("Run PDF Fit")
    #
    #     if uploaded_exp_pdf is not None and run_fit:
    #         # -------------------------------------------------
    #         # 1) Read experimental PDF
    #         # -------------------------------------------------
    #         # try flexible read: CSV or whitespace
    #         raw = uploaded_exp_pdf.read()
    #         try:
    #             df_exp = pd.read_csv(io.BytesIO(raw), sep=None, engine="python", header=None)
    #         except Exception:
    #             df_exp = pd.read_csv(io.BytesIO(raw), delim_whitespace=True, header=None)
    #
    #         # Expect first 2 cols: r, G(r)
    #         df_exp = df_exp.rename(columns={0: "r (Å)", 1: "G_exp(r)"})
    #         df_exp = df_exp.sort_values(by="r (Å)").reset_index(drop=True)
    #
    #         # limit to chosen r-window
    #         df_exp_window = df_exp[(df_exp["r (Å)"] >= rmin_fit) & (df_exp["r (Å)"] <= rmax_fit)].copy()
    #         r_exp = df_exp_window["r (Å)"].to_numpy()
    #         g_exp = df_exp_window["G_exp(r)"].to_numpy()
    #
    #         # -------------------------------------------------
    #         # 2) Set up initial structure and bounds
    #         # -------------------------------------------------
    #         base_atoms = modified_atoms.copy()
    #         init_positions = base_atoms.get_positions()  # (N,3)
    #         x0 = init_positions.flatten()  # 3N vector
    #
    #         # bounds: each coord ± max_disp
    #         bounds = []
    #         for val in x0:
    #             bounds.append((val - max_disp, val + max_disp))
    #
    #         fit_settings = {
    #             "qmin": qmin_fit,
    #             "qmax": qmax_fit,
    #             "rmin": rmin_fit,
    #             "rmax": rmax_fit,
    #             "qdamp": 0.06,
    #             "qbroad": 0.06,
    #             "uiso": 0.01,
    #         }
    #
    #         # -------------------------------------------------
    #         # 3) Run optimization
    #         # -------------------------------------------------
    #         result = minimize(
    #             pdf_mismatch_cost,
    #             x0,
    #             args=(base_atoms, r_exp, g_exp, fit_settings),
    #             method="L-BFGS-B",
    #             bounds=bounds,
    #             options={"maxiter": int(n_iter_hint)},
    #         )
    #
    #         # -------------------------------------------------
    #         # 4) Build refined structure from result
    #         # -------------------------------------------------
    #         refined_atoms = base_atoms.copy()
    #         refined_atoms.set_positions(result.x.reshape((-1, 3)))
    #
    #         # Final simulated PDF from refined structure
    #         r_fit_sim, g_fit_sim = simulate_pdf_from_atoms(
    #             refined_atoms,
    #             qmin=qmin_fit,
    #             qmax=qmax_fit,
    #             rmin=rmin_fit,
    #             rmax=rmax_fit,
    #             qdamp=0.06,
    #             qbroad=0.06,
    #             uiso=0.01,
    #         )
    #
    #         # Interpolate refined sim onto experimental grid
    #         g_fit_interp = interpolate_to_common_grid(r_exp, r_fit_sim, g_fit_sim)
    #
    #         # Pearson r after fit
    #         valid_mask = np.isfinite(g_fit_interp) & np.isfinite(g_exp)
    #         if np.count_nonzero(valid_mask) >= 5:
    #             r_final, _ = pearsonr(g_fit_interp[valid_mask], g_exp[valid_mask])
    #         else:
    #             r_final = np.nan
    #
    #         st.subheader("Fit Results")
    #         st.write(f"Pearson r after refinement: **{r_final:.4f}**")
    #
    #         # -------------------------------------------------
    #         # 5) Plot experimental vs refined simulated
    #         # -------------------------------------------------
    #         fig_fit = go.Figure()
    #
    #         fig_fit.add_trace(go.Scatter(
    #             x=r_exp,
    #             y=g_exp,
    #             mode="lines",
    #             name="Experimental G(r)",
    #             line=dict(width=2),
    #         ))
    #         fig_fit.add_trace(go.Scatter(
    #             x=r_exp,
    #             y=g_fit_interp,
    #             mode="lines",
    #             name="Refined Simulated G(r)",
    #             line=dict(width=2, dash="dash"),
    #         ))
    #
    #         fig_fit.update_layout(
    #             xaxis_title="r (Å)",
    #             yaxis_title="G(r)",
    #             xaxis=dict(
    #                 range=[rmin_fit, rmax_fit],
    #                 tickfont=dict(size=20, color="black"),
    #                 title_font=dict(size=20, color="black"),
    #             ),
    #             yaxis=dict(
    #                 tickfont=dict(size=20, color="black"),
    #                 title_font=dict(size=20, color="black"),
    #             ),
    #             font=dict(color="black"),
    #             margin=dict(t=40, b=40, l=40, r=40),
    #             legend=dict(yanchor="top", y=0.99, xanchor="center", x=0.8),
    #         )
    #
    #         st.plotly_chart(fig_fit, use_container_width=True)
    #
    #         # -------------------------------------------------
    #         # 6) Offer refined structure for download
    #         # -------------------------------------------------
    #         cif_bytes = atoms_to_cif_bytes(refined_atoms)
    #         st.download_button(
    #             label="Download refined structure (CIF)",
    #             data=cif_bytes,
    #             file_name="refined_structure.cif",
    #             mime="chemical/x-cif",
    #         )
    #
    #         # Optional: show final coordinates table
    #         df_coords = pd.DataFrame(
    #             {
    #                 "element": refined_atoms.get_chemical_symbols(),
    #                 "x (Å)": refined_atoms.get_positions()[:, 0],
    #                 "y (Å)": refined_atoms.get_positions()[:, 1],
    #                 "z (Å)": refined_atoms.get_positions()[:, 2],
    #             }
    #         )
    #         with st.expander("View refined atomic coordinates"):
    #             st.dataframe(df_coords, hide_index=True, use_container_width=True)















    # if create_cent_option:
    #     st.header("Create Idealized Structure")
    #
    #     atoms_idl = None
    #
    #
    #     inorganic_indices_acent = st.multiselect("Enter inorganic molecule indices, separated by spaces: ",
    #                                             options=range(1, len(molecules) + 1), key='initial_cent')
    #
    #     if inorganic_indices_acent:
    #         initial_organic_acent, initial_inorganic_acent = generate_substructure(modified_atoms, molecules,
    #                                                                              inorganic_indices_acent)
    #         # create_labelled_download_file(initial_inorganic_acent, "initial_inorganic", "")
    #
    #
    #
    #         file_name_ac = os.path.splitext(file_name)[0]
    #
    #         output_cif_file_acent = f"{file_name_ac}_inorganic.cif"
    #         # standardized_atoms, selected_symprec = write_cif_with_higher_symmetry(modified_atoms, symprec_lower,
    #         #                                                                       symprec_upper, selected_index)
    #
    #         lattice, scaled_positions, numbers = spglib.standardize_cell(initial_inorganic_acent, to_primitive=False, no_idealize=False,
    #                                                                      symprec=0.0001)
    #
    #         standardized_atoms = Atoms(cell=lattice, scaled_positions=scaled_positions, numbers=numbers)
    #
    #         pymatgen_structure = AseAtomsAdaptor.get_structure(standardized_atoms)
    #
    #         cif_writer = CifWriter(pymatgen_structure, symprec=0.0001)
    #
    #         with tempfile.NamedTemporaryFile(mode="w+", suffix=".cif", delete=False) as output_file:
    #             cif_writer.write_file(output_file.name)  # Write the content to the temporary file
    #             output_file.seek(0)
    #             output_content = output_file.read()
    #             st.markdown(get_download_link(f"{output_cif_file_acent}", output_content), unsafe_allow_html=True)
    #
    #         # create_labelled_download_file(initial_organic_acent, file_name_ac, "_acentric_organic")
    #         create_aims_download_file(initial_organic_acent, file_name_ac,"_organic")
    #
    #         file_buffer_idl = st.file_uploader("Upload the idealized inorganic structure (Do a PseudoSymmetry analysis)",
    #                                            type=[".in", ".cif", ".next_step"])
    #         if file_buffer_idl:
    #             file_name_idl = file_buffer_idl.name
    #             file_format_idl = get_file_format(file_name_idl)
    #             atoms_idl, molecules_idl, modified_symbols_idl = initialize_structure_v2(file_buffer_idl,
    #                                                                                      file_format_idl)
    #
    #         if initial_organic_acent is not None and atoms_idl is not None:
    #             molecules_io_acent = detect_molecules(initial_organic_acent)
    #             modified_symbols_acent = [f"{atom.symbol}{i + 1}" for i, atom in enumerate(initial_organic_acent)]
    #
    #             print_detected_molecules(modified_symbols_acent, molecules_io_acent, "initial organic sublattice")
    #
    #             rotate_indices_acent = st.multiselect(
    #                 "Enter molecular indices you want to rotate, separated by spaces: ",
    #                 options=range(1, len(molecules_io_acent) + 1), key='rotate_mol')
    #
    #             if rotate_indices_acent:
    #                 if "rotation_axes" not in st.session_state:
    #                     st.session_state.rotation_axes = [None] * len(molecules_io_acent)
    #
    #                 for i in rotate_indices_acent:
    #                     st.subheader(f"Molecule {i}")
    #
    #                     with st.form(key=f"molecule_{i}_form"):
    #                         hkl_input = st.text_input("Enter crystal direction as h, k, l separated by spaces")
    #
    #                         if st.form_submit_button(f"Set Axis for Molecule {i}"):
    #                             hkl = np.array([int(val) for val in hkl_input.split()])
    #                             lattice_vectors = initial_organic_acent.get_cell()
    #                             axis = np.dot(hkl, lattice_vectors)
    #                             axis /= np.linalg.norm(axis)
    #
    #                             st.session_state.rotation_axes[i - 1] = axis
    #
    #             generate_structure_button = st.button("Generate Structure")
    #
    #             if generate_structure_button:
    #                 chosen_rotation_axes = [st.session_state.rotation_axes[i - 1] for i in rotate_indices_acent]
    #                 chosen_molecules = [molecules_io_acent[i - 1] for i in rotate_indices_acent]
    #                 rotation_angle = 180
    #
    #                 rotated_organic_structure = initial_organic_acent.copy()
    #                 for molecule, axis in zip(chosen_molecules, chosen_rotation_axes):
    #                     rotated_organic_structure = rotate_molecules_v2(rotated_organic_structure, molecule, axis,
    #                                                                     rotation_angle)
    #
    #                 # Merge O2 and I2
    #                 cent_str = merge_structures(rotated_organic_structure, atoms_idl)
    #                 create_aims_download_file(cent_str, file_name, "_centric")

    def _normalize_name(name: str) -> str:
        # Convert trailing "_" on one-letter symbols (e.g., "I_") to "I"
        if isinstance(name, str) and name.endswith("_") and len(name.rstrip("_")) == 1:
            return name.rstrip("_")
        return name


    def _parse_id_field(s: str) -> list[int]:
        """
        Parse an ID input string like:
          "1, 3, 4" or "5:10" or "1, 4:7, 12"
        into a unique, ordered list of ints. Ranges are inclusive.
        """
        if not s or not str(s).strip():
            return []
        tokens = re.split(r"[,\s]+", str(s).strip())
        out: list[int] = []
        seen = set()
        for tok in tokens:
            if not tok:
                continue
            m = re.fullmatch(r"(\d+)\s*:\s*(\d+)", tok)
            if m:
                a, b = map(int, m.groups())
                rng = range(a, b + 1) if a <= b else range(a, b - 1, -1)
                for x in rng:
                    if x not in seen:
                        out.append(x);
                        seen.add(x)
            else:
                try:
                    x = int(tok)
                    if x not in seen:
                        out.append(x);
                        seen.add(x)
                except ValueError:
                    # ignore unparseable tokens gracefully
                    pass
        return out


    def _parse_bader_integrated_atomic_properties(text: str) -> pd.DataFrame:
        """
        Find and parse the '* Integrated atomic properties' table.
        Returns DataFrame with columns: Id, Name, Z, Pop, PartialCharge
        """
        lines = text.splitlines()
        # 1) locate the section start
        start = None
        for i, ln in enumerate(lines):
            if "* Integrated atomic properties" in ln:
                start = i
                break
        if start is None:
            raise ValueError("Could not find '* Integrated atomic properties' section.")
        # 2) locate the header (contains 'Id' and 'Pop')
        header = None
        for j in range(start, len(lines)):
            if "Id" in lines[j] and "Pop" in lines[j]:
                header = j
                break
        if header is None:
            raise ValueError("Could not find the table header with 'Id' and 'Pop'.")
        # 3) parse rows until a blank/comment/new section
        rows = []
        for ln in lines[header + 1:]:
            s = ln.strip()
            if not s or s.startswith("#") or s.startswith("*"):
                if rows:  # stop once we’ve started and hit a non-data line
                    break
                else:
                    continue
            toks = s.split()
            # Expected minimal columns:
            # 0:Id 1:cp 2:ncp 3:Name 4:Z 5:mult 6:Volume 7:Pop 8:Lap
            if len(toks) < 9:
                break
            try:
                Id = int(toks[0])
                Name = _normalize_name(toks[3])
                Z = int(toks[4])
                Pop = float(toks[7].replace("D", "E"))
                rows.append({"Id": Id, "Name": Name, "Z": Z, "Pop": Pop})
            except Exception:
                # end of clean block or stray line—stop
                break
        if not rows:
            raise ValueError("No data rows parsed from the atomic properties table.")
        df = pd.DataFrame(rows)
        df["PartialCharge"] = df["Z"] - df["Pop"]
        return df


    if charge_analysis_option:
        render_section_header("Analyze charge differences", kicker="Structure Workspace")

        uploaded = st.file_uploader("Upload Bader charge analysis output (.out)", type=["out", "txt", "dat"])
        if uploaded is not None:
            try:
                text = uploaded.read().decode("utf-8", errors="ignore")
                df_all = _parse_bader_integrated_atomic_properties(text)
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

            ids_a = _parse_id_field(ids_a_str)
            ids_b = _parse_id_field(ids_b_str)

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

            base_name = os.path.splitext(file_name)[0]
            st.download_button(
                label="📥 Download as PNG",
                data=png_buffer,
                file_name=f"{base_name}.png",
                mime="image/png",
            )

    if distance_option:
        render_section_header("Calculate atomic distances", kicker="Structure Workspace")

        # User input for atomic symbols
        first_atom = st.text_input('Enter the symbol of the first atom (A):', value="Pb")
        second_atoms = st.text_input('Enter the symbol of the second atom (B):', value="I")

        min_cutoff, max_cutoff = st.slider(
            "Set cut-off range for searching the atoms",
            min_value=0.0,
            max_value=10.0,
            value=(0.0, 3.5),  # Default values for min and max
            step=0.1,
        )

        if st.button('Calculate'):
            found_distances = find_third_atom_distances_with_cutoff(modified_atoms, first_atom, second_atoms, min_cutoff, max_cutoff)

            st.dataframe(found_distances, use_container_width=True, hide_index=True)

    if distortion_option:
        render_section_header("Calculate distortion parameters", kicker="Structure Workspace")

        # User input for atomic symbols
        center_atom = st.text_input('Enter the symbol of the center atom (A):', value="Pb")
        surrounding_atoms = st.text_input('Enter the symbol of the surrounding atoms (B):', value="I")

        # User input for type of distortion(s)
        distortion_type = st.selectbox(
            'Select the type of distortion to calculate:',
            ('all','Bond distance variance', 'Angle variance', 'Bridging angle(s)', 'In and out deviations'
             )
        )

        with st.expander ("Optional parameters"):
            # Experimental
            center_atom_2 = st.text_input('Enter the symbol of a second center atom, if available (useful for double perovskites):', value=None)
            b_parameter = st.number_input("Relax the bond distance limit (useful for chloride-based systems):",
                                          value=0.00)
            c_paramter = st.number_input("Relax the octahedron distortion limit (useful for highly distorted systems):",
                                         value=0.00)
            supercell_size= st.number_input("Modify the supercell size (useful for checking convergence):",
                                         value=3)

        # Button for confirmation
        if st.button('Calculate'):
            try:
                super_atoms, periodic_image_dict, A2_indices = filter_atoms_by_symbols_and_extend(modified_atoms, A=center_atom,
                                                                                      B=surrounding_atoms, A2=center_atom_2, s_size=supercell_size)
                AB6_octahedra, AB_distances = identify_AB_groups(super_atoms, center_atom, surrounding_atoms, b=b_parameter, c=c_paramter)
                unq_AB_distances = filter_unique_distances(AB_distances)
                octahedral_distances = find_matching_distances(modified_atoms, center_atom, surrounding_atoms,
                                                               unq_AB_distances, A2_indices=A2_indices, A2_symbol=center_atom_2)

                st.markdown(f'**Distance of {center_atom} - {surrounding_atoms} bonds in octahedra**')
                st.dataframe(octahedral_distances, use_container_width=True, hide_index=True)

                distortion_mapping = {
                    'Bond distance variance': calculate_bond_distance_variance,
                    'Bond distance varience simplified (x 1e-05)' : calculate_bond_distance_variance_v2,
                    'Metal off-centering' : calculate_off_centering,
                    '2D projected Metal off-Centering' : calculate_off_centering_proj,
                    '2D Metal off-centering': calculate_mc_2D,
                    '2D projected 2D off-Centering': calculate_mc_2D_proj,
                    'Angle variance': calculate_angle_variance,
                    'Bridging angle(s)': calculate_unique_ABA_angles,
                    'In and out deviations': calculate_in_out_planes,
                }

                output_data = []
                if distortion_type == 'all':
                    for func_name, func in distortion_mapping.items():
                        result = func(AB6_octahedra, super_atoms, periodic_image_dict, b=b_parameter, A2_indices=A2_indices, A2_symbol=center_atom_2)
                        if func_name == 'Bridging angle(s)':
                            output_data.extend(handle_bridging_angles(result, periodic_image_dict))
                        elif func_name == 'In and out deviations':
                            output_data.extend(handle_in_out_deviations(result))
                        else:
                            output_data.append((func_name, ', '.join(result)))
                else:
                    result = distortion_mapping[distortion_type](AB6_octahedra, super_atoms, periodic_image_dict,A2_indices=A2_indices, A2_symbol=center_atom_2)
                    if distortion_type == 'Bridging angle(s)':
                        output_data.extend(handle_bridging_angles(result, periodic_image_dict))
                    elif distortion_type == 'In and out deviations':
                        output_data.extend(handle_in_out_deviations(result))
                    else:
                        output_data.append((distortion_type, ', '.join(result)))

                df = pd.DataFrame(output_data, columns=['Distortion Parameter', 'Value'])
                st.dataframe(df, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(e)
                st.write ('''
                If you see an error message "['A_index'] not found in axis", try increasing the bond distance limit (e.g., to 0.5) and the octahedron distortion limit (e.g., to 0.3) in the Optional parameters box.  
                          or  
                          Is this a double perovskite structure (e.g., (AE2T)2AgBiI8)? If so, input the second A atom label in the Optional parameters box.
                          ''')


if interpolate_option:
    render_section_header("Interpolate Structures", kicker="Structure Workspace")
    file_buffer1 = st.file_uploader("Upload an initial structure file (AIMS or CIF)", type=[".in", ".cif"],
                                    key="file_buffer1")
    file_buffer2 = st.file_uploader("Upload a final structure file (AIMS or CIF)", type=[".in", ".cif"],
                                    key="file_buffer2")

    if file_buffer1 is not None and file_buffer2 is not None:

        atoms1, atoms2, file_name1, file_name2 = process_uploaded_files(file_buffer1, file_buffer2)

        if atoms1 is not None and atoms2 is not None:
            n = st.number_input("Enter the number of interpolated structures to generate:", min_value=1,
                                step=1)

            # Convert ase atoms to pymatgen structures
            initial_structure = AseAtomsAdaptor.get_structure(atoms1)
            final_structure = AseAtomsAdaptor.get_structure(atoms2)

            # Initialize the StructureMatcher with primitive_cell set to False
            sm = StructureMatcher(primitive_cell=False)

            # Match two structures
            final_structure_reordered = sm.get_s2_like_s1(initial_structure, final_structure)

            label_atoms = st.checkbox("Do you want labelled atoms for checking?")

            if label_atoms:
                file_name_o1 = file_name1 + "_labelled"
                file_name_o2 = file_name2 + "_reordered_labelled"
                generate_labelled_cif(initial_structure, file_name_o1)
                generate_labelled_cif(final_structure_reordered, file_name_o2)

    if st.button("Generate Interpolated Structures"):
        if atoms1 is not None and atoms2 is not None:
            try:
                # Interpolate between the two structures
                interpolated_structures = initial_structure.interpolate(final_structure_reordered,
                                                                        nimages=n,
                                                                        autosort_tol=0.5,
                                                                        interpolate_lattices=True)

                # Convert pymatgen structures back to ase atoms
                interpolated_atoms = [AseAtomsAdaptor.get_atoms(structure) for structure in
                                      interpolated_structures]

                # Save interpolated structures to a temporary ZIP file
                create_interpolated_structures_zip(interpolated_atoms)

            except Exception as e:
                st.error(f"Error: {e}")

# if trans_rotate_option:
#     st.header("Translate Inorganic and Rotate Organic Subunits")
#     file_buffer1 = st.file_uploader("Upload an initial structure file (AIMS or CIF)", type=[".in", ".cif"],
#                                     key="file_buffer1")
#     file_buffer2 = st.file_uploader("Upload a final structure file (AIMS or CIF)", type=[".in", ".cif"],
#                                     key="file_buffer2")
#
#     if file_buffer1 is not None and file_buffer2 is not None:
#
#         atoms1, molecules1 = process_file_and_print_molecules(file_buffer1, "initial structure")
#
#         inorganic_indices1 = st.multiselect("Enter inorganic molecule indices, separated by spaces: ",
#                                             options=range(1, len(molecules1) + 1), key='initial')
#
#         initial_organic, initial_inorganic = generate_substructure(atoms1, molecules1, inorganic_indices1)
#
#         atoms2, molecules2 = process_file_and_print_molecules(file_buffer2, "final structure")
#
#         inorganic_indices2 = st.multiselect("Enter inorganic molecule indices, separated by spaces: ",
#                                             options=range(1, len(molecules2) + 1), key='final')
#
#         final_organic, final_inorganic = generate_substructure(atoms2, molecules2, inorganic_indices2)
#
#         # Let user decide whether to show download links for initial/final organic/inorganic files
#         show_download_links = st.checkbox("Show download links for initial/final organic/inorganic files")
#
#         if show_download_links:
#             create_labelled_download_file(initial_inorganic, "initial_inorganic", "")
#             create_labelled_download_file(initial_organic, "initial_organic", "")
#             create_labelled_download_file(final_inorganic, "final_inorganic", "")
#             create_labelled_download_file(final_organic, "final_organic", "")
#
#         if inorganic_indices1 and inorganic_indices2:
#
#             st.subheader("Starting Interpolation")
#             n = st.number_input("Enter the number of interpolated structures to generate:", min_value=1,
#                                 step=1)
#             n = (n + 1)
#
#             molecules_io = detect_molecules(initial_organic)
#             modified_symbols = [f"{atom.symbol}{i + 1}" for i, atom in enumerate(initial_organic)]
#
#             print_detected_molecules(modified_symbols, molecules_io, "initial organic sublattice")
#
#             rotate_indices = st.multiselect("Enter molecular indices you want to rotate, separated by spaces: ",
#                                             options=range(1, len(molecules_io) + 1), key='rotate_mol')
#
#             use_custom_axis = st.checkbox("Use custom rotation axis")
#
#             axis_input = st.text_input(
#                 "Enter custom axis as x, y, z separated by spaces") if use_custom_axis else None
#             axis = axis_input.split() if axis_input else st.selectbox("Select rotation axis",
#                                                                       options=["x", "y", "z"])
#
#             if use_custom_axis:
#                 axis = np.array([float(val) for val in axis_input.split()])
#             else:
#                 axis_dict = {'x': [1, 0, 0], 'y': [0, 1, 0], 'z': [0, 0, 1]}
#                 axis = axis_dict[axis]
#
#             if st.button("Generate Interpolated Structures"):
#                 if atoms1 is not None and atoms2 is not None:
#                     try:
#                         # Rotate the organic
#                         rotated_organic_structures = rotate_organic_molecules(initial_organic,molecules_io, n, rotate_indices, axis)       #180 deg rotated structure is the last one
#
#
#                         # Translate the inorganic
#                         if rotated_organic_structures is not None:
#
#                             inorganic_interpolated_structures = interpolate_inorganic_lattice(initial_inorganic,
#                                                                                               final_inorganic, n)
#
#
#                             if rotated_organic_structures is not None and inorganic_interpolated_structures is not None:
#                                 st.subheader("Here are the interpolated structures:")
#                                 # Save interpolated structures to a temporary ZIP file
#                                 merge_and_create_zip(rotated_organic_structures, inorganic_interpolated_structures)
#
#
#
#
#                     except Exception as e:
#                         st.error(f"Error: {e}")

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
    uploaded_files = st.file_uploader("Upload Total DOS and element DOS files:", type=['dat', 'txt'],
                                      accept_multiple_files=True)

    # Input for shift value
    shift = float(st.number_input("Enter shift value:", value=0.00))
    st.session_state.shift = shift

    # Input field for plot_range variable
    plot_range = st.slider("Select plot range:", min_value=-30.0, max_value=30.0, value=(-2.0, 5.0), step=1.0)


    # Plot button
    plot_button = st.button("Plot")

    # Process the uploaded files to create dos_data dictionary
    if plot_button:
        if uploaded_files:
            dos_data = {}

            for file in uploaded_files:
                if file.name == "KS_DOS_total.dat":
                    dos_data['Total'] = np.loadtxt(file)
                else:
                    # Extract element name from the file name
                    element_name = re.match(r'(\w+)_l_proj_dos.dat', file.name)
                    if element_name:
                        element_name = element_name.group(1)
                        dos_data[element_name] = np.loadtxt(file)

            # Check if Total DOS data is provided
            if 'Total' in dos_data:
                energy_values = dos_data['Total'][:, 0]
                total_dos = dos_data['Total'][:, 1]

                # Create a DataFrame with the energy column
                df = pd.DataFrame({'Energy': energy_values, 'Total DOS': total_dos})

                # Add each element's DOS to the DataFrame
                for element, data in dos_data.items():
                    if element != 'Total':  # Assuming you don't want to include the Total's DOS again
                        df[element] = data[:, 1]  # Add the second column (DOS values) of each element

                st.dataframe(pd.DataFrame(df), hide_index=True, use_container_width=True)
                # Call the plot_pdos_streamlit function and display the plot
                fig = plot_pdos_streamlit(dos_data, st.session_state.shift, plot_range)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("Total DOS file (KS_DOS_total.dat) not found in the uploaded files.")
        # else:
        #     st.warning("Please upload the required files.")

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
    render_section_header("Calculate deviation", kicker="Structure Workspace")

    file_buffer1 = st.file_uploader("Upload an initial structure file (AIMS or CIF)", type=[".in", ".cif"],
                                    key="file_buffer1")
    file_buffer2 = st.file_uploader("Upload a final structure file (AIMS or CIF)", type=[".in", ".cif"],
                                    key="file_buffer2")

    if file_buffer1 is not None and file_buffer2 is not None:

        atoms1, atoms2, file_name1, file_name2 = process_uploaded_files(file_buffer1, file_buffer2)

        if atoms1 is not None and atoms2 is not None:
            # Convert ase atoms to pymatgen structures
            initial_structure = AseAtomsAdaptor.get_structure(atoms1)
            final_structure = AseAtomsAdaptor.get_structure(atoms2)

            # Extract lattice parameters
            lattice_parameters = ['a (Å)', 'b (Å)', 'c (Å)', 'alpha (°)', 'beta (°)', 'gamma (°)', 'volume (Å^3)']
            lattice_parameter_keys = ['a', 'b', 'c', 'alpha', 'beta', 'gamma', 'volume']
            initial_params = [getattr(initial_structure.lattice, p) for p in lattice_parameter_keys]
            final_params = [getattr(final_structure.lattice, p) for p in lattice_parameter_keys]

            # Calculate percentage deviations
            deviations = [(final - initial) / initial * 100 for initial, final in zip(initial_params, final_params)]

            # Prepare data for the table
            table_data = list(zip(lattice_parameters, initial_params, final_params, deviations))

            # Create dataframe
            df = pd.DataFrame(table_data,
                              columns=["Lattice Parameter", "Initial Value", "Final Value", "Deviation (%)"])

            # Display the dataframe
            st.dataframe(df, use_container_width=True, hide_index=True)

if MD_option:
    render_section_header("Analyze AIMS Molecular Dynamics (MD) Output files", kicker="Dynamics Workspace")

    file_buffer_md = st.file_uploader("Upload MD output files", type=[".out"], accept_multiple_files=True,
                                      key="file_buffer_md")

    if file_buffer_md:
        df = process_streams(file_buffer_md)
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
    with zipfile.ZipFile(file_buffer_md, 'r') as zip_ref:
        zip_ref.extractall('frames_dir')
    timestep = timestep / 1000
    return build_universe_from_dir('frames_dir', timestep=timestep)


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


        u = create_universe(file_buffer_md, timestep)

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

import mpld3
import streamlit.components.v1 as components

if plot_spin_v2_option:
    render_section_header(
        "Plot Spin Texture",
        kicker="Utilities Workspace",
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

                    uploaded_file.seek(0)
                    try:
                        fig = plot_spin_quivers_3D(uploaded_file, states, spin_direction)
                        # fig_html = mpld3.fig_to_html(fig)




                        buf = io.BytesIO()
                        fig.savefig(buf, format='pdf', transparent=True)
                        buf.seek(0)

                        st.markdown(f"### State {states}")
                        st.pyplot(fig, use_container_width=True)

                        st.download_button(
                            label="Download plot as PDF",
                            data=buf,
                            file_name=f"plot_state_{states}.pdf",
                            mime="application/pdf"
                        )

                    except Exception as e:
                        st.error(f"An error occurred while plotting: {e}")
            else:
                st.error("Entered states are out of the available range.")


from matplotlib.ticker import MultipleLocator
import json


def format_subscripts(text):
    """Convert any _X to $_{X}$ (e.g., A_2BC_4 → A$_{2}$BC$_{4}$)"""
    return re.sub(r'_(\w)', r'$_{\1}$', text)

# def convert_underscores_to_subscripts(text):
#     return re.sub(r'_(\w)', r'$_{\1}$', text)

def modify_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    st.subheader("🔧 Dataset Modification via Math Expressions")

    # Build alias map and safe namespace
    alias_map = {}
    local_vars = {
        'np': np,
        'pi': np.pi,
        'e': np.e,
        'sin': np.sin,
        'cos': np.cos,
        'tan': np.tan,
        'log': np.log,
        'sqrt': np.sqrt,
        'abs': np.abs,
        'exp': np.exp
    }

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
                result = eval(formula, {}, local_vars)
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
            for i in range(num_datasets):
                with st.expander(f"📊 Dataset {i + 1}"):
                    ds_cfg = config_data["datasets"][i] if config_data and "datasets" in config_data and i < len(
                        config_data["datasets"]) else {}

                    x_col = st.selectbox(f"X-axis column", columns, key=f"x{i}",
                                         index=columns.index(ds_cfg.get("x", columns[0])) if ds_cfg.get(
                                             "x") in columns else 0)
                    y_col = st.selectbox(f"Y-axis column", columns, key=f"y{i}",
                                         index=columns.index(ds_cfg.get("y", columns[0])) if ds_cfg.get(
                                             "y") in columns else 0)

                    label = st.text_input(f"Label for Dataset {i + 1} (use _ for subscript)",
                                          value=ds_cfg.get("label", f"Data_{i + 1}"), key=f"label{i}")

                    color = st.color_picker(f"Color for Dataset {i + 1}", value=ds_cfg.get("color", "#1f77b4"),
                                            key=f"color{i}")
                    marker = st.selectbox(f"Marker for Dataset {i + 1}", ["None", "o", "s", "D", "^", "x", "*"],
                                          index=["None", "o", "s", "D", "^", "x", "*"].index(ds_cfg.get("marker", "o")),
                                          key=f"marker{i}")
                    linestyle = st.selectbox(f"Line Style for Dataset {i + 1}",
                                             ["solid", "dashed", "dashdot", "dotted"],
                                             index=["solid", "dashed", "dashdot", "dotted"].index(
                                                 ds_cfg.get("linestyle", "solid")), key=f"linestyle{i}")

                    dataset_info.append({
                        "x": x_col,
                        "y": y_col,
                        "label": format_subscripts(label),
                        "color": color,
                        "marker": None if marker == "None" else marker,
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
                    ax.plot(df[ds["x"]], df[ds["y"]],
                            color=ds["color"],
                            linewidth=2.0,
                            marker=ds["marker"],
                            linestyle=ds["linestyle"],
                            label=ds["label"] if show_legend else None)

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
                            "marker": ds["marker"] if ds["marker"] else "None",
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
