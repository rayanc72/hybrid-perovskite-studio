import hashlib
from importlib import import_module
import os
from io import StringIO
import numpy as np
from ase import Atom, Atoms
from ase.io import read, write
from ase.neighborlist import natural_cutoffs
from ase.geometry import get_distances
from ase.data import covalent_radii
from ase.spacegroup import get_spacegroup
from ase.build import make_supercell
import spglib
import base64
import os
import io
import tempfile
import numpy as np
from ase import Atom, Atoms
from ase.io import read
from pymatgen.core import Structure
import shutil
from shutil import make_archive
from ipyspeck import stspeck
from ase.io import write
from ase.spacegroup import get_spacegroup
from pymatgen.io.ase import AseAtomsAdaptor
from pymatgen.io.cif import CifWriter
from pymatgen.analysis.structure_matcher import StructureMatcher
import zipfile
import tempfile
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from pymatgen.symmetry.groups import SpaceGroup
from pymatgen.core.structure import Molecule
from pymatgen.core.structure import Structure
from pymatgen.analysis.graphs import MoleculeGraph
from pymatgen.core.operations import SymmOp
from pymatgen.analysis.graphs import MoleculeGraph, ConnectedSite
from pymatgen.util.coord import find_in_coord_list
import networkx as nx
from bokeh.models import ColumnDataSource
from bokeh.models.tools import HoverTool
from bokeh.layouts import row, gridplot
from bokeh.plotting import figure, show
from typing import List, Tuple
from io import BytesIO
import re


def _inject_public_names(module):
    for name in dir(module):
        if not name.startswith("_"):
            globals().setdefault(name, getattr(module, name))


for _module_name in (
    "pymatgen.analysis.dimensionality",
    "pymatgen.analysis.local_env",
    "scipy.interpolate",
    "hps.domain.molecule_builder",
):
    _inject_public_names(import_module(_module_name))

def image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def get_file_format(file_name):
    file_extension = os.path.splitext(file_name)[1].lower()
    if file_extension == '.in':
        return 'aims'
    elif file_extension == '.next_step':
        return 'aims'
    elif file_extension == '.cif':
        return 'cif'
    else:
        raise ValueError("Invalid file format. Please provide an AIMS or CIF file.")

def read_structure_file(fileobj, file_format='aims'):
    with tempfile.NamedTemporaryFile(mode='w+b', suffix=f'.{file_format}', delete=False) as temp_file:
        temp_file.write(fileobj.getvalue())
        temp_file.flush()
        atoms = read(temp_file.name, format=file_format)
    os.unlink(temp_file.name)  # Remove the temporary file
    return atoms

def initialize_structure(uploaded_data, file_format, file_name, exceptions=None,b_p=0):
    atoms = read_structure_file(uploaded_data, file_format=file_format)

    print_space_group(atoms)
    molecules = detect_molecules(atoms, exceptions=exceptions, b=b_p)
    modified_symbols = [f"{atom.symbol}{i + 1}" for i, atom in enumerate(atoms)]
    return atoms, molecules, modified_symbols

from fractions import Fraction

def normalize_fractional_direction(dipole_frac, tol=1e-6):
    """
    Take the raw fractional dipole vector (Δx, Δy, Δz),
    zero out any tiny components, then return the minimal
    integer [u v w] direction with the convention that the
    dominant component is positive.
    """
    # 1) kill sub-threshold noise
    vec = np.array(dipole_frac, dtype=float)
    vec[np.abs(vec) < tol] = 0

    # 2) turn each component into a Fraction
    fracs = [Fraction(v).limit_denominator() for v in vec]

    # 3) clear denominators
    lcm = np.lcm.reduce([f.denominator for f in fracs])
    ints = np.array([f * lcm for f in fracs], dtype=int)

    # 4) divide out any common factor
    gcd = np.gcd.reduce(ints)
    ints //= gcd

    # 5) if the *largest* component is negative, flip the whole thing
    idx = np.argmax(np.abs(ints))
    if ints[idx] < 0:
        ints = -ints

    return ints.tolist()

def wrap_frac(coords):
    # coords: (N,3) array of fractional coords in [0,1)
    return (coords + 0.5) % 1.0 - 0.5


def initialize_structure_v2(uploaded_data, file_format):


    atoms = read_structure_file(uploaded_data, file_format=file_format)

    molecules = detect_molecules(atoms)

    modified_symbols = [f"{atom.symbol}{i + 1}" for i, atom in enumerate(atoms)]

    return atoms, molecules, modified_symbols

def write_modified_aims_file(atoms, file_name):
    symbols = atoms.get_chemical_symbols()
    modified_symbols = [f"{symbol}{i+1}" for i, symbol in enumerate(symbols)]

    if hasattr(file_name, "write"):
        f = file_name
        if atoms.get_pbc().any():
            f.write("# Lattice_vectors\n")
            for vec in atoms.get_cell():
                f.write(f"lattice_vector {vec[0]} {vec[1]} {vec[2]}\n")
            f.write("\n")

        f.write("# Atoms\n")
        for i, atom in enumerate(atoms):
            f.write(f"atom {atom.position[0]} {atom.position[1]} {atom.position[2]} {modified_symbols[i]}\n")
        return

    with open(file_name, 'w') as f:
        if atoms.get_pbc().any():
            f.write("# Lattice_vectors\n")
            for vec in atoms.get_cell():
                f.write(f"lattice_vector {vec[0]} {vec[1]} {vec[2]}\n")
            f.write("\n")

        f.write("# Atoms\n")
        for i, atom in enumerate(atoms):
            f.write(f"atom {atom.position[0]} {atom.position[1]} {atom.position[2]} {modified_symbols[i]}\n")


def detect_molecules(atoms, exceptions: List[Tuple[str, str]] = None, b=0):
    exceptions = exceptions if exceptions else []

    cov_radii = [covalent_radii[a.number] for a in atoms]
    element_tolerance = [0.1 if a.symbol in ["C", "H", "N", "O", "S"] else 0.5 if a.symbol in ["Cl"] else (0.25+b) for a in atoms]
    cutoffs = [natural_cutoff + tolerance for natural_cutoff, tolerance in
               zip(natural_cutoffs(atoms), element_tolerance)]
    coords = atoms.get_positions()

    # Convert cutoffs to a NumPy array
    cutoffs = np.array(cutoffs)

    # Calculate vector differences between all atoms, considering periodic boundary conditions
    vec_diffs, _ = get_distances(coords, coords, cell=atoms.cell, pbc=atoms.pbc)

    # Calculate scalar distances
    dist_matrix = np.linalg.norm(vec_diffs, axis=-1)

    # Initialize bonded_atoms matrix
    bonded_atoms = dist_matrix < cutoffs[:, None] + cutoffs

    # Handle exceptions: If there's a bond between atoms that shouldn't be considered, remove the bond
    for i, atom_i in enumerate(atoms):
        for j, atom_j in enumerate(atoms):
            if (atom_i.symbol, atom_j.symbol) in exceptions or (atom_j.symbol, atom_i.symbol) in exceptions:
                bonded_atoms[i, j] = False
                bonded_atoms[j, i] = False


    # Create a graph of bonded atoms
    graph = {}
    for i, atom in enumerate(atoms):
        graph[i] = bonded_atoms[i].nonzero()[0].tolist()

    def dfs_visit(i, visited, graph, component):
        visited[i] = True
        component.append(i)

        for neighbor in graph[i]:
            if not visited[neighbor]:
                dfs_visit(neighbor, visited, graph, component)

    visited = [False] * len(atoms)
    molecules = []
    for i, atom in enumerate(atoms):
        if not visited[i]:
            component = []
            dfs_visit(i, visited, graph, component)
            molecules.append(component)

    return molecules

def rotation_matrix(axis, theta):
    axis = np.asarray(axis)
    axis = axis / np.linalg.norm(axis)
    a = np.cos(theta / 2.0)
    b, c, d = -axis * np.sin(theta / 2.0)
    aa, bb, cc, dd = a * a, b * b, c * c, d * d
    bc, ad, ac, ab, bd, cd = b * c, a * d, a * c, a * b, b * d, c * d
    return np.array([[aa + bb - cc - dd, 2 * (bc + ad), 2 * (bd - ac)],
                     [2 * (bc - ad), aa + cc - bb - dd, 2 * (cd + ab)],
                     [2 * (bd + ac), 2 * (cd - ab), aa + dd - bb - cc]])

import numpy as np
from pymatgen.core import Structure
from pymatgen.core.lattice import Lattice
from pymatgen.core.surface import miller_index_from_sites

def crystal_direction_v3(v, lattice_vectors):
    v = np.real(v)
    # Create a pymatgen lattice object
    lattice = Lattice(lattice_vectors)

    # Find a vector orthogonal to v
    u = np.array([1, 0, 0])
    if np.isclose(np.dot(u, v), 0):
        u = np.array([0, 1, 0])

    orthogonal_vec = np.cross(v, u)

    # Sample three points on the plane perpendicular to v
    point_1 = orthogonal_vec
    point_2 = orthogonal_vec * 2
    point_3 = np.cross(v, orthogonal_vec)

    # Create a pymatgen structure object with the lattice vectors and three points
    coords = np.vstack([point_1, point_2, point_3])
    structure = Structure(lattice, ["H"] * 3, coords)

    # Calculate the Miller indices using pymatgen's miller_index_from_sites() function
    hkl = miller_index_from_sites(structure.lattice,structure.cart_coords, coords_are_cartesian=True)

    return hkl

def rotation_axis_and_angle_from_matrix_v2(rotation_matrix):

    rotation_matrix = np.asarray(rotation_matrix)

    # Check if the rotation matrix is proper
    det_R = np.linalg.det(rotation_matrix)
    if not np.isclose(det_R, 1.0, rtol=1e-5):
        raise ValueError("The input rotation matrix is not proper.")

    # Find the eigenvectors and eigenvalues
    eigvals, eigvecs = np.linalg.eig(rotation_matrix)

    # Find the eigenvector corresponding to the eigenvalue 1
    index = np.where(np.isclose(eigvals, 1.0, rtol=1e-5))[0][0]
    rotation_axis = eigvecs[:, index]

    # Calculate the orthogonal eigenvectors
    orthogonal_eigvecs = np.column_stack(
        (eigvecs[:, (index) % 3], eigvecs[:, (index + 1) % 3], eigvecs[:, (index + 2) % 3]))

    # Construct the 3x3 matrix A and its inverse
    A = orthogonal_eigvecs
    A_inv = np.linalg.inv(A)

    # Calculate A_inv * R * A
    R_transformed = A_inv @ rotation_matrix @ A

    # Calculate the rotation angle from the transformed matrix
    angle_comp = np.arccos((np.trace(R_transformed) - 1) / 2)
    angle_real = np.real(angle_comp)
    angle = np.degrees(angle_real)

    return rotation_axis, angle

from pymatgen.analysis.molecule_matcher import HungarianOrderMatcher
def align_vector_with_plane(vector, lattice_vectors, miller_indices):
    # Calculate the reciprocal lattice vectors
    a_star = np.cross(lattice_vectors[1], lattice_vectors[2]) / np.dot(lattice_vectors[0], np.cross(lattice_vectors[1], lattice_vectors[2]))
    b_star = np.cross(lattice_vectors[2], lattice_vectors[0]) / np.dot(lattice_vectors[1], np.cross(lattice_vectors[2], lattice_vectors[0]))
    c_star = np.cross(lattice_vectors[0], lattice_vectors[1]) / np.dot(lattice_vectors[2], np.cross(lattice_vectors[0], lattice_vectors[1]))

    # Calculate the plane normal in Cartesian coordinates based on the Miller indices
    plane_normal = (miller_indices[0] * a_star + miller_indices[1] * b_star + miller_indices[2] * c_star)
    plane_normal = plane_normal / np.linalg.norm(plane_normal)

    # # #testing pymatgen function
    # # Calculate the target_vector_parallel
    # projection_vector = vector - np.dot(vector, plane_normal) * plane_normal
    # target_vector_parallel = (np.linalg.norm(vector) / np.linalg.norm(projection_vector)) * projection_vector
    #
    # # Ensure the target_vector_parallel maintains the same direction as the initial vector
    # if np.dot(vector, target_vector_parallel) < 0:
    #     target_vector_parallel = -target_vector_parallel
    #
    # pymat_rotation_matrix = HungarianOrderMatcher.rotation_matrix_vectors(vector, target_vector_parallel)
    # st.write(pymat_rotation_matrix)


    # Calculate the angle between the input vector and the plane normal
    angle_between = np.arccos(np.dot(vector, plane_normal) / (np.linalg.norm(vector) * np.linalg.norm(plane_normal)))
    # st.write(angle_between)

    # Calculate the rotation angle needed to align the vector with the plane
    rotation_angle = np.pi / 2 - angle_between

    # Calculate the rotation axis by taking the cross product of the vector and the plane normal
    rotation_axis = np.cross(vector, plane_normal)
    rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)

    # Calculate the rotation matrix using Rodrigues' rotation formula
    sin_angle = np.sin(rotation_angle)
    cos_angle = np.cos(rotation_angle)
    cross_product_matrix = np.array([[0, -rotation_axis[2], rotation_axis[1]],
                                     [rotation_axis[2], 0, -rotation_axis[0]],
                                     [-rotation_axis[1], rotation_axis[0], 0]])

    rotation_matrix = np.identity(3) + sin_angle * cross_product_matrix + (1 - cos_angle) * np.matmul(cross_product_matrix, cross_product_matrix)
    return rotation_matrix

def join_fragments(mol_graph):
    undirected_graph = mol_graph.graph.to_undirected()
    connected_components = list(nx.connected_components(undirected_graph))

    sites = mol_graph.molecule.sites
    updated_sites = []

    for component in connected_components:
        submolecule_indices = sorted(list(component))
        submolecule = Molecule.from_sites([sites[i] for i in submolecule_indices])

        # Find the index of the connected site with the smallest distance
        connected_site_index = min(submolecule_indices, key=lambda i: sites[i].distance(sites[submolecule_indices[0]]))

        # Get the connected sites of the connected site in the submolecule
        connected_sites = mol_graph.get_connected_sites(connected_site_index)

        for connected_site in connected_sites:
            if connected_site.index not in submolecule_indices:
                # Update the coordinates of the connected site in the submolecule
                coord = submolecule.cart_coords[connected_site_index - submolecule_indices[0]]
                new_coord = coord + connected_site.vec
                submolecule.replace(submolecule_indices.index(connected_site_index), submolecule.species[connected_site_index], new_coord)

        updated_sites.extend(submolecule.sites)

    return Molecule.from_sites(updated_sites)


from itertools import combinations
from pymatgen.core import Element

def get_dm_direction(molecule, charges=None):
    """
    Calculate dipole direction, and optionally dipole magnitude in Debye.

    Parameters
    ----------
    molecule : structure-like object
        Must support iteration over atoms with `.coords` and `.specie` attributes,
        and have `.center_of_mass` property.
    charges : array-like or None, optional
        Partial charges in units of elementary charge (e). If provided,
        dipole moment will be calculated in Debye. Length must match number of atoms.

    Returns
    -------
    tuple
        (dm_direction, com) if charges is None
        (dm_direction, dipole_moment_debye, com) if charges is provided
    """
    com = molecule.center_of_mass

    if charges is not None:
        # --- Physically meaningful dipole using charges ---
        total_dipole = np.zeros(3)
        for atom, q in zip(molecule, charges):
            position_vector = atom.coords - com
            total_dipole += q * position_vector

        norm = np.linalg.norm(total_dipole)
        if norm == 0:
            dm_direction = np.zeros(3)
            dipole_moment_debye = 0.0
        else:
            dm_direction = total_dipole / norm
            # Convert e·Å to Debye
            dipole_moment_debye = norm * 4.80320427

        return dm_direction, dipole_moment_debye, com

    else:
        # --- Fallback: heuristic dipole direction using electronegativity differences ---
        total_dipole = np.zeros(3)
        for atom1, atom2 in combinations(molecule, 2):
            en_diff = Element(atom1.specie).X - Element(atom2.specie).X
            pos_diff = atom2.coords - atom1.coords
            total_dipole += en_diff * pos_diff

        norm = np.linalg.norm(total_dipole)
        dm_direction = total_dipole / norm if norm != 0 else np.zeros(3)

        return dm_direction, com

def get_crystal_direction(direction_vector, atoms, com):
    # Convert the direction vector to fractional coordinates
    lattice_matrix = atoms.get_cell()
    fractional_direction = np.linalg.solve(lattice_matrix.T, direction_vector)
    fractional_com = np.linalg.solve(lattice_matrix.T, com)

    # Normalize the fractional coordinates
    crystal_direction = fractional_direction / np.linalg.norm(fractional_direction)

    # Convert the crystal direction to hkl format (nearest integers)
    hkl = np.round(crystal_direction).astype(int)

    return tuple(crystal_direction), fractional_com

def get_perpendicular_crystal_directions(direction_vector, atoms):
    # Convert the direction vector to fractional coordinates
    lattice_matrix = atoms.get_cell()
    fractional_direction = np.linalg.solve(lattice_matrix.T, direction_vector)

    # Normalize the fractional coordinates
    crystal_direction = fractional_direction / np.linalg.norm(fractional_direction)

    # Find perpendicular directions in hkl format (nearest integers) for all basis vectors
    perpendicular_directions = {}
    basis_vectors = np.eye(3)

    for i, basis_vector in enumerate(basis_vectors):
        perpendicular_direction = np.cross(crystal_direction, basis_vector)
        if not np.allclose(perpendicular_direction, 0):
            hkl = np.round(perpendicular_direction).astype(int)
            perpendicular_directions[f'basis_vector_{i+1}'] = tuple(hkl)

    return perpendicular_directions


def rotate_molecules_v2(atoms, molecule, axis, angle):
    angle_rad = np.deg2rad(angle)

    rotated_atoms = atoms.copy()
    molecule_atoms = rotated_atoms[molecule]
    mol_structure = AseAtomsAdaptor().get_structure(molecule_atoms)

    joined_coords = get_connected_coordinates(mol_structure)

    mol = Molecule(mol_structure.species, joined_coords)
    cnn = CovalentBondNN(tol=0.5)
    mol_graph = MoleculeGraph.with_local_env_strategy(mol, cnn)


    # Check if all the atoms in the molecule are connected
    all_connected = True

    for i in range(len(mol)):
        connected_sites = mol_graph.get_connected_sites(i)
        if not connected_sites:
            all_connected = False
            break

    if not all_connected:
        st.write("Not all atoms are connected within the molecule.")
        st.pyplot(draw_molecule_graph(mol_graph))
        return None


    centroid = mol.center_of_mass

    rotation_mat = rotation_matrix(axis, angle_rad)
    symmop = SymmOp.from_rotation_and_translation(rotation_mat, translation_vec=(0, 0, 0))

    # Apply the rotation to the molecule
    rotated_coords = []
    for coord in mol.cart_coords:
        coord = coord - centroid  # Translate the molecule so that the centroid is at the origin
        coord = symmop.operate(coord)
        rotated_coords.append(coord + centroid)  # Translate the molecule back to its original position

    # Update the rotated atomic positions in the original ASE Atoms object
    for i, coord in enumerate(rotated_coords):
        rotated_atoms.positions[molecule[i]] = coord

    return rotated_atoms

def rotate_molecules_v5(atoms, molecule, axis, angle, pivot_point_index, atoms_to_rotate_indices):

    # molecule is a list of atom indices in the atoms object

    angle_rad = np.deg2rad(angle)

    rotated_atoms = atoms.copy()

    mol_obj = get_molecule_object(atoms, molecule)

    rotated_mol = mol_obj.copy()

    rotated_mol.rotate_sites(atoms_to_rotate_indices, angle_rad, axis,
                                                      mol_obj.cart_coords[pivot_point_index])


    rotated_coords = rotated_mol.cart_coords

    # Update the rotated atomic positions in the original ASE Atoms object
    for i, coord in enumerate(rotated_coords):
        rotated_atoms.positions[molecule[i]] = coord

    return rotated_atoms


def rotate_molecules_v4(atoms, molecule, mol_obj, rot_mat):
    rotated_atoms = atoms.copy()

    centroid = mol_obj.center_of_mass

    rotation_mat = rot_mat
    # rotation_mat = rotation_matrix
    symmop = SymmOp.from_rotation_and_translation(rotation_mat, translation_vec=(0, 0, 0))

    # Apply the rotation to the molecule
    rotated_coords = []
    for coord in mol_obj.cart_coords:
        coord = coord - centroid  # Translate the molecule so that the centroid is at the origin
        coord = symmop.operate(coord)
        rotated_coords.append(coord + centroid)  # Translate the molecule back to its original position

    # Update the rotated atomic positions in the original ASE Atoms object
    for i, coord in enumerate(rotated_coords):
        rotated_atoms.positions[molecule[i]] = coord

    return rotated_atoms

def rotate_molecules_v3(atoms, molecules, molecule_indices, axis, angle,
                                              centroid_option, custom_centroid):
    chosen_molecules = [molecules[i - 1] for i in molecule_indices]
    angle_rad = np.deg2rad(angle)

    rotated_atoms = atoms.copy()

    for molecule in chosen_molecules:

        molecule_atoms = rotated_atoms[molecule]
        mol_structure = AseAtomsAdaptor().get_structure(molecule_atoms)

        joined_coords = get_connected_coordinates(mol_structure)

        mol = Molecule(mol_structure.species, joined_coords)
        cnn = CovalentBondNN(tol=0.5)
        mol_graph = MoleculeGraph.with_local_env_strategy(mol, cnn)

        # Check if all the atoms in the molecule are connected
        all_connected = True

        for i in range(len(mol)):
            connected_sites = mol_graph.get_connected_sites(i)
            if not connected_sites:
                all_connected = False
                break

        if not all_connected:
            st.write("Not all atoms are connected within the molecule.")
            st.pyplot(draw_molecule_graph(mol_graph))
            return None

        if centroid_option == 2:
            centroid = custom_centroid
        elif centroid_option == 3:
            lattice_vectors = atoms.get_cell()
            centroid = np.sum(lattice_vectors, axis=0) / 2
        else:
            centroid = mol.center_of_mass

        rotation_mat = rotation_matrix(axis, angle_rad)
        symmop = SymmOp.from_rotation_and_translation(rotation_mat, translation_vec=(0, 0, 0))

        # Apply the rotation to the molecule
        rotated_coords = []
        for coord in mol.cart_coords:
            coord = coord - centroid  # Translate the molecule so that the centroid is at the origin
            coord = symmop.operate(coord)
            rotated_coords.append(coord + centroid)  # Translate the molecule back to its original position

        # Update the rotated atomic positions in the original ASE Atoms object
        for i, coord in enumerate(rotated_coords):
            rotated_atoms.positions[molecule[i]] = coord

    return rotated_atoms

def get_com(atoms, molecules, scale_choice = False):
    selected_atoms = atoms.copy()
    centroid_list = []

    for index in range(len(molecules)):
        molecule = molecules[index]
        molecule_atoms = selected_atoms[molecule]

        for j, atom1 in enumerate(molecule_atoms):
            for k, atom2 in enumerate(molecule_atoms):
                if j != k:
                    diff = atom2.position - atom1.position
                    for vec in np.eye(3):  # loop over unit vectors (x, y, z)
                        cell_vec = np.dot(vec, atoms.cell)
                        img_diff = diff - cell_vec
                        if np.linalg.norm(img_diff) < np.linalg.norm(diff):
                            molecule_atoms.positions[k] = atom2.position - cell_vec
                            diff = img_diff


        centroid_list.append(molecule_atoms.get_center_of_mass(scaled=scale_choice))

    return centroid_list

def plot_dipole_moment_vectors(direction_df, atoms, chosen_molecules, camera_pos):
    fig = go.Figure()

    # Define a list of colors to be used for the cones
    colors = ['blueviolet', 'brown', 'burlywood', 'cadetblue', 'chartreuse',
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



    # Define a dictionary to map atom types to their corresponding colors
    atom_colors = {'N': 'darkgreen', 'O': 'crimson', 'F': 'goldenrod', 'I':'mediumvioletred', 'Pb':'black'}

    for index, (row, molecules) in enumerate(zip(direction_df.iterrows(), chosen_molecules)):
        _, row = row
        mol_index = row['Molecule Index']
        com = row['Center of Mass']
        dm_vector = row['Dipole Moment Vector']

        # Choose a color for the cone based on the index
        cone_color = colors[index % len(colors)]

        # Add arrows for dipole moment vectors
        fig.add_trace(
            go.Cone(
                x=[com[0]], y=[com[1]], z=[com[2]],
                u=[dm_vector[0]], v=[dm_vector[1]], w=[dm_vector[2]],
                sizemode='absolute',
                sizeref=2,
                anchor='tail',
                text=f"Molecule {mol_index}",
                showlegend=True,
                name=f"Molecule {mol_index}",
                colorscale=[[0, cone_color], [1, cone_color]],
                showscale=False
            )
        )

        # Plot atomic positions relative to the COM
        mol_obj = get_molecule_object(atoms, molecules)
        for site in mol_obj:
            atom_type = site.species_string

            # Skip plotting hydrogen atoms
            if atom_type == 'H':
                continue

            position = site.coords
            atom_color = atom_colors.get(atom_type, cone_color)

            # Set opacity and size based on atom type
            atom_opacity = 0 if atom_type == 'C' else 0
            atom_size = 5 if atom_type == 'C' else 6 if atom_type == 'F' else 7

            fig.add_trace(
                go.Scatter3d(
                    x=[position[0]], y=[position[1]], z=[position[2]],
                    mode='markers',
                    marker=dict(size=atom_size, color=atom_color, opacity=atom_opacity),
                    showlegend=False
                )
            )

    # Set axis labels
    fig.update_layout(scene=dict(xaxis_title='X (Å)', yaxis_title='Y (Å)', zaxis_title='Z (Å)',xaxis=dict(tickfont=dict(size=15)),
        yaxis=dict(tickfont=dict(size=15)),
        zaxis=dict(tickfont=dict(size=15))),font=dict(size=18))

    # Set the figure size to 900x900 pixels
    fig.update_layout(height=900, width= 1600)
    fig.layout.scene.camera = {'eye': {'x': camera_pos[0], 'y': camera_pos[1], 'z': camera_pos[2]}}
    fig.layout.scene.camera.projection.type = "orthographic"

    # Show the 3D plot using Streamlit
    return fig

def create_3d_scatter_plot(df, title, box_vectors):
    fig = go.Figure()

    for i, row in df.iterrows():
        fig.add_trace(go.Scatter3d(x=[row['a']], y=[row['b']], z=[row['c']], mode='markers+text', text=[i],
                                   textposition='top center'))

    fig.update_layout(scene=dict(xaxis_title='a', yaxis_title='b', zaxis_title='c'), title=title, width=600, height=600 )

    # Draw the unit cell box
    for i in range(3):
        start = box_vectors[i]
        end = np.sum([box_vectors[j % 3] for j in range(i + 1, i + 3)], axis=0)
        fig.add_trace(go.Scatter3d(x=[start[0], end[0]], y=[start[1], end[1]], z=[start[2], end[2]], mode='lines',
                                   line=dict(color='black')))
    for v1, v2 in [(box_vectors[0], box_vectors[1]), (box_vectors[0], box_vectors[2]),
                   (box_vectors[1], box_vectors[2])]:
        fig.add_trace(
            go.Scatter3d(x=[v1[0], v1[0] + v2[0]], y=[v1[1], v1[1] + v2[1]], z=[v1[2], v1[2] + v2[2]], mode='lines',
                         line=dict(color='black')))
        fig.add_trace(
            go.Scatter3d(x=[v2[0], v1[0] + v2[0]], y=[v2[1], v1[1] + v2[1]], z=[v2[2], v1[2] + v2[2]], mode='lines',
                         line=dict(color='black')))

    return fig

from ase.geometry import wrap_positions


def get_distance_matrix(modified_atoms, molecules):
    scale_choice = False
    centroids = np.array(get_com(modified_atoms, molecules, scale_choice))
    lattice_vectors = modified_atoms.get_cell()

    # Wrap centroids inside the unit cell boundary
    centroids = wrap_positions(centroids, cell=lattice_vectors)

    if scale_choice:
        centroids_frac = np.dot(np.linalg.inv(lattice_vectors.T), centroids.T).T
        centroids_frac %= 1
        centroids = np.dot(lattice_vectors.T, centroids_frac.T).T

    # Create a pandas DataFrame for centroids
    df_centroids = pd.DataFrame(centroids, columns=['a', 'b', 'c'])
    df_centroids.index = [f'Molecule {i}' for i in range(1, len(centroids) + 1)]

    # Calculate the true center of the unit cell
    unit_cell_center = np.sum(lattice_vectors, axis=0) / 2

    if scale_choice:
        unit_cell_center = np.dot(np.linalg.inv(lattice_vectors.T), unit_cell_center)

    df_centroids.loc['Unit Cell Center'] = unit_cell_center

    # Calculate distances with periodic boundary conditions
    positions = np.vstack([centroids, unit_cell_center[np.newaxis, :]])
    distances = get_distances(positions, cell=lattice_vectors, pbc=True)[1][-1, :-1]

    # Create a DataFrame for distances
    df_distances = pd.DataFrame(distances.reshape(-1, 1), columns=['Distance'],
                                index=[f'Molecule {i}' for i in range(1, len(centroids) + 1)])

    # Merge the DataFrames
    df_merged = df_centroids.copy()
    df_merged['Distance'] = df_distances['Distance']

    # Print the distance matrix
    distance_matrix = positions[:-1] - unit_cell_center
    wrapped_distance_matrix = wrap_positions(distance_matrix, cell=lattice_vectors)
    df_distance_matrix = pd.DataFrame(wrapped_distance_matrix, columns=['a', 'b', 'c'],
                                      index=[f'Molecule {i}' for i in range(1, len(centroids) + 1)])

    # # Use Streamlit column containers to display the dfs
    # col1, col2 = st.columns(2)
    # with col1:
    #     st.dataframe(df_merged, use_container_width=True)
    # with col2:
    #     st.write("Distance Matrix (vector format):", df_distance_matrix)

    return df_centroids, df_distance_matrix, lattice_vectors, df_merged


import itertools

def find_closest_partners(df_centroids, lattice_vectors, initial_threshold=1e-3, max_iterations=1):
    def distance_from_line(point, line_point1, line_point2):
        line_vec = line_point2 - line_point1
        point_vec = point - line_point1
        line_unit_vec = line_vec / np.linalg.norm(line_vec)
        proj = point_vec.dot(line_unit_vec)
        proj_point = line_point1 + proj * line_unit_vec
        return np.linalg.norm(point - proj_point), proj_point

    found_partners = [False] * len(df_centroids)
    partners = {}
    lattice_center = df_centroids.loc['Unit Cell Center']
    threshold = initial_threshold
    longest_direction = np.argmax(np.linalg.norm(lattice_vectors, axis=1))

    progress_text = st.empty()
    progress_bar = st.progress(0)

    for iteration in range(max_iterations):
        for idx, (label, centroid) in enumerate(df_centroids.iloc[:-1].iterrows()):
            if not found_partners[idx]:
                min_distance = float("inf")
                closest_partner = None
                translation = None

                for idx2, (label2, centroid2) in enumerate(df_centroids.iloc[:-1].iterrows()):
                    if not found_partners[idx2] and idx != idx2:
                        for a, b, c in itertools.product(range(-1, 2), range(-1, 2), range(-1, 2)):
                            shift = np.dot(lattice_vectors.T, np.array([a, b, c]))
                            shifted_centroid = centroid2 + shift
                            if (a, b, c) == (0, 0, 0) or (a, b, c)[longest_direction] != 0:
                                distance, proj_point = distance_from_line(shifted_centroid, centroid, lattice_center)
                                if distance < min_distance:
                                    min_distance = distance
                                    closest_partner = label2
                                    translation = proj_point - centroid2

                if min_distance <= threshold:
                    partners[label] = (closest_partner, translation)
                    found_partners[idx] = True
                    found_partners[df_centroids.index.get_loc(closest_partner)] = True

        if all(found_partners):
            break

        threshold *= 2
        progress_text.text(f"Iteration {iteration + 1}")
        progress_bar.progress((iteration + 1) / max_iterations)

    formatted_partners = {
        key: f"{value[0]} should be moved {value[1][0]:.4f} Angstrom in X direction, "
             f"{value[1][1]:.4f} Angstrom in Y direction, and {value[1][2]:.4f} Angstrom in Z direction "
             f"to meet its partner, {key}."
        for key, value in partners.items()
    }

    return formatted_partners


def find_translation_to_restore_symmetry(df_centroids, lattice_vectors, threshold=1e-3):
    required_translations = {}
    found_inversion_partners = [False] * len(df_centroids)
    lattice_center = df_centroids.loc['Unit Cell Center']

    # Generate periodic images of the centroids
    periodic_images = []
    for i in range(-1, 2):
        for j in range(-1, 2):
            for k in range(-1, 2):
                if not (i == 0 and j == 0 and k == 0):
                    shift = np.dot(lattice_vectors.T, np.array([i, j, k]))
                    periodic_images.append(df_centroids.iloc[:-1] + shift)

    output = []
    for idx, (label, centroid) in enumerate(df_centroids.iloc[:-1].iterrows()):
        if not found_inversion_partners[idx]:
            inversion_partner = -centroid + 2 * lattice_center
            min_distance = float("inf")
            closest_partner = None

            for idx2, (label2, centroid2) in enumerate(df_centroids.iloc[:-1].iterrows()):
                if not found_inversion_partners[idx2] and idx != idx2:
                    for image in periodic_images:
                        image_centroid = image.loc[label2]
                        distance = np.linalg.norm(inversion_partner - image_centroid)
                        if distance < min_distance:
                            min_distance = distance
                            closest_partner = label2

            if min_distance > threshold:
                translation = (inversion_partner - df_centroids.loc[closest_partner]) / 2
                required_translations[label] = translation
            else:
                translation = (inversion_partner - df_centroids.loc[closest_partner]) / 2
                output.append(f"Possible partner pair: {label}, {closest_partner}")
                output.append(f"Keep {label} unchanged, move {closest_partner} by {translation} angstroms")

    return required_translations, output


def print_space_group(atoms, symprec=1e-3):
    space_group = get_spacegroup(atoms, symprec=symprec)
    formatted_space_group = f"Space Group: {space_group}"
    return formatted_space_group

# def write_cif_with_higher_symmetry(atoms, symprec_lower, symprec_upper, selected_option):
#     if symprec_lower != symprec_upper:
#         symprec_values = np.linspace(symprec_lower, symprec_upper, 6)
#     else:
#         symprec_values = [symprec_lower]

#     space_groups = []
#     for symprec in symprec_values:
#         space_group = get_spacegroup(atoms, symprec=symprec)
#         space_groups.append(space_group)

#     space_group_strings = [f"Tolerance: {symprec:.4f} - Space group: {space_group.symbol}"
#                            for symprec, space_group in zip(symprec_values, space_groups)]

#     selected_index = space_group_strings.index(selected_option)
#     selected_symprec = symprec_values[selected_index]
#     selected_space_group = space_groups[selected_index]

#     lattice, scaled_positions, numbers = spglib.standardize_cell(atoms, to_primitive=False, no_idealize=False, symprec=selected_symprec)

#     standardized_atoms = Atoms(cell=lattice, scaled_positions=scaled_positions, numbers=numbers)
#     standardized_atoms.info['spacegroup'] = selected_space_group

#     return standardized_atoms, selected_symprec
def calculate_space_groups(atoms, symprec_lower, symprec_upper, angle_tol):
    symprec_list = np.linspace(symprec_lower, symprec_upper, 6)
    space_groups = []

    for symprec in symprec_list:
        try:
            structure = AseAtomsAdaptor.get_structure(atoms)
            space_group_an = SpacegroupAnalyzer(structure, symprec=symprec, angle_tolerance=angle_tol)
            space_group_symbol = space_group_an.get_space_group_symbol()
            point_group_symbol = space_group_an.get_point_group_symbol()
            if space_group_symbol is not None:
                space_groups.append((space_group_symbol, point_group_symbol))
            else:
                space_groups.append('Not found')
        except Exception as e:
            space_groups.append(f"Not found (tolerance too high)")
    return symprec_list, space_groups


def get_space_group_strings(symprec_list, space_groups):
    return [f"Tolerance: {symprec:.4f} - Space group: {sg[0]}, Point group: {sg[1]}"
            if sg != 'Not found' and sg != 'Not found (tolerance too high)'
            else f"Tolerance: {symprec:.4f} - {sg}"
            for symprec, sg in zip(symprec_list, space_groups)]

def extract_symprec_from_string(selected_string):
    try:
        # Assuming the string format is "Tolerance: {symprec:.4f} - Space group: {space_group}"
        selected_symprec_str = selected_string.split(' - ')[0].replace('Tolerance: ', '')
        return float(selected_symprec_str)
    except (IndexError, ValueError) as e:
        raise ValueError(f"Failed to extract symprec: {e}")

def generate_symmetrized_structure(atoms, symprec, angle_tol):
    structure = AseAtomsAdaptor.get_structure(atoms)
    space_group_analyzer = SpacegroupAnalyzer(structure, symprec=symprec, angle_tolerance=angle_tol)
    return space_group_analyzer.get_symmetrized_structure()



def translate_molecule(atoms, molecules, scope_choice, selected_indices, axes_choice, translation_distances):
    if scope_choice == 'molecules':
        selected_atoms = [molecules[index - 1] for index in selected_indices]
    else:
        selected_atoms = [[index - 1] for index in selected_indices]

    if axes_choice == 'custom':
        axis, distance = list(translation_distances.items())[0]
        translation_vector = np.array(axis) * distance
    else:
        valid_axes = ['x', 'y', 'z']
        translation_vector = np.zeros(3)
        for axis, distance in translation_distances.items():
            axis_index = valid_axes.index(axis)
            translation_vector[axis_index] = distance

    translated_atoms = atoms.copy()

    for atom_group in selected_atoms:
        group_atoms = translated_atoms[atom_group]

        new_positions = group_atoms.positions + translation_vector
        group_atoms.set_positions(new_positions, apply_constraint=False)

        for i in range(len(atom_group)):
            translated_atoms.positions[atom_group[i]] = group_atoms.positions[i]

    return translated_atoms

def delete_molecules(atoms, molecules, molecule_indices):

    molecule_indices = [int(index) - 1 for index in molecule_indices]

    atoms_to_remove = [molecules[index] for index in molecule_indices]
    atoms_to_remove = [item for sublist in atoms_to_remove for item in sublist] # Flatten the list

    modified_atoms = atoms.copy()
    modified_atoms = modified_atoms[[i for i in range(len(atoms)) if i not in atoms_to_remove]]

    return modified_atoms

def find_twofold_rotation_axes(initial_space_group, final_space_group):
    initial_sg_analyzer = SpacegroupAnalyzer(Structure.from_spacegroup(initial_space_group, Lattice.cubic(1), "X", [[0, 0, 0]]))
    final_sg_analyzer = SpacegroupAnalyzer(Structure.from_spacegroup(final_space_group, Lattice.cubic(1), "X", [[0, 0, 0]]))

    initial_symm_ops = initial_sg_analyzer.get_symmetry_operations()
    final_symm_ops = final_sg_analyzer.get_symmetry_operations()

    lost_operations = [op for op in initial_symm_ops if op not in final_symm_ops]
    twofold_rotation_axes = []

    for op in lost_operations:
        rotation_matrix = op.rotation_matrix
        if is_two_fold_rotation(rotation_matrix):
            axis = find_rotation_axis(rotation_matrix)
            if axis not in twofold_rotation_axes:
                twofold_rotation_axes.append(axis)

    return twofold_rotation_axes
def create_labelled_download_file(atoms, file_name, output_suffix):
    output_labelled_buffer = io.StringIO()
    write_modified_aims_file(atoms, output_labelled_buffer)
    output_labelled_content = output_labelled_buffer.getvalue()
    download_name = f"{os.path.splitext(file_name)[0]}{output_suffix}_labelled.in"
    st.download_button(
        label=f"Download {download_name}",
        data=output_labelled_content,
        file_name=download_name,
        mime="text/plain",
        key=f"download_labelled_{download_name}",
    )

def create_aims_download_file(atoms, file_name, output_suffix):
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".in", delete=False) as output_file:
        try:
            write(output_file.name, atoms, format='aims')
            output_file.seek(0)
            output_content = output_file.read()
        finally:
            output_file.close()
            os.unlink(output_file.name)

    download_name = f"{os.path.splitext(file_name)[0]}{output_suffix}.in"
    st.download_button(
        label=f"Download {download_name}",
        data=output_content,
        file_name=download_name,
        mime="text/plain",
        key=f"download_aims_{download_name}",
    )

def get_download_link(file_name, content):
    if isinstance(content, str):
        content_encoded = content.encode("utf-8")
    elif isinstance(content, bytes):
        content_encoded = content
    else:
        raise ValueError("Invalid content type. Must be a str or bytes object.")

    b64 = base64.b64encode(content_encoded).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{file_name}">Download {file_name}</a>'
    return href


def data_download_links(data_frame, file_name):
    csv_data = data_frame.to_csv(index=False)
    txt_data = data_frame.to_csv(index=False, sep='\t')
    tsv_data = data_frame.to_csv(index=False, sep='\t')

    csv_link = get_download_link(f'{file_name}.csv', csv_data)
    txt_link = get_download_link(f'{file_name}.txt', txt_data)
    tsv_link = get_download_link(f'{file_name}.tsv', tsv_data)



    return csv_link, txt_link, tsv_link

def process_uploaded_files(file_buffer1, file_buffer2):
    file_name1 = file_buffer1.name
    file_name2 = file_buffer2.name
    file_format1 = get_file_format(file_name1)
    file_format2 = get_file_format(file_name2)

    try:
        atoms1, _, _ = initialize_structure(file_buffer1, file_format=file_format1, file_name=file_buffer1.name)
        atoms2, _, _ = initialize_structure(file_buffer2, file_format=file_format2, file_name=file_buffer2.name)
    except Exception as e:
        st.error(f"Error: {e}")
        return None, None, None, None

    return atoms1, atoms2, file_name1, file_name2

def generate_labelled_cif(structure, file_name):
    cif_writer = CifWriter(structure, write_magmoms=True)
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".cif", delete=False) as output_file:
        cif_writer.write_file(output_file.name)
        output_file.seek(0)
        with open(output_file.name, "r") as f:
            output_content = f.read()
            st.markdown(get_download_link(file_name, output_content), unsafe_allow_html=True)

def create_interpolated_structures_zip(interpolated_atoms):
    with tempfile.NamedTemporaryFile(mode="w+b", suffix=".zip", delete=False) as output_file:
        with zipfile.ZipFile(output_file, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for i, atoms in enumerate(interpolated_atoms[:-1], start=1):
                temp_structure_file = f"interpolated_structure_{i}.in"

                # Create a temporary file for the AIMS structure
                with tempfile.NamedTemporaryFile(mode="w+t", suffix=".in", delete=False) as temp_atoms_file:
                    # Write the AIMS structure to the temporary file
                    write(temp_atoms_file.name, atoms, format='aims')

                    # Add the temporary AIMS file to the ZIP file
                    zf.write(temp_atoms_file.name, temp_structure_file)

                # Remove the temporary AIMS file
                os.remove(temp_atoms_file.name)

        # Create a download link for the ZIP file
        output_file.seek(0)
        output_content = output_file.read()
        st.markdown(get_download_link(f"interpolated_structures.zip", output_content), unsafe_allow_html=True)

def merge_structures(lattice_a, lattice_b):
    # Step 1: Calculate fractional coordinates of atoms in lattice A
    fractional_coords_a = lattice_a.get_scaled_positions()

    # Step 2: Convert fractional coordinates to Cartesian coordinates using lattice vectors of lattice B
    cartesian_coords_c = fractional_coords_a.dot(lattice_b.get_cell())

    # Step 3: Create a new lattice C with lattice vectors from B and updated atomic positions
    lattice_c = Atoms(symbols=lattice_a.get_chemical_symbols(),
                      positions=cartesian_coords_c,
                      cell=lattice_b.get_cell(),
                      pbc=lattice_b.get_pbc())

    # Step 4: Add atoms from lattice B to the new lattice C
    lattice_c.extend(lattice_b)

    return lattice_c

def merge_and_create_zip(rotated_organic_structures, inorganic_interpolated_structures):
    interpolated_atoms = []
    for (organic_structure, angle_deg), inorganic_structure in zip(rotated_organic_structures,
                                                                   inorganic_interpolated_structures):
        merged_structure = merge_structures(organic_structure, inorganic_structure)
        interpolated_atoms.append((merged_structure, angle_deg))

    output_file = tempfile.NamedTemporaryFile(mode="w+b", suffix=".zip", delete=False)
    output_file.close()

    with zipfile.ZipFile(output_file.name, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for i, (atoms, angle_deg) in enumerate(interpolated_atoms, start=1):
            temp_structure_file = f"interpolated_structure_{i}_rot{angle_deg:.1f}deg.in"

            # Create a temporary file for the AIMS structure
            with tempfile.NamedTemporaryFile(mode="w+t", suffix=".in", delete=False) as temp_atoms_file:
                # Write the AIMS structure to the temporary file
                write(temp_atoms_file.name, atoms, format='aims')

                # Add the temporary AIMS file to the ZIP file
                zf.write(temp_atoms_file.name, temp_structure_file)

                # Remove the temporary AIMS file
            os.remove(temp_atoms_file.name)

    # Create a download link for the ZIP file
    with open(output_file.name, 'rb') as f:
        output_content = f.read()
    st.markdown(get_download_link(f"Trans_Rot_structures.zip", output_content), unsafe_allow_html=True)
    os.remove(output_file.name)

def print_detected_molecules(modified_symbols, molecules, structure_type):
    molecule_list = []

    for i, molecule in enumerate(molecules, 1):
        molecule_labels = [modified_symbols[mol_atom] for mol_atom in molecule]
        molecule_list.append(f"Molecule {i}: {', '.join(molecule_labels)}")

    molecule_list_formatted = "\n".join(molecule_list)
    st.write(f"Detected molecules in {structure_type}:")
    st.markdown(f"```\n{molecule_list_formatted}\n```")

def process_file_and_print_molecules(file_buffer, structure_type):
    file_name = file_buffer.name
    file_format = get_file_format(file_name)

    atoms, molecules, modified_symbols = initialize_structure_v2(file_buffer, file_format=file_format)

    print_detected_molecules(modified_symbols, molecules, structure_type)

    return atoms, molecules

def generate_substructure(atoms, molecules, inorganic_indices):
    inorganic_indices = [int(index) - 1 for index in inorganic_indices]

    inorganic_atoms = []
    organic_atoms = []
    for i, molecule in enumerate(molecules):
        if i in inorganic_indices:
            inorganic_atoms.extend(molecule)
        else:
            organic_atoms.extend(molecule)

    inorganic = atoms[inorganic_atoms]
    organic = atoms[organic_atoms]

    return organic, inorganic

def rotate_organic_molecules(organic_initial, molecules, n, rotate_indices, axis):
    molecule_indices = rotate_indices
    molecule_indices = [int(index) - 1 for index in molecule_indices]

    rotated_organic_structures = []

    for i in range(n + 1):
        angle_deg = (180 / n) * i
        # st.write(angle_deg)

        angle_rad = np.deg2rad(angle_deg)

        rotated_organic = organic_initial.copy()

        for index in molecule_indices:

            molecule = molecules[index]

            molecule_atoms = rotated_organic[molecule]

            for j, atom1 in enumerate(molecule_atoms):
                for k, atom2 in enumerate(molecule_atoms):
                    if j != k:
                        diff = atom2.position - atom1.position
                        for vec in np.eye(3):  # loop over unit vectors (x, y, z)
                            cell_vec = np.dot(vec, organic_initial.cell)
                            img_diff = diff - cell_vec
                            if np.linalg.norm(img_diff) < np.linalg.norm(diff):
                                molecule_atoms.positions[k] = atom2.position - cell_vec
                                diff = img_diff

            centroid = molecule_atoms.get_center_of_mass()

            rotation_mat = rotation_matrix(axis, angle_rad)
            new_positions = np.dot(molecule_atoms.positions - centroid, rotation_mat.T) + centroid
            molecule_atoms.set_positions(new_positions, apply_constraint=False)

            for j in range(len(molecule)):
                rotated_organic.positions[molecule[j]] = molecule_atoms.positions[j]

        rotated_organic_structures.append((rotated_organic, angle_deg))

    return rotated_organic_structures

def interpolate_inorganic_lattice(atoms1, atoms2, n):
    # Convert ASE Atoms objects to pymatgen Structure objects
    structure1 = AseAtomsAdaptor().get_structure(atoms1)
    structure2 = AseAtomsAdaptor().get_structure(atoms2)

    # Check if the number of atoms in both structures is the same
    if len(atoms1) != len(atoms2):
        st.write(f"initial_inorganic_length is {len(atoms1)}")
        st.write(f"final_inorganic_length is {len(atoms2)}")
        raise ValueError("The two structures have a different number of atoms.")

    # Initialize the StructureMatcher with primitive_cell set to False
    sm = StructureMatcher(primitive_cell=False, ltol = 0.2, stol = 0.5, angle_tol= 8)


    # Try to fit the two structures
    # st.write(structure1)
    # st.write(structure2.as_dict())
    # st.write(sm.fit(structure1, structure2))

    # structure2_a = AseAtomsAdaptor().get_atoms(structure2)
    # create_labelled_download_file(structure2_a, "structure2", "")


    # Match two structures (only works for translation)

    structure2_reordered = sm.get_s2_like_s1(structure1, structure2)
    # st.write(structure2_reordered.as_dict())
    structure2_reordered_a = AseAtomsAdaptor().get_atoms(structure2_reordered)
    # create_labelled_download_file(structure2_reordered_a, "structure2_reordered", "")

    # Interpolate between the two structures
    interpolated_structures = structure1.interpolate(structure2_reordered, nimages=n, autosort_tol=0.75,
                                                     interpolate_lattices=True)

    # Convert interpolated pymatgen Structure objects to ASE Atoms objects
    interpolated_atoms_list = [AseAtomsAdaptor().get_atoms(structure) for structure in interpolated_structures]

    interpolated_atoms_list.append(structure2_reordered_a)         # putting the final (centrosymmetric) structure at the end


    return interpolated_atoms_list

def extended_symmetry_info(atoms, symprec=1e-3):
    space_group_no = get_spacegroup(atoms, symprec=symprec).no
    space_group_info = SpaceGroup.from_int_number(space_group_no)
    space_group_info_lst = {}
    for idx, op in enumerate(space_group_info):
        space_group_info_lst[idx] = op

    formatted_space_group_info = f"Space Group: {space_group_info_lst}"
    return space_group_info_lst

# def rotate_part_of_molecule(mol_obj, pivot_point, angle, axis, centroid, atoms_to_rotate):

def get_perpendicular_axis(atoms, index1, index2, index3):
    # Get the positions of the three atoms
    pos1 = atoms[index1].position
    pos2 = atoms[index2].position
    pos3 = atoms[index3].position

    st.write(pos1)
    st.write(pos2)
    st.write(pos3)

    # Use periodic images if an index is repeated
    for i in range(3):
        if index1 == index2 or index1 == index3 or index2 == index3:
            indices = [index1, index2, index3]
            indices.remove(i)
            pos3[i] += atoms.get_cell()[i,i]

    # Calculate two vectors in the plane
    v1 = pos2 - pos1
    v2 = pos3 - pos1

    # Calculate the normal vector to the plane using the cross product
    normal = np.cross(v1, v2)

    # Calculate the angle between the normal vector and the z-axis
    z_axis = np.array([0, 0, 1])
    angle = get_angles(normal, z_axis, index1)

    # If the angle is close to 0 or 180 degrees, use the x-axis instead
    if np.isclose(angle, 0) or np.isclose(angle, np.pi):
        axis = np.array([1, 0, 0])
    else:
        # Calculate the axis perpendicular to the plane
        axis = np.cross(normal, z_axis)
        axis /= np.linalg.norm(axis)

    return axis


def generate_key(seed, suffix):
    hash_obj = hashlib.md5((seed + suffix).encode('utf-8'))
    return hash_obj.hexdigest()

class StopExecution(Exception):
    def _render_traceback_(self):
        pass
def atoms_to_speck(atoms, seed):
    key_x = generate_key(seed, 'supercell_x')
    key_y = generate_key(seed, 'supercell_y')
    key_z = generate_key(seed, 'supercell_z')
    key_sp_obj = generate_key(seed, 'sp_obj')

    supercell_x = st.slider("Supercell size in x direction:", 1, 3, 1, key=key_x)
    supercell_y = st.slider("Supercell size in y direction:", 1, 3, 1, key=key_y)
    supercell_z = st.slider("Supercell size in z direction:", 1, 3, 1, key=key_z)

    scaling_matrix = [[supercell_x, 0, 0], [0, supercell_y, 0], [0, 0, supercell_z]]
    supercell_atoms = make_supercell(atoms, scaling_matrix)

    formula = supercell_atoms.get_chemical_formula().format()
    num_atoms = len(supercell_atoms)

    output = f"{num_atoms}\n{formula}\n"

    for atom in supercell_atoms:
        output += f"{atom.symbol}    {atom.position[0]:.6f}    {atom.position[1]:.6f}    {atom.position[2]:.6f}\n"

    sp_obj = stspeck.Speck(
        data=output,
        brightness=0.55,
        atomShade=0.2,
        dofStrength=0.2,
        width="900px",
        height="800px",
        key=key_sp_obj
    )


    return sp_obj

def create_zip_with_rotated_structures(rotated_atoms_list, file_name):
    output_file = tempfile.NamedTemporaryFile(mode="w+b", suffix=".zip", delete=False)
    output_file.close()

    with zipfile.ZipFile(output_file.name, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for i, (atoms, angle_deg) in enumerate(rotated_atoms_list, start=1):
            temp_structure_file = f"{angle_deg:.2f}_deg/{file_name}_rotated_{angle_deg:.2f}_deg.in"

            # Create a temporary file for the AIMS structure
            with tempfile.NamedTemporaryFile(mode="w+t", suffix=".in", delete=False) as temp_atoms_file:
                # Write the AIMS structure to the temporary file
                write(temp_atoms_file.name, atoms, format='aims')

                # Add the temporary AIMS file to the ZIP file
                zf.write(temp_atoms_file.name, temp_structure_file)

                # Remove the temporary AIMS file
            os.remove(temp_atoms_file.name)

    # Create a download link for the ZIP file
    with open(output_file.name, 'rb') as f:
        output_content = f.read()
    st.markdown(get_download_link(f"{file_name}_rotated_structures.zip", output_content), unsafe_allow_html=True)
    os.remove(output_file.name)


def create_plot(source, x_key, y_key, title, x_axis_label, y_axis_label):
    plot = figure(title=title, x_axis_label=x_axis_label, y_axis_label=y_axis_label)

    x = source.data[x_key]
    y = source.data[y_key]

    # Catmull-Rom spline interpolation
    interpolator = PchipInterpolator(x, y)
    new_x = np.linspace(x.min(), x.max(), 100)
    new_y = interpolator(new_x)

    plot.line(new_x, new_y, line_color='dodgerblue', line_width=2)
    plot.circle(x_key, y_key, size=14, source=source, color='crimson')

    plot.xaxis.axis_label_text_font_size = "16pt"
    plot.yaxis.axis_label_text_font_size = "16pt"
    plot.xaxis.major_label_text_font_size = "13pt"
    plot.yaxis.major_label_text_font_size = "13pt"

    # Make axis tick labels bold
    plot.xaxis.major_label_text_font_style = "bold"
    plot.yaxis.major_label_text_font_style = "bold"

    hover = HoverTool(tooltips=[(x_axis_label, f"@{x_key}"), ("Value", f"@{y_key} μC/cm²")])
    plot.add_tools(hover)

    # Modify axis properties to create a black-bordered box
    plot.outline_line_color = 'black'
    plot.outline_line_width = 2

    plot.xaxis.axis_line_color = 'black'
    plot.xaxis.axis_line_width = 2
    plot.yaxis.axis_line_color = 'black'
    plot.yaxis.axis_line_width = 2

    plot.xaxis.major_tick_line_color = 'black'
    plot.yaxis.major_tick_line_color = 'black'
    plot.xaxis.minor_tick_line_color = 'black'
    plot.yaxis.minor_tick_line_color = 'black'

    return plot

def plot_pol_figure(data, parameter_name, parameter_unit):
    # Sort the data by the 'Parameter' column
    data = data.sort_values(by="Parameter")

    data_x = dict(Parameter=data["Parameter"], Value=data["Px"]*100)
    data_y = dict(Parameter=data["Parameter"], Value=data["Py"]*100)
    data_z = dict(Parameter=data["Parameter"], Value=data["Pz"]*100)
    data_e = dict(Parameter=data["Parameter"], Value=data["Et"])

    source_x = ColumnDataSource(data=data_x)
    source_y = ColumnDataSource(data=data_y)
    source_z = ColumnDataSource(data=data_z)
    source_e = ColumnDataSource(data=data_e)

    p1 = create_plot(source_x, "Parameter", "Value", "Polarization X", f"{parameter_name} ({parameter_unit})", "Polarization (μC/cm²)")
    p2 = create_plot(source_y, "Parameter", "Value", "Polarization Y", f"{parameter_name} ({parameter_unit})", "Polarization (μC/cm²)")
    p3 = create_plot(source_z, "Parameter", "Value", "Polarization Z", f"{parameter_name} ({parameter_unit})", "Polarization (μC/cm²)")
    et = create_plot(source_e, "Parameter", "Value", "Total Energy", f"{parameter_name} ({parameter_unit})",
                     "Energy (eV)")

    # # Display the Bokeh plots in Streamlit
    # plots = row(p1, p2, p3, et)
    # make a grid
    plots = gridplot([[p1, p2], [p3, et]])
    st.bokeh_chart(plots)

def extract_polarization(content: str):
    for line in content.split("\n"):
        if "| Cartesian Polarization" in line:
            _, _, _, x, y, z = line.split()
            return float(x), float(y), float(z)
    return None, None, None

def extract_totalenergy(content: str):
    for line in content.split("\n"):
        if "| Total energy of the DFT / Hartree-Fock s.c.f. calculation      :" in line:
            Et = line.split()
            return float(Et[11])
    return None

def rotate_molecules_individually(atoms, molecules, rotation_parameters):
    rotated_atoms = atoms.copy()

    for i, (molecule, (axis, angle, centroid_option, custom_centroid)) in enumerate(zip(molecules, rotation_parameters)):
        rotated_atoms = rotate_molecules(rotated_atoms, molecules, [i], axis, angle, centroid_option, custom_centroid)

    return rotated_atoms


import numpy as np
from ase.spacegroup import crystal


def plane_params_from_hkl(atoms, hkl):
    """
    Calculate the normal vector and origin point for a crystal plane given by its hkl indices.

    Args:
        atoms (ASE Atoms object): An object representing a collection of atoms and their properties.
        hkl (tuple or list): A tuple or list containing the Miller indices (h, k, l) of the crystal plane.

    Returns:
        normal_vector (numpy array): A 3x1 array representing the normal to the plane of reflection.
        origin_point (numpy array): A 3x1 array representing a point on the plane of reflection.
    """
    # Calculate the reciprocal lattice vector
    reciprocal_lattice = 2 * np.pi * np.linalg.inv(atoms.cell).T
    g = reciprocal_lattice.dot(hkl)

    # Calculate the normal vector to the plane
    normal_vector = g / np.linalg.norm(g)

    # Calculate the origin point on the plane
    frac_coords = np.array([0.0, 0.0, 0.0])
    max_index = np.argmax(hkl)  # Use NumPy function argmax() to get the index of the maximum value in hkl
    frac_coords[max_index] = 0.5
    origin_point = atoms.cell.dot(frac_coords)

    return normal_vector, origin_point


def reflect_molecules(atoms, molecule, mol_obj, normal_vector, origin_point, atoms_not_to_reflect=None):
    reflected_atoms = atoms.copy()

    # Create a set of indices not to reflect for faster lookups
    if atoms_not_to_reflect is None:
        atoms_not_to_reflect = set()
    else:
        atoms_not_to_reflect = set(atoms_not_to_reflect)

    symmop = SymmOp.reflection(normal_vector, origin_point)

    # Apply the reflection to the molecule
    reflected_coords = []
    for i, coord in enumerate(mol_obj.cart_coords):
        if i not in atoms_not_to_reflect:
            coord = symmop.operate(coord)
        reflected_coords.append(coord)

    # Update the rotated atomic positions in the original ASE Atoms object
    for i, coord in enumerate(reflected_coords):
        reflected_atoms.positions[molecule[i]] = coord

    return reflected_atoms

def get_atom_labels(atoms, molecule):
    return [(idx, f"{atom.symbol} {idx + 1}") for idx, atom in zip(molecule, atoms[molecule])]

def find_local_indices(molecule, selected_global_indices):
    return [molecule.index(global_idx) for global_idx in selected_global_indices]


def filter_atoms_by_symbols_and_extend(atoms, A, B, A2=None, s_size=3):
    A2_indices = []

    # If A2 is provided, change labels of A2 atoms to A and record A2 indices
    if A2 is not None:
        all_symbols = atoms.get_chemical_symbols()
        for idx, sym in enumerate(all_symbols):
            if sym == A2:
                A2_indices.append(idx)
                all_symbols[idx] = A
        atoms.set_chemical_symbols(all_symbols)

    # Filter out A and B atoms
    all_symbols = atoms.get_chemical_symbols()
    all_positions = atoms.get_positions()

    new_symbols = [sym for sym in all_symbols if sym == A or sym == B]
    new_positions = [pos for sym, pos in zip(all_symbols, all_positions) if sym == A or sym == B]

    new_atoms = Atoms(symbols=new_symbols, positions=new_positions, cell=atoms.cell, pbc=atoms.pbc)

    # Create a supercell
    new_atoms_ext = new_atoms * (s_size, s_size, s_size)  # Extending from -1.5 to 1.5 in all directions

    # Convert to Cartesian coordinates if not already
    new_atoms_ext.set_positions(new_atoms_ext.get_positions(wrap=True))

    # Create a dictionary to track new atom indices from periodic images
    periodic_image_dict = {index: [] for index in range(len(new_atoms))}
    for super_index, super_atom in enumerate(new_atoms_ext):
        original_index = super_index % len(new_atoms)
        periodic_image_dict[original_index].append(super_index)  # Mapping new index to corresponding original index

    return new_atoms_ext, periodic_image_dict, A2_indices


def identify_AB_groups(atoms, A: str, B: str, b=0, c=0):
    # Step 1: Detect Molecules
    molecules = detect_molecules(atoms, b=b)

    # Initialize dictionaries
    AB_groups = {}
    AB_distance_groups = {}

    # Step 2: Initial collection of A-B groups without rule checks
    for molecule in molecules:
        A_indices = [idx for idx in molecule if atoms[idx].symbol == A]
        B_indices = [idx for idx in molecule if atoms[idx].symbol == B]

        for A_index in A_indices:
            AB_groups[A_index] = B_indices

    # Step 3: Filter based on A-B distance < 3.5 Angstrom
    coords = atoms.get_positions()
    filtered_AB_groups = {}
    for A_index, B_indices in AB_groups.items():
        A_coords = coords[A_index]
        B_coords = coords[B_indices]
        dists = get_distances(A_coords.reshape(1, 3), B_coords)[1][0]

        # Keep B_indices that are closer than 3.5 Angstrom to A
        valid_B_indices_and_dists = [(B_indices[i], dists[i]) for i in np.where(dists < 3.5 + c)[0]]

        if len(valid_B_indices_and_dists) == 6:
            valid_B_indices = [idx for idx, _ in valid_B_indices_and_dists]
            filtered_AB_groups[A_index] = valid_B_indices
            AB_distance_groups[A_index] = valid_B_indices_and_dists

    return filtered_AB_groups, AB_distance_groups


def filter_unique_distances(AB_distance_groups):
    unique_distances = defaultdict(list)
    unique_filtered = {}

    # Populate dictionary with distances as keys, and list of (A_index, B_index) as values
    for A_index, dist_tuples in AB_distance_groups.items():
        for B_index, dist in dist_tuples:
            rounded_dist = round(dist, 4)  # Round to four decimal places
            unique_distances[rounded_dist].append((A_index, B_index))

    # Sort and filter for unique distances
    for dist, AB_pairs in unique_distances.items():
        sorted_AB_pairs = sorted(AB_pairs, key=lambda x: x[0])  # Sort by A_index
        unique_filtered[dist] = sorted_AB_pairs[0]  # Take the smallest A_index

    return unique_filtered


def find_matching_distances(atoms, A, B, unique_filtered, A2_indices=None, A2_symbol=None):
    data = []

    A_indices = [i for i, atom in enumerate(atoms) if atom.symbol == A]
    B_indices = [i for i, atom in enumerate(atoms) if atom.symbol == B]

    for A_index in A_indices:
        for B_index in B_indices:
            dist = atoms.get_distance(A_index, B_index, mic=True)
            rounded_dist = round(dist, 4)

            data.append([A_index, B_index, rounded_dist])

    df = pd.DataFrame(data, columns=['A_index', 'B_index', 'Distance'])

    matching_rows = df[df['Distance'].isin(unique_filtered.keys())]

    unique_distances = {}
    for _, row in matching_rows.iterrows():
        A_index = int(row['A_index'])
        B_index = int(row['B_index'])
        distance = row['Distance']

        # Check if A_index is in A2_indices and update symbol if needed
        current_A_symbol = A2_symbol if A2_indices is not None and A_index in A2_indices else A
        B_symbol = atoms[B_index].symbol

        Atom1 = f"{current_A_symbol}{A_index + 1}"
        Atom2 = f"{B_symbol}{B_index + 1}"

        if distance not in unique_distances.keys() or A_index < unique_distances[distance]['A_index']:
            unique_distances[distance] = {'A_index': A_index, 'Atom1': Atom1, 'Atom2': Atom2, 'Distance': distance}

    sorted_data = sorted(unique_distances.values(), key=lambda x: x['A_index'])
    output_df = pd.DataFrame(sorted_data).drop(columns=['A_index'])

    return output_df


def find_third_atom_distances_with_cutoff(atoms, Atom1, Atom2, min_cutoff, max_cutoff):
    Atom1_indices = [atom.index for atom in atoms if atom.symbol == Atom1]
    Atom2_indices = [atom.index for atom in atoms if atom.symbol == Atom2]

    all_data = []
    unique_dists = set()

    for Atom1_index in sorted(Atom1_indices):
        for Atom2_index in Atom2_indices:
            distance = atoms.get_distances(Atom1_index, [Atom2_index], mic=True)[0]
            rounded_dist = round(float(distance), 4)
            # print(f"Distance between {Atom2}{Atom2_index} and {Atom3}{Atom3_index}: {rounded_dist}")

            if rounded_dist >= min_cutoff and rounded_dist <= max_cutoff and rounded_dist not in unique_dists:
                unique_dists.add(rounded_dist)
                all_data.append({
                     Atom1: f"{Atom1}{Atom1_index + 1}",
                     Atom2: f"{Atom2}{Atom2_index + 1}",
                    'Distance': rounded_dist
                })

    if all_data:
        df = pd.DataFrame(all_data).sort_values(by=[Atom1, 'Distance'])
        df.reset_index(drop=True, inplace=True)  # Resetting the index
        df.index += 1
        return df
    else:
        return all_data.append("No bond met the cutoff criteria.")
        # return Atom2_indices


def detect_ABA_groups(AB_groups):
    # Create a dictionary to store B to A mappings
    B_to_As = {}

    # Create a list to store ABA groups
    ABA_groups = []

    # Populate B_to_As
    for A, Bs in AB_groups.items():
        for B in Bs:
            if B not in B_to_As:
                B_to_As[B] = []
            B_to_As[B].append(A)

    # Create ABA groups
    for B, As in B_to_As.items():
        if len(As) == 2:  # Each B is shared by exactly two As
            A1, A2 = As
            ABA_group = [A1, B, A2]
            ABA_groups.append(ABA_group)

    return ABA_groups


from scipy.spatial import Delaunay



def volume_tetrahedron(tetrahedron):
    matrix = np.array([
        tetrahedron[0] - tetrahedron[3],
        tetrahedron[1] - tetrahedron[3],
        tetrahedron[2] - tetrahedron[3]
    ])
    return abs(np.linalg.det(matrix))/6

def volume_octahedron_del(input_list):
    input_list = np.array(input_list)
    tri = Delaunay(input_list)
    tetrahedra = input_list[tri.simplices]
    volumes = np.array([volume_tetrahedron(t) for t in tetrahedra])

    return np.sum(volumes)






def calculate_centroid(coordinates):
    """
    Calculate the centroid of a set of 3D points.

    Args:
    coordinates (list of lists or tuples): A list of [x, y, z] coordinates.

    Returns:
    list: The [x, y, z] coordinates of the centroid.
    """
    sum_x = sum(point[0] for point in coordinates)
    sum_y = sum(point[1] for point in coordinates)
    sum_z = sum(point[2] for point in coordinates)
    n = len(coordinates)

    centroid_x = sum_x / n
    centroid_y = sum_y / n
    centroid_z = sum_z / n

    return [centroid_x, centroid_y, centroid_z]





import itertools
def calculate_angle(P, A, B):
    vec_PA = A - P
    vec_PB = B - P
    cos_theta = np.dot(vec_PA, vec_PB) / (np.linalg.norm(vec_PA) * np.linalg.norm(vec_PB))
    theta_rad = np.arccos(np.clip(cos_theta, -1.0, 1.0))
    theta_deg = np.degrees(theta_rad)
    return theta_deg




def find_bonded_b_atoms(AB_groups):
    # Create a reverse lookup dictionary to map B atoms to A atoms they are bonded with
    B_to_A_map = {}
    for A, Bs in AB_groups.items():
        for B in Bs:
            if B in B_to_A_map:
                B_to_A_map[B].append(A)
            else:
                B_to_A_map[B] = [A]

    # Create the result dictionary where each key is A atom index, and values are a list of four B atom indices
    result = {}

    # Loop through each A atom
    for A, Bs in AB_groups.items():
        bonded_Bs = []

        # Check each B atom to see if it is bonded to four different A atoms (other than the original A)
        for B in Bs:
            if B in B_to_A_map and len(B_to_A_map[B]) >= 2:  # Ensure B is bonded to at least one more A
                other_As = [other_A for other_A in B_to_A_map[B] if other_A != A]
                if len(other_As) >= 1:  # Check if there are at least one other A atoms bonded to B
                    bonded_Bs.append(B)
            if len(bonded_Bs) == 4:  # We need exactly four such B atoms
                break

        if len(bonded_Bs) == 4:
            result[A] = bonded_Bs

    return result



def calculate_layer_planes(AB_groups, atoms_obj,b):
    layers = detect_molecules(atoms_obj, b=b)
    # Initialize a dictionary to store the plane normal vectors by layer index

    layer_planes = {}

    # Create a mapping from atom index to layer index
    atom_to_layer = {}
    for layer_index, layer_atoms in enumerate(layers):
        for atom in layer_atoms:
            atom_to_layer[atom] = layer_index

    # Group A atoms by their layer using the mapping
    layer_to_A_atoms = {}
    for A in AB_groups.keys():
        if A in atom_to_layer:  # Ensure the A atom is in the layer list
            layer = atom_to_layer[A]
            if layer in layer_to_A_atoms:
                layer_to_A_atoms[layer].append(A)
            else:
                layer_to_A_atoms[layer] = [A]

    # Calculate the average plane for each layer of A atoms
    for layer, A_atoms in layer_to_A_atoms.items():
        A_positions = np.array([atoms_obj[A].position for A in A_atoms])
        centroid = np.mean(A_positions, axis=0)
        cov_matrix = np.cov((A_positions - centroid).T)
        eigenvalues, eigenvectors = np.linalg.eig(cov_matrix)
        normal_vector = eigenvectors[:, np.argmin(eigenvalues)]
        layer_planes[layer] = normal_vector.tolist()

    return layer_planes






def project_point_to_plane(point, normal_vector, point_on_plane):
    # Convert inputs to numpy arrays if they aren't already
    point = np.array(point)
    normal_vector = np.array(normal_vector)
    point_on_plane = np.array(point_on_plane)

    # Calculate the vector from point_on_plane to point
    vector = point - point_on_plane

    # Project vector onto normal vector
    distance_from_plane = np.dot(vector, normal_vector)
    projection = point - distance_from_plane * normal_vector

    return projection

def find_closest_plane_and_calculate_distance(layer_planes, point_M, point_X):
    # Initialize minimum distance with a large number
    min_distance = float('inf')
    closest_plane_normal = None
    point_on_plane = None

    # Calculate the closest plane to point_M
    for layer, normal_vector in layer_planes.items():
        # Arbitrarily use the first A atom's position in this layer as a point on the plane
        # Assuming the first A atom's index is available
        first_atom_index = layer_planes[layer][0]
        A_position = np.array(layer_planes[layer])
        centroid = np.mean(A_position, axis=0)

        # Project point_M to this plane
        projected_point_M = project_point_to_plane(point_M, normal_vector, centroid)
        distance =  np.linalg.norm(projected_point_M -  point_M)

        # Update closest plane if this one is closer
        if distance < min_distance:
            min_distance = distance
            closest_plane_normal = normal_vector
            point_on_plane = centroid

    # Project both point_M and point_X onto the closest plane
    projected_M = project_point_to_plane(point_M, closest_plane_normal, point_on_plane)
    projected_X = project_point_to_plane(point_X, closest_plane_normal, point_on_plane)


    return projected_X, projected_M






def find_in_planes(atoms_obj, unique_angles_dict, AB_groups):
    in_planes = {}

    first_entry = next(iter(unique_angles_dict.values()))
    A1, _, _ = first_entry
    A_symbol = atoms_obj[A1].symbol

    for angle, (A1, _, A2) in unique_angles_dict.items():
        pos_A1 = atoms_obj[A1].position
        pos_A2 = atoms_obj[A2].position

        for atom in atoms_obj:
            if atom.symbol == A_symbol and atom.index not in [A1, A2]:
                pos_A3 = atom.position
                dist_A1_A3 = np.linalg.norm(pos_A1 - pos_A3)
                dist_A2_A3 = np.linalg.norm(pos_A2 - pos_A3)

                if dist_A1_A3 <= 10 or dist_A2_A3 <= 10:                    # Not a good idea to hardcode this
                    if dist_A1_A3 < dist_A2_A3:
                        vec_A1_A3 = pos_A3 - pos_A1
                        vec_A2_A3 = pos_A3 - pos_A2
                    else:
                        vec_A1_A3 = pos_A2 - pos_A1
                        vec_A2_A3 = pos_A2 - pos_A3

                    norm1 = np.linalg.norm(vec_A1_A3)
                    norm2 = np.linalg.norm(vec_A2_A3)

                    if norm1 == 0 or norm2 == 0:
                        continue  # Skip if one of the vectors is zero

                    cos_theta = np.dot(vec_A1_A3, vec_A2_A3) / (norm1 * norm2)

                    if np.isnan(cos_theta):
                        continue  # Skip if cos_theta is NaN

                    theta_deg = np.degrees(np.arccos(np.clip(cos_theta, -1.0, 1.0)))

                    if 40 <= theta_deg <= 92:
                        in_planes[angle] = (A1, A2, atom.index)
                        break
    return in_planes


def find_perpendicular_planes(in_planes, atoms_obj):
    perp_planes = {}

    for angle, (A1, A2, A3) in in_planes.items():
        # Get positions
        pos_A1 = np.array(atoms_obj[A1].position)
        pos_A2 = np.array(atoms_obj[A2].position)
        pos_A3 = np.array(atoms_obj[A3].position)

        # Calculate vectors for the in-plane
        vec_A1_A2 = pos_A2 - pos_A1
        vec_A1_A3 = pos_A3 - pos_A1

        # Calculate the normal to the in-plane
        normal_vector_in = np.cross(vec_A1_A2, vec_A1_A3)

        # Normalize the normal vector
        normal_vector_in /= np.linalg.norm(normal_vector_in)

        # Create an arbitrary point along the normal vector
        arbitrary_point = pos_A1 + normal_vector_in * 1.0

        # Calculate vectors for the out-of-plane
        vec_A1_arbitrary = arbitrary_point - pos_A1
        vec_A2_arbitrary = arbitrary_point - pos_A2

        # Calculate the normal to the out-plane
        normal_vector_out = np.cross(vec_A1_arbitrary, vec_A2_arbitrary)

        # Normalize the out-plane normal vector
        normal_vector_out /= np.linalg.norm(normal_vector_out)

        # Ensure the vectors are perpendicular by checking dot product of the normal vectors
        dot_normal_vectors = np.dot(normal_vector_in, normal_vector_out)

        if abs(dot_normal_vectors) < 1e-6:
            perp_planes[angle] = {'in_plane': (pos_A1, pos_A2, pos_A3), 'out_plane': (pos_A1, pos_A2, arbitrary_point)}
        else:
            print(f"Normal vectors for angle {angle} are not perpendicular. Skipping.")

    return perp_planes


def project_point_onto_plane(point, plane_point, normal_vector):
    return point - np.dot(point - plane_point, normal_vector) * normal_vector


def calculate_angle(p1, p2, p3):
    vec1 = p1 - p2
    vec2 = p3 - p2
    cos_theta = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    return np.arccos(np.clip(cos_theta, -1.0, 1.0)) * 180.0 / np.pi


def calculate_plane_components(perp_planes, unique_angles_dict, atoms_obj):
    B_indices = {angle: B for angle, (A1, B, A2) in unique_angles_dict.items()}
    in_out_plane_angles = {}

    for angle, planes in perp_planes.items():
        try:
            pos_A1, pos_A2, pos_A3 = planes['in_plane']
            _, _, arbitrary_point = planes['out_plane']
            B = B_indices.get(angle, None)
            if B is None:
                continue

            # Retrieve B position from atoms_obj
            pos_B = np.array(atoms_obj[B].position)

            # Calculate normal for in_plane
            normal_in_plane = np.cross(pos_A2 - pos_A1, pos_A3 - pos_A1)
            normal_in_plane /= np.linalg.norm(normal_in_plane)

            # Project B onto in-plane and out-plane
            B_prime_in_plane = project_point_onto_plane(pos_B, pos_A1, normal_in_plane)
            normal_out_plane = np.cross(pos_A2 - pos_A1, arbitrary_point - pos_A1)
            normal_out_plane /= np.linalg.norm(normal_out_plane)
            B_prime_out_plane = project_point_onto_plane(pos_B, pos_A1, normal_out_plane)

            # Calculate angle components for in_plane and out_plane
            angle_in_plane = calculate_angle(pos_A1, B_prime_in_plane, pos_A2)
            angle_out_plane = calculate_angle(pos_A1, B_prime_out_plane, pos_A2)

            in_out_plane_angles[angle] = {'in_plane': (180 - angle_in_plane), 'out_plane': (180 - angle_out_plane)}

        except Exception as e:
            print(f"Exception occurred: {e}")
            continue

    return in_out_plane_angles







def calculate_angle_differences(unique_angles_dict):
    # Extract unique angles from the dictionary keys
    unique_angles = list(unique_angles_dict.keys())

    # Check the number of unique angles
    if len(unique_angles) == 1:
        return 0

    # List to store the differences
    angle_diffs = []

    # Calculate pairwise differences
    for i in range(len(unique_angles)):
        for j in range(i + 1, len(unique_angles)):
            angle_diff = abs(unique_angles[i] - unique_angles[j])
            angle_diff = round(angle_diff, 3)
            angle_diffs.append(angle_diff)

    return angle_diffs


def search_database(df, search_str):
    """Search the given DataFrame for the search string in specific columns and return the IDs."""

    # Filtering the dataframe based on the search string
    mask = df['compound_name'].str.contains(search_str, case=False) | \
           df['formula'].str.contains(search_str, case=False) | \
           df['group'].str.contains(search_str, case=False)

    return df.loc[mask, 'id'].tolist()


def fetch_materials_datasets(conn, system_id):
    """Fetches data from the materials_datasets table based on a given system_id and specific primary_property_id values."""

    # Constructing the SQL query
    query = f"SELECT * FROM materials_dataset WHERE system_id = {system_id} AND primary_property_id IN (7)"

    # Executing the query
    results = conn.query(query)

    return results

def extract_structure_file(zip_data: bytes) -> tuple:
    """
    Extracts the first .in or .cif file from the given zip data.
    Returns the content of the file and its extension.
    """
    with zipfile.ZipFile(BytesIO(zip_data), 'r') as archive:
        # List of all files with .in or .cif extension
        matched_files = [name for name in archive.namelist() if os.path.splitext(name)[1] in ['.in', '.cif']]

        if matched_files:
            with archive.open(matched_files[0], 'r') as file:
                file_content = file.read()
            return file_content, os.path.splitext(matched_files[0])[1]
    return None, None

import tempfile

def extract_structure_file_path(zip_data):
    with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
        # Extract .in or .cif files
        files = [f for f in z.namelist() if f.endswith(('.in', '.cif'))]
        if files:
            with tempfile.NamedTemporaryFile(delete=False, suffix=files[0][-4:]) as tmp_file:  # Save with appropriate extension
                with z.open(files[0]) as source_file:
                    tmp_file.write(source_file.read())
                return tmp_file.name  # Return the path to the temporary file
        return None
def handle_bridging_angles(result, atom_dict):
    """
    Processes angle entries, replaces supercell atom indices with original ones, and
    formats the output for a DataFrame with merged Atoms and Bridging angles in one row.

    Args:
    - result (tuple): A tuple with a dictionary of angles and a list of beta values.
    - atom_dict (dict): A dictionary mapping original atom indices to their images in the supercell.

    Returns:
    - list: A list of tuples, each tuple representing a row in the DataFrame.
    """
    angles, betas = result
    output_data = []

    # Function to map supercell indices to original atom indices
    def map_indices_to_original(indices):
        original_indices = []
        for index in indices:
            for key, values in atom_dict.items():
                if index in values:
                    original_indices.append(key + 1)
                    break
        return original_indices

    # Merging Atoms and Bridging angles data
    merged_data = []
    for angle_value, atom_indices in angles.items():
        original_atom_indices = map_indices_to_original(atom_indices)
        formatted_atoms = ', '.join(map(str, original_atom_indices))
        merged_data.append(f"{angle_value}({formatted_atoms})")
    output_data.append(('Bridging angle (atom indices)', ', '.join(merged_data)))

    # Beta data
    beta_data = ', '.join([str(beta) for beta in (betas if isinstance(betas, list) else [betas])])
    output_data.append(('Angle difference', beta_data))


    return output_data

def handle_in_out_deviations(result):
    output = []
    angle_count = 0
    for angle, deviations in result.items():
        angle_count += 1
        angle_name = f'Bridging angle {angle_count}' if angle_count > 1 else 'Bridging angle'

        output.extend([
            (angle_name, angle),
            ('In-plane deviation', f'{deviations["in_plane"]:.3f}'),
            ('Out-of-plane deviation', f'{deviations["out_plane"]:.3f}')
        ])
    return output


def extract_primary_value_v2(adp_value):
    """
    Extracts the primary value from an ADP entry, including negative values, ignoring the uncertainty.

    :param adp_value: A string representing an ADP value, possibly with uncertainty.
    :return: The primary value as a float.
    """
    match = re.match(r"([-0-9.]+)\((\d+)\)", adp_value)
    return float(match.group(1)) if match else float(adp_value)


def extract_Uij_from_cif(file_buffer):
    """
    Extracts U_ij values from a CIF file buffer (as used in Streamlit) and returns a Pandas DataFrame,
    excluding the first six header lines, resetting the row indices, and removing uncertainty values.

    :param file_buffer: File buffer of the uploaded CIF file.
    :return: A Pandas DataFrame with columns for Atom_Label and U_ij values.
    """
    # Read lines from the file buffer
    lines = [line.decode('utf-8') for line in file_buffer]

    # Find the start of the U_ij section
    start_index = -1
    for i, line in enumerate(lines):
        if '_atom_site_aniso_label' in line:
            start_index = i + 1  # Starting from the line after the header
            break

    if start_index == -1:
        raise ValueError("U_ij section not found in CIF file")

    # Extract data from the U_ij section
    data = []
    for line in lines[start_index:]:
        if line.strip() == '':  # Stop at an empty line, which indicates the end of the section
            break
        values = line.split()
        # Extract and convert the ADP values, removing uncertainties and handling negative values
        values[1:] = [extract_primary_value_v2(value) for value in values[1:]]
        data.append(values)

    # Create DataFrame
    columns = ['Atom Label', 'U11', 'U22', 'U33', 'U23', 'U13', 'U12']
    df = pd.DataFrame(data, columns=columns)

    # Removing the first six rows and resetting the index
    df = df.iloc[6:].reset_index(drop=True)

    return df


def calculate_bond_distance_variance(AB_groups, atoms_obj, atom_dict, b=0, A2_indices=None, A2_symbol=None):
    unique_distance_variance_with_idx = {}
    atom_name = []

    for A, B_list in AB_groups.items():
        pos_A = atoms_obj[A].position
        idx_A = atoms_obj[A].index
        current_symbol = A2_symbol if A2_indices is not None and idx_A in A2_indices else atoms_obj[A].symbol
        atom_name.append(current_symbol)

        # Extract positions for B atoms
        B_positions = [atoms_obj[B].position.tolist() for B in B_list]

        # Calculate octahedral volume
        V = volume_octahedron_del(B_positions)

        # Calculate ideal edge length a
        a = (3 * V / np.sqrt(2)) ** (1 / 3)

        # Calculate ideal distance d0
        d0 = (a / np.sqrt(2))

        distance_squares = [(np.linalg.norm(pos_A - atoms_obj[B].position) / d0) ** 2 for B in B_list]

        distance_variance = sum(distance_squares) / 6.0
        rounded_variance = round(distance_variance, 6)

        if rounded_variance not in unique_distance_variance_with_idx or idx_A < unique_distance_variance_with_idx[rounded_variance]:
            unique_distance_variance_with_idx[rounded_variance] = idx_A

    mapped_variances_with_original_idx = {}

    for variance, supercell_idx in unique_distance_variance_with_idx.items():
        original_idx = None
        for key, values in atom_dict.items():
            if supercell_idx in values:
                original_idx = key
                break

        if original_idx is not None:
            mapped_variances_with_original_idx[variance] = original_idx

    variance_list = []
    for variance, original_idx in mapped_variances_with_original_idx.items():
        # Check if original_idx is in A2_indices and update symbol if needed
        current_symbol = A2_symbol if A2_indices is not None and original_idx in A2_indices else atom_name[0]
        variance_list.append(f"{variance} ({current_symbol}{original_idx + 1})")  # add 1 to match with VESTA

    return variance_list


def calculate_bond_distance_variance_v2(AB_groups, atoms_obj, atom_dict, b=0, A2_indices=None, A2_symbol=None):
    unique_distance_variance_with_idx = {}
    atom_name = []

    for A, B_list in AB_groups.items():
        pos_A = atoms_obj[A].position
        idx_A = atoms_obj[A].index
        current_symbol = A2_symbol if A2_indices is not None and idx_A in A2_indices else atoms_obj[A].symbol
        atom_name.append(current_symbol)

        # Extract positions for B atoms
        B_positions = [atoms_obj[B].position.tolist() for B in B_list]

        # Loop through each B in B_list to calculate distances from A
        AB_distances = [np.linalg.norm(pos_A - atoms_obj[B].position) for B in B_list]
        d0_m = np.mean(AB_distances) if AB_distances else 0

        distance_squares = [(((np.linalg.norm(pos_A - atoms_obj[B].position) - d0_m) ** 2) / (d0_m ** 2)) for B in B_list]

        distance_variance = (sum(distance_squares) / 6.0)*1e5
        rounded_variance = round(distance_variance, 6)

        if rounded_variance not in unique_distance_variance_with_idx or idx_A < unique_distance_variance_with_idx[rounded_variance]:
            unique_distance_variance_with_idx[rounded_variance] = idx_A

    mapped_variances_with_original_idx = {}

    for variance, supercell_idx in unique_distance_variance_with_idx.items():
        original_idx = None
        for key, values in atom_dict.items():
            if supercell_idx in values:
                original_idx = key
                break

        if original_idx is not None:
            mapped_variances_with_original_idx[variance] = original_idx

    variance_list = []
    for variance, original_idx in mapped_variances_with_original_idx.items():
        # Check if original_idx is in A2_indices and update symbol if needed
        current_symbol = A2_symbol if A2_indices is not None and original_idx in A2_indices else atom_name[0]
        variance_list.append(f"{variance} ({current_symbol}{original_idx + 1})")  # add 1 to match with VESTA

    return variance_list

def calculate_angle_variance(AB_groups, atoms_obj, atom_dict, b=0, A2_indices=None, A2_symbol=None):
    unique_variances_with_idx = {}
    atom_name = []

    for A, B_list in AB_groups.items():
        pos_A = atoms_obj[A].position
        idx_A = atoms_obj[A].index
        current_symbol = A2_symbol if A2_indices is not None and idx_A in A2_indices else atoms_obj[A].symbol
        atom_name.append(current_symbol)
        angle_squares = []

        # Generate all B-A-B combinations
        BAB_combinations = list(itertools.combinations(B_list, 2))

        for B1, B2 in BAB_combinations:
            pos_B1 = atoms_obj[B1].position
            pos_B2 = atoms_obj[B2].position

            # Calculate vectors and norms
            vec_B1_A = pos_A - pos_B1
            vec_B2_A = pos_A - pos_B2

            norm_B1_A = np.linalg.norm(vec_B1_A)
            norm_B2_A = np.linalg.norm(vec_B2_A)

            # Calculate cosine of angle
            cos_theta = np.dot(vec_B1_A, vec_B2_A) / (norm_B1_A * norm_B2_A)

            # Calculate angle in radians and then convert to degrees
            theta_rad = np.arccos(np.clip(cos_theta, -1.0, 1.0))
            theta_deg = np.degrees(theta_rad)

            # Skip angles close to 180 degrees
            if np.abs(theta_deg - 180) < 40:
                continue

            angle_squares.append((theta_deg - 90) ** 2)

        # Calculate the angle variance
        angle_variance = sum(angle_squares) / 11.0
        rounded_variance = round(angle_variance, 3)

        # Check if the variance already exists
        if rounded_variance not in unique_variances_with_idx or idx_A < unique_variances_with_idx[rounded_variance]:
            unique_variances_with_idx[rounded_variance] = idx_A

    mapped_variances_with_original_idx = {}

    for variance, supercell_idx in unique_variances_with_idx.items():
        original_idx = None
        for key, values in atom_dict.items():
            if supercell_idx in values:
                original_idx = key
                break

        if original_idx is not None:
            mapped_variances_with_original_idx[variance] = original_idx

    variance_list = []
    for variance, original_idx in mapped_variances_with_original_idx.items():
        # Check if original_idx is in A2_indices and update symbol if needed
        current_symbol = A2_symbol if A2_indices is not None and original_idx in A2_indices else atom_name[0]
        variance_list.append(f"{variance} ({current_symbol}{original_idx + 1})")  # add 1 to match with VESTA

    return variance_list

def calculate_unique_ABA_angles(AB_groups, atoms_obj, atom_dict=None,b=0, A2_indices=None, A2_symbol=None):
    ABA_groups = detect_ABA_groups(AB_groups)
    # Dictionary to store angles for each ABA group
    ABA_angles = {}
    unique_angles_dict = {}  # Dictionary to store unique angles

    for A1, B, A2 in sorted(ABA_groups):  # Sort to prioritize smaller A1 index
        # Get positions directly from the atoms object
        pos_A1 = atoms_obj[A1].position
        pos_B = atoms_obj[B].position
        pos_A2 = atoms_obj[A2].position

        # Calculate vectors
        vec_A1_B = pos_B - pos_A1
        vec_A2_B = pos_B - pos_A2

        # Calculate norms
        norm_A1_B = np.linalg.norm(vec_A1_B)
        norm_A2_B = np.linalg.norm(vec_A2_B)

        # Calculate cosine of angle
        cos_theta = np.dot(vec_A1_B, vec_A2_B) / (norm_A1_B * norm_A2_B)

        # Calculate angle in radians
        theta_rad = np.arccos(np.clip(cos_theta, -1.0, 1.0))

        # Convert to degrees
        theta_deg = np.degrees(theta_rad)

        # Round to 3 decimal places
        rounded_theta_deg = round(theta_deg, 3)

        # Check if this angle is already in the unique angles dictionary
        if rounded_theta_deg not in unique_angles_dict:
            unique_angles_dict[rounded_theta_deg] = (A1, B, A2)

        # Calculate beta
        beta_param = calculate_angle_differences(unique_angles_dict)

    return unique_angles_dict, beta_param

def calculate_off_centering(AB_groups, atoms_obj, atom_dict, b=0, A2_indices=None, A2_symbol=None):
    unique_distance_variance_with_idx = {}
    atom_name = []

    for A, B_list in AB_groups.items():
        pos_A = atoms_obj[A].position
        idx_A = atoms_obj[A].index
        current_symbol = A2_symbol if A2_indices is not None and idx_A in A2_indices else atoms_obj[A].symbol
        atom_name.append(current_symbol)

        # Extract positions for B atoms
        B_positions = [atoms_obj[B].position.tolist() for B in B_list]

        # calculate center of mass (com) of B-atoms
        com_B = calculate_centroid(B_positions)

        # calculate distance of A from the com of B
        x1, y1, z1 = pos_A
        x2, y2, z2 = com_B

        off_centering_var = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)

        rounded_variance = round(off_centering_var, 6)

        if rounded_variance not in unique_distance_variance_with_idx or idx_A < unique_distance_variance_with_idx[rounded_variance]:
            unique_distance_variance_with_idx[rounded_variance] = idx_A

    mapped_variances_with_original_idx = {}

    for variance, supercell_idx in unique_distance_variance_with_idx.items():
        original_idx = None
        for key, values in atom_dict.items():
            if supercell_idx in values:
                original_idx = key
                break

        if original_idx is not None:
            mapped_variances_with_original_idx[variance] = original_idx

    variance_list = []
    for variance, original_idx in mapped_variances_with_original_idx.items():
        # Check if original_idx is in A2_indices and update symbol if needed
        current_symbol = A2_symbol if A2_indices is not None and original_idx in A2_indices else atom_name[0]
        variance_list.append(f"{variance} ({current_symbol}{original_idx + 1})")  # add 1 to match with VESTA

    return variance_list


def calculate_mc_2D(AB_groups, atoms_obj, atom_dict=None,b=0, A2_indices=None, A2_symbol=None):

    AB_eq = find_bonded_b_atoms(AB_groups)

    unique_distance_variance_with_idx = {}
    atom_name = []

    for A, B_list in AB_eq.items():
        pos_A = atoms_obj[A].position
        idx_A = atoms_obj[A].index
        current_symbol = A2_symbol if A2_indices is not None and idx_A in A2_indices else atoms_obj[A].symbol
        atom_name.append(current_symbol)

        # Extract positions for B atoms
        B_positions = [atoms_obj[B].position.tolist() for B in B_list]

        # calculate center of mass (com) of B-atoms
        com_B = calculate_centroid(B_positions)

        # calculate distance of A from the com of B
        x1, y1, z1 = pos_A
        x2, y2, z2 = com_B

        off_centering_var = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)

        rounded_variance = round(off_centering_var, 6)

        if rounded_variance not in unique_distance_variance_with_idx or idx_A < unique_distance_variance_with_idx[
            rounded_variance]:
            unique_distance_variance_with_idx[rounded_variance] = idx_A

    mapped_variances_with_original_idx = {}

    for variance, supercell_idx in unique_distance_variance_with_idx.items():
        original_idx = None
        for key, values in atom_dict.items():
            if supercell_idx in values:
                original_idx = key
                break

        if original_idx is not None:
            mapped_variances_with_original_idx[variance] = original_idx

    variance_list = []
    for variance, original_idx in mapped_variances_with_original_idx.items():
        # Check if original_idx is in A2_indices and update symbol if needed
        current_symbol = A2_symbol if A2_indices is not None and original_idx in A2_indices else atom_name[0]
        variance_list.append(f"{variance} ({current_symbol}{original_idx + 1})")  # add 1 to match with VESTA

    return variance_list

def calculate_mc_2D_proj(AB_groups, atoms_obj,  atom_dict=None, b=0,A2_indices=None, A2_symbol=None):

    AB_eq = find_bonded_b_atoms(AB_groups)

    unique_distance_variance_with_idx = {}
    atom_name = []
    layer_planes = calculate_layer_planes(AB_groups, atoms_obj,b)

    for A, B_list in AB_eq.items():
        pos_A = atoms_obj[A].position
        idx_A = atoms_obj[A].index
        current_symbol = A2_symbol if A2_indices is not None and idx_A in A2_indices else atoms_obj[A].symbol
        atom_name.append(current_symbol)

        # Extract positions for B atoms
        B_positions = [atoms_obj[B].position.tolist() for B in B_list]

        # calculate center of mass (com) of B-atoms
        com_B = calculate_centroid(B_positions)

        # calculate distance of A from the com of B
        proj_A, proj_X = find_closest_plane_and_calculate_distance(layer_planes, pos_A, com_B)
        x1, y1, z1 = proj_A
        x2, y2, z2 = proj_X

        off_centering_var = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)

        rounded_variance = round(off_centering_var, 6)

        if rounded_variance not in unique_distance_variance_with_idx or idx_A < unique_distance_variance_with_idx[
            rounded_variance]:
            unique_distance_variance_with_idx[rounded_variance] = idx_A

    mapped_variances_with_original_idx = {}

    for variance, supercell_idx in unique_distance_variance_with_idx.items():
        original_idx = None
        for key, values in atom_dict.items():
            if supercell_idx in values:
                original_idx = key
                break

        if original_idx is not None:
            mapped_variances_with_original_idx[variance] = original_idx

    variance_list = []
    for variance, original_idx in mapped_variances_with_original_idx.items():
        # Check if original_idx is in A2_indices and update symbol if needed
        current_symbol = A2_symbol if A2_indices is not None and original_idx in A2_indices else atom_name[0]
        variance_list.append(f"{variance} ({current_symbol}{original_idx + 1})")  # add 1 to match with VESTA

    return variance_list


def calculate_off_centering_proj(AB_groups, atoms_obj, atom_dict, b=0, A2_indices=None, A2_symbol=None):
    unique_distance_variance_with_idx = {}
    atom_name = []
    layer_planes = calculate_layer_planes(AB_groups, atoms_obj,b)

    for A, B_list in AB_groups.items():
        pos_A = atoms_obj[A].position
        idx_A = atoms_obj[A].index
        current_symbol = A2_symbol if A2_indices is not None and idx_A in A2_indices else atoms_obj[A].symbol
        atom_name.append(current_symbol)

        # Extract positions for B atoms
        B_positions = [atoms_obj[B].position.tolist() for B in B_list]

        # calculate center of mass (com) of B-atoms
        com_B = calculate_centroid(B_positions)

        # calculate distance of A from the com of B
        proj_A, proj_X = find_closest_plane_and_calculate_distance(layer_planes, pos_A, com_B)
        x1, y1, z1 = proj_A
        x2, y2, z2 = proj_X

        off_centering_var = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)

        rounded_variance = round(off_centering_var, 6)

        if rounded_variance not in unique_distance_variance_with_idx or idx_A < unique_distance_variance_with_idx[rounded_variance]:
            unique_distance_variance_with_idx[rounded_variance] = idx_A

    mapped_variances_with_original_idx = {}

    for variance, supercell_idx in unique_distance_variance_with_idx.items():
        original_idx = None
        for key, values in atom_dict.items():
            if supercell_idx in values:
                original_idx = key
                break

        if original_idx is not None:
            mapped_variances_with_original_idx[variance] = original_idx

    variance_list = []
    for variance, original_idx in mapped_variances_with_original_idx.items():
        # Check if original_idx is in A2_indices and update symbol if needed
        current_symbol = A2_symbol if A2_indices is not None and original_idx in A2_indices else atom_name[0]
        variance_list.append(f"{variance} ({current_symbol}{original_idx + 1})")  # add 1 to match with VESTA

    return variance_list

def calculate_in_out_planes(AB_groups, atoms_obj, atom_dict=None,b =0, A2_indices=None, A2_symbol=None):
    unique_angles_dict, _ = calculate_unique_ABA_angles(AB_groups, atoms_obj)
    in_planes = find_in_planes(atoms_obj, unique_angles_dict, AB_groups)
    perp_planes = find_perpendicular_planes(in_planes, atoms_obj)
    plane_components = calculate_plane_components(perp_planes, unique_angles_dict, atoms_obj)

    return plane_components
