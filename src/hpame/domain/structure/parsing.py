"""Structure parsing wrappers."""

from __future__ import annotations

from hpame.domain import structure_manager as _impl


def get_file_format(file_name: str):
    return _impl.get_file_format(file_name)


def read_structure_file(fileobj, file_format: str = "aims"):
    return _impl.read_structure_file(fileobj, file_format=file_format)


def initialize_structure(uploaded_data, file_format, file_name, exceptions=None, b_p=0):
    return _impl.initialize_structure(
        uploaded_data,
        file_format=file_format,
        file_name=file_name,
        exceptions=exceptions,
        b_p=b_p,
    )
