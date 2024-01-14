import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import streamlit as st
from io import StringIO
import io
import math
from math import pi
import pandas as pd
import holoviews as hv
from holoviews import opts
hv.extension('bokeh')
import holoviews as hv
import pandas as pd
import numpy as np
from holoviews import opts
from bokeh.plotting import figure, show
import streamlit_bokeh_events as bokeh_events
from bokeh.models import Span
import re
import colorcet as cc


def plot_pdos_streamlit(dos_data, shift, plot_range):
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

    for element, dos in dos_data.items():
        # color = next(color_iter)
        if element == "Total":
            fig.add_trace(go.Scatter(x=dos.T[1], y=dos.T[0] + shift, mode='lines', name="Total DOS", line=dict(color='black', width=3)))
        elif element == "Sn" or element == "Pb":
            fig.add_trace(
                go.Scatter(x=dos.T[2], y=dos.T[0] + shift, mode='lines', name=f"{element}" + "(s)" , line=dict(color=next(color_iter), width=3)))
            fig.add_trace(
                go.Scatter(x=dos.T[3], y=dos.T[0] + shift, mode='lines', name=f"{element}" + "(p)", line=dict(color=next(color_iter), width=3)))
        elif element == "Cl" or element == "Br" or element == "Br1" or element == "I":
            fig.add_trace(
                go.Scatter(x=dos.T[1], y=dos.T[0] + shift, mode='lines', name=f"{element}", line=dict(color=next(color_iter), width=3)))
        else:
            fig.add_trace(go.Scatter(x=dos.T[1], y=dos.T[0] + shift, mode='lines', name=f"{element}", line=dict(color=next(color_iter), width=3)))

    fig.update_layout(
        yaxis_title="Energy (eV)",
        yaxis_tickfont=dict(size=20, color='black'),
        yaxis_title_font=dict(size=24, color='black'),

        xaxis_title="Density of States",
        xaxis_tickfont=dict(size=20, color='black'),
        xaxis_title_font=dict(size=24, color='black'),
        xaxis_showticklabels=False,

        legend=dict(font=dict(size=15), bgcolor="rgba(255, 255, 255, 0.8)"),
        margin=dict(l=50, r=30, t=30, b=50),
        plot_bgcolor="rgba(255, 255, 255, 0.8)"
    )

    fig.update_yaxes(range=plot_range)
    fig.update_layout(height=900, width=500)
    fig.update_xaxes(showline=True, linewidth=1, linecolor='black', mirror=True, side='top', ticklen=10,
                     ticks="outside")

    return fig



class Input(object):

    def __init__(self, latvec=[], species_id={}, k_path=[], band_sampling=[]):
        self.latvec = latvec
        self.species_id = species_id
        self.k_path = k_path
        self.band_sampling = band_sampling

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

    return lattice_vectors, reciprocal_lattice_vectors


def process_control_file(uploaded_file, rlatvec):
    k_label = []
    kpoint = []

    for line in uploaded_file:
        line = line.decode('utf-8')  # Decoding for binary files
        if line.strip().startswith('output band'):
            words = line.strip().split()
            kpoint.append([float(i) for i in words[2:8]])
            n_sample = int(words[-3])
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
    for i in kpoint:
        kvec = [i[j + 3] - i[j] for j in range(3)]
        temp = math.sqrt(sum([k * k for k in list(np.dot(kvec, rlatvec))]))
        step = temp / (n_sample - 1)
        xval = [i * step for i in range(n_sample)]
        xvals.append(xval)
        band_len.append(temp)

    band_len_tot = [0 if i == 0 else sum(band_len[:i]) for i in range(len(band_len))]
    for i in range(len(xvals)):
        xvals[i] = [j + band_len_tot[i] for j in xvals[i]]

    band_len_tot.append(xvals[-1][-1])

    return k_label, kpoint, band_len, k_label_reduce, xvals, band_len_tot


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

    return bands_all_files


def plot_bands(ax, bands_all_files, xvals=None, plot_color='blue'):
    for file_id, bands in enumerate(bands_all_files):
        for band_id, band in enumerate(bands):
            ax.plot(xvals[file_id], band, color=plot_color, lw=2)
    ax.axhline(0, color='k', linestyle = '--', lw=1).set_dashes([5,5])
    # Clear the default x-tick labels
    ax.set_xticks([])


def get_state_range(uploaded_file):
    df = pd.read_csv(uploaded_file, delim_whitespace=True, comment='#', header=None)
    column_names = ['k_point', 'kx', 'ky', 'kz', 'State', 'Eigenvalue', 'sigma_x', 'sigma_y', 'sigma_z']
    df.columns = column_names
    states = df['State'].unique()
    return states.min(), states.max()


def filter_state_data(uploaded_file, target_state):
    # Read the file directly from the file-like object
    df = pd.read_csv(uploaded_file, delim_whitespace=True, comment='#', header=None)
    uploaded_file.seek(0)  # Reset the file pointer to the beginning after reading
    column_names = ['k_point', 'kx', 'ky', 'kz', 'State', 'Eigenvalue', 'sigma_x', 'sigma_y', 'sigma_z']
    df.columns = column_names
    filtered_df = df[df['State'] == target_state].copy()
    filtered_df = filtered_df.drop('State', axis=1)
    filtered_df.reset_index(drop=True, inplace=True)
    return filtered_df


def prepare_plot_data(filename, state):
    filtered_df = filter_state_data(filename, state)
    k_points = filtered_df[['kx', 'ky', 'kz']].to_numpy()
    spins = filtered_df[['sigma_x', 'sigma_y', 'sigma_z']].to_numpy()
    energy = filtered_df['Eigenvalue'].to_numpy()

    return k_points, spins, energy


def plot_energy_contours(ax, kx, ky, energy, energy_shift, levels=15, cmap_type=cc.cm.CET_L18, alpha=0.0):
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
    quivers = ax.quiver(kx, ky, spin_x, spin_y, color_component, scale=scale, cmap=cc.cm.CET_D1, norm=norm, alpha=1, width=0.003)
    plt.colorbar(quivers, ax=ax).set_label(f'$<\sigma_{spin_direction}>$ component')

def plot_spin_quivers(filename, state, spin_direction, shift_energy, scale, axis_limits=None):
    fig, ax = plt.subplots(figsize=(8, 6))
    plt.rcParams["font.family"] = "Arial"
    plt.rcParams.update({'font.size': 18})
    plt.rcParams['axes.linewidth'] = 1.5
    plt.rcParams['axes.labelweight'] = "normal"

    k_points, spins, energy = prepare_plot_data(filename, state)

    if spin_direction == 'z':
        kx, ky = k_points[:, 0], k_points[:, 1]
        spin_x, spin_y, color_component = spins[:, 0], spins[:, 1], spins[:, 2]
        ax_label_x, ax_label_y = "-X$\Gamma$X ($// \\vec{a}$) ($\AA^{-1}$)", "-Y$\Gamma$Y ($// \\vec{b}$) ($\AA^{-1}$)"
    elif spin_direction == 'x':
        ky, kz = k_points[:, 1], k_points[:, 2]
        spin_y, spin_z, color_component = spins[:, 1], spins[:, 2], spins[:, 0]
        kx, spin_x = kz, spin_z
        ax_label_x, ax_label_y = "-Z$\Gamma$Z ($// \\vec{c}$) ($\AA^{-1}$)", "-Y$\Gamma$Y ($// \\vec{b}$) ($\AA^{-1}$)"
    elif spin_direction == 'y':
        kx, kz = k_points[:, 0], k_points[:, 2]
        spin_x, spin_z, color_component = spins[:, 0], spins[:, 2], spins[:, 1]
        ky, spin_y = kz, spin_z
        ax_label_x, ax_label_y = "-X$\Gamma$X ($// \\vec{a}$) ($\AA^{-1}$)", "-Z$\Gamma$Z ($// \\vec{c}$) ($\AA^{-1}$)"
    else:
        raise ValueError("Invalid spin_direction. Choose 'x', 'y', or 'z'.")

    plot_quivers(ax, kx, ky, spin_x, spin_y, color_component, spin_direction, scale=scale)

    # try:
    #     plot_energy_contours(ax, kx, ky, energy, shift_energy)
    # except Exception as e:
    #     st.error(f"An error occurred while plotting the energy contours: {e}")

    ax.set_xlabel(ax_label_x)
    ax.set_ylabel(ax_label_y)

    if axis_limits:
        ax.axis(axis_limits)
        # plt.xlim(axis_limits[0],axis_limits[1])

    plt.tight_layout()
    return plt


def get_rec_vector(filename):
    kpoint = []
    latvec = []
    f = open(filename, 'r')
    for line in f:
        if line.strip().startswith("lattice"):
            latvec.append([float(i) for i in line.strip().split()[1:4]])
    f.close()

    rlatvec = []
    pi = math.pi
    volume = (np.dot(latvec[0], np.cross(latvec[1], latvec[2])))
    rlatvec.append(2 * pi * np.cross(latvec[1], latvec[2]) / volume)
    rlatvec.append(2 * pi * np.cross(latvec[2], latvec[0]) / volume)
    rlatvec.append(2 * pi * np.cross(latvec[0], latvec[1]) / volume)

    return rlatvec



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


def get_file_uploads(num_data_sets, default_colors):
    uploaded_files = []
    colors = []
    energyshifts = []

    for i in range(num_data_sets):
        st.text(f"Upload files for data set {i + 1}:")
        files = st.file_uploader(f"Data set {i + 1} files", type=['in', 'out'], accept_multiple_files=True,
                                 key=f"uploader{i + 1}")
        color = st.text_input(f"Color for data set {i + 1} (optional):",
                              value=default_colors[i % len(default_colors)], key=f"color{i + 1}")
        energyshift = st.number_input('Enter shift value:', value=0.000, min_value=-30.000, max_value=30.000, key=i)
        if files:
            edges = get_energy_edges(files)
            st.dataframe(edges, use_container_width=True, hide_index=True)
            uploaded_files.append(files)
            colors.append(color)
            energyshifts.append(energyshift)

    return uploaded_files, colors, energyshifts


def process_files(uploaded_files_list, user_defined_colors, user_defined_energyshifts):
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
        all_data.append((bands_all_files, xvals, band_len_tot, k_label_reduce, plot_color))
    return all_data


def calculate_scaling_factors(all_data):
    reference_length = all_data[0][2][-1]  # The total k-path length of the first dataset
    scaling_factors = [reference_length / band_len_tot[-1] for _, _, band_len_tot, _, _ in all_data]
    return scaling_factors


def scale_data(all_data, scaling_factors):
    for index, (bands_all_files, xvals, band_len_tot, k_label_reduce, plot_color) in enumerate(all_data):
        if index > 0:
            scale = scaling_factors[index]
            xvals = np.array(xvals, dtype=np.float64)
            band_len_tot = np.array(band_len_tot, dtype=np.float64)
            scaled_xvals = [x * scale for x in xvals]
            scaled_band_len_tot = [x * scale for x in band_len_tot]
            all_data[index] = (bands_all_files, scaled_xvals, scaled_band_len_tot, k_label_reduce, plot_color)
    return all_data


def plot_all_bands(ax, all_data, apply_scaling, num_data_sets):
    # Determine the color for the dashed lines
    dashed_line_color = 'black' if num_data_sets == 1 or apply_scaling else None

    for index, (bands_all_files, xvals, band_len_tot, k_label_reduce, plot_color) in enumerate(all_data):
        plot_bands(ax, bands_all_files, xvals, plot_color)

        # Draw dashed lines only if it's the first dataset or if scaling is not applied
        if index == 0 or not apply_scaling:
            for kpoint_x in band_len_tot[1:]:
                ax.axvline(kpoint_x, color=dashed_line_color or plot_color, linestyle='--', lw=1).set_dashes([5, 5])


def set_custom_labels(ax, all_data, apply_scaling, n_data_sets):

    if n_data_sets > 1:
        if apply_scaling:
            # Use the first dataset's labels and positions
            band_len_tot, k_label_reduce, _ = all_data[0][2], all_data[0][3], all_data[0][4]
            # Set color to black
            label_color = 'black'
            # Set the x-axis labels based on the first dataset
            ax.set_xticks(band_len_tot)
            ax.set_xticklabels(k_label_reduce, color=label_color)
        else:
            # Set labels for each dataset without scaling
            label_y_position = -0.05  # Initial y-position for the first set of labels
            y_step = -0.06  # Step to move down the labels for each subsequent data set
            for data in all_data:
                band_len_tot, k_label_reduce, plot_color = data[2], data[3], data[4]
                label_color = plot_color
                for pos, label in zip(band_len_tot, k_label_reduce):
                    ax.text(pos, label_y_position, label, color=label_color, ha='center', transform=ax.get_xaxis_transform())
                label_y_position += y_step
    else:
        band_len_tot, k_label_reduce, _ = all_data[0][2], all_data[0][3], all_data[0][4]
        # Set color to black
        label_color = 'black'
        # Set the x-axis labels based on the first dataset
        ax.set_xticks(band_len_tot)
        ax.set_xticklabels(k_label_reduce, color=label_color, fontsize=20)

def get_energy_edges(uploaded_files):
    for uploaded_file in uploaded_files:
        # Check if the file extension is '.out' and does not start with 'band'
        if uploaded_file.name.endswith('.out') and not uploaded_file.name.startswith('band'):
            # Call parse_out_file and return its output
            return parse_out_file(uploaded_file)

    # Return an empty DataFrame if no matching file is found
    return pd.DataFrame()