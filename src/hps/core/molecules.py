"""Periodic bond graphs shared by detection and molecular reconstruction."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from ase.neighborlist import natural_cutoffs, neighbor_list

Image = tuple[int, int, int]
BOND_SETTINGS_KEY = "hps_bond_detection"


@dataclass(frozen=True, order=True)
class PeriodicBond:
    """Bond from source to target + shift @ cell (one orientation per edge)."""

    source: int
    target: int
    shift: Image


@dataclass(frozen=True)
class BondedComponent:
    """A connected group with spanning-tree images and lattice winding vectors.

    Image shifts follow indices in legacy DFS order. They unwrap a finite
    component exactly, anchored at its first atom's supplied position. For a
    periodic component they describe only a spanning tree, not a molecule.
    Winding vectors are cycle translations, not a reduced lattice basis.
    """

    indices: tuple[int, ...]
    image_shifts: tuple[Image, ...]
    winding_vectors: tuple[Image, ...]
    periodic_dimension: int

    @property
    def is_finite(self) -> bool:
        return self.periodic_dimension == 0

    def as_dict(self) -> dict[str, object]:
        return {
            "indices": list(self.indices),
            "image_shifts": [list(shift) for shift in self.image_shifts],
            "winding_vectors": [list(vector) for vector in self.winding_vectors],
            "periodic_dimension": self.periodic_dimension,
            "is_finite": self.is_finite,
        }


class PeriodicNetworkError(ValueError):
    """Raised when a periodic network is requested as a finite molecule."""


@dataclass(frozen=True)
class PeriodicBondGraph:
    """Immutable topology and geometry snapshot; rebuild after changing atoms."""

    bonds: tuple[PeriodicBond, ...]
    components: tuple[BondedComponent, ...]
    positions: tuple[tuple[float, float, float], ...]
    cell: tuple[tuple[float, float, float], ...]

    def unwrap(self, component_index: int = 0) -> np.ndarray:
        """Return finite Cartesian coordinates in the component's index order."""
        component = self.components[component_index]
        if not component.is_finite:
            raise PeriodicNetworkError(
                f"This bonded group is a {component.periodic_dimension}D periodic network; "
                "it cannot be reconstructed as a finite molecule."
            )
        return np.asarray(self.positions)[list(component.indices)] + np.asarray(
            component.image_shifts
        ) @ np.asarray(self.cell)


def _add(left: Image, right: Image) -> Image:
    return tuple(a + b for a, b in zip(left, right))


def _negate(vector: Image) -> Image:
    return tuple(-value for value in vector)


def _positive(vector: Image) -> Image:
    """Choose one orientation without changing the translation's magnitude."""
    return _negate(vector) if next((v for v in vector if v), 0) < 0 else vector


def _translation_rank(vectors: tuple[Image, ...]) -> int:
    """Exact rank in three dimensions, using Python integer arithmetic."""
    if not vectors:
        return 0
    a = vectors[0]
    for b in vectors[1:]:
        normal = (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )
        if any(normal):
            return 3 if any(sum(x * y for x, y in zip(normal, c)) for c in vectors) else 2
    return 1


def build_bond_graph(
    atoms, exceptions: list[tuple[str, str]] | None = None, bond_padding: float | None = None
) -> PeriodicBondGraph:
    """Build a graph retaining every bonded periodic image, including self-images.

    Bonds are strictly shorter than the sum of ASE covalent radii plus 0.1 Å
    per C/H/N/O/S atom, 0.5 Å per Cl, or 0.25 Å + padding for other elements.
    Exception pairs suppress both orientations. Omitted settings use
    atoms.info['hps_bond_detection'] when present, otherwise [] and 0.0.
    Explicit [] and 0.0 override stored settings. This function never mutates atoms.

    A nonzero lattice translation around a cycle identifies an extended
    network. The rank of those translations gives its periodic dimension.
    A bond crossing a cell boundary alone does not imply a periodic network.
    """
    settings = atoms.info.get(BOND_SETTINGS_KEY, {})
    if exceptions is None:
        exceptions = settings.get("exceptions", [])
    if bond_padding is None:
        bond_padding = settings.get("bond_padding", 0.0)
    if not np.isfinite(bond_padding):
        raise ValueError("bond_padding must be finite")
    symbols = atoms.get_chemical_symbols()
    tolerances = [
        0.1
        if symbol in {"C", "H", "N", "O", "S"}
        else 0.5
        if symbol == "Cl"
        else 0.25 + bond_padding
        for symbol in symbols
    ]
    cutoffs = np.asarray(natural_cutoffs(atoms)) + tolerances
    if np.any(cutoffs < 0):
        raise ValueError("bond_padding must not produce negative atomic cutoffs")

    excluded = {frozenset(pair) for pair in exceptions}
    bonds = set()
    if len(atoms):
        sources, targets, shifts = neighbor_list("ijS", atoms, cutoffs, self_interaction=False)
        for source, target, shift in zip(sources, targets, shifts):
            if frozenset((symbols[source], symbols[target])) in excluded:
                continue
            source, target = int(source), int(target)
            shift = tuple(int(value) for value in shift)
            if source > target:
                source, target, shift = target, source, _negate(shift)
            elif source == target:
                shift = _positive(shift)
            bonds.add(PeriodicBond(source, target, shift))

    adjacency = [[] for _ in atoms]
    for bond in sorted(bonds):
        adjacency[bond.source].append((bond.target, bond.shift))
        adjacency[bond.target].append((bond.source, _negate(bond.shift)))
    for neighbors in adjacency:
        neighbors.sort()

    images: dict[int, Image] = {}
    components = []
    for root in range(len(atoms)):
        if root in images:
            continue
        images[root] = (0, 0, 0)
        indices = [root]
        winding = set()
        # Iterator frames preserve recursive DFS ordering without a depth limit.
        stack = [(root, iter(adjacency[root]))]
        while stack:
            source, neighbors = stack[-1]
            edge = next(neighbors, None)
            if edge is None:
                stack.pop()
                continue
            target, shift = edge
            expected_image = _add(images[source], shift)
            if target not in images:
                images[target] = expected_image
                indices.append(target)
                stack.append((target, iter(adjacency[target])))
            else:
                residual = _add(expected_image, _negate(images[target]))
                if any(residual):
                    winding.add(_positive(residual))
        vectors = tuple(sorted(winding))
        components.append(
            BondedComponent(
                tuple(indices),
                tuple(images[index] for index in indices),
                vectors,
                _translation_rank(vectors),
            )
        )
    return PeriodicBondGraph(
        tuple(sorted(bonds)),
        tuple(components),
        tuple(tuple(float(value) for value in row) for row in atoms.positions),
        tuple(tuple(float(value) for value in row) for row in atoms.cell),
    )


def detect_molecules(
    atoms, exceptions: list[tuple[str, str]] | None = None, bond_padding: float | None = None
) -> list[list[int]]:
    """Return legacy bonded groups, including periodic networks and isolated atoms."""
    graph = build_bond_graph(atoms, exceptions=exceptions, bond_padding=bond_padding)
    return [list(component.indices) for component in graph.components]


def unwrap_molecule(atoms, indices=None, *, exceptions=None, bond_padding=None) -> np.ndarray:
    """Unwrap one connected finite group, preserving the supplied atom order.

    The first supplied atom stays in its original image. The selection must
    have unique valid indices; disconnected selections and networks raise
    ValueError. ASE periodic flags, including partial/no PBC, are respected.
    """
    if indices is not None:
        indices = list(indices)
        if any(
            not isinstance(i, (int, np.integer)) or i < 0 or i >= len(atoms) for i in indices
        ) or len(set(indices)) != len(indices):
            raise ValueError("Molecule indices must be unique valid atom indices")
        atoms = atoms[indices]
    graph = build_bond_graph(atoms, exceptions=exceptions, bond_padding=bond_padding)
    if len(graph.components) != 1:
        raise ValueError("The selected atoms must form one nonempty connected bonded group")
    coordinates = np.empty((len(atoms), 3))
    coordinates[list(graph.components[0].indices)] = graph.unwrap()
    return coordinates
