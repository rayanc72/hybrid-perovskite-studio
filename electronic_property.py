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

class Band(object):

    def __init__(self, eigenvalues={}, sampling=0, coordinate=[]):
        self.eigenvalues = eigenvalues
        self.sampling = sampling
        self.coordinate = coordinate

    def process_band_file(self, file):
        data = file.readlines()
        self.sampling = len(data)
        for grid in range(self.sampling):
            item = data[grid].split()
            self.coordinate.append([float(k) for k in item[1:4]])
            for i in range(1, (len(item) - 4) // 2 + 1):
                try:
                    self.eigenvalues[i].append(float(item[2 * i + 3]))
                except KeyError:
                    self.eigenvalues[i] = [float(item[2 * i + 3])]
        file.seek(0)  # Reset file pointer to the beginning

    def print_VBM(self, line=0.00):
        for state in self.eigenvalues:
            if (max(self.eigenvalues[state + 1]) > line):
                break
        max_energy = max(self.eigenvalues[state])
        VBM_list = [x for x in range(len(self.eigenvalues[state]))
                    if (self.eigenvalues[state][x] == max_energy)]
        st.write("VBM energy: " + str(max_energy) + " eV")
        st.write("Current state: " + str(state))
        for i in range(len(VBM_list)):
            st.write("Coordinate: " + str(self.coordinate[VBM_list[i]]) + "  " +
                  "Energy: " + str(max_energy) + " eV")

    def print_CBM(self, line=0.00):
        for state in self.eigenvalues:
            if (max(self.eigenvalues[state + 1]) > line):
                break
        state = state + 1
        min_energy = min(self.eigenvalues[state])
        CBM_list = [x for x in range(len(self.eigenvalues[state]))
                    if (self.eigenvalues[state][x] == min_energy)]
        st.write("CBM energy: " + str(min_energy) + " eV")
        st.write("Current state: " + str(state))
        for i in range(len(CBM_list)):
            st.write("Coordinate: " + str(self.coordinate[CBM_list[i]]) + "  " +
                  "Energy: " + str(min_energy) + " eV")

    def find_VBM_state(self, line=0.01):
        for state in self.eigenvalues:
            if (max(self.eigenvalues[state + 1]) > line):
                break
        return state

    def find_VBM_energy(self, line=0.01):
        VBM_state = self.find_VBM_state(line)
        st.write(" ")
        st.write(VBM_state)
        return (max(self.eigenvalues[VBM_state]))


def band_files_process(uploaded_files):
    current_band = Band()

    for file in uploaded_files:
        file = StringIO(file.getvalue().decode())  # Convert the file-like object to StringIO with decoded content
        current_band.process_band_file(file)

    return current_band

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


def process_geometry_file(uploaded_files):
    # Look for the "geometry.in" file in the uploaded files
    geometry_file = None
    for uploaded_file in uploaded_files:
        if uploaded_file.name == "geometry.in":
            geometry_file = uploaded_file
            break

    # Raise an error if the file was not found
    if geometry_file is None:
        raise ValueError("The 'geometry.in' file was not uploaded.")

    latvec = []
    rlatvec = []

    # Convert binary object to string
    file_text = geometry_file.read().decode()

    # Use StringIO to treat the string as a file for parsing
    f = io.StringIO(file_text)
    for line in f:
        words = line.strip().split()
        if len(words) == 0:
            continue
        if words[0] == "lattice_vector":
            latvec.append([float(i) for i in words[1:4]])

    # Calculate reciprocal lattice vectors
    volume = (np.dot(latvec[0], np.cross(latvec[1], latvec[2])))
    rlatvec.append(2 * pi * np.cross(latvec[1], latvec[2]) / volume)
    rlatvec.append(2 * pi * np.cross(latvec[2], latvec[0]) / volume)
    rlatvec.append(2 * pi * np.cross(latvec[0], latvec[1]) / volume)

    return rlatvec


def process_control_file(uploaded_files, rlatvec):
    # Look for the "control.in" file in the uploaded files
    control_file = None
    for uploaded_file in uploaded_files:
        if uploaded_file.name == "control.in":
            control_file = uploaded_file
            break

    # Raise an error if the file was not found
    if control_file is None:
        raise ValueError("The 'control.in' file was not uploaded.")

    k_label = []
    kpoint = []

    # Convert binary object to string
    file_text = control_file.read().decode()

    # Use StringIO to treat the string as a file for parsing
    f = io.StringIO(file_text)
    for line in f:
        if line.strip().startswith('output band'):
            words = line.strip().split()
            kpoint.append([float(i) for i in words[2:8]])
            n_sample = int(words[-3])
            k_label.append(words[-2:])

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

    xvals = []
    for i in kpoint:
        kvec = []
        for j in range(3):
            kvec.append(i[j + 3] - i[j])
        temp = math.sqrt(sum([k * k for k in list(np.dot(kvec, rlatvec))]))
        step = temp / (n_sample - 1)
        xval = []
        for i in range(n_sample):
            xval.append(i * step)
        xvals.append(xval)
        band_len = [len(x) for x in xvals]

    band_len_tot = []
    for i in range(len(band_len)):
        if i == 0:
            band_len_tot.append(0)
        else:
            band_len_tot.append(sum(band_len[:i]))

    for i in range(len(xvals)):
        xvals[i] = [j + band_len_tot[i] for j in xvals[i]]

    band_len_tot.append(xvals[-1][-1])

    return k_label, kpoint, band_len, k_label_reduce, xvals, band_len_tot


def parse_output_files(uploaded_files, energyshift=None):
    bands_all_files = []

    # Uploaded files is a list of binary objects
    for uploaded_file in uploaded_files:
        # Filter out .out files
        if uploaded_file.name.endswith('.out'):
            # Convert binary object to string
            file_text = uploaded_file.read().decode()

            energys = []

            # Use StringIO to treat the string as a file for parsing
            f = io.StringIO(file_text)
            for line in f:
                words = line.strip().split()
                energy = []
                occ_ene = words[4:]
                for i in range(0, len(occ_ene), 2):
                    energy.append(float(occ_ene[i+1]) - energyshift)
                energys.append(energy)

            bands = []
            for i in range(len(energy)):
                band = []
                for j in range(len(energys)):
                    band.append(energys[j][i])
                bands.append(band)
            bands_all_files.append(bands)

    return bands_all_files


def plot_band(uploaded_files, energyshift=None, ymin=None, ymax=None,
               orghomo=[], inorghomo=[], orglumo=[], inorglumo=[], special_line=3, solid=None, black_bands=1):
    #Process each file
    bands_all_files = parse_output_files(uploaded_files=uploaded_files, energyshift=energyshift)
    rlatvec = process_geometry_file(uploaded_files=uploaded_files)
    k_label, kpoint, band_len, k_label_reduce, xvals, band_len_tot = process_control_file(uploaded_files=uploaded_files,
                                                                                          rlatvec=rlatvec)

    # Prepare the data for DataFrame
    df_dict = {}

    # Fill the DataFrame with energy levels and x-values
    for file_id, bands in enumerate(bands_all_files):
        for band_id, band in enumerate(bands):
            df_dict[f"X_{band_id}_File_{file_id}"] = xvals[file_id]
            df_dict[f"Y_{band_id}_File_{file_id}"] = band

    # Create DataFrame
    df = pd.DataFrame(df_dict)

    curve_dict = {}
    for file_id, bands in enumerate(bands_all_files):
        for band_id, band in enumerate(bands):
            key = f"Band_{band_id}_File_{file_id}"
            curve = hv.Curve((df[f"X_{band_id}_File_{file_id}"], df[f"Y_{band_id}_File_{file_id}"]), 'X', 'Y')
            curve.opts(line_width=special_line if band_id in orghomo or band_id in inorghomo or band_id in orglumo or band_id in inorglumo else black_bands)
            curve.opts(color='g' if band_id in orghomo else 'r' if band_id in inorghomo else 'b' if band_id in orglumo else 'r' if band_id in inorglumo else 'k')
            curve_dict[key] = curve

    ndoverlay = hv.NdOverlay(curve_dict)

    # Set options
    ndoverlay.opts(opts.Curve(width=800, height=600, tools=['hover']))

    p = hv.render(ndoverlay, backend='bokeh')

    # Add vertical lines at each k point
    for kpoint_x in band_len_tot[1:]:
        vline = Span(location=kpoint_x, dimension='width', line_color='black', line_dash='dashed', line_width=1)
        p.renderers.extend([vline])

    # Zero energy horizontal line
    hline = Span(location=0, dimension='height', line_color='black', line_dash='dashed', line_width=1)
    p.renderers.extend([hline])

    # Update y axis
    p.y_range.start = ymin
    p.y_range.end = ymax

    # Update x axis
    p.xaxis.ticker = band_len_tot
    p.xaxis.major_label_overrides = dict(zip(band_len_tot, k_label_reduce))

    st.bokeh_chart(p)


def filter_state_data(filename, target_state):
    # Read the file
    df = pd.read_csv(filename, delim_whitespace=True, comment='#', header=None)

    # Assign column names
    column_names = ['k_point', 'kx', 'ky', 'kz', 'State', 'Eigenvalue', 'sigma_x', 'sigma_y', 'sigma_z']
    df.columns = column_names

    # Filter rows by target_state
    filtered_df = df[df['State'] == target_state]

    # Drop the 'State' column as it's constant
    filtered_df.drop('State', axis=1, inplace=True)

    # Reset index for aesthetics
    filtered_df.reset_index(drop=True, inplace=True)

    return filtered_df
