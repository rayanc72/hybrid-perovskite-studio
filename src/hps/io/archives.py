"""Safe extraction helpers for user-provided ZIP archives."""

from __future__ import annotations

import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import BinaryIO


class UnsafeArchiveError(ValueError):
    """Raised when an archive is unsafe or exceeds configured limits."""


def safe_extract_zip(
    source: BinaryIO,
    destination: Path,
    *,
    max_files: int = 10_000,
    max_total_size: int = 1_000_000_000,
    max_file_size: int = 250_000_000,
) -> list[Path]:
    """Extract a ZIP after validating paths, entry types, and expanded sizes."""

    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []

    try:
        archive = zipfile.ZipFile(source)
    except (zipfile.BadZipFile, OSError) as exc:
        raise UnsafeArchiveError("The uploaded file is not a valid ZIP archive.") from exc

    with archive:
        entries = archive.infolist()
        if len(entries) > max_files:
            raise UnsafeArchiveError(f"Archive contains more than {max_files} entries.")

        total_size = 0
        validated: list[tuple[zipfile.ZipInfo, Path]] = []
        for entry in entries:
            path = PurePosixPath(entry.filename.replace("\\", "/"))
            has_windows_drive = bool(path.parts and path.parts[0].endswith(":"))
            if path.is_absolute() or has_windows_drive or ".." in path.parts:
                raise UnsafeArchiveError(f"Unsafe archive path: {entry.filename!r}.")
            if not path.parts or path.parts == (".",):
                continue

            unix_mode = entry.external_attr >> 16
            if stat.S_ISLNK(unix_mode):
                raise UnsafeArchiveError(f"Symbolic links are not allowed: {entry.filename!r}.")
            file_type = stat.S_IFMT(unix_mode)
            if file_type and file_type not in {stat.S_IFREG, stat.S_IFDIR}:
                raise UnsafeArchiveError(
                    f"Unsupported archive entry type: {entry.filename!r}."
                )
            if entry.file_size > max_file_size:
                raise UnsafeArchiveError(
                    f"Archive entry exceeds the {max_file_size}-byte limit: {entry.filename!r}."
                )
            total_size += entry.file_size
            if total_size > max_total_size:
                raise UnsafeArchiveError(
                    f"Archive expands beyond the {max_total_size}-byte total limit."
                )

            target = destination.joinpath(*path.parts).resolve()
            if target != destination and destination not in target.parents:
                raise UnsafeArchiveError(f"Unsafe archive path: {entry.filename!r}.")
            validated.append((entry, target))

        for entry, target in validated:
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source_file, target.open("wb") as target_file:
                shutil.copyfileobj(source_file, target_file)
            extracted.append(target)

    return extracted
