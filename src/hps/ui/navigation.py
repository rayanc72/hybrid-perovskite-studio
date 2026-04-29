"""Single source of truth for app navigation and feature-map content."""

from __future__ import annotations


NAVIGATION_REGISTRY = {
    "Structure": {
        "description": "Upload structures, inspect geometry, run transformations, and access <strong>PDF</strong> and <strong>PXRD</strong> analysis.",
        "views": {
            "Overview": {
                "summary": [
                    "Upload structure",
                    "Review loaded structure",
                    "Remove current structure",
                ]
            },
            "Analysis": {
                "groups": {
                    "Symmetry": {
                        "tools": [
                            "Symmetrize structure",
                            "Anisotropic displacement parameters",
                            "Calculate polarization direction",
                        ]
                    },
                    "Molecules": {
                        "tools": [
                            "Find center of mass",
                            "Calculate dipole moment",
                            "Charge analysis",
                        ]
                    },
                    "Structure Metrics": {
                        "tools": [
                            "Calculate atomic distances",
                            "Calculate octahedral distortions",
                            "Calculate percentage deviation",
                        ]
                    },
                    "PXRD Analysis": {
                        "tools": [
                            "Simulate PXRD",
                        ]
                    },
                    "PDF Analysis": {
                        "tools": [
                            "Simulate PDF",
                            "Plot RDF",
                            "Compare experimental PDF",
                            "Convert reduced PDF to g(r)",
                        ]
                    },
                }
            },
            "Transformations": {
                "groups": {
                    "Molecule Operations": {
                        "tools": {
                            "Rotation": {
                                "details": [
                                    "Rotate Individual Molecules",
                                    "Rotate Multiple Molecules",
                                    "Random Rotation",
                                    "Interpolate by Rotation",
                                    "Rotate Part of Molecules",
                                    "Rotate by Dipole Moment",
                                ]
                            },
                            "Reflection": {
                                "details": [
                                    "Reflect molecules on a plane",
                                ]
                            },
                            "Translation": {
                                "details": [
                                    "Molecules",
                                    "Atoms",
                                ]
                            },
                            "Deletion": {
                                "details": [
                                    "Delete selected molecule groups",
                                ]
                            },
                            "Labelling": {
                                "details": [
                                    "Apply a custom atom label to a selected molecule group",
                                ]
                            },
                        }
                    },
                    "Lattice Operations": {
                        "tools": {
                            "Translation": {
                                "details": [
                                    "Molecules",
                                    "Atoms",
                                ]
                            },
                            "Interpolation": {
                                "details": [
                                    "Generate interpolated structures between uploaded endpoints",
                                ]
                            },
                        }
                    },
                }
            },
        },
    },
    "Electronic": {
        "description": "Explore polarization, DOS, bands, spin, and optical outputs.",
        "views": {
            "Bands and Spin": {
                "tools": [
                    "Plot bandstructure",
                    "Plot spin texture",
                    "Plot 3D spin texture",
                    "Plot partial density of states (PDOS)",
                ]
            },
            "Advanced": {
                "tools": [
                    "Plot polarization",
                    "Plot absorption spectra",
                ]
            },
        },
    },
    "Dynamics": {
        "description": "Review molecular dynamics outputs and trajectory-derived metrics.",
        "views": {
            "Analyze AIMS MD output": {
                "details": [
                    "Plot parsed MD output",
                    "Export CSV",
                    "Generate geometry files",
                ]
            },
            "Trajectory analysis": {
                "details": [
                    "H-Bond Analysis",
                    "Distance Analysis",
                    "Average Structure",
                    "Distortion Analysis",
                    "Pair Distribution Function",
                    "Anisotropic Displacement Parameter",
                ],
            },
        },
    },
    "Utilities": {
        "description": "Use supporting scripts and general plotting tools.",
        "views": {
            "Run your own script": {
                "details": [
                    "JupyterLite browser workspace",
                ]
            },
            "Plot Data": {
                "details": [
                    "Custom dataset plotting and math-expression transforms",
                ]
            },
        },
    },
}


def workspace_descriptions():
    return {
        workspace: config["description"]
        for workspace, config in NAVIGATION_REGISTRY.items()
    }


def workspace_names():
    return list(NAVIGATION_REGISTRY.keys())


def view_names(workspace_name: str):
    return list(NAVIGATION_REGISTRY[workspace_name]["views"].keys())


def group_names(workspace_name: str, view_name: str):
    groups = NAVIGATION_REGISTRY[workspace_name]["views"][view_name].get("groups", {})
    return list(groups.keys())


def tool_options(workspace_name: str, view_name: str, group_name: str | None = None):
    view = NAVIGATION_REGISTRY[workspace_name]["views"][view_name]
    if group_name is not None:
        group = view["groups"][group_name]
        tools = group.get("tools", [])
    else:
        tools = view.get("tools", [])

    if isinstance(tools, dict):
        return list(tools.keys())
    return list(tools)


def tool_details(workspace_name: str, view_name: str, tool_name: str, group_name: str | None = None):
    view = NAVIGATION_REGISTRY[workspace_name]["views"][view_name]
    if group_name is not None:
        group = view["groups"][group_name]
        tools = group.get("tools", {})
    else:
        tools = view

    if isinstance(tools, dict) and tool_name in tools:
        return tools[tool_name].get("details", [])
    return []


def build_feature_tree():
    tree = {}
    for workspace_name, workspace_config in NAVIGATION_REGISTRY.items():
        workspace_tree = {}
        for view_name, view_config in workspace_config["views"].items():
            if "groups" in view_config:
                group_tree = {}
                for group_name, group_config in view_config["groups"].items():
                    tools = group_config.get("tools", [])
                    if isinstance(tools, dict):
                        tool_tree = {}
                        for tool_name, tool_config in tools.items():
                            details = tool_config.get("details", [])
                            tool_tree[tool_name] = details
                        group_tree[group_name] = tool_tree
                    else:
                        group_tree[group_name] = tools
                workspace_tree[view_name] = group_tree
            elif "tools" in view_config:
                workspace_tree[view_name] = view_config["tools"]
            elif "details" in view_config:
                workspace_tree[view_name] = view_config["details"]
            elif "summary" in view_config:
                workspace_tree[view_name] = view_config["summary"]
        tree[workspace_name] = workspace_tree
    return tree


def render_tree_lines(tree, indent=0):
    lines = []
    prefix = "  " * indent
    if isinstance(tree, dict):
        for key, value in tree.items():
            lines.append(f"{prefix}- {key}")
            lines.extend(render_tree_lines(value, indent + 1))
    elif isinstance(tree, list):
        for item in tree:
            lines.append(f"{prefix}- {item}")
    return lines
