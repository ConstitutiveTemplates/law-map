"""Process-global error/warning collection for corpus validation.

Kept in its own module so validators, report helpers, and the legacy
``validate`` shim all share one sink without a circular import.
The canonical lists live in :mod:`validation.const` (so ``validate.errors``
keeps working); this module re-exports the same objects plus helpers.
"""

from __future__ import annotations

from .const import errors, warnings

__all__ = ["errors", "warnings", "error", "warn", "reset"]


def error(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def reset() -> None:
    """Clear collected messages (used by tests and repeated CLI runs)."""
    del errors[:]
    del warnings[:]
