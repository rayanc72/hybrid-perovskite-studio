"""Backend-backed powder X-ray diffraction workflow."""

from __future__ import annotations

import base64
import io
import os
from collections.abc import Callable, MutableMapping
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from hps.ui.backend_workflows import get_workflow_state, run_workflow


def x_values_to_d_spacing(x_values, x_axis: str, wavelength: float):
    values = np.asarray(x_values, dtype=float)
    if x_axis in {"q", "q (A^-1)"}:
        with np.errstate(divide="ignore", invalid="ignore"):
            return 2.0 * np.pi / values
    theta = np.radians(values / 2.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        return wavelength / (2.0 * np.sin(theta))


def secondary_d_axis_ticks(x_values, x_axis: str, wavelength: float, count: int = 6):
    tick_values = np.linspace(float(np.min(x_values)), float(np.max(x_values)), count)
    d_values = x_values_to_d_spacing(tick_values, x_axis, wavelength)
    finite = np.isfinite(d_values) & (d_values > 0)
    return tick_values[finite], [f"{value:.3g}" for value in d_values[finite]]


def requested_two_theta_range(
    x_axis: str,
    range_min: float,
    range_max: float,
    wavelength: float,
) -> tuple[float, float]:
    if range_min >= range_max:
        raise ValueError("The minimum range value must be smaller than the maximum range value.")
    if x_axis != "q":
        return range_min, range_max

    argument = wavelength * np.array([range_min, range_max], dtype=float) / (4.0 * np.pi)
    if np.any(argument <= 0) or np.any(argument >= 1.0):
        raise ValueError(
            "For the selected wavelength, q-range values must be positive and smaller "
            "than 4pi/lambda."
        )
    return tuple(np.degrees(2.0 * np.arcsin(argument)))


def build_pxrd_payload(
    file_name: str,
    file_bytes: bytes,
    *,
    wavelength: float,
    two_theta_range: tuple[float, float],
    fwhm: float,
    x_axis: str,
) -> dict[str, object]:
    return {
        "file_name": file_name,
        "file_bytes_b64": base64.b64encode(file_bytes).decode("utf-8"),
        "wavelength": float(wavelength),
        "two_theta_range": [float(two_theta_range[0]), float(two_theta_range[1])],
        "fwhm": float(fwhm),
        "x_axis": x_axis,
        "scaled": True,
        "num_points": 4000,
    }


def parse_experimental_pxrd(
    content: bytes,
    *,
    source_axis: str,
    target_axis: str,
    wavelength: float,
    x_column: str,
    simulated_range: tuple[float, float],
) -> pd.DataFrame:
    frame = pd.read_csv(
        io.StringIO(content.decode("utf-8", errors="ignore")),
        sep=None,
        engine="python",
        comment="#",
        header=None,
    )
    if frame.shape[1] < 2:
        raise ValueError("Expected at least two columns.")
    frame = (
        frame.iloc[:, :2]
        .rename(columns={0: "x", 1: "Intensity"})
        .apply(pd.to_numeric, errors="coerce")
        .dropna()
    )
    if frame.empty:
        raise ValueError("No numeric data rows were found.")

    if source_axis == "2theta" and target_axis == "q":
        frame["x"] = 4.0 * np.pi * np.sin(np.radians(frame["x"].to_numpy() / 2.0)) / wavelength
    elif source_axis == "q" and target_axis == "2theta":
        argument = wavelength * frame["x"].to_numpy() / (4.0 * np.pi)
        if np.any(np.abs(argument) > 1.0):
            raise ValueError("Experimental q values are out of range for the selected wavelength.")
        frame["x"] = np.degrees(2.0 * np.arcsin(argument))

    frame = frame.rename(columns={"x": x_column})
    frame = frame[frame[x_column].between(*simulated_range)].reset_index(drop=True)
    if frame.empty:
        raise ValueError("No experimental data points fall within the simulated x-axis range.")
    return frame


def normalize_comparison_profiles(simulated, experimental, reflections):
    simulated = np.asarray(simulated, dtype=float).copy()
    experimental = np.asarray(experimental, dtype=float).copy()
    reflections = np.asarray(reflections, dtype=float).copy()
    simulated_max = float(np.max(simulated)) if simulated.size else 0.0
    experimental_max = float(np.max(experimental)) if experimental.size else 0.0
    if simulated_max > 0:
        simulated /= simulated_max
        reflections /= simulated_max
    if experimental_max > 0:
        experimental /= experimental_max
    return simulated, experimental, reflections


def publication_pxrd_pdf_bytes(
    x_values,
    simulated_intensity,
    x_label,
    y_label,
    wavelength,
    *,
    show_d_spacing_axis=False,
    experimental_x=None,
    experimental_intensity=None,
    reflection_x=None,
    reflection_intensity=None,
):
    figure, axis = plt.subplots(figsize=(8, 6), constrained_layout=True)
    axis.plot(
        x_values, simulated_intensity, color="black", linewidth=1.8, label="Simulated", zorder=3
    )
    if experimental_x is not None and experimental_intensity is not None:
        axis.plot(
            experimental_x,
            experimental_intensity,
            color="#c23b22",
            linewidth=1.5,
            label="Experimental",
            zorder=2,
        )
    if reflection_x is not None and reflection_intensity is not None:
        axis.vlines(
            reflection_x,
            0.0,
            reflection_intensity,
            color="#4169e1",
            linewidth=0.8,
            alpha=0.65,
            label="Bragg reflections",
            zorder=1,
        )

    axis.set_xlabel(
        r"$q\ (\mathrm{\AA}^{-1})$" if x_label == "q (A^-1)" else r"$2\theta\ (^\circ)$",
        fontsize=16,
    )
    axis.set_ylabel(y_label, fontsize=16)
    axis.tick_params(axis="both", which="major", labelsize=13, direction="in", length=8, width=1.8)
    axis.minorticks_off()
    axis.margins(x=0.01)
    for spine in axis.spines.values():
        spine.set_linewidth(1.8)

    if show_d_spacing_axis:
        secondary = axis.twiny()
        secondary.set_xlim(axis.get_xlim())
        tick_values, tick_text = secondary_d_axis_ticks(x_values, x_label, wavelength)
        secondary.set_xticks(tick_values)
        secondary.set_xticklabels(tick_text)
        secondary.set_xlabel(r"$d\ (\mathrm{\AA})$", fontsize=16)
        secondary.tick_params(
            axis="x", which="major", labelsize=13, direction="in", length=8, width=1.8
        )
        secondary.minorticks_off()
        for spine in secondary.spines.values():
            spine.set_linewidth(1.8)

    if axis.get_legend_handles_labels()[0]:
        axis.legend(frameon=False, fontsize=20, loc="best")
    buffer = io.BytesIO()
    figure.savefig(buffer, format="pdf", bbox_inches="tight")
    plt.close(figure)
    return buffer.getvalue()


def render_pxrd_analysis(
    state: MutableMapping[str, Any],
    registry: MutableMapping[str, dict[str, Any]],
    uploaded_structure_bytes: bytes,
    *,
    render_section_header: Callable[..., None],
) -> None:
    render_section_header(
        "Simulate powder X-ray diffraction",
        kicker="Structure Workspace",
        subtitle="Simulate a PXRD pattern for the loaded structure with configurable wavelength, broadening, and axis units.",
    )
    wavelength = st.number_input(
        "Wavelength (A)", min_value=0.01, value=1.5406, step=0.0001, format="%.4f"
    )
    x_axis = st.radio(
        "Plot x-axis as",
        options=("2theta", "q"),
        horizontal=True,
        format_func=lambda value: "2theta (deg)" if value == "2theta" else "q (A^-1)",
    )
    columns = st.columns(2)
    with columns[0]:
        range_min_text = st.text_input(
            "2theta min (deg)" if x_axis == "2theta" else "q min (A^-1)",
            value="0.5",
            key="pxrd_range_min_2theta" if x_axis == "2theta" else "pxrd_range_min_q",
        )
    with columns[1]:
        range_max_text = st.text_input(
            "2theta max (deg)" if x_axis == "2theta" else "q max (A^-1)",
            value="50" if x_axis == "2theta" else "5.0",
            key="pxrd_range_max_2theta" if x_axis == "2theta" else "pxrd_range_max_q",
        )
    fwhm = st.number_input(
        "FWHM broadening (deg)",
        min_value=0.0,
        value=0.1,
        step=0.01,
        format="%.2f",
        help="Applied in degrees of 2theta before optional q conversion. Set to 0 for unbroadened intensities.",
    )
    show_reflections = st.checkbox("Show Bragg reflections", value=False)
    show_d_axis = st.checkbox("Show d-spacing axis", value=False)
    experimental_file = st.file_uploader(
        "Optional experimental PXRD data",
        type=["csv", "txt", "xy", "dat", "chi"],
        help="Upload a two-column dataset, including .chi files with '#' header lines.",
        key="pxrd_experimental_uploader",
    )
    experimental_axis = None
    if experimental_file is not None:
        experimental_axis = st.radio(
            "Experimental x-axis units",
            options=("2theta", "q"),
            horizontal=True,
            format_func=lambda value: "2theta (deg)" if value == "2theta" else "q (A^-1)",
        )

    try:
        range_min = float(range_min_text)
        range_max = float(range_max_text)
        two_theta_range = requested_two_theta_range(x_axis, range_min, range_max, wavelength)
    except ValueError as exc:
        st.error(
            str(exc)
            if "range" in str(exc)
            else "Enter numeric values for the selected x-axis range."
        )
        st.stop()

    payload = build_pxrd_payload(
        state["file_name"],
        uploaded_structure_bytes,
        wavelength=wavelength,
        two_theta_range=two_theta_range,
        fwhm=fwhm,
        x_axis=x_axis,
    )
    state_key = f"structure_pxrd::{state['file_name']}"
    result = run_workflow(registry, "structure_pxrd", payload, state_key, start=True)
    workflow_state = get_workflow_state(registry, state_key)
    if result is None:
        if workflow_state.get("error"):
            st.error(f"PXRD simulation failed: {workflow_state['error']}")
        else:
            st.info("PXRD simulation is still running. Re-run shortly if the plot does not appear.")
        st.stop()

    profile = pd.DataFrame(result["profile"])
    reflections = pd.DataFrame(result["reflections"])
    x_column = result["x_label"]
    simulated_intensity = profile["Intensity"].to_numpy(copy=True)
    reflection_intensity = reflections["Intensity"].to_numpy(copy=True)
    experimental = None
    experimental_intensity = None
    if experimental_file is not None:
        try:
            experimental = parse_experimental_pxrd(
                experimental_file.getvalue(),
                source_axis=experimental_axis,
                target_axis=x_axis,
                wavelength=wavelength,
                x_column=x_column,
                simulated_range=(float(profile[x_column].min()), float(profile[x_column].max())),
            )
            experimental_intensity = experimental["Intensity"].to_numpy(copy=True)
        except Exception as exc:
            st.error(f"Could not parse experimental PXRD data: {exc}")
            st.stop()

    if experimental_intensity is not None:
        simulated_intensity, experimental_intensity, reflection_intensity = (
            normalize_comparison_profiles(
                simulated_intensity, experimental_intensity, reflection_intensity
            )
        )

    figure = _build_interactive_figure(
        profile,
        reflections,
        experimental,
        x_column,
        simulated_intensity,
        experimental_intensity,
        reflection_intensity,
        fwhm,
        show_reflections,
        show_d_axis,
        x_axis,
        wavelength,
    )
    st.plotly_chart(figure, use_container_width=True)
    y_label = (
        "Normalized intensity"
        if experimental is not None
        else ("Relative intensity" if fwhm > 0 else "Intensity")
    )
    pdf_bytes = publication_pxrd_pdf_bytes(
        profile[x_column].to_numpy(),
        simulated_intensity,
        x_column,
        y_label,
        wavelength,
        show_d_spacing_axis=show_d_axis,
        experimental_x=None if experimental is None else experimental[x_column].to_numpy(),
        experimental_intensity=experimental_intensity,
        reflection_x=reflections[x_column].to_numpy() if show_reflections else None,
        reflection_intensity=reflection_intensity if show_reflections else None,
    )
    root = os.path.splitext(state.get("file_name") or "structure")[0]
    st.download_button(
        "Download Plot",
        data=pdf_bytes,
        file_name=f"{root}_pxrd_plot.pdf",
        mime="application/pdf",
        key="pxrd_plot_pdf_download",
    )
    with st.expander("View simulated PXRD profile"):
        st.dataframe(profile, use_container_width=True, hide_index=True)
    with st.expander("View PXRD reflection table"):
        st.dataframe(reflections, use_container_width=True, hide_index=True)
    if experimental is not None:
        with st.expander("View experimental PXRD data"):
            st.dataframe(experimental, use_container_width=True, hide_index=True)
    st.stop()


def _build_interactive_figure(
    profile,
    reflections,
    experimental,
    x_column,
    simulated_intensity,
    experimental_intensity,
    reflection_intensity,
    fwhm,
    show_reflections,
    show_d_axis,
    x_axis,
    wavelength,
):
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=profile[x_column],
            y=simulated_intensity,
            mode="lines",
            name="Broadened profile" if fwhm > 0 else "Sampled profile",
            line=dict(width=2.5),
        )
    )
    if experimental is not None:
        figure.add_trace(
            go.Scatter(
                x=experimental[x_column],
                y=experimental_intensity,
                mode="lines",
                name="Experimental data",
                line=dict(width=2),
            )
        )
    if show_reflections:
        figure.add_trace(
            go.Bar(
                x=reflections[x_column],
                y=reflection_intensity,
                name="Bragg reflections",
                opacity=0.3,
            )
        )
    y_label = (
        "Normalized intensity"
        if experimental is not None
        else ("Relative intensity" if fwhm > 0 else "Intensity")
    )
    layout = dict(
        xaxis_title=x_column,
        yaxis_title=y_label,
        template="plotly_white",
        margin=dict(t=90 if show_d_axis else 40, b=40, l=40, r=40),
    )
    if show_d_axis:
        tick_values, tick_text = secondary_d_axis_ticks(
            profile[x_column].to_numpy(), x_axis, wavelength
        )
        if tick_values.size:
            figure.add_trace(
                go.Scatter(
                    x=tick_values,
                    y=[None] * len(tick_values),
                    mode="markers",
                    marker=dict(opacity=0),
                    showlegend=False,
                    hoverinfo="skip",
                    xaxis="x2",
                    yaxis="y",
                )
            )
        layout["xaxis2"] = dict(
            title="d (A)",
            anchor="y",
            overlaying="x",
            matches="x",
            side="top",
            tickmode="array",
            tickvals=tick_values.tolist(),
            ticktext=tick_text,
            showgrid=False,
            showline=True,
            showticklabels=True,
            ticks="outside",
        )
    figure.update_layout(**layout)
    return figure
