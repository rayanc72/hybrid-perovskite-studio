"""Streamlit-free electronic-structure helpers for backend workflows."""

from __future__ import annotations

from io import StringIO
import re

import numpy as np
import pandas as pd


PDOS_TOTAL_FILENAME = "ks_dos_total.dat"
PDOS_PROJECTED_RE = re.compile(r"(.+)_l_proj_dos\.dat$", re.IGNORECASE)
PDOS_PROJECTED_SP_ELEMENTS = {"Pb", "Sn"}
PDOS_ORBITAL_COLUMN_LABELS = {
    2: "s",
    3: "p",
    4: "d",
    5: "f",
}


def detect_pdos_file_roles(uploaded_files: list[dict[str, str]]) -> dict[str, list[object]]:
    roles: dict[str, list[object]] = {
        "total": [],
        "projected": [],
        "unrecognized": [],
    }

    for file in uploaded_files or []:
        name = str(file.get("name", ""))
        lower_name = name.lower()
        projected_match = PDOS_PROJECTED_RE.fullmatch(name)

        if lower_name == PDOS_TOTAL_FILENAME:
            roles["total"].append(name)
        elif projected_match:
            roles["projected"].append({"name": name, "element": projected_match.group(1)})
        else:
            roles["unrecognized"].append(name)

    return roles


def _read_pdos_array(file_bytes: bytes):
    text = file_bytes.decode("utf-8", errors="ignore")
    data = np.loadtxt(StringIO(text))
    data = np.asarray(data)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    return data


def _validate_pdos_array(name: str, data, min_columns: int) -> None:
    if data.ndim != 2 or data.shape[1] < min_columns:
        raise ValueError(
            f"`{name}` must contain at least {min_columns} numeric columns for PDOS plotting."
        )
    if data.shape[0] == 0:
        raise ValueError(f"`{name}` does not contain any PDOS rows.")


def _pdos_required_columns(element: str) -> int:
    if element in PDOS_PROJECTED_SP_ELEMENTS:
        return 4
    return 2


def _pdos_trace_columns(element: str):
    if element == "Total":
        return [("Total DOS", 1)]
    if element in PDOS_PROJECTED_SP_ELEMENTS:
        return [(f"{element}(s)", 2), (f"{element}(p)", 3)]
    return [(element, 1)]


def _pdos_table_columns(element: str, data):
    columns = [(element, 1)]
    for column_index, orbital_label in PDOS_ORBITAL_COLUMN_LABELS.items():
        if data.shape[1] > column_index:
            columns.append((f"{element}({orbital_label})", column_index))
    return columns


def build_pdos_table(dos_data: dict[str, np.ndarray]) -> pd.DataFrame:
    if "Total" not in dos_data:
        raise ValueError("Total DOS data is required before building the PDOS table.")

    total = dos_data["Total"]
    _validate_pdos_array("Total DOS", total, 2)
    energy_values = total[:, 0]
    table_data = {
        "Energy": energy_values,
        "Total DOS": total[:, 1],
    }

    for element, data in dos_data.items():
        if element == "Total":
            continue
        _validate_pdos_array(element, data, _pdos_required_columns(element))
        if len(data[:, 0]) != len(energy_values) or not np.allclose(data[:, 0], energy_values):
            raise ValueError(f"`{element}` PDOS energy values do not match `KS_DOS_total.dat`.")
        for column_name, column_index in _pdos_table_columns(element, data):
            table_data[column_name] = data[:, column_index]

    return pd.DataFrame(table_data)


def get_pdos_trace_options(dos_data: dict[str, np.ndarray]) -> list[str]:
    trace_options: list[str] = []
    for element in dos_data:
        trace_options.extend(trace_name for trace_name, _ in _pdos_trace_columns(element))
    return trace_options


def _resolve_pdos_column_name(pdos_table: pd.DataFrame, term: str) -> str:
    term = term.strip()
    if len(term) >= 2 and term[0] == "`" and term[-1] == "`":
        term = term[1:-1].strip()

    if term in pdos_table.columns:
        return term

    lower_term = term.lower()
    matches = [column for column in pdos_table.columns if column.lower() == lower_term]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"`{term}` matches multiple PDOS columns.")

    raise ValueError(f"`{term}` is not an available PDOS contribution.")


def _evaluate_pdos_combination(pdos_table: pd.DataFrame, expression: str):
    tokens = re.split(r"(\+|-)", expression)
    result = None
    sign = 1
    used_column = False

    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if token == "+":
            sign = 1
            continue
        if token == "-":
            sign = -1
            continue

        column_name = _resolve_pdos_column_name(pdos_table, token)
        contribution = pdos_table[column_name].to_numpy()
        result = sign * contribution if result is None else result + sign * contribution
        used_column = True
        sign = 1

    if not used_column:
        raise ValueError(f"`{expression}` does not contain a PDOS contribution.")
    return result


def get_pdos_combination_labels(combination_text: str) -> list[str]:
    if not combination_text or not combination_text.strip():
        return []

    labels = []
    lines = [line.strip() for line in combination_text.splitlines() if line.strip()]
    for index, line in enumerate(lines, start=1):
        if "=" in line:
            label, _expression = line.split("=", 1)
            label = label.strip()
        else:
            label = f"Combination {index}"
        if label:
            labels.append(label)
    return labels


def add_pdos_combinations(pdos_table: pd.DataFrame, combination_text: str):
    if not combination_text or not combination_text.strip():
        return pdos_table.copy(), []

    combined_table = pdos_table.copy()
    created_columns = []
    lines = [line.strip() for line in combination_text.splitlines() if line.strip()]

    for index, line in enumerate(lines, start=1):
        if "=" in line:
            label, expression = line.split("=", 1)
            label = label.strip()
            expression = expression.strip()
        else:
            label = f"Combination {index}"
            expression = line

        if not label:
            raise ValueError(f"Combination line {index} needs a label before `=`.")
        if label in {"Energy"}:
            raise ValueError("`Energy` cannot be used as a combination label.")
        if not expression:
            raise ValueError(f"Combination `{label}` needs an expression after `=`.")

        combined_table[label] = _evaluate_pdos_combination(combined_table, expression)
        created_columns.append(label)

    return combined_table, created_columns


def parse_pdos_payload(
    uploaded_files: list[dict[str, object]],
    combination_text: str = "",
) -> dict[str, object]:
    normalized_files = [{"name": str(file["name"])} for file in uploaded_files]
    roles = detect_pdos_file_roles(normalized_files)

    if not uploaded_files:
        raise ValueError("Upload `KS_DOS_total.dat` and one or more `*_l_proj_dos.dat` files.")
    if roles["unrecognized"] and not roles["total"] and not roles["projected"]:
        raise ValueError(
            "No FHI-aims PDOS files were recognized. Expected `KS_DOS_total.dat` and `*_l_proj_dos.dat`."
        )
    if not roles["total"]:
        raise ValueError("Total DOS file `KS_DOS_total.dat` was not found.")
    if len(roles["total"]) > 1:
        raise ValueError("Only one `KS_DOS_total.dat` file can be plotted at a time.")

    dos_data: dict[str, np.ndarray] = {}
    seen_elements: set[str] = set()

    for file in uploaded_files:
        name = str(file["name"])
        lower_name = name.lower()
        projected_match = PDOS_PROJECTED_RE.fullmatch(name)
        file_bytes = bytes(file["content"])

        if lower_name == PDOS_TOTAL_FILENAME:
            data = _read_pdos_array(file_bytes)
            _validate_pdos_array(name, data, 2)
            dos_data["Total"] = data
        elif projected_match:
            element = projected_match.group(1)
            if element in seen_elements:
                raise ValueError(f"Duplicate PDOS file for `{element}`.")
            data = _read_pdos_array(file_bytes)
            _validate_pdos_array(name, data, _pdos_required_columns(element))
            dos_data[element] = data
            seen_elements.add(element)

    pdos_table = build_pdos_table(dos_data)
    combination_columns: list[str] = []
    if combination_text.strip():
        pdos_table, combination_columns = add_pdos_combinations(pdos_table, combination_text)

    return {
        "roles": roles,
        "trace_options": get_pdos_trace_options(dos_data),
        "combination_columns": combination_columns,
        "pdos_table": pdos_table.to_dict(orient="records"),
        "pdos_columns": list(pdos_table.columns),
        "dos_data": {
            element: data.tolist()
            for element, data in dos_data.items()
        },
    }
