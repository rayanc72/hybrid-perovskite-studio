import matplotlib as mpl
import streamlit as st

from hps.io.paths import APP_TMP_DIR
from hps.ui.backend_workflows import ensure_workflow_registry
from hps.ui.workspaces.dynamics import render_dynamics_workspace
from hps.ui.workspaces.electronic import (
    load_pdos_color_preferences,
    render_electronic_workspace,
    render_spin_texture_3d,
)
from hps.ui.workspaces.structure.overview import (
    render_current_structure_card,
    render_structure_upload_panel,
)
from hps.ui.workspaces.structure.navigation import render_structure_navigation
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
from hps.ui.workspaces.utilities import render_utilities_workspace
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
