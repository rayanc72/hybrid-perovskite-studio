"""Molecule presentation helpers using the shared periodic bond model."""

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from ase import Atoms
from pymatgen.core.graphs import StructureGraph
from pymatgen.core.structure import Molecule
from pymatgen.io.ase import AseAtomsAdaptor

from hps.core.molecules import build_bond_graph, detect_molecules, unwrap_molecule


def save_molecule_to_xyz(molecule, filename):
    with open(filename, "w") as f:
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


def update_coordinates_function(structure, *, exceptions=None, bond_padding=None):
    """Unwrap a finite fragment once and return its equivalent StructureGraph."""
    atoms = AseAtomsAdaptor.get_atoms(structure, msonable=False)
    graph = build_bond_graph(atoms, exceptions=exceptions, bond_padding=bond_padding)
    if len(graph.components) != 1:
        raise ValueError("The selected atoms must form one nonempty connected bonded group")
    coordinates = np.empty((len(atoms), 3))
    coordinates[list(graph.components[0].indices)] = graph.unwrap()
    edges = {(bond.source, bond.target, (0, 0, 0), bond.shift): None for bond in graph.bonds}
    return coordinates, StructureGraph.from_edges(structure, edges)


def test_connectivity_in_molecule(species, coords):
    """Test nonperiodic connectivity with the same bond rule used for detection."""
    atoms = Atoms(symbols=[str(specie) for specie in species], positions=coords)
    return len(detect_molecules(atoms)) == 1


def get_connected_coordinates(
    mol_structure, max_iterations=10, *, exceptions=None, bond_padding=None
):
    """Unwrap a finite fragment with graph image offsets, without iteration.

    max_iterations is retained for compatibility: zero allows only already
    unwrapped coordinates, while any positive value permits one traversal.
    Disconnected/empty selections return None; periodic networks raise ValueError.
    """
    if max_iterations < 0:
        raise ValueError("max_iterations must be non-negative")
    atoms = AseAtomsAdaptor.get_atoms(mol_structure, msonable=False)
    graph = build_bond_graph(atoms, exceptions=exceptions, bond_padding=bond_padding)
    if len(graph.components) != 1:
        return None
    coordinates = np.empty((len(atoms), 3))
    coordinates[list(graph.components[0].indices)] = graph.unwrap()
    if max_iterations == 0 and any(any(shift) for shift in graph.components[0].image_shifts):
        return None
    return coordinates


def get_molecule_object(atoms, molecule, *, exceptions=None, bond_padding=None):
    """Build a finite Molecule, retaining selection order and the ASE PBC flags."""
    molecule = list(molecule)
    coordinates = unwrap_molecule(atoms, molecule, exceptions=exceptions, bond_padding=bond_padding)
    return Molecule(atoms[list(molecule)].get_chemical_symbols(), coordinates)
