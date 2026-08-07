from __future__ import annotations

import io
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

from hps.io.archives import UnsafeArchiveError, safe_extract_zip


def zip_bytes(entries: dict[str, bytes]) -> io.BytesIO:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    buffer.seek(0)
    return buffer


class SafeArchiveTests(unittest.TestCase):
    def test_extracts_regular_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir)
            extracted = safe_extract_zip(
                zip_bytes({"frames/geometry0001.in": b"atom 0 0 0 H\n"}),
                destination,
            )
            self.assertEqual(
                extracted,
                [(destination / "frames" / "geometry0001.in").resolve()],
            )
            self.assertEqual(extracted[0].read_bytes(), b"atom 0 0 0 H\n")

    def test_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ("../outside.txt", "..\\outside.txt", "C:/outside.txt"):
                with self.subTest(name=name):
                    with self.assertRaisesRegex(UnsafeArchiveError, "Unsafe archive path"):
                        safe_extract_zip(zip_bytes({name: b"no"}), Path(tmpdir))

    def test_rejects_symlinks(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            entry = zipfile.ZipInfo("link")
            entry.create_system = 3
            entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(entry, "target")
        buffer.seek(0)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(UnsafeArchiveError, "Symbolic links"):
                safe_extract_zip(buffer, Path(tmpdir))

    def test_enforces_expanded_size_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(UnsafeArchiveError, "total limit"):
                safe_extract_zip(
                    zip_bytes({"one": b"1234", "two": b"5678"}),
                    Path(tmpdir),
                    max_total_size=7,
                )
