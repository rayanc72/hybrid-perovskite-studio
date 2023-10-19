
from pymatgen.io.ase import AseAtomsAdaptor
from pymatgen.io.babel import BabelMolAdaptor
from pymatgen.io.cif import CifWriter
from pymatgen.analysis.structure_matcher import StructureMatcher
import zipfile
import tempfile
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from pymatgen.symmetry.groups import SpaceGroup
from pymatgen.analysis.dimensionality import *
from pymatgen.core.structure import Molecule, IStructure
from pymatgen.analysis.graphs import MoleculeGraph
from pymatgen.analysis.local_env import *
from pymatgen.core.operations import SymmOp
from pymatgen.analysis.local_env import *
from pymatgen.analysis.graphs import MoleculeGraph, ConnectedSite
from pymatgen.util.coord import find_in_coord_list
import matplotlib.pyplot as plt
import networkx as nx

def save_molecule_to_xyz(molecule, filename):
    with open(filename, 'w') as f:
        f.write(f"{len(molecule)}\n")
        f.write("Molecule XYZ\n")
        for site in molecule:
            f.write(f"{site.species_string} {site.x} {site.y} {site.z}\n")

def draw_molecule_graph(mol_graph):
    fig, ax = plt.subplots()
    nx.draw(mol_graph.graph, with_labels=True, ax=ax)
    st.pyplot(fig)

def create_distance_matrix(updated_coords):
    num_atoms = len(updated_coords)
    distance_matrix = np.zeros((num_atoms, num_atoms))

    for i in range(num_atoms):
        for j in range(i+1, num_atoms):
            distance = np.linalg.norm(updated_coords[i] - updated_coords[j])
            distance_matrix[i, j] = distance
            distance_matrix[j, i] = distance

    distance_df = pd.DataFrame(distance_matrix)
    return distance_df

def create_distance_matrix_from_structure_graph(structure_graph):
    num_atoms = len(structure_graph.structure.sites)
    coords = np.array([site.coords for site in structure_graph.structure.sites])
    distance_matrix = np.zeros((num_atoms, num_atoms))

    for i in range(num_atoms):
        for j in range(i + 1, num_atoms):
            distance = np.linalg.norm(coords[i] - coords[j])
            distance_matrix[i, j] = distance
            distance_matrix[j, i] = distance

    distance_df = pd.DataFrame(distance_matrix)
    return distance_df
#
# def find_large_distance_indices(distance_df, cut_off=None):
#     if cut_off is None:
#         # Calculate the cut-off distance as (largest distance in the data frame) / 2
#         cut_off = distance_df.max().max() * 0.4
#
#     # Find atom indices with a distance larger than the cut-off from atom index 0
#     large_distance_indices = distance_df[0][distance_df[0] > cut_off].index.tolist()
#
#     return large_distance_indices
#
# def find_min_distance_periodic_images(structure_graph, large_distance_indices):
#     lattice_vectors = structure_graph.structure.lattice.matrix
#     atom_0_coords = structure_graph.structure.sites[0].coords
#
#     min_distance_periodic_images = {}
#
#     for atom_index in large_distance_indices:
#         atom_coords = structure_graph.structure.sites[atom_index].coords
#         min_distance = float('inf')
#         min_image_coords = None
#
#         for i in range(-1, 2):
#             for j in range(-1, 2):
#                 for k in range(-1, 2):
#                     translation = np.dot([i, j, k], lattice_vectors)
#                     translated_coords = atom_coords + translation
#                     distance = np.linalg.norm(atom_0_coords - translated_coords)
#
#                     if distance < min_distance:
#                         min_distance = distance
#                         min_image_coords = translated_coords
#
#         min_distance_periodic_images[atom_index] = min_image_coords
#
#     return min_distance_periodic_images



def update_coordinates_function(structure):

    # Create a new StructureGraph using the new_structure
    jnn = JmolNN()
    new_structure_graph = StructureGraph.with_local_env_strategy(structure, jnn)

    # Initialize a set to store indices of atoms that need their coordinates updated
    indices_need_update = set()
    # Extract the lattice matrix from the input structure
    lattice_vectors = structure.lattice.matrix

    # Extract the adjacency matrix from the structure graph dictionary
    new_structure_graph_dict = new_structure_graph.as_dict()
    adj_mat = new_structure_graph_dict["graphs"]["adjacency"]

    # Find the indices of atoms connected to periodic images and add them to the set
    indices_need_update.update(
        (adj_mat[i][j]["id"], tuple(adj_mat[i][j]["to_jimage"]))
        for i in range(len(adj_mat))
        for j in range(len(adj_mat[i]))
        if any(adj != 0 for adj in adj_mat[i][j]["to_jimage"])
    )
    # Add the indices of atoms that are connected to the atoms outside the unit cell
    temp_indices = set(
        (adj_mat[i][j]["id"], tuple(k))
        for i, k in indices_need_update
        for j in range(len(adj_mat[i]))
        if adj_mat[i][j]["id"] not in (id_ for id_, _ in indices_need_update)
    )
    indices_need_update.update(temp_indices)

    # Extract the Cartesian coordinates of all atoms in the input structure
    mol_coords = structure.cart_coords
    # Create a copy of the Cartesian coordinates to store the updated coordinates
    updated_coords = mol_coords.copy()

    # Update the coordinates of the atoms that need to be connected to their periodic images
    for site, direction in indices_need_update:
        # Compute the translation vector based on the lattice vectors and direction
        translation = np.dot(direction, lattice_vectors)
        # Update the coordinates of the atom by adding the translation vector
        updated_coords[site] = structure[site].coords + translation

    return updated_coords, new_structure_graph



# def update_coords_by_min_distance_periodic_images(structure_graph, initial_coords):
#     # Create a new Structure object using the initial_coords
#     species = [site.specie for site in structure_graph.structure.sites]
#     lattice = structure_graph.structure.lattice
#     new_structure = Structure(lattice, species, initial_coords, coords_are_cartesian = True)
#
#     updated_coords, new_structure_graph = update_coordinates_function(new_structure)
#
#     # Create a distance matrix using the new_structure_graph
#     distance_df = create_distance_matrix_from_structure_graph(new_structure_graph)
#
#     # Identify the atom indices with large distances
#     large_distance_indices = find_large_distance_indices(distance_df)
#     st.write(large_distance_indices)
#
#     # Find the periodic images that minimize the distance to atom index 0
#     min_distance_periodic_images = find_min_distance_periodic_images(structure_graph, large_distance_indices)
#
#     # Update the initial_coords with the new periodic image coordinates
#     updated_coords = initial_coords.copy()
#     for atom_index, new_coords in min_distance_periodic_images.items():
#         updated_coords[atom_index] = new_coords
#
#     return updated_coords



def test_connectivity_in_molecule(species, coords):
    test_mol = Molecule(species, coords)
    cnn = CovalentBondNN(tol=0.2)
    test_mol_graph = MoleculeGraph.with_local_env_strategy(test_mol, cnn)
    disconnected_fragment = test_mol_graph.get_disconnected_fragments()


    # Check if all the atoms in the molecule are connected
    all_connected = True

    for i in range(len(test_mol)):
        connected_sites = test_mol_graph.get_connected_sites(i)
        if not connected_sites:
            all_connected = False
            break

    if not all_connected or len(disconnected_fragment) > 1:
        return False
    else:
        return True


def get_connected_coordinates(mol_structure, max_iterations=10):

    # Extract the species, lattice, and initial coordinates from the input mol_structure object
    species = [site.specie for site in mol_structure.sites]
    lattice = mol_structure.lattice
    current_coords = mol_structure.cart_coords

    # Initialize iteration counter
    iteration = 0

    # Perform the loop
    while iteration < max_iterations:
        # Check the connectivity of the current molecular structure using the test_connectivity_in_molecule function
        connectivity = test_connectivity_in_molecule(species, current_coords)

        # If the connectivity test returns True, break the loop
        if connectivity:
            break

        # If the connectivity test returns False, update the coordinates and create a structure graph using the update_coordinates_function
        new_structure = Structure(lattice, species, current_coords, coords_are_cartesian=True)
        updated_coords, _ = update_coordinates_function(new_structure)

        # Update the current coordinates and increase the iteration counter
        current_coords = updated_coords
        iteration += 1

    # If the connectivity is still False after max_iterations, return None
    if not connectivity:
        return None

    return current_coords


def get_molecule_object(atoms, molecule):
    molecule_atoms = atoms[molecule]

    mol_structure = AseAtomsAdaptor().get_structure(molecule_atoms)

    joined_coords = get_connected_coordinates(mol_structure)


    mol = Molecule(mol_structure.species, joined_coords)

    return mol