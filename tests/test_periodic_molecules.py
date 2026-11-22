"""Physical invariants for graph unwrapping and periodic network classification."""

import io

import numpy as np
import pytest
from ase import Atoms
from ase.io import read
from pymatgen.io.ase import AseAtomsAdaptor

from hps.core.molecules import (
    BOND_SETTINGS_KEY,
    PeriodicNetworkError,
    build_bond_graph,
    detect_molecules,
    unwrap_molecule,
)
from hps.core.structure import summarize_structure_upload
from hps.domain.molecule_builder import (
    get_connected_coordinates,
    get_molecule_object,
    update_coordinates_function,
)
from hps.domain.structure_manager import get_com, initialize_structure, rotate_molecules_v2
from hps.examples import EXAMPLES_ROOT


def boundary_ring():
    atoms = Atoms(
        "CCCC",
        positions=[[9.5, 4, 0], [10.9, 4, 0], [10.9, 5.4, 0], [9.5, 5.4, 0]],
        cell=[10, 10, 10],
        pbc=True,
    )
    atoms.wrap()
    return atoms


def test_boundary_crossing_ring_is_finite_and_closes_every_bond():
    atoms = boundary_ring()
    graph = build_bond_graph(atoms)
    component = graph.components[0]
    assert component.is_finite
    assert component.winding_vectors == ()
    assert len(graph.bonds) == 4
    coords = unwrap_molecule(atoms)
    np.testing.assert_allclose(coords[0], atoms.positions[0])
    for bond in graph.bonds:
        np.testing.assert_allclose(
            coords[bond.target] - coords[bond.source],
            atoms.positions[bond.target]
            - atoms.positions[bond.source]
            + np.asarray(bond.shift) @ atoms.cell,
            atol=1e-12,
        )


@pytest.mark.parametrize(
    "pbc, dimension", [([True, False, False], 1), ([True, True, False], 2), (True, 3)]
)
def test_self_image_bonds_identify_network_dimension(pbc, dimension):
    atoms = Atoms("C", cell=[1.5, 1.5, 1.5], pbc=pbc)
    graph = build_bond_graph(atoms)
    assert graph.components[0].periodic_dimension == dimension
    assert detect_molecules(atoms) == [[0]]
    with pytest.raises(PeriodicNetworkError, match=f"{dimension}D periodic network"):
        unwrap_molecule(atoms)


def test_parallel_image_bonds_identify_chain_without_self_bonds():
    atoms = Atoms(
        "CC", positions=[[0.75, 0, 0], [2.25, 0, 0]], cell=[3, 8, 8], pbc=[True, False, False]
    )
    graph = build_bond_graph(atoms)
    assert len(graph.bonds) == 2
    assert all(bond.source != bond.target for bond in graph.bonds)
    assert graph.components[0].periodic_dimension == 1
    with pytest.raises(PeriodicNetworkError):
        get_molecule_object(atoms, [1, 0])
    with pytest.raises(PeriodicNetworkError):
        rotate_molecules_v2(atoms, [0, 1], [0, 0, 1], 90)


def test_long_fragment_arbitrary_images_and_skewed_cell_unwrap_in_one_pass():
    coords = np.zeros((30, 3))
    coords[:, 0] = np.arange(30) * 1.5
    atoms = Atoms("C" * 30, positions=coords, cell=[[60, 0, 0], [9, 15, 0], [3, 2, 12]], pbc=True)
    rng = np.random.default_rng(94)
    shifts = rng.integers(-20, 21, (30, 3))
    shifts[0] = 0
    atoms.positions += shifts @ atoms.cell
    original = atoms.positions.copy()
    np.testing.assert_allclose(unwrap_molecule(atoms), coords, atol=1e-12)
    structure = AseAtomsAdaptor.get_structure(atoms)
    np.testing.assert_allclose(
        get_connected_coordinates(structure, max_iterations=1), coords, atol=1e-12
    )
    updated, structure_graph = update_coordinates_function(structure)
    np.testing.assert_allclose(updated, coords, atol=1e-12)
    assert len(structure_graph.graph.edges) == 29
    np.testing.assert_array_equal(atoms.positions, original)


def test_selection_order_and_root_image_are_preserved():
    atoms = boundary_ring()
    order = [2, 0, 3, 1]
    expected = unwrap_molecule(atoms)[order]
    expected += atoms.positions[2] - expected[0]
    np.testing.assert_allclose(unwrap_molecule(atoms, order), expected, atol=1e-12)
    np.testing.assert_allclose(get_molecule_object(atoms, order).cart_coords, expected, atol=1e-12)


def test_periodic_classification_is_invariant_to_site_images_and_permutation():
    atoms = Atoms(
        "CC", positions=[[0.75, 0, 0], [2.25, 0, 0]], cell=[3, 8, 8], pbc=[True, False, False]
    )
    atoms.positions[0] += 57 * atoms.cell[0]
    atoms.positions[1] -= 92 * atoms.cell[0]
    assert build_bond_graph(atoms[[1, 0]]).components[0].periodic_dimension == 1


def test_no_cell_and_partial_periodicity_are_respected():
    atoms = Atoms("CH", positions=[[0, 0, 0], [1.09, 0, 0]])
    np.testing.assert_allclose(get_molecule_object(atoms, [0, 1]).cart_coords, atoms.positions)
    atoms = Atoms(
        "CC", positions=[[0.2, 0, 0], [8.7, 0, 0]], cell=[10, 10, 10], pbc=[False, True, False]
    )
    with pytest.raises(ValueError, match="connected bonded group"):
        unwrap_molecule(atoms)
    atoms.pbc = [True, False, False]
    assert build_bond_graph(atoms).components[0].is_finite
    assert np.linalg.norm(np.diff(unwrap_molecule(atoms), axis=0)) == pytest.approx(1.5)


def test_isolated_atom_is_a_finite_molecule():
    atoms = Atoms("He", positions=[[2, 3, 4]])
    assert build_bond_graph(atoms).components[0].periodic_dimension == 0
    np.testing.assert_allclose(get_molecule_object(atoms, [0]).cart_coords, atoms.positions)


@pytest.mark.parametrize("indices", [[], [0, 0], [-1], [2], [0.5]])
def test_invalid_selections_raise(indices):
    with pytest.raises(ValueError):
        unwrap_molecule(Atoms("CC", positions=[[0, 0, 0], [1.5, 0, 0]]), indices)


def test_bond_settings_are_shared_and_explicit_overrides_take_precedence():
    atoms = Atoms("PbI", positions=[[0, 0, 0], [3.5, 0, 0]])
    atoms.info[BOND_SETTINGS_KEY] = {"exceptions": [], "bond_padding": 0.3}
    assert detect_molecules(atoms) == [[0, 1]]
    from hps.domain.structure.analysis import detect_molecules as domain_detect

    assert domain_detect(atoms) == [[0, 1]]
    assert len(get_molecule_object(atoms, [0, 1])) == 2
    with pytest.raises(ValueError, match="connected bonded group"):
        get_molecule_object(atoms, [0, 1], bond_padding=0.0)
    atoms.info[BOND_SETTINGS_KEY]["exceptions"] = [["I", "Pb"]]
    assert detect_molecules(atoms) == [[0], [1]]
    assert len(get_molecule_object(atoms, [0, 1], exceptions=[])) == 2


def test_exceptions_remove_self_image_network_edges():
    atoms = Atoms("C", cell=[1.5, 1.5, 1.5], pbc=True)
    assert build_bond_graph(atoms, exceptions=[("C", "C")]).components[0].is_finite


def test_com_and_rotation_use_unwrapped_geometry():
    atoms = boundary_ring()
    expected = unwrap_molecule(atoms)
    center = expected.mean(axis=0)
    np.testing.assert_allclose(get_com(atoms, [[0, 1, 2, 3]])[0], center)
    rotated = rotate_molecules_v2(atoms, [0, 1, 2, 3], [0, 0, 1], 90)
    np.testing.assert_allclose(rotated.positions.mean(axis=0), center, atol=1e-12)
    np.testing.assert_allclose(
        np.linalg.norm(rotated.positions[:, None] - rotated.positions[None, :], axis=-1),
        np.linalg.norm(expected[:, None] - expected[None, :], axis=-1),
        atol=1e-12,
    )


def test_reference_perovskite_classification_and_reconstruction():
    path = EXAMPLES_ROOT / "data/structure/MC3I_PbI_100K.in"
    atoms = read(path, format="aims")
    graph = build_bond_graph(atoms)
    assert any(not component.is_finite for component in graph.components)
    assert any(component.is_finite for component in graph.components)
    for component in graph.components:
        if component.is_finite:
            molecule = get_molecule_object(atoms, component.indices)
            assert len(molecule) == len(component.indices)
    summary = summarize_structure_upload(file_name=path.name, file_bytes=path.read_bytes())
    assert summary["finite_molecule_count"] + summary["periodic_network_count"] == 10
    assert summary["bonded_components"] == [component.as_dict() for component in graph.components]
    assert summary["molecules"] == [list(component.indices) for component in graph.components]


def test_ui_initialization_retains_bond_policy_for_reconstruction():
    content = b"atom 0 0 0 Pb\natom 3.5 0 0 I\n"
    # initialize_structure prints symmetry; a periodic cell is needed for that step.
    content = b"lattice_vector 15 0 0\nlattice_vector 0 15 0\nlattice_vector 0 0 15\n" + content
    atoms, groups, _ = initialize_structure(io.BytesIO(content), "aims", "test.in", b_p=0.3)
    assert groups == [[0, 1]]
    assert len(get_molecule_object(atoms, groups[0])) == 2


def test_oblique_network_rank_is_not_number_of_nonzero_image_axes():
    atoms = Atoms("C", cell=[[5, 0, 0], [-4, 1, 0], [0, 0, 10]], pbc=True)
    component = build_bond_graph(atoms).components[0]
    assert component.winding_vectors == ((1, 1, 0),)
    assert component.periodic_dimension == 1


def test_finite_ui_selection_and_com_labels_preserve_original_group_numbers():
    from hps.domain.structure_manager import get_distance_matrix
    from hps.ui.workspaces.structure.molecule_selection import finite_molecule_numbers

    atoms = Atoms(
        "CHe", positions=[[0, 0, 0], [0, 4, 0]], cell=[1.5, 12, 12], pbc=[True, False, False]
    )
    groups = detect_molecules(atoms)
    assert groups == [[0], [1]]
    assert finite_molecule_numbers(atoms, groups) == [2]
    centroids, _, _, merged = get_distance_matrix(atoms, [[1]], molecule_numbers=[2])
    assert list(centroids.index) == ["Molecule 2", "Unit Cell Center"]
    assert "Molecule 2" in merged.index
    np.testing.assert_allclose(centroids.loc["Molecule 2"], [0, 4, 0], atol=1e-12)
