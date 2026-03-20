"""Structure analysis wrappers."""

from __future__ import annotations

from hpame.domain import structure_manager as _impl


def detect_molecules(atoms, exceptions=None, b=0):
    return _impl.detect_molecules(atoms, exceptions=exceptions, b=b)


def print_space_group(atoms, symprec=1e-3):
    return _impl.print_space_group(atoms, symprec=symprec)


def calculate_space_groups(atoms, symprec_lower, symprec_upper, angle_tol):
    return _impl.calculate_space_groups(atoms, symprec_lower, symprec_upper, angle_tol)


def extended_symmetry_info(atoms, symprec=1e-3):
    return _impl.extended_symmetry_info(atoms, symprec=symprec)
