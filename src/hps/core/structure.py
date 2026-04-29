"""Streamlit-free structure parsing helpers for backend workflows."""

from __future__ import annotations

import os
import tempfile
import warnings
from io import BytesIO

import numpy as np
import pandas as pd
import spglib
from ase.data import covalent_radii
from ase.geometry import get_distances
from ase.io import read
from ase.neighborlist import natural_cutoffs
from pymatgen.analysis.diffraction.xrd import XRDCalculator
from pymatgen.io.ase import AseAtomsAdaptor
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


def get_file_format(file_name: str) -> str:
    file_extension = os.path.splitext(file_name)[1].lower()
    if file_extension in {".in", ".next_step"}:
        return "aims"
    if file_extension == ".cif":
        return "cif"
    raise ValueError("Invalid file format. Please provide an AIMS or CIF file.")


def read_structure_bytes(file_bytes: bytes, file_format: str):
    buffer = BytesIO(file_bytes)
    with tempfile.NamedTemporaryFile(mode="w+b", suffix=f".{file_format}", delete=False) as temp_file:
        temp_file.write(buffer.getvalue())
        temp_file.flush()
        if file_format == "cif":
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"crystal system '.*' is not interpreted for space group .*",
                    category=UserWarning,
                    module=r"ase\.io\.cif",
                )
                atoms = read(temp_file.name, format=file_format)
        else:
            atoms = read(temp_file.name, format=file_format)
    os.unlink(temp_file.name)
    return atoms


def detect_molecules(atoms, exceptions: list[tuple[str, str]] | None = None, bond_padding: float = 0.0):
    exceptions = exceptions if exceptions else []

    element_tolerance = [
        0.1
        if atom.symbol in ["C", "H", "N", "O", "S"]
        else 0.5
        if atom.symbol in ["Cl"]
        else (0.25 + bond_padding)
        for atom in atoms
    ]
    cutoffs = [
        natural_cutoff + tolerance
        for natural_cutoff, tolerance in zip(natural_cutoffs(atoms), element_tolerance)
    ]
    coords = atoms.get_positions()
    cutoffs = np.array(cutoffs)

    vec_diffs, _ = get_distances(coords, coords, cell=atoms.cell, pbc=atoms.pbc)
    dist_matrix = np.linalg.norm(vec_diffs, axis=-1)
    bonded_atoms = dist_matrix < cutoffs[:, None] + cutoffs

    for i, atom_i in enumerate(atoms):
        for j, atom_j in enumerate(atoms):
            if (atom_i.symbol, atom_j.symbol) in exceptions or (
                atom_j.symbol,
                atom_i.symbol,
            ) in exceptions:
                bonded_atoms[i, j] = False
                bonded_atoms[j, i] = False

    graph = {i: bonded_atoms[i].nonzero()[0].tolist() for i, _atom in enumerate(atoms)}

    def dfs_visit(index: int, visited: list[bool], component: list[int]) -> None:
        visited[index] = True
        component.append(index)
        for neighbor in graph[index]:
            if not visited[neighbor]:
                dfs_visit(neighbor, visited, component)

    visited = [False] * len(atoms)
    molecules: list[list[int]] = []
    for index, _atom in enumerate(atoms):
        if not visited[index]:
            component: list[int] = []
            dfs_visit(index, visited, component)
            molecules.append(component)

    return molecules


def _spacegroup_cell(atoms):
    return (
        atoms.cell.array,
        atoms.get_scaled_positions(),
        atoms.get_atomic_numbers(),
    )


def summarize_structure_upload(
    *,
    file_name: str,
    file_bytes: bytes,
    exceptions: list[tuple[str, str]] | None = None,
    bond_padding: float = 0.0,
) -> dict[str, object]:
    file_format = get_file_format(file_name)
    atoms = read_structure_bytes(file_bytes, file_format=file_format)
    molecules = detect_molecules(atoms, exceptions=exceptions, bond_padding=bond_padding)
    dataset = spglib.get_symmetry_dataset(_spacegroup_cell(atoms), symprec=1e-3)

    if dataset is None:
        space_group = "Unavailable"
        space_group_number = None
        hall_symbol = None
    else:
        space_group = str(dataset.international)
        space_group_number = int(dataset.number)
        hall_symbol = str(dataset.hall)

    return {
        "file_name": file_name,
        "file_format": file_format,
        "formula": atoms.get_chemical_formula(),
        "atom_count": len(atoms),
        "molecule_group_count": len(molecules),
        "molecules": molecules,
        "modified_symbols": [f"{atom.symbol}{index + 1}" for index, atom in enumerate(atoms)],
        "lattice_vectors": atoms.cell.array.tolist(),
        "space_group": space_group,
        "space_group_number": space_group_number,
        "hall_symbol": hall_symbol,
        "space_group_display": (
            f"Space Group: {space_group} (No. {space_group_number}, Hall: {hall_symbol})"
            if space_group_number is not None
            else "Space Group: Unavailable"
        ),
    }


def calculate_space_group_sweep(
    *,
    file_name: str,
    file_bytes: bytes,
    symprec_lower: float,
    symprec_upper: float,
    angle_tol: float,
) -> dict[str, object]:
    file_format = get_file_format(file_name)
    atoms = read_structure_bytes(file_bytes, file_format=file_format)
    structure = AseAtomsAdaptor.get_structure(atoms)

    symprec_list = np.linspace(symprec_lower, symprec_upper, 6)
    space_groups: list[dict[str, object]] = []

    for symprec in symprec_list:
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"dict interface \(SpglibDataset\['.*'\]\) is deprecated.*",
                    category=DeprecationWarning,
                    module=r"spglib\.spglib",
                )
                analyzer = SpacegroupAnalyzer(structure, symprec=float(symprec), angle_tolerance=float(angle_tol))
                space_group_symbol = analyzer.get_space_group_symbol()
                point_group_symbol = analyzer.get_point_group_symbol()
            if space_group_symbol is not None:
                space_groups.append(
                    {
                        "symprec": float(symprec),
                        "space_group": str(space_group_symbol),
                        "point_group": str(point_group_symbol),
                        "label": (
                            f"Tolerance: {float(symprec):.4f} - "
                            f"Space group: {space_group_symbol}, Point group: {point_group_symbol}"
                        ),
                    }
                )
            else:
                space_groups.append(
                    {
                        "symprec": float(symprec),
                        "space_group": None,
                        "point_group": None,
                        "label": f"Tolerance: {float(symprec):.4f} - Not found",
                    }
                )
        except Exception:
            space_groups.append(
                {
                    "symprec": float(symprec),
                    "space_group": None,
                    "point_group": None,
                    "label": f"Tolerance: {float(symprec):.4f} - Not found (tolerance too high)",
                }
            )

    return {
        "summary": summarize_structure_upload(file_name=file_name, file_bytes=file_bytes),
        "space_groups": space_groups,
    }


def _two_theta_to_q(two_theta_values, wavelength):
    theta_radians = np.radians(np.asarray(two_theta_values, dtype=float) / 2.0)
    return (4.0 * np.pi * np.sin(theta_radians)) / float(wavelength)


def simulate_pxrd_from_upload(
    *,
    file_name: str,
    file_bytes: bytes,
    wavelength: float = 1.5406,
    two_theta_range: tuple[float, float] = (5.0, 80.0),
    fwhm: float = 0.1,
    x_axis: str = "2theta",
    scaled: bool = True,
    num_points: int = 4000,
) -> dict[str, object]:
    if wavelength <= 0:
        raise ValueError("Wavelength must be positive.")
    if fwhm < 0:
        raise ValueError("FWHM broadening must be non-negative.")
    if len(two_theta_range) != 2 or two_theta_range[0] >= two_theta_range[1]:
        raise ValueError("two_theta_range must be an increasing (min, max) pair.")
    if x_axis not in {"2theta", "q"}:
        raise ValueError("x_axis must be either '2theta' or 'q'.")
    if num_points < 2:
        raise ValueError("num_points must be at least 2.")

    file_format = get_file_format(file_name)
    atoms = read_structure_bytes(file_bytes, file_format=file_format)
    structure = AseAtomsAdaptor.get_structure(atoms)
    calculator = XRDCalculator(wavelength=wavelength)
    pattern = calculator.get_pattern(
        structure,
        scaled=scaled,
        two_theta_range=(float(two_theta_range[0]), float(two_theta_range[1])),
    )

    peak_positions = np.asarray(pattern.x, dtype=float)
    peak_intensities = np.asarray(pattern.y, dtype=float)

    reflections_df = pd.DataFrame(
        {
            "2theta (deg)": peak_positions,
            "Intensity": peak_intensities,
            "d (A)": np.asarray(pattern.d_hkls, dtype=float),
            "hkl": [
                ", ".join(f"{entry['hkl']} x{entry['multiplicity']}" for entry in peak_group)
                for peak_group in pattern.hkls
            ],
        }
    )

    two_theta_grid = np.linspace(two_theta_range[0], two_theta_range[1], int(num_points))
    profile_intensity = np.zeros_like(two_theta_grid)

    if peak_positions.size:
        if fwhm == 0:
            nearest_indices = np.abs(two_theta_grid[:, None] - peak_positions[None, :]).argmin(axis=0)
            np.add.at(profile_intensity, nearest_indices, peak_intensities)
        else:
            sigma = float(fwhm) / (2.0 * np.sqrt(2.0 * np.log(2.0)))
            deltas = two_theta_grid[:, None] - peak_positions[None, :]
            profile_intensity = np.exp(-0.5 * (deltas / sigma) ** 2) @ peak_intensities

    if scaled and profile_intensity.max() > 0:
        profile_intensity = 100.0 * profile_intensity / profile_intensity.max()

    if x_axis == "q":
        profile_x = _two_theta_to_q(two_theta_grid, wavelength)
        reflection_x = _two_theta_to_q(peak_positions, wavelength)
        x_label = "q (A^-1)"
    else:
        profile_x = two_theta_grid
        reflection_x = peak_positions
        x_label = "2theta (deg)"

    profile_df = pd.DataFrame(
        {
            x_label: profile_x,
            "Intensity": profile_intensity,
        }
    )
    if x_axis == "q":
        reflections_df.insert(1, x_label, reflection_x)

    return {
        "profile": profile_df.to_dict(orient="records"),
        "reflections": reflections_df.to_dict(orient="records"),
        "x_label": x_label,
    }
