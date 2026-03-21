"""Structure transformation wrappers."""

from __future__ import annotations

from hps.domain import structure_manager as _impl


def rotate_molecules_v2(atoms, molecule, axis, angle):
    return _impl.rotate_molecules_v2(atoms, molecule, axis, angle)


def rotate_molecules_v3(atoms, molecules, molecule_indices, axis, angle, centroid_option, custom_centroid=None):
    return _impl.rotate_molecules_v3(
        atoms,
        molecules,
        molecule_indices,
        axis,
        angle,
        centroid_option,
        custom_centroid,
    )


def rotate_molecules_v4(atoms, molecule, mol_obj, rot_mat):
    return _impl.rotate_molecules_v4(atoms, molecule, mol_obj, rot_mat)


def rotate_molecules_v5(atoms, molecule, axis, angle, pivot_point_index, atoms_to_rotate_indices):
    return _impl.rotate_molecules_v5(atoms, molecule, axis, angle, pivot_point_index, atoms_to_rotate_indices)


def rotate_molecules_individually(atoms, molecules, rotation_parameters):
    return _impl.rotate_molecules_individually(atoms, molecules, rotation_parameters)


def generate_symmetrized_structure(atoms, symprec, angle_tol):
    return _impl.generate_symmetrized_structure(atoms, symprec, angle_tol)


def translate_molecule(atoms, molecules, scope_choice, selected_indices, axes_choice, translation_distances):
    return _impl.translate_molecule(
        atoms,
        molecules,
        scope_choice,
        selected_indices,
        axes_choice,
        translation_distances,
    )


def delete_molecules(atoms, molecules, molecule_indices):
    return _impl.delete_molecules(atoms, molecules, molecule_indices)


def create_labelled_download_file(atoms, file_name, output_suffix):
    return _impl.create_labelled_download_file(atoms, file_name, output_suffix)


def create_aims_download_file(atoms, file_name, output_suffix):
    return _impl.create_aims_download_file(atoms, file_name, output_suffix)
