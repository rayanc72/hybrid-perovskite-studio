"""Pure parsers used by the Structure charge-analysis workflow."""

from __future__ import annotations

import re

import pandas as pd


def parse_id_field(value: str) -> list[int]:
    """Parse comma/space-separated atom IDs and inclusive ranges."""

    if not value or not str(value).strip():
        return []
    identifiers: list[int] = []
    seen: set[int] = set()
    for token in re.split(r"[,\s]+", str(value).strip()):
        if not token:
            continue
        match = re.fullmatch(r"(\d+)\s*:\s*(\d+)", token)
        if match:
            start, end = map(int, match.groups())
            values = range(start, end + 1) if start <= end else range(start, end - 1, -1)
        else:
            try:
                values = (int(token),)
            except ValueError:
                continue
        for identifier in values:
            if identifier not in seen:
                identifiers.append(identifier)
                seen.add(identifier)
    return identifiers


def parse_bader_integrated_atomic_properties(text: str) -> pd.DataFrame:
    """Parse the integrated atomic-properties table from Bader output."""

    lines = text.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if "* Integrated atomic properties" in line),
        None,
    )
    if start is None:
        raise ValueError("Could not find '* Integrated atomic properties' section.")
    header = next(
        (
            index
            for index in range(start, len(lines))
            if "Id" in lines[index] and "Pop" in lines[index]
        ),
        None,
    )
    if header is None:
        raise ValueError("Could not find the table header with 'Id' and 'Pop'.")

    rows: list[dict[str, int | float | str]] = []
    for line in lines[header + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "*")):
            if rows:
                break
            continue
        tokens = stripped.split()
        if len(tokens) < 9:
            break
        try:
            name = tokens[3]
            if name.endswith("_") and len(name.rstrip("_")) == 1:
                name = name.rstrip("_")
            rows.append(
                {
                    "Id": int(tokens[0]),
                    "Name": name,
                    "Z": int(tokens[4]),
                    "Pop": float(tokens[7].replace("D", "E")),
                }
            )
        except (TypeError, ValueError):
            break
    if not rows:
        raise ValueError("No data rows parsed from the atomic properties table.")
    frame = pd.DataFrame(rows)
    frame["PartialCharge"] = frame["Z"] - frame["Pop"]
    return frame
