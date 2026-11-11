"""Measured pins for tools, Typst packages and fonts.

The lock file is evidence, not configuration: every entry carries a hash of
the artefact that was actually used, and nothing is accepted without one.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from bookify.errors import BookifyError

LOCK_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class FontPin:
    family: str
    weight: str
    path: str
    sha256: str


@dataclass(frozen=True)
class PackagePin:
    name: str
    version: str
    path: str
    sha256: str


@dataclass(frozen=True)
class ToolPin:
    version: str
    binary: str
    sha256: str
    archive_sha256: str | None
    source: str | None


@dataclass(frozen=True)
class PythonPin:
    version: str
    executable: str
    packages: dict[str, str]


@dataclass(frozen=True)
class ToolchainLock:
    path: Path
    python: PythonPin
    typst: ToolPin
    packages: tuple[PackagePin, ...]
    fonts: tuple[FontPin, ...]

    def package(self, name: str) -> PackagePin:
        for package in self.packages:
            if package.name == name:
                return package
        raise BookifyError("INPUT_INVALID", f"package not pinned: {name}", name)

    def font(self, family: str, weight: str | None = None) -> FontPin:
        candidates = [f for f in self.fonts if f.family == family]
        if weight is not None:
            candidates = [f for f in candidates if f.weight == weight]
        if not candidates:
            raise BookifyError("INPUT_INVALID", f"font not pinned: {family} {weight or ''}".strip(), family)
        return candidates[0]

    def font_paths(self, root: Path) -> list[Path]:
        return [root / font.path for font in self.fonts]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_sha256(directory: Path) -> str:
    """Hash a package directory by relative path and file content, order-stable."""
    digest = hashlib.sha256()
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        digest.update(path.relative_to(directory).as_posix().encode())
        digest.update(b"\0")
        digest.update(file_sha256(path).encode())
        digest.update(b"\0")
    return digest.hexdigest()


def _require(mapping: dict, keys: tuple[str, ...], locator: str) -> None:
    for key in keys:
        if key not in mapping:
            raise BookifyError("INPUT_INVALID", f"missing {key} in {locator}", locator)


def _hash(value: object, locator: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise BookifyError("INPUT_INVALID", f"sha256 must be 64 hex characters: {locator}", locator)
    int(value, 16)  # raises ValueError if not hexadecimal
    return value


def load(path: Path) -> ToolchainLock:
    if not path.exists():
        raise BookifyError("INPUT_INVALID", f"toolchain lock not found: {path}", str(path))
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise BookifyError("INPUT_INVALID", f"toolchain lock is not valid JSON: {error}", str(path)) from error

    _require(data, ("schemaVersion", "python", "typst", "packages", "fonts"), str(path))
    if data["schemaVersion"] != LOCK_SCHEMA_VERSION:
        raise BookifyError("INPUT_INVALID", f"unsupported lock schema: {data['schemaVersion']}", str(path))

    python_data = data["python"]
    _require(python_data, ("version", "executable", "packages"), "python")
    python = PythonPin(
        version=python_data["version"],
        executable=python_data["executable"],
        packages=dict(python_data["packages"]),
    )

    typst_data = data["typst"]
    _require(typst_data, ("version", "binary", "sha256", "source"), "typst")
    typst = ToolPin(
        version=typst_data["version"],
        binary=typst_data["binary"],
        sha256=_hash(typst_data["sha256"], "typst"),
        archive_sha256=typst_data.get("archiveSha256"),
        source=typst_data.get("source"),
    )

    packages: list[PackagePin] = []
    for entry in data["packages"]:
        _require(entry, ("name", "version", "path", "sha256"), "packages[]")
        packages.append(
            PackagePin(
                name=entry["name"],
                version=entry["version"],
                path=entry["path"],
                sha256=_hash(entry["sha256"], entry["name"]),
            )
        )

    fonts: list[FontPin] = []
    for entry in data["fonts"]:
        _require(entry, ("family", "weight", "path", "sha256"), "fonts[]")
        fonts.append(
            FontPin(
                family=entry["family"],
                weight=entry["weight"],
                path=entry["path"],
                sha256=_hash(entry["sha256"], entry["family"]),
            )
        )

    return ToolchainLock(
        path=path,
        python=python,
        typst=typst,
        packages=tuple(packages),
        fonts=tuple(fonts),
    )
