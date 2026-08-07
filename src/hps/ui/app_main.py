import os

import matplotlib as mpl
import streamlit as st

from hps.io.paths import APP_TMP_DIR
from hps.ui.backend_workflows import ensure_workflow_registry
from hps.ui.navigation import (
    build_feature_tree,
    render_tree_lines,
    tool_options,
    view_names,
    workspace_descriptions,
    workspace_names,
)
from hps.ui.workspaces.dynamics import render_dynamics_workspace
from hps.ui.workspaces.electronic import (
    load_pdos_color_preferences,
    render_electronic_workspace,
    render_spin_texture_3d,
)
from hps.ui.workspaces.structure.analysis.metrics import (
    render_adp_table,
    render_atomic_distances,
    render_distortions,
    render_percentage_deviation,
)
from hps.ui.workspaces.structure.analysis.molecules import render_molecule_analysis
from hps.ui.workspaces.structure.analysis.pdf import render_pdf_analysis
from hps.ui.workspaces.structure.analysis.pxrd import render_pxrd_analysis
from hps.ui.workspaces.structure.analysis.symmetry import render_symmetry_analysis
from hps.ui.workspaces.structure.navigation import render_structure_navigation
from hps.ui.workspaces.structure.overview import (
    render_current_structure_card,
    render_structure_upload_panel,
)
from hps.ui.workspaces.structure.state import (
    initialize_state as initialize_structure_workspace_state,
)
from hps.ui.workspaces.structure.state import (
    load_active_structure,
)
from hps.ui.workspaces.structure.transformations.operations import (
    render_deletion,
    render_interpolation,
    render_labelling,
    render_reflection,
    render_translation,
)
from hps.ui.workspaces.structure.transformations.rotation import render_rotation
from hps.ui.workspaces.utilities import render_utilities_workspace


def _debug_log(message):
    APP_TMP_DIR.mkdir(exist_ok=True)
    with open(APP_TMP_DIR / "upload_debug.log", "a", encoding="utf-8") as fh:
        fh.write(f"{message}\n")


def _get_backend_workflow_registry():
    return ensure_workflow_registry(st.session_state)


_debug_log("startup: entered hps.ui.app_main")


_debug_log("startup: loaded explicit packaged dependencies")

# from streamlit_ketcher import st_ketcher
# from scipy.optimize import minimize
# from scipy.stats import pearsonr
# import tempfile
# from ase import Atoms
# from pathlib import Path
# from diffpy.srreal.structureadapter import loadStructure
# from diffpy.srreal.pdfcalculator import DebyePDFCalculator
# from pymatgen.io.cif import CifWriter
mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42
mpl.rcParams["font.family"] = "Arial"


def render_section_header(title, kicker=None, subtitle=None):
    kicker_html = f'<div class="section-kicker">{kicker}</div>' if kicker else ""
    subtitle_html = f'<div class="section-head-copy">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="section-head">
            {kicker_html}
            <div class="section-head-title">{title}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="Hybrid Perovskite Studio", layout="wide")
_debug_log("startup: page config set")

if backend_startup_error := os.environ.get("HPS_BACKEND_STARTUP_ERROR"):
    st.warning(
        "The local analysis backend is unavailable. Backend-powered workflows will "
        f"remain offline until the service is restored. Details: {backend_startup_error}"
    )

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
    st.session_state.pdos_saved_trace_colors = load_pdos_color_preferences()
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
        --hp-bg-soft: #f4f7f7;
        --hp-surface: rgba(255, 255, 255, 0.96);
        --hp-surface-strong: rgba(255, 255, 255, 0.99);
        --hp-text: #10232a;
        --hp-text-muted: #556371;
        --hp-text-subtle: #677787;
        --hp-border: rgba(49, 51, 63, 0.12);
        --hp-border-strong: rgba(0, 122, 138, 0.42);
        --hp-accent: #007a8a;
        --hp-accent-bright: #65e6d4;
        --hp-accent-soft: rgba(0, 122, 138, 0.1);
        --hp-ink: #061b22;
        --hp-shadow-sm: 0 8px 20px rgba(15, 23, 42, 0.05);
        --hp-shadow-md: 0 14px 30px rgba(15, 23, 42, 0.07);
        --hp-shadow-lg: 0 18px 38px rgba(15, 23, 42, 0.08);
        --hp-radius-sm: 14px;
        --hp-radius-md: 18px;
        --hp-radius-lg: 24px;
    }
    .block-container {
        padding-top: 4.5rem;
        padding-bottom: 4rem;
    }
    .stApp {
        background: var(--hp-bg-soft);
    }
    header[data-testid="stHeader"] {
        background: rgba(244, 247, 247, 0.9);
        border-bottom: 1px solid rgba(16, 35, 42, 0.06);
        backdrop-filter: blur(12px);
    }
    .app-brand-wrap {
        display: flex;
        align-items: baseline;
        gap: 0.8rem;
        width: 100%;
        padding: 0.4rem 0 1.35rem;
        box-sizing: border-box;
        border-bottom: 1px solid var(--hp-border);
    }
    .app-brand-title {
        font-size: 1.08rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: var(--hp-text);
        line-height: 1;
    }
    .app-brand-title span {
        color: var(--hp-accent);
    }
    .app-brand-subtitle {
        font-size: 0.73rem;
        line-height: 1;
        color: var(--hp-text-subtle);
        text-transform: uppercase;
        letter-spacing: 0.11em;
    }
    h1, h2, h3 {
        letter-spacing: -0.035em;
        color: var(--hp-text);
    }
    h1 { font-weight: 720; }
    h2, h3 { font-weight: 680; }
    hr {
        border-color: var(--hp-border) !important;
    }
    div[data-testid="stMarkdownContainer"] p {
        color: var(--hp-text-muted);
    }
    div[data-testid="stCaptionContainer"] {
        color: var(--hp-text-subtle);
    }
    div[data-testid="stAlert"] {
        border-radius: 8px;
        border: 0;
        border-left: 3px solid var(--hp-accent);
        box-shadow: none;
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
        padding: 0.48rem 0.9rem;
        background: rgba(255, 255, 255, 0.62);
        box-shadow: none;
        transition: all 0.2s ease;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
        border-color: var(--hp-border-strong);
        background: rgba(255, 255, 255, 0.9);
    }
    div[data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
        background: var(--hp-accent-soft);
        border-color: rgba(0, 122, 138, 0.62);
        box-shadow: inset 0 0 0 1px rgba(0, 122, 138, 0.08);
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
        border-radius: 8px;
    }
    div[data-testid="stFileUploader"] section {
        min-height: 4.5rem;
        background: rgba(255, 255, 255, 0.52);
        border: 1px dashed rgba(16, 35, 42, 0.22);
    }
    div[data-baseweb="select"] > div,
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stTextArea"] textarea {
        background: rgba(255, 255, 255, 0.72);
        border-color: var(--hp-border);
        box-shadow: none;
    }
    div[data-testid="stButton"] > button,
    div[data-testid="stDownloadButton"] > button {
        border-radius: 999px;
        border: 1px solid var(--hp-border);
        background: rgba(255, 255, 255, 0.76);
        color: var(--hp-text);
        font-weight: 600;
        box-shadow: none;
        transition: all 0.18s ease;
    }
    div[data-testid="stButton"] > button:hover,
    div[data-testid="stDownloadButton"] > button:hover {
        border-color: var(--hp-border-strong);
        color: var(--hp-accent);
        transform: translateY(-1px);
        background: #ffffff;
        box-shadow: 0 8px 18px rgba(16, 35, 42, 0.07);
    }
    .workspace-open,
    .workspace-start {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        min-height: 2.45rem;
        border: 1px solid var(--hp-border);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.76);
        color: var(--hp-text-muted) !important;
        font-size: 0.86rem;
        font-weight: 600;
        text-decoration: none !important;
        transition: all 0.18s ease;
    }
    .workspace-open:hover,
    .workspace-start:hover {
        border-color: var(--hp-border-strong);
        background: #ffffff;
        color: var(--hp-accent) !important;
        transform: translateY(-1px);
        box-shadow: 0 8px 18px rgba(16, 35, 42, 0.07);
    }
    .workspace-open.selected {
        color: var(--hp-text-subtle) !important;
        background: transparent;
        cursor: default;
    }
    .workspace-start {
        margin-top: 3.05rem;
    }
    .workspace-card {
        position: relative;
        padding: 1.15rem 0.2rem 0.95rem;
        min-height: 8rem;
        border-top: 1px solid rgba(16, 35, 42, 0.2);
        background: transparent;
        transition: border-color 0.2s ease, transform 0.2s ease;
    }
    .workspace-card::before {
        content: "";
        position: absolute;
        top: -1px;
        left: 0;
        width: 0;
        height: 2px;
        background: var(--hp-accent);
        transition: width 0.24s ease;
    }
    .workspace-card:hover::before {
        width: 100%;
    }
    .workspace-card.active {
        border-color: var(--hp-accent);
    }
    .workspace-card.active::before {
        width: 100%;
    }
    .workspace-card.compact {
        min-height: 4.25rem;
        padding: 0.9rem 0.2rem 0.3rem;
    }
    .workspace-card.compact .workspace-card-title {
        margin-bottom: 0;
        font-size: 0.98rem;
    }
    .workspace-card.compact .workspace-card-body {
        display: none;
    }
    .workspace-card-title {
        font-size: 1.1rem;
        font-weight: 700;
        letter-spacing: -0.025em;
        margin-bottom: 0.55rem;
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
    .workspace-page-head {
        padding: 2.7rem 0 1.25rem;
    }
    .workspace-page-head .workspace-header {
        margin-bottom: 0.55rem;
        color: var(--hp-accent);
        font-size: 0.73rem;
        font-weight: 700;
        letter-spacing: 0.13em;
    }
    .workspace-page-title {
        color: var(--hp-text);
        font-size: clamp(1.9rem, 3vw, 2.75rem);
        font-weight: 700;
        letter-spacing: -0.045em;
        line-height: 1.05;
    }
    .workspace-page-copy {
        max-width: 43rem;
        margin-top: 0.55rem;
        color: var(--hp-text-muted);
        font-size: 0.93rem;
        line-height: 1.55;
    }
    .section-kicker {
        margin-bottom: 0.45rem;
        color: var(--hp-accent);
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .section-head {
        margin: 1.6rem 0 1.2rem;
        padding: 1.75rem 0 1.15rem;
        border-top: 1px solid var(--hp-border);
    }
    .section-head-title {
        color: var(--hp-text);
        font-size: clamp(1.35rem, 2.1vw, 1.9rem);
        font-weight: 700;
        letter-spacing: -0.035em;
        line-height: 1.1;
    }
    .section-head-copy {
        max-width: 48rem;
        margin-top: 0.45rem;
        color: var(--hp-text-muted);
        font-size: 0.9rem;
        line-height: 1.55;
    }
    .workspace-card-copy {
        max-width: 48rem;
        color: var(--hp-text-muted);
        font-size: 0.9rem;
        line-height: 1.55;
    }
    .landing-panel {
        padding: 2.2rem 0 0.8rem;
        margin: 0;
        border-bottom: 1px solid var(--hp-border);
    }
    .landing-eyebrow {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--hp-text-subtle);
        margin-bottom: 0.35rem;
    }
    .landing-title {
        font-size: clamp(1.8rem, 3vw, 2.7rem);
        font-weight: 700;
        letter-spacing: -0.045em;
        color: var(--hp-text);
        margin-bottom: 0.45rem;
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
        padding: 3.2rem 0 2rem;
        margin: 0 0 1.5rem;
        border-bottom: 1px solid var(--hp-border);
        background: transparent;
    }
    .hp-hero {
        position: relative;
        width: 100vw;
        min-height: min(47rem, calc(100svh - 2rem));
        margin: -4.5rem 0 0 calc(50% - 50vw);
        overflow: hidden;
        display: flex;
        align-items: center;
        color: #f4fbfa;
        background:
            radial-gradient(circle at 78% 46%, rgba(31, 192, 180, 0.18), transparent 29%),
            linear-gradient(118deg, #06191f 0%, #092c34 53%, #0a343a 100%);
        isolation: isolate;
    }
    .hp-hero::after {
        content: "";
        position: absolute;
        inset: 0;
        z-index: -1;
        background: linear-gradient(90deg, rgba(3, 16, 21, 0.42), transparent 54%);
        pointer-events: none;
    }
    .hp-hero-inner {
        position: relative;
        z-index: 2;
        width: min(86rem, calc(100% - 3rem));
        margin: 0 auto;
        padding: 5.5rem 0 4.5rem;
    }
    .hp-hero-copy {
        width: min(35rem, 48vw);
        animation: hp-rise 0.75s cubic-bezier(.22, .85, .3, 1) both;
    }
    .hp-hero-kicker {
        margin-bottom: 1.15rem;
        color: var(--hp-accent-bright);
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
    }
    .hp-hero-brand {
        margin: 0;
        color: #f7fffd;
        font-size: clamp(3.7rem, 7.5vw, 7rem);
        line-height: 0.88;
        letter-spacing: -0.075em;
        font-weight: 760;
    }
    .hp-hero-title {
        margin: 1.25rem 0 0;
        max-width: 31rem;
        color: rgba(241, 252, 250, 0.92);
        font-size: clamp(1.55rem, 2.5vw, 2.45rem);
        line-height: 1.08;
        letter-spacing: -0.04em;
        font-weight: 520;
    }
    .hp-hero-copy p {
        max-width: 30rem;
        margin: 1.25rem 0 0;
        color: rgba(224, 240, 238, 0.72) !important;
        font-size: 1.02rem;
        line-height: 1.65;
    }
    .hp-hero-actions {
        display: flex;
        align-items: center;
        gap: 1.4rem;
        margin-top: 2rem;
    }
    .hp-hero-primary,
    .hp-hero-secondary {
        color: #f4fbfa !important;
        font-size: 0.88rem;
        font-weight: 700;
        text-decoration: none !important;
    }
    .hp-hero-primary {
        display: inline-flex;
        align-items: center;
        min-height: 2.9rem;
        padding: 0 1.25rem;
        border-radius: 999px;
        color: #062027 !important;
        background: var(--hp-accent-bright);
        transition: transform 0.2s ease, background 0.2s ease;
    }
    .hp-hero-primary:hover {
        transform: translateY(-2px);
        background: #84f3e4;
    }
    .hp-hero-secondary {
        padding: 0.65rem 0;
        border-bottom: 1px solid rgba(244, 251, 250, 0.36);
    }
    .hp-lattice {
        position: absolute;
        z-index: 1;
        top: 50%;
        right: max(-5rem, calc((100vw - 90rem) / 2));
        width: min(57vw, 54rem);
        height: auto;
        opacity: 0.95;
        transform: translateY(-50%);
        filter: drop-shadow(0 22px 45px rgba(0, 0, 0, 0.3));
        animation: hp-lattice-in 1.1s cubic-bezier(.22, .85, .3, 1) both,
                   hp-float 9s ease-in-out 1.1s infinite;
    }
    .hp-section-label {
        margin: 2.9rem 0 0.55rem;
        color: var(--hp-accent);
        font-size: 0.73rem;
        font-weight: 700;
        letter-spacing: 0.13em;
        text-transform: uppercase;
    }
    .hp-section-title {
        max-width: 38rem;
        margin: 0 0 1.9rem;
        color: var(--hp-text);
        font-size: clamp(1.8rem, 3vw, 2.75rem);
        line-height: 1.06;
        letter-spacing: -0.045em;
        font-weight: 700;
    }
    .hp-depth {
        display: grid;
        grid-template-columns: 1.15fr repeat(3, 1fr);
        gap: 2rem;
        margin: 3.7rem 0 1.8rem;
        padding: 2.8rem 0 2.4rem;
        border-top: 1px solid var(--hp-border);
        border-bottom: 1px solid var(--hp-border);
    }
    .hp-depth-lead {
        color: var(--hp-text);
        font-size: 1.25rem;
        line-height: 1.25;
        letter-spacing: -0.025em;
        font-weight: 700;
    }
    .hp-depth-item span {
        display: block;
        margin-bottom: 0.75rem;
        color: var(--hp-accent);
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.12em;
    }
    .hp-depth-item strong {
        display: block;
        margin-bottom: 0.35rem;
        color: var(--hp-text);
        font-size: 0.98rem;
    }
    .hp-depth-item p {
        margin: 0;
        color: var(--hp-text-muted) !important;
        font-size: 0.86rem;
        line-height: 1.5;
    }
    @keyframes hp-rise {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes hp-lattice-in {
        from { opacity: 0; transform: translate(35px, -47%) scale(0.96); }
        to { opacity: 0.95; transform: translate(0, -50%) scale(1); }
    }
    @keyframes hp-float {
        0%, 100% { transform: translateY(-50%); }
        50% { transform: translateY(calc(-50% - 10px)); }
    }
    @keyframes hp-float-mobile {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-8px); }
    }
    @media (max-width: 800px) {
        .block-container { padding-top: 4.25rem; }
        .hp-hero {
            min-height: 44rem;
            margin-top: -4.25rem;
            align-items: flex-start;
        }
        .hp-hero-inner {
            width: calc(100% - 2.5rem);
            padding-top: 5rem;
        }
        .hp-hero::after {
            z-index: 0;
            background: linear-gradient(180deg, rgba(3, 16, 21, 0.38), rgba(3, 16, 21, 0.08));
        }
        .hp-hero-copy { width: 100%; }
        .hp-hero-copy p { max-width: 26rem; }
        .hp-lattice {
            top: auto;
            right: -8rem;
            bottom: -9rem;
            width: 38rem;
            opacity: 0.32;
            animation: hp-float-mobile 10s ease-in-out infinite;
        }
        .hp-depth { grid-template-columns: 1fr; gap: 1.45rem; }
        .app-brand-subtitle { display: none; }
    }
    @media (prefers-reduced-motion: reduce) {
        .hp-hero-copy, .hp-lattice { animation: none; }
        *, *::before, *::after { scroll-behavior: auto !important; }
    }
    .feature-map-title {
        font-size: clamp(2rem, 4vw, 3.4rem);
        font-weight: 700;
        letter-spacing: -0.055em;
        line-height: 1;
        color: var(--hp-text);
        margin-bottom: 0.75rem;
    }
    div[data-testid="stExpander"] details {
        border-radius: 8px;
        border: 0;
        border-top: 1px solid var(--hp-border);
        background: transparent;
        box-shadow: none;
    }
    div[data-testid="stMetric"] {
        background: transparent;
        border: 0;
        border-top: 1px solid var(--hp-border);
        border-radius: 0;
        padding: 0.85rem 0.15rem;
        box-shadow: none;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 1.5rem;
        border-bottom: 1px solid var(--hp-border);
    }
    div[data-testid="stTabs"] [data-baseweb="tab"] {
        padding-left: 0;
        padding-right: 0;
    }
    div[data-testid="stDataFrame"],
    div[data-testid="stTable"] {
        overflow: hidden;
        border: 1px solid var(--hp-border);
        border-radius: 8px;
    }
    div[data-testid="stCode"] {
        border-radius: 8px;
        border: 1px solid var(--hp-border);
        box-shadow: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

feature_map_view = st.query_params.get("view") == "feature-map"
requested_workspace = st.query_params.get("workspace")
primary_section = requested_workspace if requested_workspace in workspace_names() else None
st.session_state.primary_section = primary_section

if feature_map_view:
    st.markdown(
        """
        <div class="app-brand-wrap">
            <div class="app-brand-title">Hybrid <span>Perovskite Studio</span></div>
            <div class="app-brand-subtitle">Materials analysis workspace</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="feature-map-panel">
            <div class="landing-eyebrow">Feature Map</div>
            <div class="feature-map-title">Hybrid Perovskite Studio Feature Map</div>
            <div class="landing-copy">
                This page shows the current workspace and tool tree.
                <a href="?" target="_self">Return to the main app</a>.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    feature_columns = st.columns(2)
    for index, (workspace_name, tree) in enumerate(workspace_tree.items()):
        with feature_columns[index % 2]:
            st.markdown(f"### {workspace_name}")
            st.markdown("\n".join(render_tree_lines(tree)))
            st.divider()
    st.stop()

if primary_section is None:
    st.markdown(
        """
        <section class="hp-hero" aria-labelledby="hp-hero-title">
            <div class="hp-hero-inner">
                <div class="hp-hero-copy">
                    <div class="hp-hero-kicker">Hybrid Perovskite Studio</div>
                    <h1 class="hp-hero-brand">HPS</h1>
                    <h2 class="hp-hero-title" id="hp-hero-title">
                        From atomic structure to materials insight.
                    </h2>
                    <p>
                        Prepare structures, interrogate simulation outputs, and move between
                        geometry, electronic, and dynamics workflows in one research workspace.
                    </p>
                    <div class="hp-hero-actions">
                        <a class="hp-hero-primary" href="#workspaces">Choose a workspace&nbsp; →</a>
                        <a class="hp-hero-secondary" href="?view=feature-map" target="_self">
                            Explore every tool
                        </a>
                    </div>
                </div>
            </div>
            <svg class="hp-lattice" viewBox="0 0 820 720" fill="none"
                 xmlns="http://www.w3.org/2000/svg" role="img"
                aria-label="Abstract hybrid perovskite crystal lattice">
                <defs>
                    <linearGradient id="hp-cell" x1="140" y1="100" x2="650" y2="590"
                                    gradientUnits="userSpaceOnUse">
                        <stop stop-color="#C8FFF7" stop-opacity=".4"/>
                        <stop offset="1" stop-color="#56D9CB" stop-opacity=".82"/>
                    </linearGradient>
                    <radialGradient id="hp-a-site" cx="35%" cy="28%" r="70%">
                        <stop stop-color="#F2FFFD"/>
                        <stop offset=".35" stop-color="#77EBDD"/>
                        <stop offset="1" stop-color="#087D89"/>
                    </radialGradient>
                    <radialGradient id="hp-b-site" cx="35%" cy="25%" r="70%">
                        <stop stop-color="#FFF4C7"/>
                        <stop offset=".4" stop-color="#F6C866"/>
                        <stop offset="1" stop-color="#B46620"/>
                    </radialGradient>
                    <filter id="hp-glow" x="-90%" y="-90%" width="280%" height="280%">
                        <feGaussianBlur stdDeviation="5" result="blur"/>
                        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                    </filter>
                </defs>
                <g fill="rgba(79, 215, 200, .025)" stroke="url(#hp-cell)" stroke-width="2.2">
                    <path d="M160 120H480V440H160V120Z"/>
                    <path d="M280 220H600V540H280V220Z"/>
                    <path d="M160 120L280 220M480 120L600 220M480 440L600 540M160 440L280 540"/>
                </g>
                <g stroke="#B8FFF4" stroke-width="2">
                    <path d="M380 170L440 380L540 330L380 170Z" fill="#65E6D4" fill-opacity=".09"/>
                    <path d="M380 170L320 280L220 330L380 170Z" fill="#65E6D4" fill-opacity=".05"/>
                    <path d="M380 490L440 380L540 330L380 490Z" fill="#65E6D4" fill-opacity=".13"/>
                    <path d="M380 490L320 280L220 330L380 490Z" fill="#65E6D4" fill-opacity=".07"/>
                    <path d="M380 170L440 380L380 490L320 280L380 170Z" fill="none"/>
                    <path d="M220 330L320 280L540 330L440 380L220 330Z" fill="none"/>
                </g>
                <g fill="url(#hp-a-site)" filter="url(#hp-glow)">
                    <circle cx="160" cy="120" r="13"/><circle cx="480" cy="120" r="13"/>
                    <circle cx="480" cy="440" r="13"/><circle cx="160" cy="440" r="13"/>
                    <circle cx="280" cy="220" r="14"/><circle cx="600" cy="220" r="14"/>
                    <circle cx="600" cy="540" r="14"/><circle cx="280" cy="540" r="14"/>
                </g>
                <g fill="#D5FFF9" filter="url(#hp-glow)">
                    <circle cx="380" cy="170" r="8"/><circle cx="380" cy="490" r="8"/>
                    <circle cx="220" cy="330" r="8"/><circle cx="540" cy="330" r="8"/>
                    <circle cx="320" cy="280" r="8"/><circle cx="440" cy="380" r="8"/>
                </g>
                <circle cx="380" cy="330" r="24" fill="#F2B84F" opacity=".12"
                        filter="url(#hp-glow)"/>
                <circle cx="380" cy="330" r="16" fill="url(#hp-b-site)"/>
            </svg>
        </section>
        <div id="workspaces" class="hp-section-label">Four focused workspaces</div>
        <div class="hp-section-title">Begin with the material question in front of you.</div>
        """,
        unsafe_allow_html=True,
    )
    _debug_log("startup: landing hero rendered")
else:
    st.markdown(
        """
        <div class="app-brand-wrap">
            <div class="app-brand-title">Hybrid <span>Perovskite Studio</span></div>
            <div class="app-brand-subtitle">Materials analysis workspace</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _debug_log("startup: compact title rendered")

workspace_columns = st.columns(4)
for column, workspace_name in zip(workspace_columns, workspace_names()):
    card_class = "workspace-card active" if workspace_name == primary_section else "workspace-card"
    if primary_section is not None:
        card_class += " compact"
    with column:
        st.markdown(
            f"""
            <div class="{card_class}">
                <div class="workspace-card-title">{workspace_name}</div>
                <div class="workspace-card-body">{workspace_descriptions[workspace_name]}</div>
            </div>
            {
                f'<span class="workspace-open selected">{workspace_name} Selected</span>'
                if primary_section == workspace_name
                else f'<a class="workspace-open" href="?workspace={workspace_name}" '
                     f'target="_self">Open {workspace_name}</a>'
            }
            """,
            unsafe_allow_html=True,
        )

if primary_section is None:
    st.markdown(
        """
        <div class="hp-depth">
            <div class="hp-depth-lead">One continuous path through your materials data.</div>
            <div class="hp-depth-item">
                <span>01</span><strong>Prepare</strong>
                <p>
                    Inspect structures and make reproducible molecular or lattice transformations.
                </p>
            </div>
            <div class="hp-depth-item">
                <span>02</span><strong>Interrogate</strong>
                <p>Connect geometry with bands, density of states, spin, diffraction, and PDF.</p>
            </div>
            <div class="hp-depth-item">
                <span>03</span><strong>Resolve</strong>
                <p>Analyze trajectories and export publication-ready scientific outputs.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    toolbar_col1, toolbar_col2 = st.columns([6, 1.4])
    with toolbar_col1:
        st.markdown(
            f"""
            <div class="workspace-page-head">
                <div class="workspace-header">Current workspace</div>
                <div class="workspace-page-title">{primary_section}</div>
                <div class="workspace-page-copy">
                    {workspace_descriptions[primary_section]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with toolbar_col2:
        st.markdown(
            '<a class="workspace-start" href="?" target="_self">Start Page</a>',
            unsafe_allow_html=True,
        )

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
if (
    uploaded_structure_name
    and uploaded_structure_bytes is not None
    and primary_section == "Structure"
):
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
    st.warning(
        "Load a structure from Structure -> Overview before using structure-dependent tools."
    )
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

    render_molecule_analysis(
        polarization_option=polarization_option,
        charge_analysis_option=charge_analysis_option,
        com_option=com_option,
        dm_option=dm_option,
        modified_atoms=modified_atoms,
        molecules=molecules,
        render_section_header=render_section_header,
    )
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
            file_name=st.session_state.file_name,
            file_bytes=uploaded_structure_bytes,
            workflow_registry=_get_backend_workflow_registry(),
            render_section_header=render_section_header,
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

render_electronic_workspace(
    plot_polarization_option=plot_polarization_option,
    plot_pdos_option=plot_pdos_option,
    plot_bs_option=plot_bs_option,
    plot_spin_option=plot_spin_option,
    plot_absorption_option=plot_absorption_option,
    render_section_header=render_section_header,
)
if deviation_calculation_option:
    render_percentage_deviation(render_section_header=render_section_header)

render_dynamics_workspace(
    MD_option=MD_option,
    MDanalysis_option=MDanalysis_option,
    render_section_header=render_section_header,
)
render_spin_texture_3d(
    plot_spin_v2_option=plot_spin_v2_option,
    render_section_header=render_section_header,
)
render_utilities_workspace(
    script_option=script_option,
    xy_plot_option=xy_plot_option,
    render_section_header=render_section_header,
)
