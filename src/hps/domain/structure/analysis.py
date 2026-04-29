"""Structure analysis wrappers."""

from __future__ import annotations

from hps.domain import structure_manager as _impl


def detect_molecules(atoms, exceptions=None, b=0):
    return _impl.detect_molecules(atoms, exceptions=exceptions, b=b)


def print_space_group(atoms, symprec=1e-3):
    return _impl.print_space_group(atoms, symprec=symprec)


def calculate_space_groups(atoms, symprec_lower, symprec_upper, angle_tol):
    return _impl.calculate_space_groups(atoms, symprec_lower, symprec_upper, angle_tol)


def extended_symmetry_info(atoms, symprec=1e-3):
    return _impl.extended_symmetry_info(atoms, symprec=symprec)


def simulate_pxrd(
    atoms,
    wavelength=1.5406,
    two_theta_range=(5.0, 80.0),
    fwhm=0.1,
    x_axis="2theta",
    scaled=True,
    num_points=4000,
):
    return _impl.simulate_pxrd(
        atoms,
        wavelength=wavelength,
        two_theta_range=two_theta_range,
        fwhm=fwhm,
        x_axis=x_axis,
        scaled=scaled,
        num_points=num_points,
    )
