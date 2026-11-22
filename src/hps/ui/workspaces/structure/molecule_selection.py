"""Keep original group numbers when selecting finite molecules for analysis."""

from hps.core.molecules import build_bond_graph


def finite_molecule_numbers(atoms, molecules) -> list[int]:
    """Return one-based group numbers whose selected subgraph is connected and finite."""
    numbers = []
    for number, indices in enumerate(molecules, 1):
        components = build_bond_graph(atoms[list(indices)]).components
        if len(components) == 1 and components[0].is_finite:
            numbers.append(number)
    return numbers
