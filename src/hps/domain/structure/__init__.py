"""Structure-focused wrappers split by responsibility."""

from .analysis import calculate_space_groups, detect_molecules, extended_symmetry_info, print_space_group
from .parsing import get_file_format, initialize_structure, read_structure_file
from .transforms import (
    create_aims_download_file,
    create_labelled_download_file,
    delete_molecules,
    generate_symmetrized_structure,
    rotate_molecules_individually,
    rotate_molecules_v2,
    rotate_molecules_v3,
    rotate_molecules_v4,
    rotate_molecules_v5,
    translate_molecule,
)

__all__ = [
    "calculate_space_groups",
    "create_aims_download_file",
    "create_labelled_download_file",
    "delete_molecules",
    "detect_molecules",
    "extended_symmetry_info",
    "generate_symmetrized_structure",
    "get_file_format",
    "initialize_structure",
    "print_space_group",
    "read_structure_file",
    "rotate_molecules_individually",
    "rotate_molecules_v2",
    "rotate_molecules_v3",
    "rotate_molecules_v4",
    "rotate_molecules_v5",
    "translate_molecule",
]
