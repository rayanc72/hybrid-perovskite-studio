import base64
import os
from pathlib import Path

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

_SPIN_VALLEY_ASSET = Path(__file__).with_name("assets") / "spinvalley.svg"
_SPIN_VALLEY_DATA_URI = (
    "data:image/svg+xml;base64,"
    + base64.b64encode(_SPIN_VALLEY_ASSET.read_bytes()).decode("ascii")
)
_LAYERED_PEROVSKITE_ASSET = (
    Path(__file__).with_name("assets") / "layered-perovskite.svg"
)
_LAYERED_PEROVSKITE_DATA_URI = (
    "data:image/svg+xml;base64,"
    + base64.b64encode(_LAYERED_PEROVSKITE_ASSET.read_bytes()).decode("ascii")
)


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
        top: 45%;
        right: max(-3rem, calc((100vw - 90rem) / 2));
        width: min(49vw, 46rem);
        height: auto;
        opacity: 0.95;
        transform: translateY(-50%);
        filter: drop-shadow(0 22px 45px rgba(0, 0, 0, 0.3));
        animation: hp-lattice-in 1.1s cubic-bezier(.22, .85, .3, 1) both,
                   hp-float 9s ease-in-out 1.1s infinite;
    }
    .hp-spin-field {
        position: absolute;
        z-index: 0;
        top: 74%;
        right: max(8rem, calc((100vw - 90rem) / 2 + 12rem));
        left: auto;
        width: min(51vw, 50rem);
        height: auto;
        opacity: 0.34;
        pointer-events: none;
        transform: translateY(-50%) rotate(-1deg);
        filter: saturate(1.04) contrast(1.02) brightness(1.04)
                drop-shadow(0 18px 32px rgba(0, 0, 0, 0.16));
        -webkit-mask-image: radial-gradient(ellipse 74% 70% at 50% 52%, #000 50%, transparent 100%);
        mask-image: radial-gradient(ellipse 74% 70% at 50% 52%, #000 50%, transparent 100%);
        animation: hp-spin-in 1.25s cubic-bezier(.22, .85, .3, 1) 0.2s both,
                   hp-spin-drift 14s ease-in-out 1.45s infinite;
    }
    .hp-spin-field-draft, .hp-lattice-draft { display: none; }
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
    @keyframes hp-spin-in {
        from { opacity: 0; transform: translate(42px, -46%) rotate(-3deg) scale(0.97); }
        to { opacity: 0.34; transform: translate(0, -50%) rotate(-1deg) scale(1); }
    }
    @keyframes hp-spin-drift {
        0%, 100% { transform: translateY(-50%) rotate(-1deg); }
        50% { transform: translate(-8px, calc(-50% + 7px)) rotate(-0.4deg); }
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
            right: -6rem;
            bottom: -1rem;
            width: 31rem;
            opacity: 0.32;
            animation: hp-float-mobile 10s ease-in-out infinite;
        }
        .hp-spin-field {
            top: auto;
            right: auto;
            left: -2rem;
            bottom: 2rem;
            width: 38rem;
            opacity: 0.18;
            transform: rotate(-2deg);
            animation: none;
            -webkit-mask-image: radial-gradient(ellipse 68% 62% at 52% 54%, #000 42%, transparent 100%);
            mask-image: radial-gradient(ellipse 68% 62% at 52% 54%, #000 42%, transparent 100%);
        }
        .hp-depth { grid-template-columns: 1fr; gap: 1.45rem; }
        .app-brand-subtitle { display: none; }
    }
    @media (prefers-reduced-motion: reduce) {
        .hp-hero-copy, .hp-lattice, .hp-spin-field { animation: none; }
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
        f"""
        <section class="hp-hero" aria-labelledby="hp-hero-title">
            <div class="hp-hero-inner">
                <div class="hp-hero-copy">
                    <div class="hp-hero-kicker">Hybrid Perovskite Studio</div>
                    <h1 class="hp-hero-brand">HPS</h1>
                    <h2 class="hp-hero-title" id="hp-hero-title">
                        From atomic structure to materials insight.
                    </h2>
                    <p>
                        Model structures, analyze simulation outputs, and experimental data, and move between
                        geometry, electronic, and dynamics workflows in one workspace.
                    </p>
                    <div class="hp-hero-actions">
                        <a class="hp-hero-primary" href="#workspaces">Choose a workspace&nbsp; →</a>
                        <a class="hp-hero-secondary" href="?view=feature-map" target="_self">
                            Explore every tool
                        </a>
                    </div>
                </div>
            </div>
            <img class="hp-spin-field" src="{_SPIN_VALLEY_DATA_URI}" alt="" aria-hidden="true"/>
            <svg class="hp-spin-field-draft" viewBox="0 0 820 720" fill="none"
                 xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <defs>
                    <linearGradient id="hp-spin-surface-lower" x1="142" y1="442"
                                    x2="711" y2="478" gradientUnits="userSpaceOnUse">
                        <stop stop-color="#4BA9F8" stop-opacity=".42"/>
                        <stop offset=".42" stop-color="#C7FFF7" stop-opacity=".18"/>
                        <stop offset=".62" stop-color="#F5FBF8" stop-opacity=".12"/>
                        <stop offset="1" stop-color="#FF8F7E" stop-opacity=".44"/>
                    </linearGradient>
                    <linearGradient id="hp-spin-surface-upper" x1="160" y1="305"
                                    x2="692" y2="354" gradientUnits="userSpaceOnUse">
                        <stop stop-color="#FF9B87" stop-opacity=".3"/>
                        <stop offset=".5" stop-color="#B9FFF5" stop-opacity=".12"/>
                        <stop offset="1" stop-color="#58B5FF" stop-opacity=".3"/>
                    </linearGradient>
                    <g id="hp-spin-arrow-blue" fill="none" stroke="#76BCFF"
                       stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M0 0H13M8-4L13 0L8 4" vector-effect="non-scaling-stroke"/>
                    </g>
                    <g id="hp-spin-arrow-red" fill="none" stroke="#FF9A88"
                       stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M0 0H13M8-4L13 0L8 4" vector-effect="non-scaling-stroke"/>
                    </g>
                    <clipPath id="hp-spin-lower-clip">
                        <path d="M116 408C190 340 255 525 347 430C439 325 490 575 585 455C640 370 690 375 725 382L693 523C619 591 554 676 462 568C370 463 319 687 227 582C172 517 160 538 147 545Z"/>
                    </clipPath>
                </defs>
                <g>
                    <path class="spin-surface upper"
                          d="M154 302C220 250 276 410 350 330C428 245 480 445 560 348C615 283 660 276 695 283L670 386C604 438 548 478 474 428C396 375 344 540 264 445C209 380 186 393 166 400Z"/>
                    <g class="spin-mesh upper">
                        <path d="M154 302C220 250 276 410 350 330C428 245 480 445 560 348C615 283 660 276 695 283"/>
                        <path d="M158 335C224 283 280 443 354 363C432 278 484 478 564 381C619 316 660 309 687 316"/>
                        <path d="M162 367C228 315 284 475 358 395C436 310 488 510 568 413C623 348 652 342 679 349"/>
                        <path d="M166 400C232 348 288 508 362 428C440 343 492 543 572 446C627 381 650 379 670 386"/>
                        <path d="M154 302C158 334 162 368 166 400M276 410C280 442 284 476 288 508M350 330C354 362 358 396 362 428M480 445C484 477 488 511 492 543M560 348C564 380 568 414 572 446M695 283C687 315 679 353 670 386"/>
                    </g>
                </g>
                <g>
                    <path class="spin-surface lower"
                          d="M116 408C190 340 255 525 347 430C439 325 490 575 585 455C640 370 690 375 725 382L693 523C619 591 554 676 462 568C370 463 319 687 227 582C172 517 160 538 147 545Z"/>
                    <g class="spin-mesh">
                        <path d="M116 408C190 340 255 525 347 430C439 325 490 575 585 455C640 370 690 375 725 382"/>
                        <path d="M124 442C198 374 263 559 355 464C447 359 498 609 593 489C648 404 688 409 717 416"/>
                        <path d="M132 476C206 408 271 593 363 498C455 393 506 643 601 523C656 438 684 443 709 450"/>
                        <path d="M140 510C214 442 279 627 371 532C463 427 514 677 609 557C664 472 676 477 701 486"/>
                        <path d="M147 545C221 477 286 662 378 567C470 462 521 712 616 592C671 507 680 516 693 523"/>
                        <path d="M116 408C124 441 132 477 147 545M255 525C263 558 271 594 286 662M347 430C355 463 363 499 378 567M490 575C498 608 506 644 521 712M585 455C593 488 601 524 616 592M725 382C717 415 709 451 693 523"/>
                    </g>
                    <g class="spin-arrow-field" clip-path="url(#hp-spin-lower-clip)">
                        <g transform="translate(270 575) rotate(12) scale(1 .62)">
                            <use href="#hp-spin-arrow-blue" transform="rotate(0) translate(22) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(30) translate(22) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(60) translate(22) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(90) translate(22) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(120) translate(22) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(150) translate(22) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(180) translate(22) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(210) translate(22) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(240) translate(22) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(270) translate(22) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(300) translate(22) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(330) translate(22) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(0) translate(52) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(30) translate(52) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(60) translate(52) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(90) translate(52) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(120) translate(52) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(150) translate(52) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(180) translate(52) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(210) translate(52) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(240) translate(52) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(270) translate(52) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(300) translate(52) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(330) translate(52) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(0) translate(82) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(45) translate(82) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(90) translate(82) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(135) translate(82) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(180) translate(82) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(225) translate(82) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(270) translate(82) rotate(180)"/>
                            <use href="#hp-spin-arrow-blue" transform="rotate(315) translate(82) rotate(180)"/>
                        </g>
                        <g transform="translate(510 610) rotate(12) scale(1 .62)">
                            <use href="#hp-spin-arrow-red" transform="rotate(0) translate(22)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(30) translate(22)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(60) translate(22)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(90) translate(22)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(120) translate(22)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(150) translate(22)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(180) translate(22)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(210) translate(22)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(240) translate(22)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(270) translate(22)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(300) translate(22)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(330) translate(22)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(0) translate(52)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(30) translate(52)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(60) translate(52)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(90) translate(52)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(120) translate(52)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(150) translate(52)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(180) translate(52)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(210) translate(52)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(240) translate(52)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(270) translate(52)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(300) translate(52)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(330) translate(52)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(0) translate(82)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(45) translate(82)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(90) translate(82)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(135) translate(82)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(180) translate(82)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(225) translate(82)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(270) translate(82)"/>
                            <use href="#hp-spin-arrow-red" transform="rotate(315) translate(82)"/>
                        </g>
                    </g>
                </g>
            </svg>
            <img class="hp-lattice" src="{_LAYERED_PEROVSKITE_DATA_URI}"
                 alt="Layered two-dimensional hybrid perovskite with organic cations"/>
            <svg class="hp-lattice-draft" viewBox="0 0 900 720" fill="none"
                 xmlns="http://www.w3.org/2000/svg" role="img"
                 aria-label="Layered two-dimensional hybrid perovskite with organic cations">
                <defs>
                    <linearGradient id="hp-octa-face" x1="-54" y1="-52" x2="54" y2="58"
                                    gradientUnits="userSpaceOnUse">
                        <stop stop-color="#C8FFF7" stop-opacity=".34"/>
                        <stop offset="1" stop-color="#2DB7B2" stop-opacity=".08"/>
                    </linearGradient>
                    <radialGradient id="hp-metal" cx="34%" cy="27%" r="72%">
                        <stop stop-color="#FFF4C7"/>
                        <stop offset=".42" stop-color="#F3BE54"/>
                        <stop offset="1" stop-color="#A75B1A"/>
                    </radialGradient>
                    <radialGradient id="hp-halide" cx="34%" cy="27%" r="72%">
                        <stop stop-color="#E9FFFB"/>
                        <stop offset=".38" stop-color="#72E8DB"/>
                        <stop offset="1" stop-color="#087985"/>
                    </radialGradient>
                    <filter id="hp-glow" x="-90%" y="-90%" width="280%" height="280%">
                        <feGaussianBlur stdDeviation="4" result="blur"/>
                        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                    </filter>
                    <g id="hp-octahedron">
                        <g fill="url(#hp-octa-face)" stroke="#AFFFF3" stroke-width="1.5">
                            <path d="M0-62L-58 0L-13-27Z"/>
                            <path d="M0-62L-13-27L58 0Z" fill-opacity=".22"/>
                            <path d="M0-62L58 0L14 29Z" fill-opacity=".13"/>
                            <path d="M0 62L14 29L58 0Z" fill-opacity=".25"/>
                            <path d="M0 62L-58 0L14 29Z" fill-opacity=".16"/>
                            <path d="M-58 0L-13-27L58 0L14 29Z" fill-opacity=".1"/>
                        </g>
                        <g stroke="#D4FFF9" stroke-width="1.35" stroke-opacity=".8">
                            <path d="M0-62L0 62M-58 0L58 0"/>
                            <path d="M0-62L-13-27M0-62L14 29M0 62L-13-27M0 62L14 29"/>
                        </g>
                        <g fill="url(#hp-halide)" filter="url(#hp-glow)">
                            <circle cy="-62" r="6.5"/><circle cy="62" r="6.5"/>
                            <circle cx="-58" r="6.5"/><circle cx="58" r="6.5"/>
                            <circle cx="-13" cy="-27" r="5.5"/><circle cx="14" cy="29" r="5.5"/>
                        </g>
                        <circle r="10" fill="url(#hp-metal)"/>
                    </g>
                    <g id="hp-organic">
                        <path d="M0 0V-17L13-31L4-47L18-62L9-78" stroke="#B9F6ED"
                              stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>
                        <circle r="8.5" fill="url(#hp-halide)"/>
                        <circle cx="13" cy="-31" r="3.5" fill="#F2BE58"/>
                        <circle cx="18" cy="-62" r="3.5" fill="#F2BE58"/>
                        <circle cx="9" cy="-78" r="4.5" fill="#D8FFF8"/>
                    </g>
                </defs>
                <g opacity=".72">
                    <g transform="translate(232 266)"><use href="#hp-organic"/></g>
                    <g transform="translate(332 256) scale(.94)"><use href="#hp-organic"/></g>
                    <g transform="translate(432 266)"><use href="#hp-organic"/></g>
                    <g transform="translate(532 256) scale(.94)"><use href="#hp-organic"/></g>
                    <g transform="translate(632 266)"><use href="#hp-organic"/></g>
                    <g transform="translate(732 256) scale(.94)"><use href="#hp-organic"/></g>
                </g>
                <g transform="translate(0 8) skewX(-10)">
                    <path d="M208 304L674 304L718 458L252 458Z" fill="#35BFB7" fill-opacity=".035"
                          stroke="#73E9DD" stroke-opacity=".24" stroke-width="2"/>
                    <g opacity=".9">
                        <g transform="translate(270 360) scale(.78)"><use href="#hp-octahedron"/></g>
                        <g transform="translate(360.48 360) scale(.78)"><use href="#hp-octahedron"/></g>
                        <g transform="translate(450.96 360) scale(.78)"><use href="#hp-octahedron"/></g>
                        <g transform="translate(541.44 360) scale(.78)"><use href="#hp-octahedron"/></g>
                        <g transform="translate(631.92 360) scale(.78)"><use href="#hp-octahedron"/></g>
                        <g transform="translate(291.06 403.68) scale(.78)"><use href="#hp-octahedron"/></g>
                        <g transform="translate(381.54 403.68) scale(.78)"><use href="#hp-octahedron"/></g>
                        <g transform="translate(472.02 403.68) scale(.78)"><use href="#hp-octahedron"/></g>
                        <g transform="translate(562.5 403.68) scale(.78)"><use href="#hp-octahedron"/></g>
                        <g transform="translate(652.98 403.68) scale(.78)"><use href="#hp-octahedron"/></g>
                    </g>
                </g>
                <g opacity=".62">
                    <g transform="translate(262 501) rotate(180)"><use href="#hp-organic"/></g>
                    <g transform="translate(362 511) rotate(180) scale(.94)"><use href="#hp-organic"/></g>
                    <g transform="translate(462 501) rotate(180)"><use href="#hp-organic"/></g>
                    <g transform="translate(562 511) rotate(180) scale(.94)"><use href="#hp-organic"/></g>
                    <g transform="translate(662 501) rotate(180)"><use href="#hp-organic"/></g>
                    <g transform="translate(762 511) rotate(180) scale(.94)"><use href="#hp-organic"/></g>
                </g>
            </svg>
        </section>
        <div id="workspaces" class="hp-section-label">Focused workspaces</div>
        <div class="hp-section-title">Start here.</div>
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
                <p>Analyze and export publication-ready scientific outputs.</p>
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
