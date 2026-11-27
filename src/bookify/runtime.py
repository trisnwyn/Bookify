"""Runtime path resolution for both source checkouts and installed Python wheels.

In a source checkout, engine assets live at the repository root (`typst/`,
`schemas/`, `vendor/typst/`, `assets/fonts/`, `toolchain.lock.json`).
In an installed wheel (`pip install bookify` / `uv tool install bookify`),
the core engine assets live inside `bookify/_data/` while optional large packs
(CJK fonts, pinned cross-platform Typst binary) live in the user cache dir.
"""

from __future__ import annotations

import importlib.metadata
import os
import sys
from pathlib import Path

from bookify.errors import BookifyError

ENGINE_ENV = "BOOKIFY_ENGINE"
CACHE_ENV = "BOOKIFY_CACHE_DIR"
FALLBACK_VERSION = "0.2.0"


def version() -> str:
    for dist_name in ("bookify-typst", "bookify"):
        try:
            return importlib.metadata.version(dist_name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return FALLBACK_VERSION


def _is_engine_dir(path: Path) -> bool:
    return (path / "typst").is_dir() and (path / "schemas").is_dir()


def engine_root() -> Path:
    """Locate the read-only Bookify engine asset directory."""
    env = os.environ.get(ENGINE_ENV, "").strip()
    if env:
        candidate = Path(env).expanduser().resolve()
        if _is_engine_dir(candidate):
            return candidate
        raise BookifyError("INPUT_INVALID", f"{ENGINE_ENV} is not a valid engine tree: {candidate}", str(candidate))

    package_dir = Path(__file__).resolve().parent
    # Source checkout: <repo>/src/bookify/runtime.py -> parents[2] == <repo>
    checkout = package_dir.parents[1]
    if _is_engine_dir(checkout):
        return checkout

    # Installed wheel: site-packages/bookify/_data/
    bundled = package_dir / "_data"
    if _is_engine_dir(bundled):
        return bundled

    raise BookifyError(
        "BUILD_FAILED",
        "Bookify engine assets (typst/, schemas/) not found; reinstall the bookify package or set BOOKIFY_ENGINE",
        str(package_dir),
    )


def is_installed_wheel(root: Path | None = None) -> bool:
    """True when running from wheel-bundled `_data` rather than a repo checkout."""
    target = (root or engine_root()).resolve()
    return target.name == "_data" or not (target / "pyproject.toml").is_file()


def cache_dir() -> Path:
    env = os.environ.get(CACHE_ENV, "").strip()
    if env:
        return Path(env).expanduser().resolve()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "bookify" / "cache"
    xdg = os.environ.get("XDG_CACHE_HOME", "").strip()
    if xdg:
        return Path(xdg).expanduser() / "bookify"
    return Path.home() / ".cache" / "bookify"


def fonts_cache_dir() -> Path:
    return cache_dir() / "fonts"


def bin_cache_dir() -> Path:
    return cache_dir() / "bin"


def resolve_font_path(engine: Path, relative_path: str) -> Path | None:
    """Locate a vendored font in the engine tree or the user font cache."""
    bundled = engine / relative_path
    if bundled.is_file():
        return bundled
    cached = fonts_cache_dir() / Path(relative_path).name
    if cached.is_file():
        return cached
    return None
