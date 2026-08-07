import numpy as np
from pymatgen.io.ase import AseAtomsAdaptor
import pandas as pd
from pymatgen.core.structure import Molecule, Structure
from pymatgen.analysis.local_env import CovalentBondNN, JmolNN
from pymatgen.core.graphs import MoleculeGraph, StructureGraph
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
    return fig


def _distance_matrix_from_coords(coords):
    coords = np.asarray(coords, dtype=float)
    deltas = coords[:, None, :] - coords[None, :, :]
    return np.linalg.norm(deltas, axis=-1)

def create_distance_matrix(updated_coords):
    return pd.DataFrame(_distance_matrix_from_coords(updated_coords))

def create_distance_matrix_from_structure_graph(structure_graph):
    coords = np.array([site.coords for site in structure_graph.structure.sites])
    return pd.DataFrame(_distance_matrix_from_coords(coords))
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
    """Translate sites to connected periodic images for a molecular fragment."""

    jnn = JmolNN()
    new_structure_graph = StructureGraph.from_local_env_strategy(structure, jnn)
    indices_need_update = set()
    lattice_vectors = structure.lattice.matrix

    new_structure_graph_dict = new_structure_graph.as_dict()
    adj_mat = new_structure_graph_dict["graphs"]["adjacency"]

    indices_need_update.update(
        (adj_mat[i][j]["id"], tuple(adj_mat[i][j]["to_jimage"]))
        for i in range(len(adj_mat))
        for j in range(len(adj_mat[i]))
        if any(adj != 0 for adj in adj_mat[i][j]["to_jimage"])
    )
    temp_indices = set(
        (adj_mat[i][j]["id"], tuple(k))
        for i, k in indices_need_update
        for j in range(len(adj_mat[i]))
        if adj_mat[i][j]["id"] not in (id_ for id_, _ in indices_need_update)
    )
    indices_need_update.update(temp_indices)

    mol_coords = structure.cart_coords
    updated_coords = mol_coords.copy()

    for site, direction in indices_need_update:
        translation = np.dot(direction, lattice_vectors)
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
    test_mol_graph = MoleculeGraph.from_local_env_strategy(test_mol, cnn)
    disconnected_fragment = test_mol_graph.get_disconnected_fragments()

    all_connected = all(test_mol_graph.get_connected_sites(i) for i in range(len(test_mol)))
    return all_connected and len(disconnected_fragment) <= 1


def get_connected_coordinates(mol_structure, max_iterations=10):
    if max_iterations < 0:
        raise ValueError("max_iterations must be non-negative")

    species = [site.specie for site in mol_structure.sites]
    lattice = mol_structure.lattice
    current_coords = mol_structure.cart_coords
    connectivity = test_connectivity_in_molecule(species, current_coords)

    if connectivity:
        return current_coords

    iteration = 0
    while iteration < max_iterations:
        connectivity = test_connectivity_in_molecule(species, current_coords)
        if connectivity:
            break

        new_structure = Structure(lattice, species, current_coords, coords_are_cartesian=True)
        updated_coords, _ = update_coordinates_function(new_structure)
        current_coords = updated_coords
        iteration += 1

    if not connectivity:
        return None

    return current_coords


def get_molecule_object(atoms, molecule):
    molecule_atoms = atoms[molecule]
    mol_structure = AseAtomsAdaptor().get_structure(molecule_atoms)
    joined_coords = get_connected_coordinates(mol_structure)

    if joined_coords is None:
        raise ValueError("Could not construct a connected molecule within the maximum number of iterations")

    mol = Molecule(mol_structure.species, joined_coords)
    return mol
