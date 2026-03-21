"""Service-level utilities for the packaged app."""

from .runtime import (
    dependency_status_by_group,
    full_install_command,
    grouped_missing_modules,
    legacy_app_is_runnable,
)

__all__ = [
    "dependency_status_by_group",
    "full_install_command",
    "grouped_missing_modules",
    "legacy_app_is_runnable",
]
