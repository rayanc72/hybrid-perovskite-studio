"""Structure pair-distribution-function workflow renderer."""

from __future__ import annotations

import base64
import io
import json
import os
from collections.abc import Callable
from importlib import import_module
from itertools import combinations_with_replacement
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from hps.domain.pdf import (
    infer_rho0_from_cif,
    integrate_gr_window,
    load_or_create_plot_config,
    load_or_create_plot_config_matplotlib,
    plot_rdf_pdf,
    plot_rdf_pdf_matplotlib,
    reduced_pdf_to_gr,
)
from hps.ui.backend_workflows import get_workflow_state, run_workflow

PDF_WORKFLOW_TITLES = {
    "Simulate PDF": "Simulate pair distribution function",
    "Plot RDF": "Plot radial distribution function",
    "Compare experimental PDF": "Compare experimental and simulated PDF",
    "Convert reduced PDF to g(r)": "Convert reduced PDF to g(r)",
}


def pdf_analysis_available() -> bool:
    """Return whether the optional PDF implementation can be imported."""

    try:
        import_module("hps.domain.pdf_analysis")
    except Exception:
        return False
    return True


def parse_reduced_pdf(content: bytes, r_range: tuple[float, float]) -> pd.DataFrame:
    """Parse a PDFgui-style reduced-PDF file and clip it to an r range."""

    lines = content.decode("utf-8", errors="ignore").splitlines()
    data_start = next(
        (index for index, line in enumerate(lines) if line.strip().startswith("#### start data")),
        None,
    )
    if data_start is None:
        raise ValueError("Couldn't find '#### start data' in the .gr file.")
    frame = pd.read_csv(
        io.StringIO("\n".join(lines[data_start + 3 :])),
        sep=r"\s+",
        header=None,
        names=["r", "G_exp"],
    )
    frame = frame.apply(pd.to_numeric, errors="coerce").dropna()
    frame = frame[frame["r"].between(*r_range)].reset_index(drop=True)
    if frame.empty:
        raise ValueError("No PDF data points fall within the selected r range.")
    return frame


def render_pdf_analysis(
    workflow: str | None,
    modified_atoms: Any,
    *,
    file_name: str,
    file_bytes: bytes,
    workflow_registry: dict,
    render_section_header: Callable[..., None],
) -> None:
    """Render the selected Structure PDF workflow."""

    PDF_workflow = workflow
    PDF_ANALYSIS_AVAILABLE = pdf_analysis_available()

    render_section_header(
        PDF_WORKFLOW_TITLES.get(PDF_workflow, "PDF Analysis"),
        kicker="Structure Workspace",
        subtitle="Run the selected pair distribution function workflow for the loaded structure.",
    )

    if not PDF_ANALYSIS_AVAILABLE:
        st.warning(
            "PDF Analysis is available in this workspace, but the optional PDF dependencies are not installed in the current environment."
        )
        st.code('pip install "hybrid-perovskite-studio[pdf]"', language="bash")
        st.info("After installing the PDF extra, restart the app and reopen this tool.")
        st.stop()

    needs_simulated_pdf = PDF_workflow in {
        "Simulate PDF",
        "Plot RDF",
        "Compare experimental PDF",
    }

    if needs_simulated_pdf:
        qmin, qmax = st.slider("q (Å⁻¹)", 0, 25, (1, 20))
    rmin, rmax = st.slider("r (Å)", 0.0, 30.0, (0.1, 20.0))

    if needs_simulated_pdf:
        payload = {
            "file_name": file_name,
            "file_bytes_b64": base64.b64encode(file_bytes).decode("utf-8"),
            "q_range": [qmin, qmax],
            "r_range": [rmin, rmax],
            "qdamp": 0.06,
            "qbroad": 0.06,
        }
        result = run_workflow(
            workflow_registry,
            "structure_pdf",
            payload,
            "structure_pdf_simulation",
            start=True,
            poll_timeout=10.0,
        )
        state = get_workflow_state(workflow_registry, "structure_pdf_simulation")
        if result is None:
            if state.get("error"):
                st.error(f"PDF simulation failed: {state['error']}")
            else:
                st.info("PDF simulation is still running in the backend.")
            st.stop()
        df_pdf = pd.DataFrame(result["profile"]).rename(columns={"r (A)": "r (Å)"})
        r1 = df_pdf["r (Å)"].to_numpy()
        g1 = df_pdf["G_sim(r)"].to_numpy()

    if PDF_workflow == "Simulate PDF":
        with st.expander("View simulated PDF data"):
            st.dataframe(df_pdf, use_container_width=True, hide_index=True)

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=df_pdf["r (Å)"], y=df_pdf["G_sim(r)"], mode="lines", name="Simulated G(r)")
        )

        fig.update_layout(
            xaxis_title="r (Å)",
            yaxis_title="G(r)",
            xaxis=dict(
                range=[rmin, rmax],
                tickfont=dict(size=20, color="black"),
                title_font=dict(size=20, color="black"),
            ),
            yaxis=dict(
                tickfont=dict(size=20, color="black"), title_font=dict(size=20, color="black")
            ),
            font=dict(color="black"),
            margin=dict(t=40, b=40, l=40, r=40),
            legend=dict(yanchor="top", y=0.99, xanchor="center", x=0.8),
        )

        st.plotly_chart(fig, use_container_width=True)

    if PDF_workflow == "Plot RDF":
        st.subheader("Radial Distribution Function")

        rdf_atoms = st.text_input("Enter atom labels (comma-sep)", "Pb, I")
        atom_list = [a.strip() for a in rdf_atoms.split(",") if a.strip()]
        all_pairs = list(combinations_with_replacement(atom_list, 2))
        bins = st.slider("Number of bins", 50, 500, 200)
        rdf_w_weights = st.radio("Scale by atomic weights?", ["True", "False"])

        if rdf_w_weights == "True":
            weight = True
        else:
            weight = False

        lib = st.radio("Choose plotting library", ["Matplotlib", "Plotly"])

        if lib == "Matplotlib":
            config = load_or_create_plot_config_matplotlib(all_pairs)
        else:
            config = load_or_create_plot_config(all_pairs)

        if st.button("Compute RDF"):
            rdf_result = run_workflow(
                workflow_registry,
                "structure_rdf",
                {
                    "file_name": file_name,
                    "file_bytes_b64": base64.b64encode(file_bytes).decode("utf-8"),
                    "atom_list": atom_list,
                    "r_max": rmax,
                    "bins": bins,
                    "weighted": weight,
                },
                "structure_rdf_simulation",
                start=True,
                poll_timeout=10.0,
            )
            rdf_state = get_workflow_state(workflow_registry, "structure_rdf_simulation")
            if rdf_result is None:
                if rdf_state.get("error"):
                    st.error(f"RDF simulation failed: {rdf_state['error']}")
                else:
                    st.info("RDF simulation is still running in the backend.")
                st.stop()
            rdf_lookup = {
                tuple(item["pair"]): (
                    np.asarray(item["r"], dtype=float),
                    np.asarray(item["g"], dtype=float),
                )
                for item in rdf_result["pairs"]
            }

            def backend_rdf(_structure, pair, **_kwargs):
                return rdf_lookup.get(tuple(pair), (None, None))

            if lib == "Matplotlib":
                fig, df_all = plot_rdf_pdf_matplotlib(
                    atom_list, modified_atoms, df_pdf, rmin, rmax, bins, backend_rdf, config, weight
                )
                st.pyplot(fig)

                buf_png = io.BytesIO()
                fig.savefig(buf_png, format="png", bbox_inches="tight")
                st.download_button(
                    "Download as PNG",
                    buf_png.getvalue(),
                    file_name="rdf_plot.png",
                    mime="image/png",
                )

                buf_pdf = io.BytesIO()
                fig.savefig(buf_pdf, format="pdf", bbox_inches="tight")
                st.download_button(
                    "Download as PDF",
                    buf_pdf.getvalue(),
                    file_name="rdf_plot.pdf",
                    mime="application/pdf",
                )

            else:
                fig_rdf, df_all = plot_rdf_pdf(
                    atom_list, modified_atoms, df_pdf, rmax, bins, backend_rdf, config, weight
                )
                st.plotly_chart(fig_rdf, use_container_width=True)

            with st.expander("View simulated RDF data"):
                st.dataframe(df_all, use_container_width=True, hide_index=True)

    if PDF_workflow in {"Simulate PDF", "Plot RDF"}:
        st.stop()

    if PDF_workflow == "Convert reduced PDF to g(r)":
        st.subheader("Convert Reduced PDF to g(r)")

        exp_file2 = st.file_uploader(
            "Upload experimental .gr file",
            type=["gr"],
            key="gr_uploader2",
        )

        if exp_file2 is not None:
            try:
                df_exp2 = parse_reduced_pdf(exp_file2.read(), (rmin, rmax))

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
                                st.warning(
                                    "Not enough points in the selected r-window for integration."
                                )
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

        st.stop()

    st.subheader("Compare Experimental vs. Simulated PDF")

    # -------------------------------------------------------------------------
    # 5) Optionally load experimental .gr
    # -------------------------------------------------------------------------=
    # Choose normalization method
    norm_method = st.selectbox(
        "Normalize y-axis before fitting using:",
        ["Z-score (mean 0, std 1)", "Min-max [0,1]"],
        index=0,
        key="pdf_norm_method",
    )

    exp_file = st.file_uploader(
        "Optionally upload experimental .gr file", type=["gr"], key="gr_uploader"
    )
    if exp_file is not None:
        try:
            df_exp = parse_reduced_pdf(exp_file.read(), (rmin, rmax))
        except ValueError as exc:
            st.error(str(exc))
        else:
            comparison = run_workflow(
                workflow_registry,
                "structure_pdf_compare",
                {
                    "simulated_r": r1.tolist(),
                    "simulated_g": g1.tolist(),
                    "experimental_r": df_exp.r.tolist(),
                    "experimental_g": df_exp.G_exp.tolist(),
                    "normalization": ("zscore" if norm_method.startswith("Z-score") else "minmax"),
                },
                "structure_pdf_comparison",
                start=True,
                poll_timeout=10.0,
            )
            comparison_state = get_workflow_state(workflow_registry, "structure_pdf_comparison")
            if comparison is None:
                if comparison_state.get("error"):
                    st.error(f"PDF comparison failed: {comparison_state['error']}")
                else:
                    st.info("PDF comparison is still running in the backend.")
                st.stop()

            df_combined = pd.DataFrame(comparison["table"]).rename(columns={"r (A)": "r (Å)"})
            A_eff = comparison["effective_slope"]
            B_eff = comparison["effective_intercept"]
            pcc_value_orig = comparison["pcc_original"]
            pcc_value_norm = comparison["pcc_normalized"]

            with st.expander("View combined PDF data"):
                st.dataframe(df_combined, use_container_width=True, hide_index=True)

            with st.expander("Fit details (normalized → original)"):
                st.markdown(
                    f"- Effective original-units mapping: y ≈ **{A_eff:.4f}** · x + **{B_eff:.4f}**\n"
                    f"- PCC (original): **{pcc_value_orig:.4f}**, PCC (normalized): **{pcc_value_norm:.4f}**"
                )
        # --- 6) Plotting: customization, trigger button, downloads, and interactive Plotly ---
        # Load saved customization if provide
        with st.expander("Plot customization"):
            config_file = st.file_uploader(
                "Upload plot customization config (.json)", type=["json"], key="config_uploader"
            )
            if config_file:
                config = json.load(config_file)
            else:
                config = {}

            sim_color = st.color_picker("Simulated line color", config.get("sim_color", "#1f77b4"))
            sim_width = st.slider(
                "Simulated line width", 0.5, 5.0, config.get("sim_width", 2.0), step=0.1
            )
            sim_ls = st.selectbox(
                "Simulated line style",
                ["-", "--", "-.", ":"],
                index=["-", "--", "-.", ":"].index(config.get("sim_ls", "-")),
            )
            sim_opacity = st.slider(
                "Simulated line opacity", 0.0, 1.0, config.get("sim_opacity", 1.0), step=0.05
            )
            exp_color = st.color_picker(
                "Experimental line color", config.get("exp_color", "#ff7f0e")
            )
            exp_width = st.slider(
                "Experimental line width", 0.5, 5.0, config.get("exp_width", 2.0), step=0.1
            )
            exp_ls = st.selectbox(
                "Experimental line style",
                ["-", "--", "-.", ":"],
                index=["-", "--", "-.", ":"].index(config.get("exp_ls", "--")),
            )
            exp_opacity = st.slider(
                "Experimental line opacity", 0.0, 1.0, config.get("exp_opacity", 1.0), step=0.05
            )
            bar_color = st.color_picker("Residual bar color", config.get("bar_color", "#7f7f7f"))
            spline_width = st.slider(
                "Fitted line width", 0.5, 5.0, config.get("spline_width", 1.5), step=0.1
            )
            text_size = st.slider("Text size", 8, 20, config.get("text_size", 12))
            text_style = st.selectbox(
                "Text style",
                ["normal", "bold", "italic"],
                index=["normal", "bold", "italic"].index(config.get("text_style", "normal")),
            )
            axis_lw = st.slider(
                "Axis spine linewidth", 0.5, 5.0, config.get("axis_linewidth", 1.0), step=0.1
            )
            tick_lw = st.slider(
                "Tick mark linewidth", 0.5, 5.0, config.get("tick_linewidth", 1.0), step=0.1
            )
            hide_legends = st.checkbox("Hide legends", config.get("hide_legends", False))
            show_sim = st.checkbox("Show simulated data", config.get("show_sim", True))
            show_exp = st.checkbox("Show experimental data", config.get("show_exp", True))
            show_res = st.checkbox("Show residual data", config.get("show_res", True))
            aspect_opt = st.selectbox(
                "Aspect ratio",
                ["auto", "equal", "custom"],
                index=["auto", "equal", "custom"].index(config.get("aspect_option", "equal")),
            )
            aspect_val = config.get("aspect_val", 1.0)
            if aspect_opt == "custom":
                aspect_val = st.number_input(
                    "Custom aspect ratio (y/x)", 0.1, 10.0, aspect_val, step=0.1
                )
            # axis limits & ticks
            x_min = st.number_input("X-axis min", value=config.get("x_min", rmin), step=0.1)
            x_max = st.number_input("X-axis max", value=config.get("x_max", rmax), step=0.1)
            y_min = st.number_input(
                "Y-axis min",
                value=config.get("y_min", float(df_combined.G_sim.min() - 1.5)),
                step=0.1,
            )
            y_max = st.number_input(
                "Y-axis max", value=config.get("y_max", float(df_combined.G_sim.max())), step=0.1
            )
            tick_gap_x = st.number_input(
                "X-axis tick interval",
                value=config.get("tick_gap_x", (x_max - x_min) / 5),
                step=0.1,
            )
            tick_gap_y = st.number_input(
                "Y-axis tick interval",
                value=config.get("tick_gap_y", (y_max - y_min) / 5),
                step=0.1,
            )
            plot_title = st.text_input("Plot title", value=config.get("plot_title", "PDF"))
            show_fit = st.checkbox("Plot fitted data", config.get("show_fit", False))

            # Download current customization as JSON
            config_out = {
                "sim_color": sim_color,
                "sim_width": sim_width,
                "sim_ls": sim_ls,
                "sim_opacity": sim_opacity,
                "exp_color": exp_color,
                "exp_width": exp_width,
                "exp_ls": exp_ls,
                "exp_opacity": exp_opacity,
                "bar_color": bar_color,
                "spline_width": spline_width,
                "text_size": text_size,
                "text_style": text_style,
                "axis_linewidth": axis_lw,
                "tick_linewidth": tick_lw,
                "hide_legends": hide_legends,
                "show_sim": show_sim,
                "show_exp": show_exp,
                "show_res": show_res,
                "aspect_option": aspect_opt,
                "aspect_val": aspect_val,
                "x_min": x_min,
                "x_max": x_max,
                "y_min": y_min,
                "y_max": y_max,
                "tick_gap_x": tick_gap_x,
                "tick_gap_y": tick_gap_y,
                "plot_title": plot_title,
                "show_fit": show_fit,
            }
            st.download_button(
                "Download customization as JSON",
                data=json.dumps(config_out, indent=2),
                file_name="plot_config.json",
                mime="application/json",
            )

        plot_btn = st.button("Generate Plot")
        if plot_btn:
            import matplotlib.style

            matplotlib.style.use("classic")
            import matplotlib.ticker as ticker

            fig, ax = plt.subplots()
            # apply spine & tick widths
            for s in ax.spines.values():
                s.set_linewidth(axis_lw)
            ax.tick_params(width=tick_lw)

            # plot based on toggles
            if show_sim:
                ax.plot(
                    r1,
                    g1,
                    color=sim_color,
                    linewidth=sim_width,
                    linestyle=sim_ls,
                    alpha=sim_opacity,
                    label="Simulated",
                )
            if exp_file and show_exp:
                ax.plot(
                    df_combined["r (Å)"],
                    df_combined["G_exp (norm)"],
                    color=exp_color,
                    linewidth=exp_width,
                    linestyle=exp_ls,
                    alpha=exp_opacity,
                    label="Experimental",
                )
            if exp_file and show_res:
                baseline = min(np.min(g1), df_combined["G_exp"].min()) - 0.5
                bar_w = (x_max - x_min) / (len(df_combined) * 1.5)
                ax.bar(
                    df_combined["r (Å)"],
                    df_combined["Residual"],
                    width=bar_w,
                    bottom=baseline,
                    color=bar_color,
                    alpha=0.6,
                    label="Residual",
                )
            if exp_file and show_fit:
                ax.plot(
                    df_combined["r (Å)"],
                    df_combined["G_fit"],
                    color="gray",
                    linewidth=spline_width,
                    linestyle=":",
                    alpha=0.8,
                    label="Fitted",
                )

            # axes limits, ticks, aspect
            ax.set_xlim(x_min, x_max)
            ax.set_ylim(y_min, y_max)
            ax.xaxis.set_major_locator(ticker.MultipleLocator(tick_gap_x))
            ax.yaxis.set_major_locator(ticker.MultipleLocator(tick_gap_y))
            ax.set_aspect(aspect_val)

            # labels & title
            title_kw = {"fontsize": text_size + 2}
            if text_style == "bold":
                title_kw["fontweight"] = "bold"
            if text_style == "italic":
                title_kw["fontstyle"] = "italic"
            ax.set_title(plot_title, **title_kw)
            label_kw = {"fontsize": text_size}
            if text_style == "bold":
                label_kw["fontweight"] = "bold"
            if text_style == "italic":
                label_kw["fontstyle"] = "italic"
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
            fig_int.add_trace(
                go.Scatter(
                    x=df_combined["r (Å)"],
                    y=df_combined["G_sim"],
                    mode="lines",
                    name="Simulated G(r)",
                    line=dict(color=sim_color, width=sim_width, dash="solid"),
                    opacity=sim_opacity,
                )
            )
            fig_int.add_trace(
                go.Scatter(
                    x=df_combined["r (Å)"],
                    y=df_combined["G_exp"],
                    mode="lines",
                    name="Experimental G(r)",
                    line=dict(color=exp_color, width=exp_width, dash="solid"),
                    opacity=exp_opacity,
                )
            )
            fig_int.add_trace(
                go.Bar(
                    x=df_combined["r (Å)"],
                    y=df_combined["Residual"],
                    base=(min(df_combined["G_sim"].min(), df_combined["G_exp"].min()) - 0.5),
                    name="Residual",
                    marker_color=bar_color,
                    opacity=0.6,
                )
            )
            if show_fit:
                fig_int.add_trace(
                    go.Scatter(
                        x=df_combined["r (Å)"],
                        y=df_combined["G_fit"],
                        mode="lines",
                        name="Fitted G(r)",
                        line=dict(color="gray", width=spline_width, dash="dot"),
                        opacity=0.8,
                    )
                )
            fig_int.update_layout(
                xaxis_title="r (Å)",
                yaxis_title="G(r)",
                xaxis=dict(
                    range=[x_min, x_max],
                    tickfont=dict(size=text_size + 12, color="black"),
                    title_font=dict(size=text_size + 12, color="black"),
                ),
                yaxis=dict(
                    range=[y_min, y_max],
                    tickfont=dict(size=text_size + 12, color="black"),
                    title_font=dict(size=text_size + 12, color="black"),
                ),
                font=dict(color="black"),
                margin=dict(t=40, b=40, l=40, r=40),
                legend=dict(yanchor="top", y=0.99, xanchor="center", x=0.8),
            )
            st.plotly_chart(fig_int, use_container_width=True)

    st.stop()
