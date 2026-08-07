"""Utilities workspace renderers."""

from __future__ import annotations

import json
import re
from io import BytesIO

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_extras.jupyterlite import jupyterlite

from hps.core.expressions import evaluate_math_expression

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



def render_utilities_workspace(
    *, script_option: bool, xy_plot_option: bool, render_section_header
) -> None:
    if script_option:
        render_section_header(
            "Run your own python script!",
            kicker="Utilities Workspace",
            subtitle="This feature uses JupyterLite and runs entirely in your browser. It does not currently have access to previously uploaded files.",
        )
        jupyterlite(900, 1600)

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
