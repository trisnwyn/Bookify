"""Explicit per-book workspace: root resolution, containment and read-only engine.

A workspace is one book. The engine tree (templates, fonts, vendored packages,
tools and pins) is read-only; book assets, intake, authoring evidence, build and
dist live inside the workspace. Legacy root discovery is unchanged when no
workspace is selected.
"""

from __future__ import annotations

import os
from pathlib import Path

from bookify import runtime
from bookify.errors import BookifyError

ENV = "BOOKIFY_WORKSPACE"


def engine_root() -> Path:
    """The installed engine tree (source checkout or wheel-bundled `_data`)."""
    return runtime.engine_root()


def from_environment() -> Path | None:
    value = os.environ.get(ENV, "").strip()
    return Path(value).expanduser() if value else None


def resolve(value: str | Path | None = None, *, engine: Path | None = None) -> Path | None:
    """Resolve an explicit workspace, falling back to ``BOOKIFY_WORKSPACE``.

    ``None`` means legacy mode. A selected workspace must exist and must not sit
    inside the engine tree.
    """
    candidate = value if value not in (None, "") else from_environment()
    if candidate in (None, ""):
        return None
    path = Path(candidate).expanduser()
    if not path.is_dir():
        raise BookifyError("INPUT_INVALID", f"workspace not found: {path}", str(path))
    resolved = path.resolve()
    require_outside_engine(resolved, engine)
    return resolved


def require_outside_engine(workspace: Path, engine: Path | None = None) -> None:
    root = (engine or engine_root()).resolve()
    try:
        workspace.resolve().relative_to(root)
    except ValueError:
        return
    raise BookifyError(
        "INPUT_INVALID",
        f"workspace must live outside the engine tree: {workspace}",
        str(workspace),
    )


def inside(
    root: Path,
    path: Path,
    *,
    label: str = "path",
    code: str = "BUILD_FAILED",
) -> Path:
    """Resolve ``path`` inside ``root``; refuse any escape, including a symlink."""
    base = root.resolve()
    candidate = path if path.is_absolute() else base / path
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as error:
        raise BookifyError(
            code,
            f"{label} must resolve inside the workspace: {candidate}",
            str(candidate),
        ) from error
    return resolved
