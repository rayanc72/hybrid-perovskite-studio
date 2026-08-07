import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import streamlit as st
from io import StringIO
import math
import pandas as pd
import holoviews as hv
import re
import colorcet as cc
from plotly.subplots import make_subplots
from scipy.interpolate import griddata
from scipy.spatial import Voronoi

hv.extension('bokeh')


PDOS_TOTAL_FILENAME = "ks_dos_total.dat"
PDOS_PROJECTED_RE = re.compile(r"(.+)_l_proj_dos\.dat$", re.IGNORECASE)
PDOS_PROJECTED_SP_ELEMENTS = {"Pb", "Sn"}
PDOS_ORBITAL_COLUMN_LABELS = {
    2: "s",
    3: "p",
    4: "d",
    5: "f",
}
PDOS_DEFAULT_COLORS = [
    "#8a2be2",
    "#5f9ea0",
    "#dc143c",
    "#228b22",
    "#ff7f50",
    "#4169e1",
    "#b8860b",
    "#c71585",
]


def detect_pdos_file_roles(uploaded_files):
    roles = {
        "total": [],
        "projected": [],
        "unrecognized": [],
    }

    for file in uploaded_files or []:
        name = getattr(file, "name", "")
        lower_name = name.lower()
        projected_match = PDOS_PROJECTED_RE.fullmatch(name)

        if lower_name == PDOS_TOTAL_FILENAME:
            roles["total"].append(name)
        elif projected_match:
            roles["projected"].append({"name": name, "element": projected_match.group(1)})
        else:
            roles["unrecognized"].append(name)

    return roles


def _read_pdos_array(file):
    try:
        file.seek(0)
    except (AttributeError, OSError):
        pass

    data = np.loadtxt(file)

    try:
        file.seek(0)
    except (AttributeError, OSError):
        pass

    data = np.asarray(data)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    return data


def _validate_pdos_array(name, data, min_columns):
    if data.ndim != 2 or data.shape[1] < min_columns:
        raise ValueError(
            f"`{name}` must contain at least {min_columns} numeric columns for PDOS plotting."
        )
    if data.shape[0] == 0:
        raise ValueError(f"`{name}` does not contain any PDOS rows.")


def _pdos_required_columns(element):
    if element in PDOS_PROJECTED_SP_ELEMENTS:
        return 4
    return 2


def _pdos_trace_columns(element):
    if element == "Total":
        return [("Total DOS", 1)]
    if element in PDOS_PROJECTED_SP_ELEMENTS:
        return [(f"{element}(s)", 2), (f"{element}(p)", 3)]
    return [(element, 1)]


def smooth_pdos_values(values, window_size):
    values = np.asarray(values, dtype=float)
    if window_size is None or window_size <= 1 or len(values) == 0:
        return values
    try:
        window_size = int(window_size)
        if window_size % 2 == 0:
            window_size += 1
        if window_size > len(values):
            window_size = len(values) if len(values) % 2 == 1 else len(values) - 1
        if window_size <= 1:
            return values

        padding = window_size // 2
        padded_values = np.pad(values, padding, mode="edge")
        kernel = np.ones(window_size) / window_size
        return np.convolve(padded_values, kernel, mode="valid")
    except Exception:
        return values


def get_pdos_trace_options(dos_data):
    trace_options = []
    for element in dos_data:
        trace_options.extend(trace_name for trace_name, _ in _pdos_trace_columns(element))
    return trace_options


def _pdos_table_columns(element, data):
    columns = [(element, 1)]
    for column_index, orbital_label in PDOS_ORBITAL_COLUMN_LABELS.items():
        if data.shape[1] > column_index:
            columns.append((f"{element}({orbital_label})", column_index))
    return columns


def parse_pdos_uploads(uploaded_files):
    uploaded_files = list(uploaded_files or [])
    roles = detect_pdos_file_roles(uploaded_files)

    if not uploaded_files:
        raise ValueError("Upload `KS_DOS_total.dat` and one or more `*_l_proj_dos.dat` files.")
    if roles["unrecognized"] and not roles["total"] and not roles["projected"]:
        raise ValueError(
            "No FHI-aims PDOS files were recognized. Expected `KS_DOS_total.dat` and `*_l_proj_dos.dat`."
        )
    if not roles["total"]:
        raise ValueError("Total DOS file `KS_DOS_total.dat` was not found.")
    if len(roles["total"]) > 1:
        raise ValueError("Only one `KS_DOS_total.dat` file can be plotted at a time.")

    dos_data = {}
    seen_elements = set()

    for file in uploaded_files:
        name = getattr(file, "name", "")
        lower_name = name.lower()
        projected_match = PDOS_PROJECTED_RE.fullmatch(name)

        if lower_name == PDOS_TOTAL_FILENAME:
            data = _read_pdos_array(file)
            _validate_pdos_array(name, data, 2)
            dos_data["Total"] = data
        elif projected_match:
            element = projected_match.group(1)
            if element in seen_elements:
                raise ValueError(f"Duplicate PDOS file for `{element}`.")
            data = _read_pdos_array(file)
            _validate_pdos_array(name, data, _pdos_required_columns(element))
            dos_data[element] = data
            seen_elements.add(element)

    table = build_pdos_table(dos_data)
    return dos_data, table, roles


def build_pdos_table(dos_data):
    if "Total" not in dos_data:
        raise ValueError("Total DOS data is required before building the PDOS table.")

    total = dos_data["Total"]
    _validate_pdos_array("Total DOS", total, 2)
    energy_values = total[:, 0]
    table_data = {
        "Energy": energy_values,
        "Total DOS": total[:, 1],
    }

    for element, data in dos_data.items():
        if element == "Total":
            continue
        _validate_pdos_array(element, data, _pdos_required_columns(element))
        if len(data[:, 0]) != len(energy_values) or not np.allclose(data[:, 0], energy_values):
            raise ValueError(f"`{element}` PDOS energy values do not match `KS_DOS_total.dat`.")
        for column_name, column_index in _pdos_table_columns(element, data):
            table_data[column_name] = data[:, column_index]

    return pd.DataFrame(table_data)


def _resolve_pdos_column_name(pdos_table, term):
    term = term.strip()
    if len(term) >= 2 and term[0] == "`" and term[-1] == "`":
        term = term[1:-1].strip()

    if term in pdos_table.columns:
        return term

    lower_term = term.lower()
    matches = [column for column in pdos_table.columns if column.lower() == lower_term]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"`{term}` matches multiple PDOS columns.")

    raise ValueError(f"`{term}` is not an available PDOS contribution.")


def _evaluate_pdos_combination(pdos_table, expression):
    tokens = re.split(r"(\+|-)", expression)
    result = None
    sign = 1
    used_column = False

    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if token == "+":
            sign = 1
            continue
        if token == "-":
            sign = -1
            continue

        column_name = _resolve_pdos_column_name(pdos_table, token)
        contribution = pdos_table[column_name].to_numpy()
        result = sign * contribution if result is None else result + sign * contribution
        used_column = True
        sign = 1

    if not used_column:
        raise ValueError(f"`{expression}` does not contain a PDOS contribution.")
    return result


def get_pdos_combination_labels(combination_text):
    if not combination_text or not combination_text.strip():
        return []

    labels = []
    lines = [line.strip() for line in combination_text.splitlines() if line.strip()]
    for index, line in enumerate(lines, start=1):
        if "=" in line:
            label, _ = line.split("=", 1)
            label = label.strip()
        else:
            label = f"Combination {index}"
        if label:
            labels.append(label)
    return labels


def add_pdos_combinations(pdos_table, combination_text):
    if not combination_text or not combination_text.strip():
        return pdos_table.copy(), []

    combined_table = pdos_table.copy()
    created_columns = []
    lines = [line.strip() for line in combination_text.splitlines() if line.strip()]

    for index, line in enumerate(lines, start=1):
        if "=" in line:
            label, expression = line.split("=", 1)
            label = label.strip()
            expression = expression.strip()
        else:
            label = f"Combination {index}"
            expression = line

        if not label:
            raise ValueError(f"Combination line {index} needs a label before `=`.")
        if label in {"Energy"}:
            raise ValueError("`Energy` cannot be used as a combination label.")
        if not expression:
            raise ValueError(f"Combination `{label}` needs an expression after `=`.")

        combined_table[label] = _evaluate_pdos_combination(combined_table, expression)
        created_columns.append(label)

    return combined_table, created_columns


def plot_pdos_streamlit(
    dos_data,
    shift,
    plot_range,
    dos_range=None,
    figure_height=900,
    figure_width=None,
    selected_trace_names=None,
    trace_colors=None,
    smoothing_window=None,
):
    fig = go.Figure()

    colors = ['blueviolet', 'brown', 'cadetblue', 'chartreuse',
              'chocolate', 'coral', 'cornflowerblue', 'crimson', 'cyan', 'darkblue', 'darkcyan', 'darkgoldenrod',
              'darkgray', 'darkgrey', 'darkgreen', 'darkkhaki', 'darkmagenta', 'darkolivegreen', 'darkorange',
              'darkorchid', 'darkred', 'darksalmon', 'darkseagreen', 'darkslateblue', 'darkslategray', 'darkslategrey',
              'darkturquoise', 'darkviolet', 'deeppink', 'deepskyblue', 'dimgray', 'dimgrey', 'dodgerblue', 'firebrick',
              'forestgreen', 'fuchsia', 'ghostwhite', 'gold', 'goldenrod', 'gray', 'grey', 'green', 'greenyellow',
              'honeydew', 'hotpink', 'indianred', 'indigo', 'khaki', 'lavender', 'lavenderblush', 'lawngreen',
              'lemonchiffon', 'lightcoral', 'lightgray', 'lightgrey', 'lightgreen', 'lightpink', 'lightsalmon',
              'lightseagreen', 'lightskyblue', 'lightslategray', 'lightslategrey', 'lightsteelblue', 'lime',
              'limegreen', 'magenta', 'maroon', 'mediumaquamarine', 'mediumblue', 'mediumorchid', 'mediumpurple',
              'mediumseagreen', 'mediumslateblue', 'mediumspringgreen', 'mediumturquoise', 'mediumvioletred',
              'midnightblue', 'mintcream', 'mistyrose', 'moccasin', 'navajowhite', 'navy', 'oldlace', 'olive',
              'olivedrab', 'orange', 'orangered', 'orchid', 'palegoldenrod', 'palegreen', 'paleturquoise',
              'palevioletred', 'papayawhip', 'peachpuff', 'peru', 'pink', 'plum', 'powderblue', 'purple', 'red',
              'rosybrown', 'royalblue', 'rebeccapurple', 'saddlebrown', 'salmon', 'sandybrown', 'seagreen',
              'seashell', 'sienna', 'silver', 'skyblue', 'slateblue', 'slategray', 'slategrey', 'snow', 'springgreen',
              'steelblue', 'tan', 'teal', 'thistle', 'tomato', 'turquoise', 'violet', 'wheat', 'yellow', 'yellowgreen']
    color_iter = iter(colors)
    selected_trace_names = None if selected_trace_names is None else set(selected_trace_names)
    trace_colors = trace_colors or {}

    for element, dos in dos_data.items():
        _validate_pdos_array(element, dos, _pdos_required_columns(element))
        for trace_name, column_index in _pdos_trace_columns(element):
            if selected_trace_names is not None and trace_name not in selected_trace_names:
                continue
            if trace_name in trace_colors:
                color = trace_colors[trace_name]
            else:
                color = "black" if element == "Total" else next(color_iter)
            width = 3.5 if element == "Total" else 2.5
            fig.add_trace(
                go.Scatter(
                    x=smooth_pdos_values(dos[:, column_index], smoothing_window),
                    y=dos[:, 0] + shift,
                    mode='lines',
                    name=trace_name,
                    line=dict(color=color, width=width),
                )
            )

    fig.update_layout(
        yaxis_title="Energy (eV)",
        yaxis_tickfont=dict(size=14, color='black'),
        yaxis_title_font=dict(size=18, color='black'),

        xaxis_title="Density of States",
        xaxis_tickfont=dict(size=14, color='black'),
        xaxis_title_font=dict(size=18, color='black'),

        legend=dict(font=dict(size=13), bgcolor="rgba(255, 255, 255, 0.9)"),
        margin=dict(l=60, r=30, t=30, b=60),
        plot_bgcolor="rgba(255, 255, 255, 0.95)",
        paper_bgcolor="white",
        hovermode="closest",
        height=figure_height,
    )
    if figure_width is not None:
        fig.update_layout(width=figure_width)

    fig.update_yaxes(range=plot_range)
    if dos_range is not None:
        fig.update_xaxes(range=dos_range)
    fig.update_xaxes(showline=True, linewidth=1, linecolor='black', mirror=True, side='top', ticklen=10,
                     ticks="outside")

    return fig


def add_pdos_combination_traces(
    fig,
    pdos_table,
    combination_columns,
    shift,
    trace_colors=None,
    smoothing_window=None,
):
    trace_colors = trace_colors or {}
    energy_values = pdos_table["Energy"].to_numpy()

    for index, column in enumerate(combination_columns):
        if column not in pdos_table.columns:
            raise ValueError(f"`{column}` is not available for plotting.")
        color = trace_colors.get(column, PDOS_DEFAULT_COLORS[index % len(PDOS_DEFAULT_COLORS)])
        fig.add_trace(
            go.Scatter(
                x=smooth_pdos_values(pdos_table[column], smoothing_window),
                y=energy_values + shift,
                mode='lines',
                name=column,
                line=dict(color=color, width=3),
            )
        )

    return fig



class Input(object):

    def __init__(self, latvec=None, species_id=None, k_path=None, band_sampling=None):
        self.latvec = [] if latvec is None else latvec
        self.species_id = {} if species_id is None else species_id
        self.k_path = [] if k_path is None else k_path
        self.band_sampling = [] if band_sampling is None else band_sampling

    def process_geometry_file(self, file):
        count = 1
        data = file.readlines()
        for i in range(len(data)):
            item = data[i].split()
            if (len(item) == 0) or (item[0].startswith("#")):
                continue
            elif (item[0] == "lattice_vector"):
                self.latvec.append([float(i) for i in item[1:4]])
            elif (item[0] == "atom") or (item[0] == "atom_frac"):
                try:
                    self.species_id[item[-1]].append(count)
                except KeyError:
                    self.species_id[item[-1]] = []
                    self.species_id[item[-1]].append(count)
                finally:
                    count += 1
        file.seek(0)  # Reset file pointer to the beginning

    def process_control_file(self, file):
        data = file.readlines()
        for i in range(len(data)):
            item = data[i].split()
            if (len(item) == 0) or (item[0].startswith("#")):
                continue
            elif (item[0] == "output"):
                if (item[1].startswith("band")):
                    self.k_path.append([float(j) for j in item[2:8]])
                    self.band_sampling.append(int(item[8]))
        file.seek(0)  # Reset file pointer to the beginning

    def get_volume(self):
        volume = np.dot(self.latvec[0],
                        np.cross(self.latvec[1], self.latvec[2]))
        return volume

    def get_rlatvec(self):
        volume = self.get_volume()
        rlatvec = []
        rlatvec.append((2 * np.pi * np.cross(self.latvec[1], self.latvec[2]) /
                        volume).tolist())
        rlatvec.append((2 * np.pi * np.cross(self.latvec[2], self.latvec[0]) /
                        volume).tolist())
        rlatvec.append((2 * np.pi * np.cross(self.latvec[0], self.latvec[1]) /
                        volume).tolist())
        st.write("rlatvec")
        st.write(rlatvec)
        return rlatvec

    def band_x_val(self):
        r_latvec = self.get_rlatvec()
        band_len = []
        for i in range(len(self.k_path)):
            k_vec = []
            for j in range(3):
                k_vec.append(self.k_path[i][j + 3] - self.k_path[i][j])
            temp = np.sqrt(sum([k * k for k in list(np.dot(k_vec, r_latvec))]))
            step = temp / (self.band_sampling[i] - 1)
            xval = []
            xvals = []
            for k in range(self.band_sampling[i]):
                xval.append(self.k_path[i] * step)
            xvals.append(xval)
            band_len.append(temp)
        band_len_tot = []
        for i in range(len(band_len)):
            if (i == 0):
                band_len_tot.append(0)
            else:
                band_len_tot.append(sum(band_len[:i]))
        st.write(band_len_tot)
        return band_len_tot

    def print_atoms(self):
        st.write(self.species_id)
        st.write(self.latvec)
        st.write(self.band_sampling)
        st.write(self.k_path)


def process_input_files(geometry_file, control_file):
    input_data = Input()

    geometry_file = StringIO(
        geometry_file.getvalue().decode())  # Convert the file-like object to StringIO with decoded content
    input_data.process_geometry_file(geometry_file)

    control_file = StringIO(
        control_file.getvalue().decode())  # Convert the file-like object to StringIO with decoded content
    input_data.process_control_file(control_file)

    return input_data


def process_geometry_file(uploaded_file):
    latvec = []
    rlatvec = []
    lattice_vectors = []
    reciprocal_lattice_vectors = []

    for line in uploaded_file:
        line = line.decode('utf-8')  # Decoding may be necessary for binary files
        words = line.strip().split()
        if len(words) == 0:
            continue
        if words[0] == "lattice_vector":
            latvec.append([float(i) for i in words[1:4]])

    # Calculating reciprocal lattice vectors
    volume = np.dot(latvec[0], np.cross(latvec[1], latvec[2]))
    pi = np.pi  # Define pi
    rlatvec.append(2 * pi * np.cross(latvec[1], latvec[2]) / volume)
    rlatvec.append(2 * pi * np.cross(latvec[2], latvec[0]) / volume)
    rlatvec.append(2 * pi * np.cross(latvec[0], latvec[1]) / volume)

    for j in range(3):
        lattice_vectors.append(latvec[j])
        reciprocal_lattice_vectors.append(rlatvec[j])

    uploaded_file.seek(0)
    return lattice_vectors, reciprocal_lattice_vectors


def process_control_file(uploaded_file, rlatvec):
    k_label = []
    kpoint = []
    n_samples = []

    for line in uploaded_file:
        line = line.decode('utf-8')  # Decoding for binary files
        if line.strip().startswith('output band') or line.strip().startswith('output                             band'):
            words = line.strip().split()
            kpoint.append([float(i) for i in words[2:8]])
            n_sample = int(words[-3])
            n_samples.append(n_sample)
            k_label.append(words[-2:])

    # Processing k labels
    k_label_reduce = []
    for k_pair in k_label:
        for i in range(len(k_pair)):
            k = k_pair[i]
            if len(k_label_reduce) == 0:
                k_label_reduce.append(k)
            elif i == 0 and k != k_label_reduce[-1]:
                k_label_reduce[-1] = k_label_reduce[-1] + "|" + k
            elif i == 0 and k == k_label_reduce[-1]:
                continue
            else:
                k_label_reduce.append(k)

    # Calculating x values
    xvals = []
    band_len = []
    for i, n_sample in zip(kpoint, n_samples):
        kvec = [i[j + 3] - i[j] for j in range(3)]
        temp = math.sqrt(sum([k * k for k in list(np.dot(kvec, rlatvec))]))
        if n_sample <= 1:
            xval = [0.0]
        else:
            step = temp / (n_sample - 1)
            xval = [i * step for i in range(n_sample)]
        xvals.append(xval)
        band_len.append(temp)

    band_len_tot = [0 if i == 0 else sum(band_len[:i]) for i in range(len(band_len))]
    for i in range(len(xvals)):
        xvals[i] = [j + band_len_tot[i] for j in xvals[i]]

    band_len_tot.append(xvals[-1][-1])
    uploaded_file.seek(0)

    return k_label, kpoint, band_len, k_label_reduce, xvals, band_len_tot


def _build_brillouin_zone_data(reciprocal_lattice_vectors):
    reciprocal_lattice_vectors = np.array(reciprocal_lattice_vectors, dtype=float)
    lattice_points = []
    point_map = []
    for i in range(-1, 2):
        for j in range(-1, 2):
            for k in range(-1, 2):
                frac = np.array([i, j, k], dtype=float)
                lattice_points.append(frac @ reciprocal_lattice_vectors)
                point_map.append((i, j, k))

    lattice_points = np.array(lattice_points)
    vor = Voronoi(lattice_points)
    origin_index = point_map.index((0, 0, 0))
    region_index = vor.point_region[origin_index]
    region = vor.regions[region_index]
    if not region or any(vertex_index < 0 for vertex_index in region):
        raise ValueError("Could not construct a finite Brillouin zone from the uploaded lattice vectors.")

    vertices = vor.vertices[region]
    ridge_segments = []
    for ridge_points, ridge_vertices in zip(vor.ridge_points, vor.ridge_vertices):
        if origin_index in ridge_points and all(vertex_index >= 0 for vertex_index in ridge_vertices):
            ridge = vor.vertices[ridge_vertices]
            ridge_segments.append(ridge)

    return vertices, ridge_segments


def build_brillouin_zone_figure(uploaded_files, dataset_label=None):
    geometry_file = next((file for file in uploaded_files if file.name == 'geometry.in'), None)
    control_file = next((file for file in uploaded_files if file.name == 'control.in'), None)
    if geometry_file is None:
        raise ValueError("`geometry.in` is required to build the Brillouin-zone plot.")

    _, reciprocal_lattice_vectors = process_geometry_file(geometry_file)
    vertices, ridge_segments = _build_brillouin_zone_data(reciprocal_lattice_vectors)

    fig = go.Figure()

    for ridge in ridge_segments:
        closed_ridge = np.vstack([ridge, ridge[0]])
        fig.add_trace(
            go.Scatter3d(
                x=closed_ridge[:, 0],
                y=closed_ridge[:, 1],
                z=closed_ridge[:, 2],
                mode="lines",
                line=dict(color="black", width=4),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    if control_file is not None:
        k_label, kpoint, *_ = process_control_file(control_file, reciprocal_lattice_vectors)
        seen_labels = set()
        label_x = []
        label_y = []
        label_z = []
        label_text = []
        for segment_index, points in enumerate(kpoint):
            start_frac = np.array(points[:3], dtype=float)
            end_frac = np.array(points[3:6], dtype=float)
            start_cart = start_frac @ np.array(reciprocal_lattice_vectors)
            end_cart = end_frac @ np.array(reciprocal_lattice_vectors)
            fig.add_trace(
                go.Scatter3d(
                    x=[start_cart[0], end_cart[0]],
                    y=[start_cart[1], end_cart[1]],
                    z=[start_cart[2], end_cart[2]],
                    mode="lines",
                    line=dict(color="crimson", width=6),
                    showlegend=False,
                    hovertemplate="k-path segment %{x:.3f}, %{y:.3f}, %{z:.3f}<extra></extra>",
                )
            )
            start_label, end_label = k_label[segment_index]
            for label, point in ((start_label, start_cart), (end_label, end_cart)):
                display_label = label.replace('Gamma', 'Γ').replace('G', 'Γ')
                dedupe_key = (display_label, tuple(np.round(point, 8)))
                if dedupe_key not in seen_labels:
                    label_x.append(point[0])
                    label_y.append(point[1])
                    label_z.append(point[2])
                    label_text.append(display_label)
                    seen_labels.add(dedupe_key)

        if label_text:
            fig.add_trace(
                go.Scatter3d(
                    x=label_x,
                    y=label_y,
                    z=label_z,
                    mode="text",
                    text=label_text,
                    textfont=dict(color="navy", size=16),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    reciprocal_vectors = np.array(reciprocal_lattice_vectors)
    vector_traces = []
    for index, vec in enumerate(reciprocal_vectors, start=1):
        fig.add_trace(
            go.Scatter3d(
                x=[0, vec[0]],
                y=[0, vec[1]],
                z=[0, vec[2]],
                mode="lines",
                line=dict(color="gray", width=5),
                showlegend=False,
                hovertemplate=f"b{index}<extra></extra>",
            )
        )
        vector_traces.append((vec[0], vec[1], vec[2], f"b{index}"))

    if vector_traces:
        fig.add_trace(
            go.Scatter3d(
                x=[item[0] for item in vector_traces],
                y=[item[1] for item in vector_traces],
                z=[item[2] for item in vector_traces],
                mode="text",
                text=[item[3] for item in vector_traces],
                textfont=dict(color="gray", size=14),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    max_extent = max(np.max(np.abs(vertices)), np.max(np.abs(reciprocal_vectors)))
    axis_limit = max_extent * 1.15 if max_extent > 0 else 1.0
    title = "Brillouin Zone"
    if dataset_label:
        title = f"{title}: {dataset_label}"

    fig.update_layout(
        title=title,
        title_font=dict(size=24),
        width=950,
        height=850,
        scene=dict(
            xaxis=dict(
                title="kx",
                range=[-axis_limit, axis_limit],
                showbackground=False,
                showgrid=False,
                zeroline=False,
                title_font=dict(size=18),
                tickfont=dict(size=14),
            ),
            yaxis=dict(
                title="ky",
                range=[-axis_limit, axis_limit],
                showbackground=False,
                showgrid=False,
                zeroline=False,
                title_font=dict(size=18),
                tickfont=dict(size=14),
            ),
            zaxis=dict(
                title="kz",
                range=[-axis_limit, axis_limit],
                showbackground=False,
                showgrid=False,
                zeroline=False,
                title_font=dict(size=18),
                tickfont=dict(size=14),
            ),
            aspectmode="cube",
        ),
        margin=dict(l=0, r=0, t=50, b=0),
        showlegend=False,
    )

    return fig


def parse_band_out_files(uploaded_files, energyshift=None):
    # Filtering and sorting the relevant files
    bandfiles = [f for f in uploaded_files if f.name.startswith('band') and f.name.endswith('.out') and len(f.name) == 12]
    bandfiles.sort(key=lambda x: int(x.name[4:-4]))

    bands_all_files = []
    for uploaded_file in bandfiles:
        energys = []

        # Reading file content
        for line in uploaded_file:
            line = line.decode('utf-8')  # Decoding for binary files
            words = line.strip().split()
            energy = []
            occ_ene = words[4:]
            for i in range(0, len(occ_ene), 2):
                energy.append(float(occ_ene[i + 1]) - energyshift)
            energys.append(energy)

        bands = []
        for i in range(len(energy)):
            band = []
            for j in range(len(energys)):
                band.append(energys[j][i])
            bands.append(band)
        bands_all_files.append(bands)
        uploaded_file.seek(0)

    return bands_all_files


def plot_bands(ax, bands_all_files, xvals=None, plot_color='blue', legend_label=None):
    legend_used = False
    for file_id, bands in enumerate(bands_all_files):
        for band_id, band in enumerate(bands):
            ax.plot(
                xvals[file_id],
                band,
                color=plot_color,
                lw=2,
                label=legend_label if legend_label and not legend_used else None,
            )
            legend_used = True
    ax.axhline(0, color='k', linestyle = '--', lw=1).set_dashes([5,5])
    # Clear the default x-tick labels
    ax.set_xticks([])


def get_state_range(uploaded_file):
    df = _read_spin_texture_dataframe(uploaded_file)
    states = df['State'].unique()
    return states.min(), states.max()


def filter_state_data(uploaded_file, target_state):
    df = _read_spin_texture_dataframe(uploaded_file)
    filtered_df = df[df['State'] == target_state].copy()
    filtered_df = filtered_df.drop('State', axis=1)
    filtered_df.reset_index(drop=True, inplace=True)
    return filtered_df


def _read_spin_texture_dataframe(uploaded_file):
    df = pd.read_csv(uploaded_file, sep=r'\s+', comment='#', header=None)
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    column_names_new = ['k_point', 'kx', 'ky', 'kz', 'State', 'Eigenvalue', 'sigma_x', 'sigma_y', 'sigma_z',
                        'rel_kx', 'rel_ky', 'rel_kz']
    column_names_old = ['k_point', 'kx', 'ky', 'kz', 'State', 'Eigenvalue', 'sigma_x', 'sigma_y', 'sigma_z']
    try:
        df.columns = column_names_new
    except ValueError:
        df.columns = column_names_old
    return df


def _read_text_lines(uploaded_file):
    if uploaded_file is None:
        return []
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    raw_content = uploaded_file.read()
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)

    if isinstance(raw_content, bytes):
        text = raw_content.decode("utf-8")
    else:
        text = raw_content
    return text.splitlines()


def get_rec_vector(uploaded_file):
    latvec = []
    for line in _read_text_lines(uploaded_file):
        stripped = line.strip()
        if stripped.startswith("lattice_vector") or stripped.startswith("lattice"):
            latvec.append([float(i) for i in stripped.split()[1:4]])

    if len(latvec) != 3:
        raise ValueError("Geometry file must contain exactly three lattice vectors.")

    rlatvec = []
    pi = math.pi
    volume = np.dot(latvec[0], np.cross(latvec[1], latvec[2]))
    rlatvec.append(2 * pi * np.cross(latvec[1], latvec[2]) / volume)
    rlatvec.append(2 * pi * np.cross(latvec[2], latvec[0]) / volume)
    rlatvec.append(2 * pi * np.cross(latvec[0], latvec[1]) / volume)

    return np.array(rlatvec)


def prepare_plot_data(filename, state, geometry_file=None):
    filtered_df = filter_state_data(filename, state)
    k_points = filtered_df[['kx', 'ky', 'kz']].to_numpy()
    spins = filtered_df[['sigma_x', 'sigma_y', 'sigma_z']].to_numpy()
    energy = filtered_df['Eigenvalue'].to_numpy()

    if geometry_file is not None:
        reciprocal_lattice = get_rec_vector(geometry_file)
        k_points = np.dot(k_points, reciprocal_lattice.T)

    return k_points, spins, energy


def plot_energy_contours(ax, kx, ky, energy, energy_shift, levels=15, cmap_type=cc.cm.CET_L18, alpha=0.1):
    shifted_energy = energy - energy_shift

    # Normalize shifted energy values to a range of 0 to 1
    energy_min = shifted_energy.min()
    energy_max = shifted_energy.max()
    normalized_energy = (shifted_energy - energy_min) / (energy_max - energy_min)

    # Create the filled contour plot
    contourf_plot = ax.tricontourf(kx, ky, normalized_energy, levels=levels, vmin=0, vmax=1,
                                   cmap=cmap_type, zorder=2, alpha=alpha)

    # Create a colorbar at the top of the figure
    cbar = plt.colorbar(contourf_plot, orientation='horizontal', pad=0.1, fraction=0.046, aspect=30, location='top')
    cbar.set_label('Energy (eV)')
    # Set ticks based on the normalized range but label with the actual energy values
    cbar.set_ticks([0, 0.5, 1])
    cbar.set_ticklabels([f'{energy_min:.2f}',
                         f'{(energy_min + energy_max) / 2:.2f}',
                         f'{energy_max:.2f}'])

    ax.autoscale(tight=True)

def plot_quivers(ax, kx, ky, spin_x, spin_y, color_component, spin_direction, scale):
    norm = plt.Normalize(color_component.min(), color_component.max())
    quivers = ax.quiver(kx, ky, spin_x, spin_y, color_component, scale=scale, cmap=cc.cm.CET_D1, norm=norm, alpha=1, width=0.005, headlength=4.0, headwidth=3.0, headaxislength=3.0)
    plt.colorbar(quivers, ax=ax).set_label(rf'$<\sigma_{{{spin_direction}}}>$ component')


def resolve_spin_texture_plane(k_points, spins, spin_direction, plane):
    if plane == 'xy':
        k1, k2 = k_points[:, 0] * 10, k_points[:, 1] * 10
        ax_label_1, ax_label_2 = "kx ($nm^{-1}$)", "ky ($nm^{-1}$)"
        if spin_direction == 'z':
            spin_1, spin_2, color_component = spins[:, 0], spins[:, 1], spins[:, 2]
        elif spin_direction == 'x':
            spin_1, spin_2, color_component = spins[:, 0], spins[:, 1], spins[:, 0]
        elif spin_direction == 'y':
            spin_1, spin_2, color_component = spins[:, 0], spins[:, 1], spins[:, 1]
        else:
            raise ValueError("Invalid spin_direction. Choose 'x', 'y', or 'z'.")
    elif plane == 'yz':
        k1, k2 = k_points[:, 1] * 10, k_points[:, 2] * 10
        ax_label_1, ax_label_2 = "ky ($nm^{-1}$)", "kz ($nm^{-1}$)"
        if spin_direction == 'z':
            spin_1, spin_2, color_component = spins[:, 1], spins[:, 2], spins[:, 2]
        elif spin_direction == 'x':
            spin_1, spin_2, color_component = spins[:, 1], spins[:, 2], spins[:, 0]
        elif spin_direction == 'y':
            spin_1, spin_2, color_component = spins[:, 1], spins[:, 2], spins[:, 1]
        else:
            raise ValueError("Invalid spin_direction. Choose 'x', 'y', or 'z'.")
    elif plane == 'xz':
        k1, k2 = k_points[:, 0] * 10, k_points[:, 2] * 10
        ax_label_1, ax_label_2 = "kx ($nm^{-1}$)", "kz ($nm^{-1}$)"
        if spin_direction == 'z':
            spin_1, spin_2, color_component = spins[:, 0], spins[:, 2], spins[:, 2]
        elif spin_direction == 'x':
            spin_1, spin_2, color_component = spins[:, 0], spins[:, 2], spins[:, 0]
        elif spin_direction == 'y':
            spin_1, spin_2, color_component = spins[:, 0], spins[:, 2], spins[:, 1]
        else:
            raise ValueError("Invalid spin_direction. Choose 'x', 'y', or 'z'.")
    else:
        raise ValueError("Invalid plane. Choose 'xy', 'yz', or 'xz'.")

    return k1, k2, spin_1, spin_2, color_component, ax_label_1, ax_label_2


def plot_spin_quivers(filename, state, spin_direction, plane, shift_energy, scale, axis_limits=None):
    fig, ax = plt.subplots(figsize=(8, 6))
    plt.rcParams["font.family"] = "Arial"
    plt.rcParams.update({'font.size': 18})
    plt.rcParams['axes.linewidth'] = 1.5
    plt.rcParams['axes.labelweight'] = "normal"

    k_points, spins, energy = prepare_plot_data(filename, state)
    k1, k2, spin_1, spin_2, color_component, ax_label_1, ax_label_2 = resolve_spin_texture_plane(
        k_points, spins, spin_direction, plane
    )

    plot_quivers(ax, k1, k2, spin_1, spin_2, color_component, spin_direction, scale=scale)

    # try:
    #     plot_energy_contours(ax, kx, ky, energy, shift_energy)
    # except Exception as e:
    #     st.error(f"An error occurred while plotting the energy contours: {e}")

    ax.set_xlabel(ax_label_1)
    ax.set_ylabel(ax_label_2)

    if axis_limits:
        ax.axis(axis_limits)
        # plt.xlim(axis_limits[0],axis_limits[1])

    plt.tight_layout()
    return plt


def parse_out_file(out_file):
    data = []

    lines = out_file.readlines()

    for i, line in enumerate(lines):
        # Decode the binary line to string
        line = line.decode('utf-8')

        # Check for the line with atoms and electrons
        if "The structure contains" in line:
            numbers = re.findall(r"\d+\.?\d*", line)
            if len(numbers) >= 1:
                data.append({"System parameter": "Number of atoms", "Value": numbers[0]})
                data.append({"System parameter": "Total number of electrons", "Value": numbers[1]})

        ##  | Chemical potential (Fermi level):    -5.83007747 eV
        # Check for fermi level
        if "Chemical potential (Fermi level) in eV" in line:
            numbers = re.findall(r"-?\d*\.?\d+(?:E[+-]?\d+)?", line)
            if numbers:
                data.append({"System parameter": "Fermi level (ELSI) (eV)", "Value": numbers[0]})

        # if "Chemical potential is" in line:
        #     numbers_cp = re.findall(r"-?\d*\.?\d+(?:E[+-]?\d+)?", line)
        #     if numbers_cp:
        #         data.append({"System parameter": "Fermi level (internal zero) (eV)", "Value": numbers_cp[0]})

        # Check for the specific block with energy states
        if "Spin-orbit-coupled \"band gap\" of total set of bands:" in line:
            # Process the next three lines for energy details
            for offset in range(1, 4):
                if i + offset < len(lines):
                    energy_line = lines[i + offset].decode("utf-8")
                    energy_data = re.findall(r"-?\d+\.\d+", energy_line)
                    if "Lowest unoccupied state" in energy_line:
                        data.append({"System parameter": "Lowest unoccupied state", "Value": energy_data[0] + " eV"})
                    elif "Highest occupied state" in energy_line:
                        data.append({"System parameter": "Highest occupied state", "Value": energy_data[0] + " eV"})
                    elif "Energy difference" in energy_line:
                        data.append({"System parameter": "Energy difference", "Value": energy_data[0] + " eV"})

    # Create DataFrame from the list of dictionaries
    df = pd.DataFrame(data)
    return df


from hps.tools.scan_cbm import Band


def build_k_label_reduce(k_label):
    """Collapse pairwise segment labels into the displayed x-axis label sequence."""
    k_label_reduce = []
    for k_pair in k_label:
        for i, k in enumerate(k_pair):
            if len(k_label_reduce) == 0:
                k_label_reduce.append(k)
            elif i == 0 and k != k_label_reduce[-1]:
                k_label_reduce[-1] = k_label_reduce[-1] + "|" + k
            elif i == 0 and k == k_label_reduce[-1]:
                continue
            else:
                k_label_reduce.append(k)
    return k_label_reduce


def parse_segment_selection(segment_text):
    """Parse a user string like '1, 3, 5-7' into one-based segment indices."""
    if not segment_text or not str(segment_text).strip():
        return None

    segments = set()
    for chunk in str(segment_text).split(","):
        item = chunk.strip()
        if not item:
            continue
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start = int(start_text.strip())
            end = int(end_text.strip())
            if start <= 0 or end <= 0:
                raise ValueError("Segment indices must be positive integers.")
            if end < start:
                raise ValueError("Segment ranges must be ascending, e.g. 3-5.")
            segments.update(range(start, end + 1))
        else:
            value = int(item)
            if value <= 0:
                raise ValueError("Segment indices must be positive integers.")
            segments.add(value)
    return sorted(segments)


def parse_label_offset_map(offset_text):
    """Parse label-offset overrides like '2:-0.08, 5:-0.15'."""
    offset_map = {}
    if not offset_text or not str(offset_text).strip():
        return offset_map

    for chunk in str(offset_text).split(","):
        item = chunk.strip()
        if not item:
            continue
        if ":" not in item:
            raise ValueError("Use label offsets in the form '2:-0.08, 5:-0.15'.")
        index_text, offset_value = item.split(":", 1)
        label_index = int(index_text.strip())
        if label_index <= 0:
            raise ValueError("Label indices must be positive integers.")
        offset_map[label_index - 1] = float(offset_value.strip())
    return offset_map

def get_file_uploads(num_data_sets, default_colors):

    if "file_uploader_key" not in st.session_state:
        st.session_state["file_uploader_key"] = 0

    uploaded_files = []
    colors = []
    legend_labels = []
    energyshifts = []
    dataset_summaries = []
    uploader_generation = st.session_state["file_uploader_key"]

    for i in range(num_data_sets):
        dataset_uploader_key = f"bandstructure_files_{uploader_generation}_{i}"
        dataset_color_key = f"bandstructure_color_{uploader_generation}_{i}"
        dataset_legend_key = f"bandstructure_legend_{uploader_generation}_{i}"
        st.text(f"Upload files for data set {i + 1}:")
        files = st.file_uploader(
            f"Data set {i + 1} files",
            type=['in', 'out'],
            accept_multiple_files=True,
            key=dataset_uploader_key,
        )
        color = st.text_input(f"Color for data set {i + 1} (optional):",
                              value=default_colors[i % len(default_colors)], key=dataset_color_key)
        legend_label = st.text_input(
            f"Legend label for data set {i + 1} (optional):",
            value=f"Data set {i + 1}",
            key=dataset_legend_key,
        )
        # energyshift = st.number_input('Enter shift value:', value=0.000, min_value=-30.000, max_value=30.000, key=i)

        if files:
            current_band = Band()
            all_band_data_VBM = []
            all_band_data_CBM = []
            # Filter files based on your criteria
            filtered_files = [file for file in files if file.name.startswith('band') and file.name.endswith('.out')]
            for file in filtered_files:
                # Use the .getvalue() method if the content needs to be read as bytes
                content = file.getvalue()  # Reading the content of the file directly
                current_band.get_band(content)  # Assuming this method is adapted to handle data directly
                VBM_info=current_band.print_VBM()
                CBM_info=current_band.print_CBM()
                all_band_data_VBM.append(VBM_info)
                all_band_data_CBM.append(CBM_info)

            max_energy_band = None
            min_energy_band = None
            if all_band_data_VBM:
                max_energy_band = max(all_band_data_VBM, key=lambda x: x["Energy"])
            if all_band_data_CBM:
                min_energy_band = min(all_band_data_CBM, key=lambda x: x["Energy"])

            uploaded_files.append(files)
            colors.append(color)
            legend_labels.append(legend_label.strip() or f"Data set {i + 1}")
            energyshifts.append(max_energy_band['Energy'] if all_band_data_VBM else 0)
            dataset_summaries.append(
                {
                    "dataset_index": i + 1,
                    "legend_label": legend_label.strip() or f"Data set {i + 1}",
                    "color": color,
                    "band_file_count": len(filtered_files),
                    "has_geometry": any(file.name == "geometry.in" for file in files),
                    "has_control": any(file.name == "control.in" for file in files),
                    "vbm_state": max_energy_band["State"] if max_energy_band is not None else None,
                    "vbm_coordinate": max_energy_band["Coordinate"] if max_energy_band is not None else None,
                    "vbm_energy": max_energy_band["Energy"] if max_energy_band is not None else None,
                    "cbm_state": min_energy_band["State"] if min_energy_band is not None else None,
                    "cbm_coordinate": min_energy_band["Coordinate"] if min_energy_band is not None else None,
                    "cbm_energy": min_energy_band["Energy"] if min_energy_band is not None else None,
                    "band_gap": (
                        min_energy_band["Energy"] - max_energy_band["Energy"]
                        if max_energy_band is not None and min_energy_band is not None
                        else None
                    ),
                }
            )

    return uploaded_files, colors, legend_labels, energyshifts, dataset_summaries


def filter_band_segments(data, selected_segments):
    if not selected_segments:
        return data

    total_segments = len(data["bands_all_files"])
    zero_based_segments = []
    for segment in selected_segments:
        zero_based = segment - 1
        if zero_based < 0 or zero_based >= total_segments:
            raise ValueError(
                f"Requested segment {segment}, but this dataset only has {total_segments} segment(s)."
            )
        zero_based_segments.append(zero_based)

    selected_k_label = [data["k_label"][segment] for segment in zero_based_segments]
    selected_band_len = [data["band_len"][segment] for segment in zero_based_segments]
    selected_band_data = [data["bands_all_files"][segment] for segment in zero_based_segments]

    segment_offsets = []
    running_offset = 0.0
    for length in selected_band_len:
        segment_offsets.append(running_offset)
        running_offset += length

    filtered_xvals = []
    for segment_index, original_segment_index in enumerate(zero_based_segments):
        segment_xvals = np.array(data["xvals"][original_segment_index], dtype=np.float64)
        filtered_xvals.append((segment_xvals - segment_xvals[0]) + segment_offsets[segment_index])

    filtered_band_len_tot = list(segment_offsets)
    if filtered_xvals:
        filtered_band_len_tot.append(float(filtered_xvals[-1][-1]))
    else:
        filtered_band_len_tot.append(0.0)

    filtered_data = data.copy()
    filtered_data["bands_all_files"] = selected_band_data
    filtered_data["xvals"] = filtered_xvals
    filtered_data["band_len_tot"] = filtered_band_len_tot
    filtered_data["k_label"] = selected_k_label
    filtered_data["k_label_reduce"] = build_k_label_reduce(selected_k_label)
    filtered_data["band_len"] = selected_band_len
    return filtered_data


def process_files(
    uploaded_files_list,
    user_defined_colors,
    user_defined_legends,
    user_defined_energyshifts,
    selected_segments=None,
):
    all_data = []
    for index, uploaded_files in enumerate(uploaded_files_list):
        energyshift = user_defined_energyshifts[index]
        bands_all_files = parse_band_out_files(uploaded_files, energyshift=energyshift)
        lattice_vectors, reciprocal_lattice_vectors, k_label, kpoint, band_len, k_label_reduce, xvals, band_len_tot = (None,)*8
        geometry_file = next((file for file in uploaded_files if file.name == 'geometry.in'), None)
        control_file = next((file for file in uploaded_files if file.name == 'control.in'), None)

        if geometry_file and control_file:
            lattice_vectors, reciprocal_lattice_vectors = process_geometry_file(geometry_file)
            k_label, kpoint, band_len, k_label_reduce, xvals, band_len_tot = process_control_file(control_file, reciprocal_lattice_vectors)

        plot_color = user_defined_colors[index]
        data = {
            "bands_all_files": bands_all_files,
            "xvals": xvals,
            "band_len_tot": band_len_tot,
            "k_label_reduce": k_label_reduce,
            "plot_color": plot_color,
            "legend_label": user_defined_legends[index],
            "k_label": k_label,
            "band_len": band_len,
        }
        all_data.append(filter_band_segments(data, selected_segments))
    return all_data


def calculate_scaling_factors(all_data):
    reference_length = all_data[0]["band_len_tot"][-1]  # The total k-path length of the first dataset
    scaling_factors = [reference_length / data["band_len_tot"][-1] for data in all_data]
    return scaling_factors


def scale_data(all_data, scaling_factors):
    for index, data in enumerate(all_data):
        if index > 0:
            scale = scaling_factors[index]
            xvals = np.array(data["xvals"], dtype=np.float64)
            band_len_tot = np.array(data["band_len_tot"], dtype=np.float64)
            data["xvals"] = [x * scale for x in xvals]
            data["band_len_tot"] = [x * scale for x in band_len_tot]
    return all_data


def plot_all_bands(ax, all_data, apply_scaling, num_data_sets):
    # Determine the color for the dashed lines
    dashed_line_color = 'black' if num_data_sets == 1 or apply_scaling else None

    for index, data in enumerate(all_data):
        bands_all_files = data["bands_all_files"]
        xvals = data["xvals"]
        band_len_tot = data["band_len_tot"]
        plot_color = data["plot_color"]
        legend_label = data["legend_label"]
        plot_bands(ax, bands_all_files, xvals, plot_color, legend_label if num_data_sets > 1 else None)

        # Draw dashed lines only if it's the first dataset or if scaling is not applied
        if index == 0 or not apply_scaling:
            for kpoint_x in band_len_tot[1:]:
                ax.axvline(kpoint_x, color=dashed_line_color or plot_color, linestyle='--', lw=1).set_dashes([5, 5])


def set_custom_labels(ax, all_data, apply_scaling, n_data_sets, label_offset_map=None):
    label_offset_map = label_offset_map or {}

    if n_data_sets > 1:
        if apply_scaling:
            # Use the first dataset's labels and positions
            band_len_tot = all_data[0]["band_len_tot"]
            k_label_reduce = all_data[0]["k_label_reduce"]
            # Set color to black
            label_color = 'black'
            # Set the x-axis labels based on the first dataset
            ax.set_xticks(band_len_tot)
            ax.set_xticklabels(k_label_reduce, color=label_color)
            for label_index, tick in enumerate(ax.xaxis.get_major_ticks()):
                tick.set_pad(3 + int(100 * abs(label_offset_map.get(label_index, 0.0))))
        else:
            # Set labels for each dataset without scaling
            label_y_position = -0.05  # Initial y-position for the first set of labels
            y_step = -0.06  # Step to move down the labels for each subsequent data set
            for data in all_data:
                band_len_tot = data["band_len_tot"]
                k_label_reduce = data["k_label_reduce"]
                label_color = data["plot_color"]
                for label_index, (pos, label) in enumerate(zip(band_len_tot, k_label_reduce)):
                    y_position = label_y_position + label_offset_map.get(label_index, 0.0)
                    ax.text(pos, y_position, label, color=label_color, ha='center', transform=ax.get_xaxis_transform())
                label_y_position += y_step
    else:
        band_len_tot = all_data[0]["band_len_tot"]
        k_label_reduce = all_data[0]["k_label_reduce"]
        # Set color to black
        label_color = 'black'
        # Set the x-axis labels based on the first dataset
        ax.set_xticks(band_len_tot)
        k_label_reduce = [label.replace('Gamma', 'Γ').replace('G', 'Γ') for label in k_label_reduce]
        ax.set_xticklabels(k_label_reduce, color=label_color, fontsize=26, rotation= 0)
        for label_index, tick in enumerate(ax.xaxis.get_major_ticks()):
            tick.set_pad(3 + int(100 * abs(label_offset_map.get(label_index, 0.0))))
        # for tick in ax.xaxis.get_major_ticks()[3:4]:
        #     tick.set_pad(30)
        # for tick in ax.xaxis.get_major_ticks()[7:8]:
        #     tick.set_pad(30)
        # for tick in ax.xaxis.get_major_ticks()[9:10]:
        #     tick.set_pad(30)

def get_energy_edges(uploaded_files):
    for uploaded_file in uploaded_files:
        # Check if the file extension is '.out' and does not start with 'band'
        if uploaded_file.name.endswith('.out') and not uploaded_file.name.startswith('band'):
            # Call parse_out_file and return its output
            return parse_out_file(uploaded_file)

    # Return an empty DataFrame if no matching file is found
    return pd.DataFrame()

def create_dataframe_from_absorption_out_files(uploaded_files):
    all_data = pd.DataFrame()
    for file in uploaded_files:
        # Assuming file-like object can be read directly
        data = pd.read_csv(file, delimiter='\t', header=None, skiprows=4)
        data_split = data[0].str.split(expand=True)
        data_split = data_split.apply(pd.to_numeric)
        all_data[file.name] = data_split[1]
    return data_split[0], all_data


def create_absorption_graphs(energy, all_data, exponent_y=False):
    # Grid plot configuration
    plot_height_per_row = 400  # Height for each row
    plot_width = 1200  # Total width of the grid
    n_rows = len(all_data.columns) // 3 + (len(all_data.columns) % 3 > 0)
    total_height = plot_height_per_row * n_rows
    vertical_spacing = 0.4 / n_rows  # Space between rows

    grid_fig = make_subplots(rows=n_rows, cols=3, subplot_titles=all_data.columns,
                             vertical_spacing=vertical_spacing)

    for i, (file, y) in enumerate(all_data.items()):
        row, col = i // 3 + 1, i % 3 + 1
        grid_fig.add_trace(go.Scatter(x=energy, y=y, name=file, mode='lines', showlegend=False), row=row, col=col)

        # Extracting the identifier (xx, yy, zz) from the file name
        identifier = file.split('_')[-2]
        yaxis_label = f'α_{identifier}{identifier}'

        subplot_layout = generate_layout_elec("", "Energy (eV)", yaxis_label, font_size=16)
        grid_fig.update_xaxes(subplot_layout['xaxis'], row=row, col=col)
        grid_fig.update_yaxes(subplot_layout['yaxis'], row=row, col=col)

        # Set y-axis type based on exponent_y
        yaxis_type = 'log' if exponent_y else 'linear'
        grid_fig.update_yaxes(type=yaxis_type, exponentformat='e' if exponent_y else None, row=row, col=col)

    # Update overall layout of the grid figure
    grid_fig.update_layout(height=total_height, width=plot_width, title=subplot_layout['title'],
                           legend=subplot_layout['legend'])

    # Overlaid plots
    overlaid_fig = go.Figure()
    for file, y in all_data.items():
        overlaid_fig.add_trace(go.Scatter(x=energy, y=y, name=file, mode='lines'))

    overlaid_layout = generate_layout_elec("Overlaid Plot", "Energy (eV)", "α", font_size=16)

    # Update legend position to be outside the plot area
    overlaid_layout['legend'] = {
        'orientation': 'h',  # Horizontal orientation
        'yanchor': "bottom",
        'y': 1.02,  # Position the legend just above the plot
        'xanchor': "right",
        'x': 1
    }

    overlaid_fig.update_layout(overlaid_layout)
    overlaid_fig.update_yaxes(type=yaxis_type, exponentformat='e' if exponent_y else None)

    return grid_fig, overlaid_fig

def generate_layout_elec(title, xaxis_title, yaxis_title, font_size=16, color_text='black', l_orientation = 'h', l_yplace=0.1):
    """Generate a layout dictionary based on the given parameters."""
    layout = {
        'title': {'text': title, 'font': {'size': font_size, 'color': color_text}},
        'width': 800,
        'height': 600,
        'xaxis': {
            'title': xaxis_title,
            'title_font': {'size': font_size + 6, 'color': color_text},
            'tickfont': {'size': font_size + 4, 'color': color_text},
            'showgrid': True,
            'griddash': "solid",
            'mirror': False,
            'ticks': 'outside',
            'showline': True,
            'linewidth': 2
        },
        'yaxis': {
            'title': yaxis_title,
            'title_font': {'size': font_size + 6, 'color': color_text},
            'tickfont': {'size': font_size + 4, 'color': color_text},
            'linewidth': 2,
            'showgrid': True,
            'griddash': "solid",
            # 'mirror': True,
            'ticks': 'outside',
            'showline': True,
        },
        'legend': {
            'orientation': l_orientation,
            'yanchor': "bottom",
            'y': l_yplace,
            'xanchor': "right",
            'x': 1
        }
    }
    return layout


def plot_multiple_energy_surfaces_with_spins(
    data_sets,
    spin_direction,
    gridsize=50,
    energy_shift_m=2.0,
    state_opacities=None,
    energy_axis_range=None,
    colorscale_name="RdBu",
    color_mode="normalized_component",
    text_size=18,
    show_background_grid=True,
    figure_height=900,
):
    """Build an interactive Plotly 3D spin-texture figure."""
    fig = go.Figure()
    if state_opacities is None:
        state_opacities = [0.18] * len(data_sets)
    if color_mode == "magnitude":
        cmin = 0.0
        cmax = max(float(np.nanmax(data_set[3])) for data_set in data_sets) if data_sets else 1.0
        if cmax <= cmin:
            cmax = 1.0
        colorbar_title = "|sigma|"
    else:
        cmin = -1.0
        cmax = 1.0
        colorbar_title = f"<σ{spin_direction}>"

    for idx, data_set in enumerate(data_sets):
        k1, k2, energy, color_component = data_set
        energy = energy + idx * energy_shift_m
        surface_opacity = float(state_opacities[idx]) if idx < len(state_opacities) else 0.18

        xi = np.linspace(np.min(k1), np.max(k1), gridsize)
        yi = np.linspace(np.min(k2), np.max(k2), gridsize)
        Xi, Yi = np.meshgrid(xi, yi)
        try:
            Zi = griddata((k1, k2), energy, (Xi, Yi), method='cubic')
        except Exception:
            Zi = griddata((k1, k2), energy, (Xi, Yi), method='nearest')

        try:
            Ci = griddata((k1, k2), color_component, (Xi, Yi), method='cubic')
        except Exception:
            Ci = griddata((k1, k2), color_component, (Xi, Yi), method='nearest')
        fig.add_trace(
            go.Surface(
                x=Xi,
                y=Yi,
                z=Zi,
                surfacecolor=np.clip(Ci, cmin, cmax),
                colorscale=colorscale_name,
                cmin=cmin,
                cmax=cmax,
                opacity=surface_opacity,
                colorbar=dict(title=colorbar_title, len=0.6) if idx == 0 else None,
                showscale=idx == 0,
                customdata=np.expand_dims(np.clip(Ci, cmin, cmax), axis=-1),
                hovertemplate=(
                    "k1=%{x:.3f}<br>"
                    "k2=%{y:.3f}<br>"
                    "E=%{z:.3f}<br>"
                    f"{colorbar_title}=%{{customdata[0]:.3f}}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        font=dict(size=text_size),
        scene=dict(
            bgcolor="white",
            xaxis_title="kx (nm^-1)",
            yaxis_title="ky (nm^-1)",
            zaxis_title="Energy (eV)",
            xaxis=dict(showgrid=show_background_grid, backgroundcolor="white"),
            yaxis=dict(showgrid=show_background_grid, backgroundcolor="white"),
            zaxis=dict(
                range=energy_axis_range,
                showgrid=show_background_grid,
                backgroundcolor="white",
            ) if energy_axis_range is not None else dict(showgrid=show_background_grid, backgroundcolor="white"),
        ),
        margin=dict(l=0, r=0, t=20, b=0),
        template="plotly_white",
        height=figure_height,
        paper_bgcolor="white",
        plot_bgcolor="white",
    )

    return fig

def plot_spin_quivers_3D(
    filename_spin,
    states,
    spin_direction,
    plane,
    geometry_file=None,
    gridsize=250,
    energy_shift_m=2.0,
    state_opacities=None,
    energy_axis_range=None,
    colorscale_name="RdBu",
    color_mode="normalized_component",
    text_size=18,
    show_background_grid=True,
    figure_height=900,
):
    plt.rcParams["font.family"] = "Arial"
    plt.rcParams.update({'font.size': 18})

    data_sets = []

    for state in states:
        k_points, spins, energy = prepare_plot_data(filename_spin, state, geometry_file=geometry_file)
        k1, k2, spin_1, spin_2, color_component, ax_label_1, ax_label_2 = resolve_spin_texture_plane(
            k_points, spins, spin_direction, plane
        )
        magnitudes = np.linalg.norm(spins, axis=1)
        if color_mode == "normalized_component":
            eps = 1e-15
            color_values = np.divide(
                color_component,
                magnitudes,
                out=np.zeros_like(color_component),
                where=magnitudes > eps,
            )
        elif color_mode == "raw_component":
            color_values = color_component
        elif color_mode == "magnitude":
            color_values = magnitudes
        else:
            raise ValueError("Invalid color_mode.")
        data_set = [k1, k2, energy, color_values]
        data_sets.append(data_set)

    fig = plot_multiple_energy_surfaces_with_spins(
        data_sets,
        spin_direction,
        gridsize=gridsize,
        energy_shift_m=energy_shift_m,
        state_opacities=state_opacities,
        energy_axis_range=energy_axis_range,
        colorscale_name=colorscale_name,
        color_mode=color_mode,
        text_size=text_size,
        show_background_grid=show_background_grid,
        figure_height=figure_height,
    )
    fig.update_layout(
        scene=dict(
            xaxis_title=ax_label_1.replace("$", ""),
            yaxis_title=ax_label_2.replace("$", ""),
        )
    )
    return fig
