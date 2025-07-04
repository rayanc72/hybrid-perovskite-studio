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
from plotly.subplots import make_subplots


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
        if line.strip().startswith('output band') or line.strip().startswith('output                             band'):
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
    column_names_new = ['k_point', 'kx', 'ky', 'kz', 'State', 'Eigenvalue', 'sigma_x', 'sigma_y', 'sigma_z','rel_kx', 'rel_ky', 'rel_kz']
    column_names_old = ['k_point', 'kx', 'ky', 'kz', 'State', 'Eigenvalue', 'sigma_x', 'sigma_y', 'sigma_z']
    try:
        df.columns = column_names_new
    except:
        df.columns = column_names_old
    states = df['State'].unique()
    return states.min(), states.max()


def filter_state_data(uploaded_file, target_state):
    # Read the file directly from the file-like object
    df = pd.read_csv(uploaded_file, delim_whitespace=True, comment='#', header=None)
    uploaded_file.seek(0)  # Reset the file pointer to the beginning after reading
    column_names_new = ['k_point', 'kx', 'ky', 'kz', 'State', 'Eigenvalue', 'sigma_x', 'sigma_y', 'sigma_z', 'rel_kx',
                        'rel_ky', 'rel_kz']
    column_names_old = ['k_point', 'kx', 'ky', 'kz', 'State', 'Eigenvalue', 'sigma_x', 'sigma_y', 'sigma_z']
    try:
        df.columns = column_names_new
    except:
        df.columns = column_names_old
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
    plt.colorbar(quivers, ax=ax).set_label(f'$<\sigma_{spin_direction}>$ component')

def plot_spin_quivers(filename, state, spin_direction, plane, shift_energy, scale, axis_limits=None):
    fig, ax = plt.subplots(figsize=(8, 6))
    plt.rcParams["font.family"] = "Arial"
    plt.rcParams.update({'font.size': 18})
    plt.rcParams['axes.linewidth'] = 1.5
    plt.rcParams['axes.labelweight'] = "normal"

    k_points, spins, energy = prepare_plot_data(filename, state)


    if plane == 'xy':
        k1, k2 = k_points[:, 0]*10, k_points[:, 1]*10
        ax_label_1, ax_label_2 = "kx ($// \\vec{a}$) ($nm^{-1}$)", "ky ($// \\vec{b}$) ($nm^{-1}$)"
        if spin_direction == 'z':
            spin_1, spin_2, color_component = spins[:, 0], spins[:, 1], spins[:, 2]
        elif spin_direction == 'x':
            spin_1, spin_2, color_component = spins[:, 0], spins[:, 1], spins[:, 0]
        elif spin_direction == 'y':
            spin_1, spin_2, color_component = spins[:, 0], spins[:, 1], spins[:, 1]
        else:
            raise ValueError("Invalid spin_direction. Choose 'x', 'y', or 'z'.")
    elif plane == 'yz':
        k1, k2 = k_points[:, 1]*10, k_points[:, 2]*10
        ax_label_1, ax_label_2 = "ky ($// \\vec{b}$) ($nm^{-1}$)", "kz ($// \\vec{c}$) ($nm^{-1}$)"
        if spin_direction == 'z':
            spin_1, spin_2, color_component = spins[:, 1], spins[:, 2], spins[:, 2]
        elif spin_direction == 'x':
            spin_1, spin_2, color_component = spins[:, 1], spins[:, 2], spins[:, 0]
        elif spin_direction == 'y':
            spin_1, spin_2, color_component = spins[:, 1], spins[:, 2], spins[:, 1]
        else:
            raise ValueError("Invalid spin_direction. Choose 'x', 'y', or 'z'.")
    elif plane == 'xz':
        k1, k2 = k_points[:, 0]*10, k_points[:, 2]*10
        ax_label_1, ax_label_2 = "kx ($// \\vec{a}$) ($nm^{-1}$)", "kz ($// \\vec{c}$) ($nm^{-1}$)"
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


from scan_CBM import Input, Band

def get_file_uploads(num_data_sets, default_colors):

    if "file_uploader_key" not in st.session_state:
        st.session_state["file_uploader_key"] = 0

    if "uploaded_files" not in st.session_state:
        st.session_state["uploaded_files"] = []


    uploaded_files = []
    colors = []
    energyshifts = []
    all_band_data_VBM = []
    all_band_data_CBM = []

    for i in range(num_data_sets):
        st.text(f"Upload files for data set {i + 1}:")
        files = st.file_uploader(f"Data set {i + 1} files", type=['in', 'out'], accept_multiple_files=True,
                                 key=st.session_state["file_uploader_key"])
        color = st.text_input(f"Color for data set {i + 1} (optional):",
                              value=default_colors[i % len(default_colors)], key=f"color{i + 1}")
        # energyshift = st.number_input('Enter shift value:', value=0.000, min_value=-30.000, max_value=30.000, key=i)

        if files:
            st.session_state["uploaded_files"] = files
            current_band = Band()
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

            if all_band_data_VBM:
                max_energy_band = max(all_band_data_VBM, key=lambda x: x["Energy"])
            if all_band_data_CBM:
                min_energy_band = min(all_band_data_CBM, key=lambda x: x["Energy"])

                # Create two columns for VBM and CBM information
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### VBM Information (shifted 0 eV)")
                st.markdown(f"- **State:** {max_energy_band['State']}")
                st.markdown(f"- **Coordinate:** {max_energy_band['Coordinate']}")
                st.markdown(f"- **Energy:** {max_energy_band['Energy']} eV")

            with col2:
                st.markdown("### CBM Information (just FYI ...)")
                st.markdown(f"- **State:** {min_energy_band['State']}")
                st.markdown(f"- **Coordinate:** {min_energy_band['Coordinate']}")
                st.markdown(f"- **Energy:** {min_energy_band['Energy']} eV")

            st.markdown(f" The band gap is {min_energy_band['Energy'] - max_energy_band['Energy']} eV")

            uploaded_files.append(files)
            colors.append(color)
            energyshifts.append(max_energy_band['Energy'] if all_band_data_VBM else 0)

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
        k_label_reduce = [label.replace('Gamma', 'Γ').replace('G', 'Γ') for label in k_label_reduce]
        ax.set_xticklabels(k_label_reduce, color=label_color, fontsize=26, rotation= 0)
        for tick in ax.xaxis.get_major_ticks()[3:4]:
            tick.set_pad(30)
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


def plot_multiple_energy_surfaces_with_spins(data_sets, view_init=None, alpha=0.1, gridsize=50,
                                             constant=0.01):
    """
    Plots multiple 3D surface plots of energy levels on the kx-ky plane, with 3D spins represented as arrows, for multiple sets of data.

    Parameters:
    - data_sets: A list of data sets, where each set is [kx, ky, energy, sigma_x, sigma_y, sigma_z].
    - color: String representing the color of the surface plot.
    - view_init: Tuple of (elev, azim) to set the view angle of the 3D plot.
    - alpha: Opacity of the surface plot.
    - gridsize: The size of the grid to interpolate onto for smoothing.
    - constant: A small constant value added to the magnitude calculation to visualize zero magnitude spins.
    - linewidths: The thickness of the arrows in the quiver plot.
    """
    # Create a new figure and add a 3D subplot
    colors = cycle(['grey', 'orchid'])

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    for data_set in data_sets:
        kx, ky, energy, sigma_x, sigma_y, sigma_z = data_set
        surface_color = next(colors)

        # Normalize spin vectors with a small constant to handle zero magnitude vectors
        magnitudes = np.sqrt(sigma_x ** 2 + sigma_y ** 2 + sigma_z ** 2) + constant
        sigma_x_normalized = sigma_x / magnitudes
        sigma_y_normalized = sigma_y / magnitudes
        sigma_z_normalized = sigma_z / magnitudes

        # Create a colormap based on the z component of the spin
        norm = Normalize(vmin=-1, vmax=1)
        cmap = plt.get_cmap('coolwarm')
        mappable = ScalarMappable(norm=norm, cmap=cmap)
        spin_colors = mappable.to_rgba(sigma_z_normalized)

        # Interpolate energy data onto the grid
        xi = np.linspace(min(kx), max(kx), gridsize)
        yi = np.linspace(min(ky), max(ky), gridsize)
        Xi, Yi = np.meshgrid(xi, yi)
        Zi = griddata((kx, ky), energy, (Xi, Yi), method='cubic')

        # Plot the surface
        ax.plot_surface(Xi, Yi, Zi, color=surface_color, edgecolor='none', alpha=alpha)

        # Calculate the energy (Z) at each spin's (kx, ky) position
        spin_z = griddata((kx, ky), energy, (kx, ky), method='nearest')

        # Plot the normalized spins as 3D arrows, coloring based on z component
        for i in range(len(kx)):
            ax.quiver(kx[i], ky[i], spin_z[i], sigma_x_normalized[i], sigma_y_normalized[i], sigma_z_normalized[i],
                      color=spin_colors[i], pivot='middle', length=0.2, arrow_length_ratio=0.1, normalize=False,
                      linewidth=1, alpha=1)

    # Optionally set the view angle
    if view_init:
        ax.view_init(elev=view_init[0], azim=view_init[1])

    # Set labels for the axes
    ax.set_xlabel('kx')
    ax.set_ylabel('ky')
    ax.set_zlabel('Energy')

    # Add colorbar for the spins' z component
    # cbar = fig.colorbar(mappable, shrink=0.1, aspect=5, pad=0.1)
    # cbar.set_label('Spin Direction (z component)')

    return fig
from itertools import cycle
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from mpl_toolkits.mplot3d import Axes3D
import math
from scipy.interpolate import griddata

def plot_spin_quivers_3D(filename_spin, states, spin_direction):
    plt.rcParams["font.family"] = "Arial"
    plt.rcParams.update({'font.size': 18})

    data_sets = []

    for state in states:
        k_points, spins, energy = prepare_plot_data(filename_spin, state)
        kx, ky, kz = k_points[:, 0], k_points[:, 1], k_points[:, 2]
        sigma_x, sigma_y, sigma_z = spins[:, 0], spins[:, 1], spins[:, 2]


        if spin_direction == 'z':
            data_set = [kx, ky, energy, sigma_x, sigma_y, sigma_z]
            data_sets.append(data_set)
        elif spin_direction == 'x':
            data_set = [kz, ky,energy, sigma_z, sigma_y, sigma_x]
            data_sets.append(data_set)
        elif spin_direction == 'y':
            data_set = [kx, kz, energy, sigma_x, sigma_z, sigma_y]
            data_sets.append(data_set)
        else:
            raise ValueError("Invalid spin_direction. Choose 'x', 'y', or 'z'.")

    return plot_multiple_energy_surfaces_with_spins(data_sets, view_init=[18,0])