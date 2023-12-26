import pandas as pd
import os
import glob
import re
import streamlit as st
import subprocess
import shutil
import zipfile
import shutil
from MDAnalysis import Universe
from MDAnalysis.coordinates.memory import MemoryReader
from MDAnalysis.analysis.hydrogenbonds.hbond_analysis import HydrogenBondAnalysis as HBA
from MDAnalysis.analysis import hbonds
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import collections
from MDAnalysis.analysis import distances
import matplotlib.cm as cm
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
from io import BytesIO
from ase.io import read
import MDAnalysis as mda
import numpy as np
from ase import Atoms
from MDAnalysis.analysis import align
from MDAnalysis.transformations import positionaveraging
from MDAnalysis.transformations import nojump
from MDAnalysis.analysis.rdf import InterRDF, InterRDF_s

def try_float_conversion(value):
    try:
        return float(value)
    except ValueError:
        print(f"Error: Unable to convert '{value}' to float.")
        return None

def extract_MD_status(lines, idx, prev_TE):
    idx += 2  # Skip two lines
    time = try_float_conversion(lines[idx].decode().split(':')[1].strip().split()[0])
    idx += 1
    FE = try_float_conversion(lines[idx].decode().split(':')[1].strip().split()[0])
    idx += 1
    T = try_float_conversion(lines[idx].decode().split(':')[1].strip().split()[0])
    idx += 1
    KE = try_float_conversion(lines[idx].decode().split(':')[1].strip().split()[0])
    idx += 1
    TE = try_float_conversion(lines[idx].decode().split(':')[1].strip().split()[0])
    idx += 1
    H = try_float_conversion(lines[idx].decode().split(':')[1].strip().split()[0])

    TE_change = TE - prev_TE if prev_TE is not None else 0.0

    row = {"Time [ps]": time, "Temperature [K]": T, "E_tot (electronic) [eV]": FE, "E_kin (nuclei) [eV]": KE,
           "Total Energy [eV]": TE, "Total Energy Change [eV]": TE_change, "Conserved_Hamiltonian [eV]": H}

    return idx, row, TE


def sort_files(directory):
    # Use glob to get all the file paths
    files = glob.glob(os.path.join(directory, 'slurm-*.out'))

    # Extract the numbers from the file names and sort by these numbers
    files.sort(key=lambda x: int(re.findall(r'\d+', os.path.basename(x))[0]))
    return files



def extract_data_from_stream(stream, prev_TE=None):
    data = []
    lines = stream.readlines()

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if not line.startswith(b'#'):
            if b'Initial conditions for Born-Oppenheimer Molecular Dynamics:' in line:
                idx, row, prev_TE = extract_MD_status(lines, idx, prev_TE)
                data.append(row)
            elif b'Advancing structure using Born-Oppenheimer Molecular Dynamics' in line:
                idx += 1  # Skip one line
                idx, row, prev_TE = extract_MD_status(lines, idx, prev_TE)
                data.append(row)
        idx += 1

    return data, prev_TE

def process_streams(streams):
    all_data = []
    prev_TE = None

    # Create a list of tuples, each containing a file name and a file-like object
    files = [(stream.name, stream) for stream in streams]

    # Sort the list of tuples based on the file names
    files.sort(key=lambda x: int(re.findall(r'\d+', x[0])[0]))

    for _, stream in files:
        data, prev_TE = extract_data_from_stream(stream, prev_TE)
        all_data.extend(data)

    return pd.DataFrame(all_data)


import plotly.graph_objects as go
from plotly.subplots import make_subplots

def generate_layout(title='Time vs. Temperature', xaxis_title='Time [ps]', yaxis_title='Temperature [K]', font_size=16, color_text='black', l_orientation = 'h', l_yplace=0.2):
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
            'mirror': True,
            'ticks': 'outside'
            # 'showline': True
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



def plot_data(df):
    color_text = 'black'  # Black color
    font_size = 26  # You can adjust the size based on your preference
    # Create 2x2 grid using Streamlit's column feature
    col1, col_space, col2 = st.columns([1, 0.1, 1])
    # col1, col2 = st.columns(2)
    col3, col_space, col4 = st.columns([1, 0.1, 1])

    # Define colors
    color_line = "gold"
    color_dash = "darkblue"


    # Time vs. Temperature
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=df["Time [ps]"], y=df["Temperature [K]"], mode='lines', name='Temperature',
                              line=dict(color=color_line)))
    fig1.add_trace(go.Scatter(x=df["Time [ps]"], y=[df["Temperature [K]"].mean()] * len(df["Time [ps]"]), mode='lines',
                              name='Average Temp.', line=dict(dash='dash', color=color_dash)))
    fig1.update_layout(**generate_layout(title='Time vs. Temperature', xaxis_title='Time [ps]', yaxis_title='Temperature [K]'))

    col1.plotly_chart(fig1)

    # Time vs. Total Energy
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df["Time [ps]"], y=df["Total Energy [eV]"], mode='lines', name='Total Energy',
                              line=dict(color=color_line)))
    fig2.add_trace(go.Scatter(x=df["Time [ps]"], y=df["Total Energy [eV]"].rolling(window=100).mean(), mode='lines',
                              name='Moving Average (100 points)', line=dict(dash='dash', color=color_dash)))
    fig2.update_layout(**generate_layout(title='Time vs. Total Energy', xaxis_title='Time [ps]', yaxis_title='Total Energy [eV]'))
    fig2.update_layout(yaxis=dict(tickformat=".6e"))
    col2.plotly_chart(fig2)

    # Time vs. Total Energy Change
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=df["Time [ps]"], y=df["Total Energy Change [eV]"], mode='lines', name='Total Energy Change', line=dict(color=color_line)))
    fig3.add_trace(go.Scatter(x=df["Time [ps]"], y=df["Total Energy Change [eV]"].rolling(window=100).mean(), mode='lines', name='Moving Average (100 points)', line=dict(dash='dash', color=color_dash)))
    fig3.update_layout(**generate_layout(title='Time vs. Total Energy Change', xaxis_title='Time [ps]', yaxis_title='Total Energy Change [eV]'))
    col3.plotly_chart(fig3)

    # Time vs. Conserved Hamiltonian
    fig4 = go.Figure()
    fig4.add_trace(
        go.Scatter(x=df["Time [ps]"], y=df["Conserved_Hamiltonian [eV]"], mode='lines', name='Conserved Hamiltonian',
                   line=dict(color=color_line)))
    fig4.add_trace(
        go.Scatter(x=df["Time [ps]"], y=df["Conserved_Hamiltonian [eV]"].rolling(window=100).mean(), mode='lines',
                   name='Moving Average (100 points)', line=dict(dash='dash', color=color_dash)))
    fig4.update_layout(**generate_layout(title='Time vs. Conserved Hamiltonian', xaxis_title='Time [ps]', yaxis_title='Cons. H [eV]'))
    fig4.update_layout(yaxis=dict(tickformat=".6e"))
    col4.plotly_chart(fig4)

import tempfile
from pathlib import Path
import base64
import re
from natsort import natsorted


def run_perl_script(input_files):
    perl_script_path = './create_geometry_zip.pl'
    joined_file_name = 'joined_file.out'
    # second_perl_script_path = './create_xyz_movie.pl'
    # output_file_name = 'create_xyz_movie_output'

    # Create a new file by joining all input files in natural order
    input_files = natsorted(input_files, key=lambda x: x.name)

    # Define pattern for the line to start from in subsequent files
    start_line_pattern = " Advancing structure using Born-Oppenheimer Molecular Dynamics:"

    with open(joined_file_name, 'wb') as outfile:
        for i, file in enumerate(input_files):
            # If it's not the first file, find the first mention of the line and discard information before that
            if i != 0:
                start_line_found = False
                for line in file.getvalue().decode().split('\n'):
                    if line.strip():  # Ignore empty or blank lines
                        if start_line_pattern in line:
                            start_line_found = True
                        if start_line_found:
                            outfile.write((line + '\n').encode())
            else:
                # If it's the first file, write it entirely
                outfile.write(file.getbuffer())

    # call the perl script with the new joined file
    process = subprocess.Popen(['perl', perl_script_path, joined_file_name], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)

    # Prepare markdown display
    markdown_display = st.empty()
    markdown_output = ""

    # Stream output to Streamlit as it's generated
    for line in iter(process.stdout.readline, b''):
        # Append to markdown_output string
        markdown_output += line.decode().replace(" ", "\n") + "\n"
        # Update markdown display
        markdown_display.markdown(f'<div style="height:200px; text-align: center; width:50%; overflow:auto; background-color:#333333; color:#FFFFFF; border-radius:10px; padding: 0px;"><pre>{markdown_output}</pre></div>', unsafe_allow_html=True)

    # Ensure all output has been read after the subprocess stops
    process.communicate()

    return Path('geometries.zip'), Path('geometries.spt')



def get_download_link_md(file_path, download_name):
    with open(file_path, "rb") as file:
        bytes = file.read()
        b64 = base64.b64encode(bytes).decode()
        href = f'<a href="data:file/octet-stream;base64,{b64}" download="{download_name}">Download {download_name}</a>'
        return href

from ase.io import read, write

# Function to build Universe from directory of frames
# Updated build_universe_from_dir function to handle subdirectories
def build_universe_from_dir(directory, timestep):
    # Get a sorted list of all frame files in the directory
    frame_files = sorted(glob.glob(os.path.join(directory, '**', 'geometry*.in'), recursive=True))

    for f in frame_files:
        atoms_compare = read(f)
        # Rewrite the file with the new positions
        write(f, atoms_compare, format='aims')

    # If no frame files found, raise an exception
    if not frame_files:
        raise Exception(f"No 'geometry*.in' files found in directory: {directory}")

    # Read the unit cell dimensions from the first geometry file
    ase_atoms = read(frame_files[0])
    unit_cell_dimensions = list(ase_atoms.cell.cellpar())  # [a, b, c, alpha, beta, gamma]

    # Initialize a Universe with the first frame
    u = Universe(frame_files[0])

    # Placeholder for the positions from all frames
    all_positions = []

    # Loop over the remaining frame files
    for frame_file in frame_files[1:]:
        # Initialize a temporary Universe with this frame
        temp_u = Universe(frame_file)

        # Add the positions from this frame to all_positions
        all_positions.append(temp_u.atoms.positions)

    # Add the remaining frames to the Universe
    u.load_new(np.array(all_positions), format=MemoryReader, dimensions=unit_cell_dimensions)

    #Add timestep info
    u.trajectory.ts.dt = timestep
    # u.dimensions = unit_cell_dimensions

    transformation = nojump.NoJump()
    u.trajectory.add_transformations(transformation)     # Useful for the hydrogens

    return u

# Function to perform hydrogen bond analysis
def hydrogen_bond_analysis(u, donor_atom, acceptor_atom, da_cutoff, angle_cutoff):
    #Info from the API doc:
    # donors_sel(str) – Selection string for the hydrogen bond donor atoms.If the universe topology contains bonding information,
    # leave donors_sel as None so that donor-hydrogen pairs can be correctly identified.
    # hydrogens_sel(str) – Selection string for the hydrogen bond hydrogen atoms.Leave as None to guess which hydrogens to use
    # in the analysis using guess_hydrogens.If hydrogens_sel is left as None, also leave donors_sel as None so that donor-hydrogen pairs can be correctly identified.
    # acceptors_sel(str) – Selection string
    # for the hydrogen bond acceptor atoms.Leave as None to guess which atoms to use in the analysis using guess_acceptors


    # Instantiate HydrogenBondAnalysis object
    h = HBA(u, donors_sel=f'name {donor_atom}',
            hydrogens_sel='name H',
            acceptors_sel=f'name {acceptor_atom}',
            d_a_cutoff=da_cutoff,
            d_h_a_angle_cutoff=angle_cutoff,
            update_selections=False)

    # Run the analysis
    h.run(verbose=True)

    # # Get times
    # times = [ts.time for ts in u.trajectory]

    # Return the result table
    return h.results



def select_atoms(u, atom_name):
    return u.select_atoms(f'name {atom_name}')


def compute_min_distances_and_indices(u, atoms1, atoms2):
    min_distances = []
    min_indices_atoms1 = []
    min_indices_atoms2 = []
    times = []

    for ts in u.trajectory:
        d = distances.distance_array(atoms1.positions, atoms2.positions, box=list(u.dimensions))
        times.append(u.trajectory.ts.time)
        min_distance = np.min(d, axis=1)
        min_distances.append(min_distance)

        local_min_indices_atoms2 = np.argmin(d, axis=1)
        local_min_indices_atoms1 = np.arange(len(atoms1))

        global_min_indices_atoms2 = atoms2.indices[local_min_indices_atoms2]
        global_min_indices_atoms1 = atoms1.indices[local_min_indices_atoms1]

        min_indices_atoms1.append(global_min_indices_atoms1)
        min_indices_atoms2.append(global_min_indices_atoms2)

    return np.array(times), np.array(min_distances), np.array(min_indices_atoms1), np.array(min_indices_atoms2)


def plot_distances(times, min_distances, atom1, atom2, standard_distance):
    fig = go.Figure()

    for i in range(min_distances.shape[1]):
        fig.add_trace(go.Scatter(x=times, y=min_distances[:, i], mode='lines',
                                 name=f'{atom1}-{atom2} pair {i + 1}', showlegend=True))

    # Only add shaded region and dashed line if standard_distance is not 0
    if standard_distance > 0:
        # Add shaded region below the standard_distance to 0 on y-axis
        fig.add_shape(
            go.layout.Shape(
                type="rect",
                xref="x",
                yref="y",
                x0=times[0],
                x1=times[-1],
                y0=0,
                y1=standard_distance,
                fillcolor="lightpink",
                opacity=0.3,
                layer="below"
            )
        )

        # Add dashed line at standard_distance
        fig.add_shape(
            go.layout.Shape(
                type="line",
                xref="x",
                yref="y",
                x0=times[0],
                x1=times[-1],
                y0=standard_distance,
                y1=standard_distance,
                line=dict(dash="dash")
            )
        )


    fig.update_layout(**generate_layout(title=f'{atom1} and {atom2} Distances', xaxis_title='Time [ps]', yaxis_title='Distance (Å)', font_size=16, color_text='black'))
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.00, xanchor="left", x=0),
    xaxis=dict(mirror=False))
    return fig

def plot_and_return_min_distances(u, atom1, atom2, standard_distance):
    atoms1 = select_atoms(u, atom1)
    atoms2 = select_atoms(u, atom2)
    times, min_distances, min_indices_atoms1, min_indices_atoms2 = compute_min_distances_and_indices(u, atoms1, atoms2)
    fig = plot_distances(times, min_distances, atom1, atom2, standard_distance)

    return fig, min_distances_to_dataframe(times, min_distances, min_indices_atoms1, min_indices_atoms2, atoms1, atoms2, atom1, atom2)

def min_distances_to_dataframe(times, min_distances, min_indices_atoms1, min_indices_atoms2, atoms1, atoms2, atom1_name, atom2_name):
    # Flatten the data and prepare for dataframe
    frames = np.repeat(times, min_distances.shape[1])
    distances_flat = min_distances.flatten()
    atom1_indices = min_indices_atoms1.flatten()
    atom2_indices = min_indices_atoms2.flatten()

    data = {
        'Frame Time': frames,
        f'{atom1_name} Index': atom1_indices,
        f'{atom2_name} Index': atom2_indices,
        'Min Distance': distances_flat
    }
    return pd.DataFrame(data)


def generate_weighted_pair_probability_heatmap(df):
    unique_indices_1 = sorted(df[f'{df.columns[1]}'].unique())
    unique_indices_2 = sorted(df[f'{df.columns[2]}'].unique())

    # Initialize matrices for frequency and distance summation
    freq_matrix = np.zeros((len(unique_indices_1), len(unique_indices_2)))
    distance_sum_matrix = np.zeros_like(freq_matrix)

    # Populate the frequency and distance summation matrices
    for _, row in df.iterrows():
        i = unique_indices_1.index(row[f'{df.columns[1]}'])
        j = unique_indices_2.index(row[f'{df.columns[2]}'])
        freq_matrix[i, j] += 1
        distance_sum_matrix[i, j] += row['Min Distance']

    # Compute average distance matrix, handle divide by zero cases
    with np.errstate(divide='ignore', invalid='ignore'):
        avg_distance_matrix = distance_sum_matrix / freq_matrix
        avg_distance_matrix[freq_matrix == 0] = 0

    # Normalize the matrix to get probabilities
    prob_matrix = freq_matrix / freq_matrix.sum()

    # Weight the probabilities by the inverse of the average distance
    with np.errstate(divide='ignore', invalid='ignore'):
        weighted_prob_matrix = prob_matrix / avg_distance_matrix
        weighted_prob_matrix[np.isnan(weighted_prob_matrix)] = 0

    # Normalize the weighted matrix to ensure values are between 0 and 1
    weighted_prob_matrix = weighted_prob_matrix / weighted_prob_matrix.max()

    # Apply Gaussian filter for smoothing
    smoothed_matrix = gaussian_filter(weighted_prob_matrix, sigma=1)

    # Create the figure and the axes for plotting
    fig, ax = plt.subplots(figsize=(12, 10))

    sns.heatmap(smoothed_matrix, cmap='YlGnBu', cbar_kws={'label': 'Weighted Probability'},
                xticklabels=unique_indices_2, yticklabels=unique_indices_1, ax=ax)

    ax.set_title("Weighted Pair Formation Probability by Average Distance")
    ax.set_ylabel(f"{df.columns[1]} (Atom Index)")
    ax.set_xlabel(f"{df.columns[2]} (Atom Index)")

    return fig


def generate_weighted_pair_probability_heatmap_plotly(df):
    color_text = 'black'  # Black color
    font_size = 16  # You can adjust the size based on your preference
    # Extract unique atom indices
    unique_indices_1 = sorted(df[f'{df.columns[1]}'].unique())
    unique_indices_2 = sorted(df[f'{df.columns[2]}'].unique())

    # Initialize matrices for frequency and distance summation
    freq_matrix = np.zeros((len(unique_indices_1), len(unique_indices_2)))
    distance_sum_matrix = np.zeros_like(freq_matrix)

    # Populate the frequency and distance summation matrices
    for _, row in df.iterrows():
        i = unique_indices_1.index(row[f'{df.columns[1]}'])
        j = unique_indices_2.index(row[f'{df.columns[2]}'])
        freq_matrix[i, j] += 1
        distance_sum_matrix[i, j] += row['Min Distance']

    # Compute average distance matrix, handle divide by zero cases
    with np.errstate(divide='ignore', invalid='ignore'):
        avg_distance_matrix = distance_sum_matrix / freq_matrix
        avg_distance_matrix[freq_matrix == 0] = 0

    # Normalize the matrix to get probabilities
    prob_matrix = freq_matrix / freq_matrix.sum()

    # Weight the probabilities by the inverse of the average distance
    with np.errstate(divide='ignore', invalid='ignore'):
        weighted_prob_matrix = prob_matrix / avg_distance_matrix
        weighted_prob_matrix[np.isnan(weighted_prob_matrix)] = 0

    # Normalize the weighted matrix to ensure values are between 0 and 1
    weighted_prob_matrix = weighted_prob_matrix / weighted_prob_matrix.max()

    # Apply Gaussian filter for smoothing
    smoothed_matrix = gaussian_filter(weighted_prob_matrix, sigma=0.1)

    # Create interactive heatmap using Plotly
    fig = go.Figure(data=go.Heatmap(
        z=smoothed_matrix,
        x=unique_indices_2,
        y=unique_indices_1,
        colorscale='YlGnBu',
        colorbar=dict(title='Weighted Probability')
    ))

    fig.update_layout(
        title="Weighted Pair Formation Probability by Average Distance",
        xaxis_title=f"{df.columns[2]}",
        yaxis_title=f"{df.columns[1]}",
        xaxis=dict(
            tickfont=dict(size=font_size, color=color_text),
            title_font=dict(size=font_size, color=color_text)
        ),
        yaxis=dict(
            tickfont=dict(size=font_size, color=color_text),
            title_font=dict(size=font_size, color=color_text)
        )
    )

    return fig


def plot_hbond_data(h, u):
    # Extract frame numbers, H-bond distances, and H-bond angles
    frame_numbers = h.hbonds[:, 0]
    hbond_distances = h.hbonds[:, 4]
    hbond_angles = h.hbonds[:, 5]

    # Get unique frame numbers and their corresponding times from u
    unique_frame_numbers = np.unique(frame_numbers)
    times_for_unique_frames = [u.trajectory[int(f)].time for f in unique_frame_numbers]

    # Create a mapping dictionary for frame to its corresponding time
    frame_to_time = dict(zip(unique_frame_numbers, times_for_unique_frames))

    # Use the mapping to get the time for each frame number in the data
    time_column = [frame_to_time[f] for f in frame_numbers]


    # Create DataFrames for distances and angles
    df_distances = pd.DataFrame({
        'Time': time_column,
        'Distance': hbond_distances
    })

    df_angles = pd.DataFrame({
        'Time': time_column,
        'Angle': hbond_angles
    })

    # Generate a random color for each unique time
    base_colors = px.colors.qualitative.Plotly
    num_frames = len(df_distances['Time'].unique())
    colors = (base_colors * (num_frames // len(base_colors) + 1))[:num_frames]
    color_dict = dict(zip(df_distances['Time'].unique(), colors))

    # Create plotly figure for distances
    fig_distances = go.Figure()

    for time in df_distances['Time'].unique():
        df_time = df_distances[df_distances['Time'] == time]
        fig_distances.add_trace(go.Scatter(
            x=df_time['Time'],
            y=df_time['Distance'],
            mode='markers',
            marker=dict(size=5, color=color_dict[time]),
            name=f'Time {time:.3f} ps'
        ))


    fig_distances.update_layout(title='H-bond Distances over Time',
                                xaxis_title='Time (ps)',
                                yaxis_title='H-bond Distance (Å)',
                                # autosize=False,
                                # width=800,
                                # height=500,
                                showlegend=False,
                                xaxis=dict(
                                    titlefont=dict(size=14, color='black', family="Arial, bold"),
                                    tickfont=dict(size=12, color='black', family="Arial, bold")
                                ),
                                yaxis=dict(
                                    titlefont=dict(size=14, color='black', family="Arial, bold"),
                                    tickfont=dict(size=12, color='black', family="Arial, bold")
                                )
                                )

    # Create plotly figure for angles
    fig_angles = go.Figure()

    for time in df_angles['Time'].unique():
        df_time = df_angles[df_angles['Time'] == time]
        fig_angles.add_trace(go.Scatter(
            x=df_time['Time'],
            y=df_time['Angle'],
            mode='markers',
            marker=dict(size=5, color=color_dict[time]),
            name=f'Time {time:.3f} ps'
        ))

    fig_angles.update_layout(title='H-bond Angles over Time',
                             xaxis_title='Time (ps)',
                             yaxis_title='H-bond Angle (Degrees)',
                             # autosize=False,
                             # width=800,
                             # height=500,
                             showlegend=False,
                             xaxis=dict(
                                 titlefont=dict(size=14, color='black', family="Arial, bold"),
                                 tickfont=dict(size=12, color='black', family="Arial, bold")
                             ),
                             yaxis=dict(
                                 titlefont=dict(size=14, color='black', family="Arial, bold"),
                                 tickfont=dict(size=12, color='black', family="Arial, bold")
                             )
                             )

    # Calculate the number of H-bonds for each unique time point
    hbond_counts = df_distances.groupby('Time').size().reset_index(name='Count')

    # Create scatter plot for number of H-bonds in each frame
    fig_hbond_counts = go.Figure(go.Scatter(
        x=hbond_counts['Time'],
        y=hbond_counts['Count'],
        mode='lines+markers',
        marker=dict(size=10,color=colors[:len(hbond_counts)]),
        line=dict(color='black')
    ))

    fig_hbond_counts.update_layout(title='Number of H-bonds over Time',
                                   xaxis_title='Time (ps)',
                                   yaxis_title='Number of H-bonds',
                                   # autosize=False,
                                   # width=800,
                                   # height=500,
                                   showlegend=False,
                                   xaxis=dict(
                                       titlefont=dict(size=14, color='black', family="Arial, bold"),
                                       tickfont=dict(size=12, color='black', family="Arial, bold")
                                   ),
                                   yaxis=dict(
                                       titlefont=dict(size=14, color='black', family="Arial, bold"),
                                       tickfont=dict(size=12, color='black', family="Arial, bold")
                                   )
                                   )

    return fig_distances, fig_angles, fig_hbond_counts

def get_figure_image_download_link(fig, filename="heatmap.png", text="Download Heatmap as PNG"):
    """
    Generate a link to download the given matplotlib figure.
    """
    buffered = BytesIO()
    fig.savefig(buffered, format="PNG", bbox_inches='tight')
    img_str = base64.b64encode(buffered.getvalue()).decode()
    href = f'<a href="data:image/png;base64,{img_str}" download="{filename}">{text}</a>'
    return href


# def plot_atom_distances_over_time(u, standard_distance=0, *atom_pairs, start_time=0):
#     """
#     Plots the distance between pairs of atoms over time.
#
#     Parameters:
#     - u: MDAnalysis universe
#     - y_value: The y-axis value for the horizontal dashed line (default 0)
#     - *atom_pairs: Variable number of atom pairs as tuples (atom_index1, atom_index2)
#
#     Returns:
#     - A Plotly Figure object representing the plot.
#     """
#
#     fig = go.Figure()
#
#     for atom_pair in atom_pairs:
#         atom_index1, atom_index2 = atom_pair
#
#         # Select the atoms based on their indices
#         atom1 = u.atoms[atom_index1]
#         atom2 = u.atoms[atom_index2]
#
#         # Retrieve the element symbols
#         symbol1 = atom1.name
#         symbol2 = atom2.name
#
#         # Compute the distances over time
#         times = []
#         distances_ar = []
#         for ts in u.trajectory:
#             if ts.time > start_time:
#                 times.append(ts.time)
#                 # take care of the periodic images!
#                 d = distances.distance_array(atom1.position, atom2.position, box=list(u.dimensions))
#                 distances_ar.append(d[0][0])
#
#         # Add a trace for each pair to the plot
#         trace_name = f'{symbol1}_{atom_index1} - {symbol2}_{atom_index2}'
#         fig.add_trace(go.Scatter(x=times, y=distances_ar, mode='lines',
#                                  name=trace_name))
#
#     if standard_distance > 0:
#         # Add shaded region below the standard_distance to 0 on y-axis
#         fig.add_shape(
#             go.layout.Shape(
#                 type="rect",
#                 xref="x",
#                 yref="y",
#                 x0=times[0],
#                 x1=times[-1],
#                 y0=0,
#                 y1=standard_distance,
#                 fillcolor="lightpink",
#                 opacity=0.3,
#                 layer="below"
#             )
#         )
#
#         # Add dashed line at standard_distance
#         fig.add_shape(
#             go.layout.Shape(
#                 type="line",
#                 xref="x",
#                 yref="y",
#                 x0=times[0],
#                 x1=times[-1],
#                 y0=standard_distance,
#                 y1=standard_distance,
#                 line=dict(dash="dash")
#             )
#         )
#
#     fig.update_layout(**generate_layout(title='Distances between Atom Pairs over Time', xaxis_title='Time [ps]', yaxis_title='Distance (Å)', font_size=16, color_text='black'))
#
#     return fig


def plot_atom_distances_over_time(u, standard_distance=0, *atom_pairs, start_time=0, end_time=None):
    """
    Plots the distance between pairs of atoms over time and returns a Plotly Figure object and a DataFrame.

    Parameters:
    - u: MDAnalysis universe
    - standard_distance: The y-axis value for the horizontal dashed line (default 0)
    - *atom_pairs: Variable number of atom pairs as tuples (atom_index1, atom_index2)

    Returns:
    - A Plotly Figure object representing the plot.
    - A Pandas DataFrame with time and distance values for each atom pair.
    """

    fig = go.Figure()
    data_list = []

    for atom_pair in atom_pairs:
        atom_index1, atom_index2 = atom_pair

        # Select the atoms based on their indices
        atom1 = u.atoms[atom_index1]
        atom2 = u.atoms[atom_index2]

        # Retrieve the element symbols
        symbol1 = atom1.name
        symbol2 = atom2.name

        if end_time is None:
            end_time = u.trajectory[-1].time
        else:
            end_time = end_time

        # transformation = nojump.NoJump()
        # u.trajectory.add_transformations(transformation)

        # Compute the distances over time
        for ts in u.trajectory:
            if ts.time > start_time and ts.time < end_time:
                d = distances.distance_array(atom1.position, atom2.position, box=list(u.dimensions))
                # d = distances.distance_array(atom1.position, atom2.position)
                data_list.append({'Time': ts.time,
                                  f'{symbol1}_{atom_index1 + 1} - {symbol2}_{atom_index2 + 1}': d[0][0]})

        # Add a trace for each pair to the plot
        trace_name = f'{symbol1}_{atom_index1 + 1} - {symbol2}_{atom_index2 + 1}'
        fig.add_trace(go.Scatter(x=[data['Time'] for data in data_list if trace_name in data],
                                 y=[data[trace_name] for data in data_list if trace_name in data],
                                 mode='lines', name=trace_name))

    if standard_distance > 0:
        # Add shaded region below the standard_distance to 0 on y-axis
        fig.add_shape(
            go.layout.Shape(
                type="rect",
                xref="x",
                yref="y",
                x0=times[0],
                x1=times[-1],
                y0=0,
                y1=standard_distance,
                fillcolor="lightpink",
                opacity=0.3,
                layer="below"
            )
        )

        # Add dashed line at standard_distance
        fig.add_shape(
            go.layout.Shape(
                type="line",
                xref="x",
                yref="y",
                x0=times[0],
                x1=times[-1],
                y0=standard_distance,
                y1=standard_distance,
                line=dict(dash="dash")
            )
        )

    fig.update_layout(**generate_layout(title='Distances between Atom Pairs over Time', xaxis_title='Time [ps]', yaxis_title='Distance (Å)', font_size=16, color_text='black'))

    # Create DataFrame
    df = pd.DataFrame(data_list)
    df = df.groupby('Time').first().reset_index()

    return fig, df

def plot_atom_distances_over_time_matplotlib(u, standard_distance=0, *atom_pairs, start_time=0):
    """
    Plots the distance between pairs of atoms over time using Matplotlib.

    Parameters:
    - u: MDAnalysis universe
    - standard_distance: The y-axis value for the horizontal dashed line (default 0)
    - *atom_pairs: Variable number of atom pairs as tuples (atom_index1, atom_index2)

    Returns:
    - A Matplotlib Figure object representing the plot.
    """

    fig, ax = plt.subplots()

    for atom_pair in atom_pairs:
        atom_index1, atom_index2 = atom_pair

        # Select the atoms based on their indices
        atom1 = u.atoms[atom_index1]
        atom2 = u.atoms[atom_index2]

        # Retrieve the element symbols
        symbol1 = atom1.name
        symbol2 = atom2.name

        # Compute the distances over time
        times = []
        distances_ar = []
        for ts in u.trajectory:
            if ts.time > start_time:
                times.append(ts.time)
                d = distances.distance_array(atom1.position, atom2.position, box=list(u.dimensions))
                distances_ar.append(d[0][0])

        # Plot for each pair
        trace_name = f'{symbol1}_{atom_index1} - {symbol2}_{atom_index2}'
        ax.plot(times, distances_ar, label=trace_name)

    if standard_distance > 0:
        # Add shaded region below the standard_distance to 0 on y-axis
        ax.fill_between(times, 0, standard_distance, color='lightpink', alpha=0.3)

        # Add dashed line at standard_distance
        ax.axhline(y=standard_distance, color='grey', linestyle='--')

    # Setting the plot layout
    ax.set_title('Distances between Atom Pairs over Time')
    ax.set_xlabel('Time [ps]')
    ax.set_ylabel('Distance (Å)')
    ax.legend()

    return fig


def average_structure_to_cif(u, start_time, filename="average_structure.in"):
    # Extract positions and times from the original universe
    positions = [ts.positions for ts in u.trajectory]
    times = [ts.time for ts in u.trajectory]

    # Create a new trajectory starting from the given start_time
    start_index = next(i for i, time in enumerate(times) if time >= start_time)
    new_trajectory_positions = positions[start_index:]

    # Create a new universe with the modified trajectory
    new_u = mda.Universe.empty(n_atoms=len(u.atoms), trajectory=True)
    new_u.load_new(new_trajectory_positions)

    # Get average structure using the new universe
    average_universe = align.AverageStructure(new_u, strict=True, ref_frame=3).run()
    average_positions = average_universe.results.positions

    # Get cell params
    cell_params = u.dimensions

    # Extracting symbols from MDAnalysis universe
    symbols = [atom.name for atom in u.atoms]

    # Convert the MDAnalysis average structure to an ASE Atoms object
    ase_atoms = Atoms(symbols=symbols, positions=average_positions)

    # Set cell dimensions
    if cell_params is not None:
        ase_atoms.set_cell(cell_params[:3])
        ase_atoms.set_pbc([True, True, True])  # Assuming periodic boundary conditions

    # Write to a CIF file
    ase_atoms.write(filename, format='aims')

    return filename


def calculate_rdf_mda(u, atom1, atom2, bins=75, range=(0, 15.0), time_range=None):
    """
    Calculate the radial distribution function (RDF) using MDAnalysis's built-in InterRDF method.

    Parameters:
    - u: Universe object
    - atom1: Name of the first atom type
    - atom2: Name of the second atom type
    - bins: Number of bins for the histogram (default is 75)
    - range: Lower and upper range of the bins (default is (0, 15.0))
    - start: Start frame for analysis
    - stop: Stop frame for analysis
    - step: Number of frames to skip between each analyzed frame
    - verbose: Turn on verbosity

    Returns:
    - A Pandas DataFrame containing the RDF data
    """

    start_time_ps = time_range[0]
    end_time_ps = time_range[1]

    # Calculate frame indices
    start_frame = int(start_time_ps / u.trajectory.dt)
    end_frame = int(end_time_ps / u.trajectory.dt)

    # Select atoms based on type
    atoms1 = select_atoms(u, atom1)
    atoms2 = select_atoms(u, atom2)

    # Initialize InterRDF object
    rdf = InterRDF(atoms1, atoms2, nbins=bins, range=range)

    # Run RDF calculation
    rdf.run(start=start_frame, stop=end_frame)

    # Convert to DataFrame for convenient handling
    rdf_data = pd.DataFrame({
        'r': rdf.bins,
        'g(r)': rdf.rdf
    })

    return rdf_data

def site_specific_rdf(u, ags, bins=75, range=(0.0, 15.0), density=True, time_range=None):
    """
    Plot the site-specific radial distribution function using MDAnalysis's InterRDF_s.

    Parameters:
    - u: MDAnalysis Universe object
    - ags: List of pairs of AtomGroup instances
    - bins (optional): Number of bins in histogram [default: 75]
    - range (optional): The size of the RDF [default: (0.0, 15.0)]
    - density (optional): If True, calculates the density. If False, calculates the rdf [default: True]

    Returns:
    - A matplotlib figure and axis objects
    """

    start_time_ps = time_range[0]
    end_time_ps = time_range[1]

    # Calculate frame indices
    start_frame = int(start_time_ps / u.trajectory.dt)
    end_frame = int(end_time_ps / u.trajectory.dt)

    # Compute the site-specific RDF
    rdf_analysis = InterRDF_s(u, ags, nbins=bins, range=range, density=density)
    rdf_analysis.run(start=start_frame, stop=end_frame)

    return rdf_analysis

def plot_rdf(rdf_df):
    """
    Create a plot of r (distance) vs. g(r) using Plotly.

    Args:
    - rdf_df (pd.DataFrame): A dataframe with columns 'r' and 'g(r)'.

    Returns:
    - plotly.graph_objects.Figure: A Plotly figure object.
    """
    fig = px.line(rdf_df, x='r', y='g(r)')

    fig.update_layout(**generate_layout(title="Radial Distribution Function", xaxis_title='r (Å)',
                                        yaxis_title='g(r)', font_size=16, color_text='black', l_orientation='v',
                                        l_yplace=0.5))
    return fig


def rdf_to_dataframe(rdf, g_pairs=None):
    # Extracting bin values
    x_values = rdf.bins

    # Flattening the nested structure to get all atom combinations
    flattened = [atom_combination for pair in rdf.rdf for group in pair for atom_combination in group]

    # Creating a dictionary with atom pairs as keys and their values as the 1D arrays
    data_dict = {}
    flattened_index = 0
    if g_pairs:
        for ag1, ag2 in g_pairs:
            for atom1 in ag1:
                for atom2 in ag2:
                    header = f'{atom1.name}_{atom1.index + 1}-{atom2.name}_{atom2.index + 1}'
                    data_dict[header] = flattened[flattened_index]
                    flattened_index += 1
    else:
        for i in range(len(flattened)):
            data_dict[f'Pair_{i+1}'] = flattened[i]

    # Creating the DataFrame
    df = pd.DataFrame(data_dict, index=x_values)
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'Distance (Å)'}, inplace=True)

    return df

def plot_atom_pairs_rdf(df):
    fig = go.Figure()

    # Assuming the first column in df is 'Distance (Å)'
    distance_col = df['Distance (Å)']

    # Iterating over columns in the dataframe (excluding the distance column)
    for col in df.columns[1:]:
        fig.add_trace(go.Scatter(x=distance_col,
                                 y=df[col],
                                 mode='lines + markers',  # Set to markers for scatter plot
                                 marker=dict(symbol='square'),  # Square markers
                                 name=col))

    # Setting the layout attributes
    # Update generate_layout function call as per your implementation details
    fig.update_layout(**generate_layout(title="Radial Distribution Function",
                                        xaxis_title='r (Å)',
                                        yaxis_title='g(r)',
                                        font_size=16,
                                        color_text='black',
                                        l_orientation='v',
                                        l_yplace=0.5))

    return fig

def get_atom_frame_positions_dataframe(universe, start_frame=None):
    """
    Extracts the positions of each atom for each frame from an MDAnalysis Universe,
    and returns them as a Pandas DataFrame.

    Parameters:
    - universe: MDAnalysis.Universe object
    - start_frame: The starting frame index to consider (optional)

    Returns:
    - Pandas DataFrame containing the positions
    """

    # Initialize an empty list to hold the DataFrame records
    records = []

    # Loop through all atoms in the universe
    for atom_index, atom in enumerate(universe.atoms):

        # Loop through each frame in the trajectory
        for frame_index, ts in enumerate(universe.trajectory):

            # Skip frames before the start_frame, if specified
            if start_frame is not None and frame_index < start_frame:
                continue

            # Get atom's position
            x, y, z = atom.position

            # Append a record for this atom and frame
            records.append({
                "atom_index": atom_index,
                "frame_index": frame_index,
                "x": x,
                "y": y,
                "z": z
            })

    # Create a DataFrame from the records
    df = pd.DataFrame(records)

    return df


def get_ADP(universe, df):
    """
    Calculate ADP (Anisotropic Displacement Parameters) for atoms from a DataFrame.

    Parameters:
    - universe: MDAnalysis Universe object containing atom information
    - df: Pandas DataFrame containing atom positions for each frame

    Returns:
    - DataFrame containing the ADP values and atom labels for each atom
    """
    # Initialize an empty DataFrame to store ADP values for all atoms
    adp_df = pd.DataFrame(columns=['Atom Label', 'U11', 'U22', 'U33', 'U23', 'U13', 'U12'])

    # Get unique atom indices
    atom_indices = df['atom_index'].unique()

    # Loop through each unique atom index
    for at in atom_indices:

        # Get atom name from MDAnalysis universe and create label
        atom_name = universe.atoms[at].name
        atom_label = f"{atom_name}{at}"

        # Filter DataFrame to only include records for the current atom
        atom_df = df[df['atom_index'] == at]

        # Initialize variables for intermediate calculations
        U11_pre, U22_pre, U33_pre, U23_pre, U13_pre, U12_pre = 0, 0, 0, 0, 0, 0

        # Retrieve positions of a single atom across different frames
        single_atom_positions = atom_df[['x', 'y', 'z']].values

        # Calculate the mean position for the single atom
        single_atom_average = np.mean(single_atom_positions, axis=0)

        # Calculate pre-final values for the ADP components
        for pos in single_atom_positions:
            x, y, z = pos
            U11_pre += (x - single_atom_average[0]) ** 2
            U22_pre += (y - single_atom_average[1]) ** 2
            U33_pre += (z - single_atom_average[2]) ** 2
            U23_pre += (y - single_atom_average[1]) * (z - single_atom_average[2])
            U13_pre += (x - single_atom_average[0]) * (z - single_atom_average[2])
            U12_pre += (x - single_atom_average[0]) * (y - single_atom_average[1])

        # Finalize the ADP component values
        num_positions = len(single_atom_positions)
        U11, U22, U33 = U11_pre / num_positions, U22_pre / num_positions, U33_pre / num_positions
        U23, U13, U12 = U23_pre / num_positions, U13_pre / num_positions, U12_pre / num_positions

        # Append the ADP values and atom label for this atom to the master DataFrame
        adp_df.loc[at] = [atom_label, U11, U22, U33, U23, U13, U12]

    return adp_df


def calculate_ellipsoid_volumes(adp_df, ignore_atoms=None):
    """
    Add a column for ellipsoid volumes to the existing adp_df.

    Parameters:
    - adp_df: DataFrame containing ADP values and atom labels
    - ignore_atoms: List of atom symbols to ignore (Optional)

    Returns:
    - Modified adp_df containing a new 'Volume' column
    """

    # Initialize a new 'Volume' column with NaN values
    adp_df['Volume'] = np.nan

    # Loop through each row in the adp_df DataFrame
    for index, row in adp_df.iterrows():
        atom_label = row['Atom Label']

        # Extract atom name from the atom_label (assuming format is "<atom_name>_<atom_index>")
        atom_name = ''.join([char for char in atom_label if not char.isdigit()])

        # Skip atoms present in ignore_atoms list, if provided
        if ignore_atoms and atom_name in ignore_atoms:
            continue

        # Extract Uij values
        U11, U22, U33, U23, U13, U12 = row[['U11', 'U22', 'U33', 'U23', 'U13', 'U12']]

        # Calculate determinant of U-matrix
        U_matrix = np.array([[U11, U12, U13], [U12, U22, U23], [U13, U23, U33]])
        det_U = np.linalg.det(U_matrix)

        # Calculate ellipsoid volume
        volume = 4 / 3 * np.pi * np.sqrt(det_U)

        # Update 'Volume' column for the current atom
        adp_df.at[index, 'Volume'] = volume

    return adp_df


def plot_atom_volumes_violinplot(adp_df):
    """
    Create a violin plot for atom volumes using Plotly.

    Parameters:
    - adp_df: DataFrame containing ADP values, atom labels, and volumes

    Returns:
    - Plotly Figure object
    """

    # Extract unique atom types from Atom_Labels for plotting
    atom_types = adp_df['Atom Label'].apply(lambda x: ''.join([char for char in x if not char.isdigit()]))
    unique_atom_types = atom_types.unique()

    # Create an empty Plotly Figure object
    fig = go.Figure()

    # Add a violin plot trace for each atom type
    for atom_type in unique_atom_types:
        atom_df = adp_df[atom_types == atom_type]

        fig.add_trace(go.Violin(
            y=atom_df['Volume'],
            x=[atom_type] * len(atom_df),
            name=atom_type,
            box_visible=True,
            meanline_visible=True
        ))

        # Add scatter plot trace to overlap with the violin plot
        fig.add_trace(go.Scatter(
            y=atom_df['Volume'],
            x=[atom_type] * len(atom_df),
            mode='markers',
            marker=dict(
                color='rgba(0, 0, 0, 0.6)',  # semi-transparent outline
            ),
            name=f"{atom_type} Points"
        ))

    layout = generate_layout(title='Ellipsoid Volumes', xaxis_title='Atom Type', yaxis_title='Volume (Å^6)',
                        font_size=16, color_text='black', l_orientation='h', l_yplace=0.2)

    fig.update_layout(**layout)

    # Update layout
    fig.update_layout(
        showlegend=False
    )

    return fig

def handle_rdf_analysis(u, t_range=None):
    rdf_analysis_type = st.selectbox("Select Analysis Type", ("Overall statistics", "Group tracking"))
    if rdf_analysis_type == "Overall statistics":
        atom1 = st.text_input("Enter first atom type for rdf analysis")
        atom2 = st.text_input("Enter second atom type for rdf analysis")
        bin_size = st.number_input("Enter bin size (optional):", value=75)


        min_dist, max_dist = st.slider(
            "Set cut-off range for distance",
            min_value=0.0,
            max_value=20.0,
            value=(0.0, 15.0),  # Default values for min and max
            step=0.1,
        )

        if st.button('Do rdf analysis'):
            try:

                st.spinner("Running rdf analysis...")
                rdf_df = calculate_rdf_mda(u, atom1, atom2, bins=bin_size, range=(min_dist, max_dist), time_range=t_range)
                # st.dataframe(rdf_df)

                # Create and display the plot after rdf_df is generated.
                rdf_plot = plot_rdf(rdf_df)
                st.plotly_chart(rdf_plot, use_container_width=True)

                # Create and display the download button for the rdf_df data.
                csv_data = rdf_df.to_csv(index=False).encode()
                st.download_button("Download rdf data as CSV", csv_data, file_name="rdf_data.csv", mime="text/csv")


            except Exception as e:
                st.write(f"Error: {str(e)}")



    elif rdf_analysis_type == "Group tracking":

        group_pairs = []

        num_pairs = st.number_input("Enter the number of atom group pairs for tracking:", min_value=1, max_value=10, step=1)
        bin_size_s = st.number_input("Enter bin size (optional):", value=75)

        min_dist, max_dist = st.slider(
            "Set cut-off range for distance",
            min_value=0.0,
            max_value=20.0,
            value=(0.0, 15.0),  # Default values for min and max
            step=0.1,
        )

        for i in range(num_pairs):
            # Get atom indices for the two atom groups using space-separated input
            atom_indices_g1 = st.text_input(
                f"Enter indices (space-separated) for atoms in pair {i + 1} group 1").split()
            atom_indices_g2 = st.text_input(
                f"Enter indices (space-separated) for atoms in pair {i + 1} group 2").split()

            try:
                # Convert indices from string to integer
                atom_indices_g1 = [(int(index) - 1) for index in atom_indices_g1]
                atom_indices_g2 = [(int(index) - 1) for index in atom_indices_g2]
            except ValueError:
                st.write("Please ensure you've entered only space-separated integers for atom indices.")
                return


            # Create AtomGroup instances

            ag1 = u.atoms[atom_indices_g1]

            ag2 = u.atoms[atom_indices_g2]

            # Append atom group pairs to the list

            group_pairs.append((ag1, ag2))

        if st.button('Do individual tracking analysis'):

            try:

                st.write("Running individual tracking analysis...")


                rdf_data = site_specific_rdf(u, group_pairs, bins=bin_size_s, range=(min_dist, max_dist), density=True, time_range=t_range)

                rdf_dataframe = rdf_to_dataframe(rdf_data, group_pairs)

                with st.expander("Download RDF data"):
                    st.dataframe(rdf_dataframe, use_container_width=True)

                # Create and display the plot after rdf_df is generated.
                rdf_plot_v2 = plot_atom_pairs_rdf(rdf_dataframe)
                st.plotly_chart(rdf_plot_v2, use_container_width=True)


            except Exception as e:

                st.write(f"Error: {str(e)}")

    pass

def handle_distance_analysis(u):
    distance_analysis_type = st.selectbox("Select Analysis Type", ("Overall statistics", "Individual tracking"))
    if distance_analysis_type == "Overall statistics":
        atom1 = st.text_input("Enter first atom for distance analysis")
        atom2 = st.text_input("Enter second atom for distance analysis")
        standard_distance = st.number_input("Enter a standard distance for comparison: ", min_value=0.0, max_value=10.0,
                                            step=0.01)

        if st.button('Do distance analysis'):
            try:
                # st.write("Building universe...")
                # u = build_universe_from_dir('frames_dir', timestep=timestep)
                st.write("Running minimum distance analysis...")
                fig, dist_df = plot_and_return_min_distances(u, atom1, atom2, standard_distance)
                with st.expander("Distance values"):
                    st.dataframe(dist_df, hide_index=True, use_container_width=True)
                fig_heatmap_png = generate_weighted_pair_probability_heatmap(dist_df)
                fig_heatmap = generate_weighted_pair_probability_heatmap_plotly(dist_df)

                # Use st.columns to display figures side by side
                col1, col_space, col2 = st.columns([1, 0.4, 1])
                with col1:
                    st.write("Minimum Distances Plot:")
                    st.plotly_chart(fig)
                with col2:
                    st.write("Weighted Pair Formation Probability Plot:")
                    st.plotly_chart(fig_heatmap)
                # Provide a download link for the PNG image below the heatmap
                st.markdown(get_figure_image_download_link(fig_heatmap_png), unsafe_allow_html=True)


            except Exception as e:
                st.write(f"Error: {str(e)}")


    elif distance_analysis_type == "Individual tracking":

        atom_pairs = []

        num_pairs = st.number_input("Enter the number of atom pairs for tracking:", min_value=1, max_value=10, step=1)
        min_time = 0.0
        max_time = u.trajectory[-1].time
        time_range = st.slider("Select the time range for analysis (ps):",
                                     min_value=min_time,
                                     max_value=max_time,
                                     value=(min_time, max_time),
                                     step=0.1)
        standard_distance = st.number_input("Enter a standard distance for comparison: ", min_value=0.0, max_value=10.0,
                                            step=0.01)

        for i in range(num_pairs):
            # User inputs the pair of atom indices as a comma-separated string
            indices_input = st.text_input(f"Enter indices of atom pair {i + 1} (e.g., 1,2):", key=f"pair_{i}")

            try:
                atom_index1, atom_index2 = [(int(index.strip()) - 1) for index in indices_input.split(',')]
                atom_pairs.append((atom_index1, atom_index2))
            except ValueError:
                # Handle the case where the input format is incorrect
                st.error("Please enter a valid pair of indices separated by a comma.")
        if st.button('Do individual tracking analysis'):
            try:
                st.write("Running individual tracking analysis...")
                # fig = plot_atom_distances_over_time_matplotlib(u, standard_distance, *atom_pairs,start_time= start_time_input)
                fig, data_df= plot_atom_distances_over_time(u, standard_distance, *atom_pairs,
                                                               start_time=time_range[0], end_time=time_range[1])

                with st.expander("Download Data"):
                    st.write("Hover mouse over the table to see the download button")
                    st.dataframe(data_df, use_container_width=True, hide_index=True)

                # Display the plot
                st.plotly_chart(fig, use_container_width=True)
                # st.pyplot(fig, use_container_width=True)


            except Exception as e:

                st.write(f"Error: {str(e)}")

    pass

def create_dist_analysis_plots(df1, df2, df3):
    plots = []

    # Plot 1: Time vs. 50-point moving average of Angle
    fig1, ax1 = plt.subplots()
    for atoms, group in df1.groupby('Atoms'):
        # Calculate 50-point moving average
        ma_angle = group['Angle'].rolling(window=50, min_periods=1).mean()
        ax1.plot(group['Time'], ma_angle)
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Angle (50-pt MA)')
    ax1.set_title('Time vs. Angle (50-pt Moving Average)')
    plots.append(fig1)

    # Plot 2: Time vs. 50-point moving average of In-Plane and Out-Plane
    fig2, ax2 = plt.subplots()
    for atoms, group in df1.groupby('Atoms'):
        # Calculate 50-point moving averages
        ma_in_plane = group['In-Plane'].rolling(window=50, min_periods=1).mean()
        ma_out_plane = group['Out-Plane'].rolling(window=50, min_periods=1).mean()

        ax2.plot(group['Time'], ma_in_plane)
        ax2.plot(group['Time'], ma_out_plane)
    ax2.set_xlabel('Time')
    ax2.set_ylabel('Plane Value (50-pt MA)')
    ax2.set_title('Time vs. In-Plane and Out-Plane (50-pt Moving Average)')
    plots.append(fig2)

    # Plot 3: Time vs. Bond Distance Variance (using df2)
    fig3, ax3 = plt.subplots()
    for col in df2.columns:
        if col != 'Time':
            ax3.plot(df2['Time'], df2[col])
    ax3.set_xlabel('Time')
    ax3.set_ylabel('Bond Distance Variance')
    ax3.set_title('Time vs. Bond Distance Variance')
    plots.append(fig3)

    # Plot 4: Time vs. Angle Variance (using df3)
    fig4, ax4 = plt.subplots()
    for col in df3.columns:
        if col != 'Time':
            ax4.plot(df3['Time'], df3[col])
    ax4.set_xlabel('Time')
    ax4.set_ylabel('Angle Variance')
    ax4.set_title('Time vs. Angle Variance')
    plots.append(fig4)

    return plots


def create_probability_distribution_plots(df1, df2, df3):
    plots = []

    # Plot for Angle Distribution
    fig_angle, ax_angle = plt.subplots()
    ax_angle.hist(df1['Angle'], bins=100, density=True, alpha=0.6, color='g')
    ax_angle.set_title('Probability Distribution of Angle')
    ax_angle.set_xlabel('Angle')
    ax_angle.set_ylabel('Probability Density')
    plots.append(fig_angle)

    # Plot for Beta Distribution
    fig_beta, ax_beta = plt.subplots()
    ax_beta.hist(df1['Beta'], bins=100, density=True, alpha=0.6, color='g')
    ax_beta.set_title('Probability Distribution of Beta')
    ax_beta.set_xlabel('Beta')
    ax_beta.set_ylabel('Probability Density')
    plots.append(fig_beta)

    # Plot for In-Plane and Out-Plane Distribution
    fig_plane, ax_plane = plt.subplots()
    ax_plane.hist(df1['In-Plane'], bins=100, density=True, alpha=0.6, color='r', label='In-Plane')
    ax_plane.hist(df1['Out-Plane'], bins=100, density=True, alpha=0.6, color='b', label='Out-Plane')
    ax_plane.set_title('Probability Distribution of In-Plane and Out-Plane')
    ax_plane.set_xlabel('Plane Value')
    ax_plane.set_ylabel('Probability Density')
    ax_plane.legend()
    plots.append(fig_plane)

    # Plot for Bond Distance Variance Distribution
    fig_bdv, ax_bdv = plt.subplots()
    melted_bdv = pd.melt(df2, id_vars=['Time'], value_vars=df2.columns[1:])
    ax_bdv.hist(melted_bdv['value'].dropna(), bins=30, density=True, alpha=0.6, color='y')
    ax_bdv.set_title('Probability Distribution of Bond Distance Variance')
    ax_bdv.set_xlabel('Bond Distance Variance')
    ax_bdv.set_ylabel('Probability Density')
    plots.append(fig_bdv)

    # Plot for Angle Variance Distribution
    fig_av, ax_av = plt.subplots()
    melted_av = pd.melt(df3, id_vars=['Time'], value_vars=df3.columns[1:])
    ax_av.hist(melted_av['value'].dropna(), bins=30, density=True, alpha=0.6, color='c')
    ax_av.set_title('Probability Distribution of Angle Variance')
    ax_av.set_xlabel('Angle Variance')
    ax_av.set_ylabel('Probability Density')
    plots.append(fig_av)

    return plots