from __future__ import annotations

import json
from itertools import combinations_with_replacement

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from diffpy.structure import loadStructure
from ase.data import atomic_numbers
from ase.neighborlist import neighbor_list
from diffpy.pdffit2 import PdfFit
from plotly.subplots import make_subplots
from pymatgen.core import Structure
from scipy.stats import pearsonr


DEFAULT_DIFFPY_STRUCTURE_ATTRIBUTES = {"Uisoequiv": 0.01}
DEFAULT_PDF_CALCULATOR_KWARGS = {
    "qmin": 1,
    "qmax": 20,
    "rmin": 1.0,
    "rmax": 20.0,
    "qdamp": 0.06,
    "qbroad": 0.06,
}

def reduced_pdf_to_gr(df, rho0, g_col="G_exp", r_col="r", r_min=1e-6):
    out = df.copy()
    r = out[r_col].to_numpy()
    G = out[g_col].to_numpy()

    g = np.ones_like(G, dtype=float)
    mask = r > r_min
    g[mask] = 1 + G[mask] / (4 * np.pi * r[mask] * rho0)

    out["g_r"] = g
    return out


def infer_rho0_from_cif(cif_bytes):
    structure = Structure.from_str(cif_bytes.decode("utf-8", errors="ignore"), fmt="cif")
    n_atoms = len(structure)
    volume = structure.lattice.volume
    rho0 = n_atoms / volume
    return rho0, n_atoms, volume


def integrate_gr_window(df, r1, r2, r_col="r", g_col="g_r", rho0=None):
    w = df[(df[r_col] >= r1) & (df[r_col] <= r2)].copy()
    if len(w) < 2:
        return None

    r = w[r_col].to_numpy()
    g = w[g_col].to_numpy()

    integral_gr = np.trapz(g, r)
    result = {"integral_gdr": integral_gr}

    if rho0 is not None:
        coord_like = 4 * np.pi * rho0 * np.trapz((r ** 2) * g, r)
        result["coordination_like"] = coord_like

    return result

def calculate_pdf(
        diffpy_structure,
        diffpy_structure_attributes=None,
        pdf_calculator_kwargs=None,
):
    """Computes the PDF of the given structure.

    Parameters
    ----------
    structure : pymatgen.core.structure.Structure
        Materials structure.
    diffpy_structure_attributes : dict, optional
        Attributes to set on the diffpy structure object.
    pdf_calculator_kwargs : dict, optional
        Keyword arguments to pass to the diffpy PDF calculator.

    Returns
    -------
    numpy.ndarray
    """

    diffpy_structure_attributes = (
        DEFAULT_DIFFPY_STRUCTURE_ATTRIBUTES.copy()
        if diffpy_structure_attributes is None
        else diffpy_structure_attributes
    )
    pdf_calculator_kwargs = (
        DEFAULT_PDF_CALCULATOR_KWARGS.copy()
        if pdf_calculator_kwargs is None
        else pdf_calculator_kwargs
    )

    for key, value in diffpy_structure_attributes.items():
        setattr(diffpy_structure, key, value)

    pf = PdfFit()
    pf.alloc('X',
             pdf_calculator_kwargs['qmax'],
             pdf_calculator_kwargs['qdamp'],
             pdf_calculator_kwargs['rmin'],
             pdf_calculator_kwargs['rmax'],
             1800
             )
    pf.setvar(pf.qbroad, pdf_calculator_kwargs['qbroad'])
    pf.add_structure(diffpy_structure)
    pf.calc()

    r1 = np.asarray(pf.getR())
    g1 = np.asarray(pf.getpdf_fit())

    return r1, g1


def compute_pcc(experimental: tuple, simulated: tuple) -> float:
    """
    Compute the Pearson correlation coefficient between experimental and simulated PDF data.

    Parameters:
        experimental: tuple of (r, g_exp) arrays
        simulated: tuple of (r, g_sim_interp) arrays (must be on same r grid)

    Returns:
        Pearson correlation coefficient (float)
    """
    _, g_exp = experimental
    _, g_sim = simulated

    if len(g_exp) != len(g_sim):
        raise ValueError("g_exp and g_sim must be the same length.")

    corr_coef, _ = pearsonr(g_exp, g_sim)
    return corr_coef

def compute_rdf_weighted(structure, pair=('O', 'H'), r_max=10.0, bins=200, w=True):
    a1, a2 = pair
    indices1 = [i for i, atom in enumerate(structure) if atom.symbol == a1]
    indices2 = [i for i, atom in enumerate(structure) if atom.symbol == a2]

    if not indices1 or not indices2:
        return None, None

    volume = structure.get_volume()
    if volume <= 0:
        return None, None

    i_list, j_list, distances = neighbor_list("ijd", structure, cutoff=r_max)

    mask = []
    weights = []
    for i, j in zip(i_list, j_list):
        s_i, s_j = structure[i].symbol, structure[j].symbol
        if (s_i, s_j) == (a1, a2) or (s_i, s_j) == (a2, a1):
            if w:
                Z_i = atomic_numbers[s_i]
                Z_j = atomic_numbers[s_j]
                weights.append(Z_i * Z_j)
                mask.append(True)
            else:
                weights.append(1)
                mask.append(True)
        else:
            mask.append(False)

    distances = distances[mask]
    weights = np.array(weights)

    if len(distances) == 0:
        return None, None

    hist, edges = np.histogram(distances, bins=bins, range=(0, r_max), weights=weights)
    r = 0.5 * (edges[1:] + edges[:-1])
    shell_volumes = 4 / 3 * np.pi * (edges[1:] ** 3 - edges[:-1] ** 3)
    avg_density = len(indices2) / volume
    rdf = hist / (len(indices1) * avg_density * shell_volumes)

    return r, rdf


def compute_pdf_from_rdf_df(df_all: pd.DataFrame, density: float) -> pd.DataFrame:
    df = df_all.copy()
    df["PDF(r)"] = 4 * np.pi * df["r (Å)"] ** 2 * density * df["g(r)"]
    return df
def plot_rdf_pdf(atom_list, modified_atoms, df_pdf, rmax, bins, compute_rdf_weighted, config, weight=True):
    fig_rdf = make_subplots(specs=[[{"secondary_y": True}]])
    df_all = pd.DataFrame()

    all_pairs = list(combinations_with_replacement(atom_list, 2))
    for pair in all_pairs:
        r, g_r = compute_rdf_weighted(modified_atoms, pair=pair, r_max=rmax, bins=bins, w=weight)
        if r is not None:
            pair_label = f"{pair[0]}–{pair[1]}"
            bar_color = config.get("pair_colors", {}).get(pair_label, "#1f77b4")

            if config.get("show_rdf", True):
                fig_rdf.add_trace(
                    go.Bar(
                        x=r,
                        y=g_r,
                        name=pair_label,
                        marker_color=bar_color,
                        opacity=config.get("opacity", 0.6),
                    ),
                    secondary_y=False,
                )
            df_temp = pd.DataFrame({
                "r (Å)": r,
                "g(r)": g_r,
                "pair": pair_label
            })
            df_all = pd.concat([df_all, df_temp], ignore_index=True)
        else:
            st.warning(f"No data found for pair {pair[0]}–{pair[1]}")

    if config.get("show_pdf", True) and "r (Å)" in df_pdf.columns and "G_sim(r)" in df_pdf.columns:
        fig_rdf.add_trace(
            go.Scatter(
                x=df_pdf["r (Å)"],
                y=df_pdf["G_sim(r)"],
                mode="lines",
                name="Simulated G(r)",
                line=dict(
                    color=config["line_color"],
                    width=config["linewidth"],
                    dash=config["line_style"],
                ),
            ),
            secondary_y=True,
        )

    label_font = {
        "size": config["text_size"],
        "color": config.get("tick_label_color", "#000000"),
        "family": config.get("tick_font_family", "Arial")
    }
    tick_font = {
        "size": config["tick_label_size"],
        "color": config["tick_label_color"],
        "family": config["tick_font_family"]
    }

    fig_rdf.update_layout(
        barmode="stack",
        template="plotly_white",
        font=label_font,
        legend=dict(
            x=config["legend_x"],
            y=config["legend_y"],
            orientation=config["legend_orientation"],
            font=dict(size=config["legend_font_size"])
        ),
        height=600,
        width=int(600 * config["aspect_ratio"]),
    )

    fig_rdf.update_xaxes(
        title_text="r (Å)", linewidth=1.5,
        showgrid=config["show_grid"], tickfont=tick_font, title_font=label_font
    )
    fig_rdf.update_yaxes(
        title_text="Simulated RDF: g(r)", secondary_y=False,
        showgrid=config["show_grid"], tickfont=tick_font, title_font=label_font
    )
    fig_rdf.update_yaxes(
        title_text="Simulated PDF: G(r)", secondary_y=True,
        showgrid=config["show_grid"], tickfont=tick_font, title_font=label_font
    )

    return fig_rdf, df_all
def get_color_map(pairs, palette_name="Plotly"):
    cmap = getattr(px.colors.qualitative, palette_name, px.colors.qualitative.Plotly)
    color_cycle = (cmap * ((len(pairs) // len(cmap)) + 1))[:len(pairs)]
    return dict(zip([f"{a}–{b}" for (a, b) in pairs], color_cycle))

def load_or_create_plot_config(all_pairs):
    st.subheader("Plotly Plot Appearance Settings")

    uploaded_config = st.file_uploader("Upload Plot Config (JSON)", type=["json"])
    config = {}
    if uploaded_config:
        try:
            config = json.load(uploaded_config)
            st.success("Configuration loaded.")
        except Exception as e:
            st.error(f"Failed to load config: {e}")

    with st.expander("Customize Plot Appearance"):
        available_palettes = [
            "Plotly", "D3", "G10", "T10", "Alphabet", "Dark2", "Set1", "Pastel1",
            "Pastel2", "Set2", "Set3", "Bold", "Safe", "Vivid"
        ]

        selected_palette = config.get("palette", "Plotly")
        if selected_palette not in available_palettes:
            selected_palette = "Plotly"

        config['palette'] = st.selectbox("Color Palette", available_palettes,
                                         index=available_palettes.index(selected_palette))

        default_colors = get_color_map(all_pairs, config['palette'])
        pair_colors = config.get("pair_colors", {})
        st.markdown("#### RDF Bar Colors")
        for pair in all_pairs:
            label = f"{pair[0]}–{pair[1]}"
            pair_colors[label] = st.color_picker(f"Color for {label}", pair_colors.get(label, default_colors[label]))
        config["pair_colors"] = pair_colors

        config['line_color'] = st.color_picker("Line Color (PDF)", config.get('line_color', "#d62728"))
        config['line_style'] = st.selectbox("Line Style (PDF)", ["solid", "dot", "dash", "longdash"],
                                            index=["solid", "dot", "dash", "longdash"].index(config.get("line_style", "solid")))
        config['opacity'] = st.slider("Bar Opacity", 0.0, 1.0, config.get("opacity", 0.6), 0.05)
        config['linewidth'] = st.slider("PDF Line Width", 1.0, 6.0, config.get("linewidth", 3.0), 0.5)

        config['show_rdf'] = st.checkbox("Show RDF (g(r))", value=config.get("show_rdf", True))
        config['show_pdf'] = st.checkbox("Show PDF (G(r))", value=config.get("show_pdf", True))

        config['show_grid'] = st.checkbox("Show Grid Lines", config.get("show_grid", True))
        config['text_size'] = st.slider("Label Text Size", 10, 30, config.get("text_size", 16))
        config['tick_label_size'] = st.slider("Tick Label Size", 6, 20, config.get("tick_label_size", 12))
        config['tick_label_color'] = st.color_picker("Tick Label Color", config.get("tick_label_color", "#000000"))
        config['tick_font_family'] = st.selectbox("Tick Font Family", ["Arial", "Courier New", "Raleway"],
                                                  index=["Arial", "Courier New", "Raleway"].index(config.get("tick_font_family", "Arial")))

        config['legend_font_size'] = st.slider("Legend Font Size", 10, 24, config.get("legend_font_size", 14))
        config['legend_x'] = st.slider("Legend X Position", 0.0, 1.0, config.get("legend_x", 0.01))
        config['legend_y'] = st.slider("Legend Y Position", 0.0, 1.0, config.get("legend_y", 0.99))
        config['legend_orientation'] = st.selectbox("Legend Orientation", ["v", "h"], index=["v", "h"].index(config.get("legend_orientation", "v")))

        config['aspect_ratio'] = st.slider("Aspect Ratio (y/x)", 0.2, 3.0, config.get("aspect_ratio", 1.0), 0.1)

    config_json = json.dumps(config, indent=2)
    st.download_button("Download Plotly Config", config_json, file_name="plotly_config.json")

    return config

def load_or_create_plot_config_matplotlib(all_pairs):
    """Build a matplotlib config via Streamlit widgets."""
    st.subheader("Matplotlib Plot Appearance Settings")
    uploaded = st.file_uploader("Upload Plot Config (JSON)", type="json")
    if uploaded:
        try:
            config = json.load(uploaded)
            st.success("Configuration loaded.")
        except Exception:
            st.error("Failed to load config.")
            config = {}
    else:
        config = {}

    with st.expander("Customize Appearance"):
        # --- Style & Figure ---
        styles = plt.style.available
        # ensure saved style exists
        default_style = config.get('style_sheet', styles[0])
        if default_style not in styles:
            default_style = styles[5]
        config['style_sheet'] = st.selectbox("Matplotlib Style", styles, index=styles.index(default_style))

        config['fig_width']  = st.slider("Width (inches)",  4.0, 12.0, config.get('fig_width',  8.0), 0.5)
        config['fig_height'] = st.slider("Height (inches)", 3.0, 10.0, config.get('fig_height', 6.0), 0.5)
        config['dpi']        = st.slider("DPI",             50,   300, config.get('dpi',    100),   1)

        # new: axes (spine) linewidth
        config['axes_linewidth'] = st.slider(
            "Axes (spine) Linewidth", 0.5, 5.0,
            config.get('axes_linewidth', 1.5), 0.1
        )

        # --- Plot types & colors ---
        config['rdf_type'] = st.selectbox(
            "RDF Plot Type", ["bar","line","both"],
            index=["bar","line","both"].index(config.get('rdf_type','bar'))
        )
        config['bar_width_factor'] = st.slider(
            "Bar width factor", 0.1, 2.0, config.get('bar_width_factor',0.9), 0.05
        )
        st.markdown("**RDF Colors / Line**")
        config.setdefault('pair_colors', {})
        default_cmap = plt.get_cmap('tab10').colors
        for i,p in enumerate(all_pairs):
            lbl = f"{p[0]}–{p[1]}"
            default = default_cmap[i % len(default_cmap)]
            default_hex = "#{:02x}{:02x}{:02x}".format(
                int(default[0]*255),int(default[1]*255),int(default[2]*255))
            config['pair_colors'][lbl] = st.color_picker(
                f"Color for {lbl}", config['pair_colors'].get(lbl, default_hex))
        config['bar_alpha']     = st.slider("Bar opacity", 0.0,1.0,config.get('bar_alpha',0.6),0.05)
        config['rdf_linewidth'] = st.slider("RDF line width", 0.5,5.0,config.get('rdf_linewidth',2.0),0.1)
        config['rdf_linestyle'] = st.selectbox(
            "RDF line style", ['solid','dashed','dotted','dashdot'],
            index=['solid','dashed','dotted','dashdot'].index(config.get('rdf_linestyle','solid'))
        )
        config['rdf_marker']    = st.selectbox(
            "RDF marker", ['','o','s','^','x','D'],
            index=['','o','s','^','x','D'].index(config.get('rdf_marker',''))
        )
        config['rdf_ms']        = st.slider("RDF marker size", 0,12,config.get('rdf_ms',6))


        # --- PDF curve & fill ---
        st.markdown("**PDF Curve & Fill**")
        config['show_pdf']       = st.checkbox("Show PDF", config.get('show_pdf',True))
        config['pdf_color']      = st.color_picker("PDF line color", config.get('pdf_color','#d62728'))
        config['pdf_linestyle']  = st.selectbox(
            "PDF line style", ['solid','dashed','dotted','dashdot'],
            index=['solid','dashed','dotted','dashdot']
                  .index(config.get('pdf_linestyle','solid'))
        )
        config['pdf_linewidth']  = st.slider("PDF line width", 0.5,5.0,config.get('pdf_linewidth',2.0),0.1)
        config['fill_pdf']       = st.checkbox("Fill under PDF", config.get('fill_pdf',False))
        config['fill_alpha']     = st.slider("Fill alpha", 0.0,1.0,config.get('fill_alpha',0.3),0.05)

        # --- Axes & scales & labels ---
        config['xlabel']   = st.text_input("X-axis label", config.get('xlabel','r (Å)'))
        config['y1label']  = st.text_input("Primary Y-axis label", config.get('y1label','g(r)'))
        config['y2label']  = st.text_input("Secondary Y-axis label", config.get('y2label','G(r)'))
        config['x_scale']  = st.selectbox("X scale", ['linear','log'], index=['linear','log'].index(config.get('x_scale','linear')))
        config['y1_scale'] = st.selectbox("Primary Y scale", ['linear','log'], index=['linear','log'].index(config.get('y1_scale','linear')))
        if config['show_pdf']:
            config['y2_scale'] = st.selectbox("Secondary Y scale", ['linear','log'], index=['linear','log'].index(config.get('y2_scale','linear')))

        # --- Grid, ticks & spines visibility ---
        config['show_grid']  = st.checkbox("Show grid", config.get('show_grid',False))
        config['grid_axis']  = st.selectbox("Grid axis", ['both','x','y'], index=['both','x','y'].index(config.get('grid_axis','both')))
        config['grid_style'] = st.selectbox("Grid style", ['-','--','-.',':'], index=['-','--','-.',':'].index(config.get('grid_style','--')))
        config['grid_color'] = st.color_picker("Grid color", config.get('grid_color','#cccccc'))
        config['grid_alpha'] = st.slider("Grid alpha", 0.0,1.0,config.get('grid_alpha',0.7),0.05)
        config['minor_ticks'] = st.checkbox("Show minor ticks", config.get('minor_ticks',False))
        config['visible_spines'] = st.multiselect(
            "Visible spines", ['left','right','top','bottom'],
            default=config.get('visible_spines',['left','bottom','right','top'])
        )

        # --- Tick‐label visibility ---
        st.markdown("**Hide Tick Labels**")
        config['hide_xticklabels']  = not st.checkbox("Show X-axis tick labels",  not config.get('hide_xticklabels', False))
        config['hide_y1ticklabels'] = not st.checkbox("Show Primary Y-axis tick labels", not config.get('hide_y1ticklabels', False))
        if config.get('show_pdf', True):
            config['hide_y2ticklabels'] = not st.checkbox("Show Secondary Y-axis tick labels", not config.get('hide_y2ticklabels', False))
        else:
            config['hide_y2ticklabels'] = False

        # --- Legend & annotation ---
        config['legend_loc']        = st.selectbox(
            "Legend location",
            ['best','upper right','upper left','lower right','lower left','center'],
            index=['best','upper right','upper left','lower right','lower left','center']
                  .index(config.get('legend_loc','best'))
        )
        config['legend_frame']       = st.checkbox("Legend frame", config.get('legend_frame',True))
        config['legend_frame_alpha'] = st.slider("Legend frame alpha", 0.0,1.0,config.get('legend_frame_alpha',1.0),0.05)
        config['legend_edgecolor']   = st.color_picker("Legend edgecolor", config.get('legend_edgecolor','#000000'))

        # Text size controls —
        st.markdown("**Text Size Settings**")
        config['title_size'] = st.slider("Title font size", 12, 36, config.get('title_size', 18))
        config['axis_label_size'] = st.slider("Axis label font size", 10, 30, config.get('axis_label_size', 14))
        config['tick_label_size'] = st.slider("Tick label font size", 6, 24, config.get('tick_label_size', 12))
        config['legend_font_size'] = st.slider("Legend font size", 8, 24, config.get('legend_font_size', 12))

        config['annotate_peaks']      = st.checkbox("Annotate RDF peaks", config.get('annotate_peaks',False))
        config['peak_prominence']     = st.slider("Peak prominence", 0.0,1.0,config.get('peak_prominence',0.1),0.01)
        config['annotation_fontsize'] = st.slider("Annotation fontsize", 6,24,config.get('annotation_fontsize',12))
        config['annotation_color']    = st.color_picker("Annotation color", config.get('annotation_color','#000000'))

    st.download_button("Download Config", json.dumps(config,indent=2), file_name="mpl_config.json")
    return config


def plot_rdf_pdf_matplotlib(
    atom_list, modified_atoms, df_pdf, rmin, rmax, bins, compute_rdf_weighted, config, weight=True
):
    """
    Apply the rich matplotlib config to plot RDF (bar/line) and PDF.
    """
    plt.style.use(config.get('style_sheet', plt.style.available[0]))

    df_all = pd.DataFrame()
    pairs = list(combinations_with_replacement(atom_list,2))
    width = (rmax/bins) * config.get('bar_width_factor',0.9)

    fig, ax = plt.subplots(
        figsize=(config.get('fig_width', 8), config.get('fig_height', 6)),
        dpi=config.get('dpi', 100),
        facecolor='white'
    )
    ax.set_facecolor('white')
    ax2 = ax.twinx() if config.get('show_pdf', True) else None
    if ax2:
        ax2.set_facecolor('white')

    # scales
    ax.set_xscale(config.get('x_scale','linear'))
    ax.set_yscale(config.get('y1_scale','linear'))
    if ax2: ax2.set_yscale(config.get('y2_scale','linear'))

    # minor ticks
    if config.get('minor_ticks'):
        ax.minorticks_on()
        if ax2: ax2.minorticks_on()

    # spines (use new axes_linewidth)
    for side in ['left','right','top','bottom']:
        spine = ax.spines[side]
        spine.set_visible(side in config.get('visible_spines',[]))
        spine.set_linewidth(config.get('axes_linewidth',1.0))

    # grid
    if config.get('show_grid'):
        ax.grid(
            True,
            axis=config.get('grid_axis','both'),
            linestyle=config.get('grid_style','--'),
            color=config.get('grid_color','#cccccc'),
            alpha=config.get('grid_alpha',0.7)
        )

    # RDF plotting
    for pair in pairs:
        r, g_r = compute_rdf_weighted(modified_atoms, pair=pair, r_max=rmax, bins=bins, w=weight)
        if r is None:
            st.warning(f"No data for {pair}")
            continue
        lbl   = f"{pair[0]}–{pair[1]}"
        color = config['pair_colors'].get(lbl,'#1f77b4')

        if config['rdf_type'] in ['bar','both']:
            ax.bar(r, g_r, width=width, label=lbl,
                   color=color, alpha=config.get('bar_alpha', 0.6),
                   edgecolor='none', linewidth=0)
        if config['rdf_type'] in ['line','both']:
            ax.plot(
                r, g_r, label=lbl,
                color=color,
                linewidth=config.get('rdf_linewidth',2.0),
                linestyle=config.get('rdf_linestyle','solid'),
                marker=config.get('rdf_marker',''),
                markersize=config.get('rdf_ms',6)
            )

        df_all = pd.concat([
            df_all,
            pd.DataFrame({"r (Å)":r,"g(r)":g_r,"pair":lbl})
        ], ignore_index=True)

        # peak annotation
        if config.get('annotate_peaks'):
            try:
                from scipy.signal import find_peaks
                peaks, _ = find_peaks(g_r, prominence=config.get('peak_prominence',0.1))
                for idx in peaks:
                    ax.text(
                        r[idx], g_r[idx],
                        f"{r[idx]:.2f}",
                        fontsize=config.get('annotation_fontsize',12),
                        color=config.get('annotation_color','#000000'),
                        ha='center', va='bottom'
                    )
            except ImportError:
                st.warning("Install scipy for peak annotations.")

    # PDF line & fill
    if ax2 and "r (Å)" in df_pdf and "G_sim(r)" in df_pdf:
        x,y = df_pdf["r (Å)"], df_pdf["G_sim(r)"]
        ax2.plot(
            x,y,color=config.get('pdf_color','#d62728'),
            linestyle=config.get('pdf_linestyle','solid'),
            linewidth=config.get('pdf_linewidth',2.0),
            label="G(r)"
        )
        if config.get('fill_pdf'):
            ax2.fill_between(x,y,color=config.get('pdf_color','#d62728'),
                             alpha=config.get('fill_alpha',0.3))

    # Tick‐label hiding
    if config.get('hide_xticklabels', False):
        ax.set_xticklabels([])
    if config.get('hide_y1ticklabels', False):
        ax.set_yticklabels([])
    if ax2 and config.get('hide_y2ticklabels', False):
        ax2.set_yticklabels([])

    # labels
    ax.set_xlabel(config.get('xlabel','r (Å)'), fontsize=config.get('label_size',14))
    ax.set_ylabel(config.get('y1label','g(r)'),   fontsize=config.get('label_size',14))
    if ax2:
        ax2.set_ylabel(config.get('y2label','G(r)'), fontsize=config.get('label_size',14))

    # limits
    ax.set_xlim(rmin, rmax)
    y1min,y1max = config.get('y1_min',None), config.get('y1_max',None)
    if y1min is not None: ax.set_ylim(bottom=y1min)
    if y1max is not None: ax.set_ylim(top=y1max)
    if ax2:
        y2min,y2max = config.get('y2_min',None), config.get('y2_max',None)
        if y2min is not None: ax2.set_ylim(bottom=y2min)
        if y2max is not None: ax2.set_ylim(top=y2max)

    # — TITLE & LABELS using new sizes —
    # ax.set_title("RDF & PDF", fontsize=config.get('title_size', 18))
    ax.set_xlabel(config.get('xlabel', 'r (Å)'), fontsize=config.get('axis_label_size', 14))
    ax.set_ylabel(config.get('y1label', 'g(r)'), fontsize=config.get('axis_label_size', 14))
    if ax2:
        ax2.set_ylabel(config.get('y2label', 'G(r)'), fontsize=config.get('axis_label_size', 14))

    # — TICKS using new size —
    ax.tick_params(axis='x', labelsize=config.get('tick_label_size', 12))
    ax.tick_params(axis='y', labelsize=config.get('tick_label_size', 12))
    if ax2:
        ax2.tick_params(axis='y', labelsize=config.get('tick_label_size', 12))

    # — LEGEND using new size —
    handles, labels = ax.get_legend_handles_labels()
    if ax2:
        h2, l2 = ax2.get_legend_handles_labels()
        handles += h2;
        labels += l2
    ax.legend(
        handles, labels,
        loc=config.get('legend_loc', 'best'),
        fontsize=config.get('legend_font_size', 12),
        frameon=config.get('legend_frame', True),
        framealpha=config.get('legend_frame_alpha', 1.0),
        edgecolor=config.get('legend_edgecolor', '#000000')
    )

    fig.tight_layout()
    return fig, df_all

# # Helper: run PDF simulation for an ASE Atoms object
# def simulate_pdf_from_atoms(
#     atoms_obj: Atoms,
#     qmin: float,
#     qmax: float,
#     rmin: float,
#     rmax: float,
#     qdamp: float = 0.06,
#     qbroad: float = 0.06,
#     uiso: float = 0.01,
# ):
#     """
#     Returns r_grid (np.ndarray), G_sim (np.ndarray) for the given ASE Atoms.
#     """
#     # 1. symmetrize / clean (your existing logic)
#     pymatgen_structure = generate_symmetrized_structure(atoms_obj, 0.01, 0.1)
#
#     # 2. write temporary cif
#     with tempfile.TemporaryDirectory() as tmpdir:
#         cif_path = Path(tmpdir) / "temp_structure.cif"
#         CifWriter(pymatgen_structure).write_file(str(cif_path))
#
#         # 3. diffpy structure + PDF
#         diffpy_structure = loadStructure(str(cif_path))
#
#         r_calc, g_calc = calculate_pdf(
#             diffpy_structure,
#             diffpy_structure_attributes={"Uisoequiv": uiso},
#             pdf_calculator_kwargs={
#                 "qmin": qmin,
#                 "qmax": qmax,
#                 "rmin": rmin,
#                 "rmax": rmax,
#                 "qdamp": qdamp,
#                 "qbroad": qbroad,
#             },
#         )
#
#     return np.array(r_calc), np.array(g_calc)
#
# # Helper: interpolate onto common r-grid
# def interpolate_to_common_grid(r_target, r_src, g_src):
#     """
#     Returns g_src_interp evaluated at r_target using linear interp.
#     Extrapolation outside the source range is filled with nan.
#     """
#     return np.interp(
#         r_target,
#         r_src,
#         g_src,
#         left=np.nan,
#         right=np.nan,
#     )
#
# # Helper: Pearson correlation cost (1 - r)
# def pdf_mismatch_cost(sim_atoms_flat, base_atoms, r_exp, g_exp, fit_settings):
#     """
#     sim_atoms_flat: flattened coords (len = 3N)
#     base_atoms: ASE Atoms template (for cell, species, etc.)
#     r_exp, g_exp: experimental data vectors (common grid)
#     fit_settings: dict with qmin,qmax,rmin,rmax,etc.
#     """
#     # rebuild atoms with new positions
#     atoms_trial = base_atoms.copy()
#     coords = sim_atoms_flat.reshape((-1, 3))
#     atoms_trial.set_positions(coords)
#
#     # simulate PDF for trial structure
#     r_sim, g_sim = simulate_pdf_from_atoms(
#         atoms_trial,
#         qmin=fit_settings["qmin"],
#         qmax=fit_settings["qmax"],
#         rmin=fit_settings["rmin"],
#         rmax=fit_settings["rmax"],
#         qdamp=fit_settings["qdamp"],
#         qbroad=fit_settings["qbroad"],
#         uiso=fit_settings["uiso"],
#     )
#
#     # interpolate sim onto experimental r-grid
#     g_sim_interp = interpolate_to_common_grid(r_exp, r_sim, g_sim)
#
#     # mask nans / invalid
#     mask = np.isfinite(g_sim_interp) & np.isfinite(g_exp)
#     if np.count_nonzero(mask) < 5:
#         # not enough overlap, punish heavily
#         return 1.0
#
#     r_val, _ = pearsonr(g_sim_interp[mask], g_exp[mask])
#
#     # objective to MINIMIZE
#     return 1.0 - r_val
#
# # Helper: write final optimized structure to CIF (returns bytes)
# def atoms_to_cif_bytes(atoms_obj: Atoms):
#     """
#     Uses your generate_symmetrized_structure -> CIF pipeline,
#     returns CIF as bytes for st.download_button.
#     """
#     pymatgen_structure = generate_symmetrized_structure(atoms_obj, 0.01, 0.1)
#
#     tmp_buf = io.StringIO()
#     # We can't directly write to StringIO with CifWriter, so write to temp then read back
#     with tempfile.TemporaryDirectory() as tmpdir:
#         cif_path = Path(tmpdir) / "refined_structure.cif"
#         CifWriter(pymatgen_structure).write_file(str(cif_path))
#         with open(cif_path, "r") as f:
#             tmp_buf.write(f.read())
#     return tmp_buf.getvalue().encode("utf-8")
