"""Generate CIF exports only when their download buttons are clicked."""

from __future__ import annotations

import io
import os
import zipfile
from collections.abc import Mapping, Sequence

import streamlit as st
from ase import Atoms
from ase.io import write


def _cif_bytes(atoms: Atoms, labels: list[str] | None = None) -> bytes:
    buffer = io.BytesIO()
    options = {"labels": [labels]} if labels is not None else {}
    write(buffer, atoms, format="cif", wrap=False, **options)
    return buffer.getvalue()


def create_cif_download_file(
    atoms: Atoms,
    file_name: str,
    output_suffix: str = "",
    *,
    atom_label_overrides: Mapping[int, str] | None = None,
    download_label: str | None = None,
) -> None:
    """Offer a deferred CIF download of an immutable transformation snapshot."""
    snapshot = atoms.copy()
    labels = None
    if atom_label_overrides:
        # CIF site names must be unique even when atoms share a molecule label.
        labels = [
            f"{atom_label_overrides[index]}_{index + 1}"
            if index in atom_label_overrides else f"{atom.symbol}{index + 1}"
            for index, atom in enumerate(snapshot)
        ]
    download_name = f"{os.path.splitext(file_name)[0]}{output_suffix}.cif"
    st.download_button(
        label=download_label or f"Download {download_name}",
        data=lambda: _cif_bytes(snapshot, labels),
        file_name=download_name,
        mime="chemical/x-cif",
        key=f"download_cif_{download_name}",
        on_click="ignore",
    )


def create_cif_archive_download(
    structures: Sequence[tuple[str, Atoms]],
    file_name: str,
    *,
    download_label: str,
) -> None:
    """Defer conversion and ZIP creation for a generated structure series."""
    snapshots = [(name, atoms.copy()) for name, atoms in structures]

    def generate_archive() -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, atoms in snapshots:
                archive.writestr(name, _cif_bytes(atoms))
        return buffer.getvalue()

    st.download_button(
        label=download_label,
        data=generate_archive,
        file_name=file_name,
        mime="application/zip",
        key=f"download_cif_archive_{file_name}",
        on_click="ignore",
    )
