"""Regression checks against the original dense bond rule and traversal order."""

import sys

import numpy as np
import pytest
from ase import Atoms
from ase.geometry import get_distances
from ase.io import read
from ase.neighborlist import natural_cutoffs

from hps.core.molecules import detect_molecules
from hps.core.structure import detect_molecules as backend_detect
from hps.domain.structure_manager import detect_molecules as ui_detect
from hps.examples import EXAMPLES_ROOT


def dense_reference(atoms, exceptions=(), padding=0.0):
    """Small-input oracle using minimum-image all-pairs distances."""
    symbols = atoms.get_chemical_symbols()
    tolerances = [
        0.1 if s in {"C", "H", "N", "O", "S"}
        else 0.5 if s == "Cl" else 0.25 + padding
        for s in symbols
    ]
    radii = np.asarray(natural_cutoffs(atoms)) + tolerances
    _, distances = get_distances(atoms.positions, cell=atoms.cell, pbc=atoms.pbc)
    bonds = distances < radii[:, None] + radii
    for i, symbol_i in enumerate(symbols):
        for j, symbol_j in enumerate(symbols):
            if (symbol_i, symbol_j) in exceptions or (symbol_j, symbol_i) in exceptions:
                bonds[i, j] = False

    visited = set()

    def visit(i, component):
        visited.add(i)
        component.append(i)
        for j in np.flatnonzero(bonds[i]):
            if int(j) not in visited:
                visit(int(j), component)

    groups = []
    for i in range(len(atoms)):
        if i not in visited:
            component = []
            visit(i, component)
            groups.append(component)
    return groups


def test_empty_and_isolated_atoms():
    assert detect_molecules(Atoms()) == []
    assert detect_molecules(Atoms("He")) == [[0]]
    assert detect_molecules(Atoms("HH", positions=[[0, 0, 0], [4, 0, 0]])) == [[0], [1]]


@pytest.mark.parametrize("pbc", [False, True, [True, False, True]])
@pytest.mark.parametrize("padding", [0.0, 0.3])
def test_matches_dense_reference_for_skewed_cells(pbc, padding):
    rng = np.random.default_rng(182)
    atoms = Atoms(
        symbols=list(rng.choice(["C", "H", "N", "O", "S", "Cl", "Pb", "I", "F"], 60)),
        scaled_positions=rng.uniform(-0.4, 1.4, (60, 3)),
        cell=[[9, 0, 0], [3, 8, 0], [1, 2, 7]],
        pbc=pbc,
    )
    exceptions = [("F", "I"), ("Pb", "Cl"), ("H", "H")]
    expected = dense_reference(atoms, exceptions, padding)
    assert detect_molecules(atoms, exceptions, padding) == expected
    assert backend_detect(atoms, exceptions, padding) == expected
    assert ui_detect(atoms, exceptions, b=padding) == expected


def test_bonds_across_only_periodic_axes():
    atoms = Atoms("HH", positions=[[0.1, 0, 0], [9.9, 0, 0]], cell=[10, 10, 10])
    assert detect_molecules(atoms) == [[0], [1]]
    atoms.pbc = [True, False, False]
    assert detect_molecules(atoms) == [[0, 1]]
    atoms.positions[:] = [[0, 0.1, 0], [0, 9.9, 0]]
    assert detect_molecules(atoms) == [[0], [1]]


@pytest.mark.parametrize("exceptions", [[("H", "C")], [("C", "H")]])
def test_exception_pairs_are_symmetric(exceptions):
    atoms = Atoms("CH", positions=[[0, 0, 0], [1.09, 0, 0]])
    assert detect_molecules(atoms) == [[0, 1]]
    assert detect_molecules(atoms, exceptions) == [[0], [1]]


def test_cutoff_is_strict_and_padding_preserves_element_rules():
    atoms = Atoms("HH", positions=[[0, 0, 0], [0, 0, 0]])
    threshold = 2 * (natural_cutoffs(atoms)[0] + 0.1)
    atoms.positions[1, 0] = threshold
    assert detect_molecules(atoms, bond_padding=0.5) == [[0], [1]]
    atoms.positions[1, 0] -= 1e-8
    assert detect_molecules(atoms) == [[0, 1]]
    atoms = Atoms("PbI", positions=[[0, 0, 0], [3.5, 0, 0]])
    assert detect_molecules(atoms) == [[0], [1]]
    assert detect_molecules(atoms, bond_padding=0.3) == [[0, 1]]


def test_periodic_images_do_not_duplicate_atoms():
    atoms = Atoms("CC", positions=[[0, 0, 0], [0.7, 0, 0]], cell=[1.4, 5, 5], pbc=True)
    assert detect_molecules(atoms) == [[0, 1]]


def test_long_connected_chain_does_not_exceed_recursion_limit():
    count = sys.getrecursionlimit() + 100
    positions = np.zeros((count, 3))
    positions[:, 0] = np.arange(count) * 1.5
    atoms = Atoms("C" * count, positions=positions, cell=[count * 1.5 + 5, 5, 5])
    assert detect_molecules(atoms) == [list(range(count))]


def test_reference_perovskite_preserves_exact_group_and_atom_order():
    atoms = read(EXAMPLES_ROOT / "data/structure/MC3I_PbI_100K.in", format="aims")
    assert detect_molecules(atoms) == dense_reference(atoms)


@pytest.mark.parametrize("padding", [float("nan"), float("inf"), -10.0])
def test_invalid_cutoffs_raise_clear_error(padding):
    with pytest.raises(ValueError, match="bond_padding"):
        detect_molecules(Atoms("Pb"), bond_padding=padding)
