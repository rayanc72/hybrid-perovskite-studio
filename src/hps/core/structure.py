"""Streamlit-free structure parsing helpers for backend workflows."""

from __future__ import annotations

import os
import tempfile
import warnings
from io import BytesIO
from itertools import combinations_with_replacement

import numpy as np
import pandas as pd
import spglib
from ase.geometry import get_distances
from ase.io import read
from ase.neighborlist import natural_cutoffs
from pymatgen.analysis.diffraction.xrd import XRDCalculator
from pymatgen.io.ase import AseAtomsAdaptor
from pymatgen.io.cif import CifWriter
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
    with tempfile.NamedTemporaryFile(
        mode="w+b", suffix=f".{file_format}", delete=False
    ) as temp_file:
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


def detect_molecules(
    atoms, exceptions: list[tuple[str, str]] | None = None, bond_padding: float = 0.0
):
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
                analyzer = SpacegroupAnalyzer(
                    structure, symprec=float(symprec), angle_tolerance=float(angle_tol)
                )
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
            nearest_indices = np.abs(two_theta_grid[:, None] - peak_positions[None, :]).argmin(
                axis=0
            )
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


def simulate_pdf_from_upload(
    *,
    file_name: str,
    file_bytes: bytes,
    q_range: tuple[float, float] = (1.0, 20.0),
    r_range: tuple[float, float] = (0.1, 20.0),
    qdamp: float = 0.06,
    qbroad: float = 0.06,
) -> dict[str, object]:
    """Simulate a PDF profile through the optional PDF backend dependency."""

    from hps.domain.pdf import calculate_pdf, load_structure

    if q_range[0] < 0 or q_range[0] >= q_range[1]:
        raise ValueError("q_range must be increasing and non-negative.")
    if r_range[0] < 0 or r_range[0] >= r_range[1]:
        raise ValueError("r_range must be increasing and non-negative.")
    atoms = read_structure_bytes(file_bytes, get_file_format(file_name))
    structure = AseAtomsAdaptor.get_structure(atoms)
    with tempfile.TemporaryDirectory(prefix="hps-pdf-backend-") as tmpdir:
        cif_path = os.path.join(tmpdir, "structure.cif")
        CifWriter(structure).write_file(cif_path)
        diffpy_structure = load_structure(cif_path)
        r_values, g_values = calculate_pdf(
            diffpy_structure,
            diffpy_structure_attributes={"Uisoequiv": 0.01},
            pdf_calculator_kwargs={
                "qmin": float(q_range[0]),
                "qmax": float(q_range[1]),
                "rmin": float(r_range[0]),
                "rmax": float(r_range[1]),
                "qdamp": float(qdamp),
                "qbroad": float(qbroad),
            },
        )
    frame = pd.DataFrame({"r (A)": r_values, "G_sim(r)": g_values})
    return {
        "profile": frame.to_dict(orient="records"),
        "q_range": [float(q_range[0]), float(q_range[1])],
        "r_range": [float(r_range[0]), float(r_range[1])],
    }


def compare_pdf_profiles(
    *,
    simulated_r: list[float],
    simulated_g: list[float],
    experimental_r: list[float],
    experimental_g: list[float],
    normalization: str = "zscore",
) -> dict[str, object]:
    """Interpolate, normalize, and linearly fit simulated PDF data to experiment."""

    sim_r = np.asarray(simulated_r, dtype=float)
    sim_g = np.asarray(simulated_g, dtype=float)
    exp_r = np.asarray(experimental_r, dtype=float)
    exp_g = np.asarray(experimental_g, dtype=float)
    if min(len(sim_r), len(sim_g), len(exp_r), len(exp_g)) < 2:
        raise ValueError("PDF comparison requires at least two simulated and experimental points.")
    if len(sim_r) != len(sim_g) or len(exp_r) != len(exp_g):
        raise ValueError("Each PDF coordinate array must match its value array.")
    if np.any(np.diff(sim_r) < 0) or np.any(np.diff(exp_r) < 0):
        raise ValueError("PDF r coordinates must be sorted in increasing order.")

    interpolated = np.interp(exp_r, sim_r, sim_g)
    eps = 1e-12
    if normalization == "zscore":
        x_origin, x_scale = float(interpolated.mean()), max(float(interpolated.std()), eps)
        y_origin, y_scale = float(exp_g.mean()), max(float(exp_g.std()), eps)
    elif normalization == "minmax":
        x_origin, x_scale = float(interpolated.min()), max(float(np.ptp(interpolated)), eps)
        y_origin, y_scale = float(exp_g.min()), max(float(np.ptp(exp_g)), eps)
    else:
        raise ValueError("normalization must be `zscore` or `minmax`.")

    x_norm = (interpolated - x_origin) / x_scale
    y_norm = (exp_g - y_origin) / y_scale
    a_norm, b_norm = np.polyfit(x_norm, y_norm, 1)
    effective_slope = float(y_scale * a_norm / x_scale)
    effective_intercept = float(y_origin + y_scale * b_norm - effective_slope * x_origin)
    fitted = effective_slope * interpolated + effective_intercept
    residual = exp_g - fitted
    original_pcc = float(np.corrcoef(exp_g, interpolated)[0, 1])
    normalized_pcc = float(np.corrcoef(y_norm, x_norm)[0, 1])
    table = pd.DataFrame(
        {
            "r (A)": exp_r,
            "G_sim": interpolated,
            "G_exp": exp_g,
            "G_fit": fitted,
            "Residual": residual,
            "G_sim (norm)": x_norm,
            "G_exp (norm)": y_norm,
            "G_fit (norm)": a_norm * x_norm + b_norm,
        }
    )
    return {
        "table": table.to_dict(orient="records"),
        "effective_slope": effective_slope,
        "effective_intercept": effective_intercept,
        "pcc_original": original_pcc,
        "pcc_normalized": normalized_pcc,
        "normalization": normalization,
    }


def simulate_rdf_from_upload(
    *,
    file_name: str,
    file_bytes: bytes,
    atom_list: list[str],
    r_max: float,
    bins: int,
    weighted: bool,
) -> dict[str, object]:
    """Calculate pair RDF tables once for reuse by either UI plotting backend."""

    from hps.domain.pdf import compute_rdf_weighted

    if not atom_list or len(atom_list) > 20:
        raise ValueError("atom_list must contain between 1 and 20 element labels.")
    if r_max <= 0 or bins < 10:
        raise ValueError("r_max must be positive and bins must be at least 10.")
    atoms = read_structure_bytes(file_bytes, get_file_format(file_name))
    pairs = []
    for pair in combinations_with_replacement(atom_list, 2):
        r_values, g_values = compute_rdf_weighted(
            atoms, pair=pair, r_max=float(r_max), bins=int(bins), w=bool(weighted)
        )
        if r_values is None:
            continue
        pairs.append(
            {
                "pair": list(pair),
                "r": np.asarray(r_values, dtype=float).tolist(),
                "g": np.asarray(g_values, dtype=float).tolist(),
            }
        )
    return {"pairs": pairs, "pair_count": len(pairs), "bins": int(bins)}
