#!/usr/bin/env python3
"""Verify an installed Bookify skill payload against its own MANIFEST.json.

Standard library only. This script ships inside the bundle, so the documented
verify command works from the installed payload without the release helper that
lives in the Bookify source project.

Verification is integrity-relative to MANIFEST.json: it detects changed, missing
or extra payload files, but it does not authenticate the manifest itself. A
release record with the expected MANIFEST.json SHA-256 is the external anchor.

By default the runtime-only paths created by setup and use (.venv, work, dist,
build, caches) are tolerated. Pass --strict to require a pristine payload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from pathlib import Path, PurePosixPath

RUNTIME_PREFIXES = (
    ("engine", ".venv"),
    ("engine", "work"),
    ("engine", "dist"),
    ("engine", "build"),
    ("engine", ".cache"),
    ("engine", ".pytest_cache"),
)
RUNTIME_PARTS = {"__pycache__", ".pytest_cache"}


class VerifyError(RuntimeError):
    """A payload verification failure."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(path: str) -> PurePosixPath:
    if not path or "\x00" in path or "\\" in path:
        raise VerifyError(f"unsafe manifest path: {path!r}")
    relative = PurePosixPath(path)
    if relative.is_absolute():
        raise VerifyError(f"absolute manifest path: {path}")
    if any(part in {"", ".."} for part in relative.parts):
        raise VerifyError(f"traversal manifest path: {path}")
    return relative


def verify(target: Path, *, allow_runtime: bool = True) -> dict:
    root = target.expanduser().resolve()
    manifest_path = root / "MANIFEST.json"
    if not manifest_path.is_file():
        raise VerifyError(f"missing manifest: {manifest_path}")
    try:
        document = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise VerifyError(f"invalid manifest: {error}") from error
    if document.get("schemaVersion") != "1.0" or document.get("id") != "bookify":
        raise VerifyError("manifest schema/id mismatch")
    entries = document.get("files")
    if not isinstance(entries, list) or not entries:
        raise VerifyError("manifest has no files")

    expected: dict[str, dict] = {}
    for entry in entries:
        path = entry.get("path")
        if not isinstance(path, str):
            raise VerifyError("manifest entry without a path")
        _safe_relative(path)
        if path == "MANIFEST.json" or path in expected:
            raise VerifyError(f"bad manifest path: {path}")
        expected[path] = entry

    actual: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if allow_runtime and any(
            relative.parts[: len(prefix)] == prefix for prefix in RUNTIME_PREFIXES
        ):
            continue
        if allow_runtime and any(part in RUNTIME_PARTS for part in relative.parts):
            continue
        if path.is_dir():
            continue
        if path.is_symlink():
            raise VerifyError(f"symlink in payload: {path}")
        if not path.is_file():
            raise VerifyError(f"non-regular file in payload: {path}")
        try:
            path.resolve().relative_to(root)
        except ValueError as error:
            raise VerifyError(f"payload file escapes its root: {path}") from error
        actual.add(relative.as_posix())

    expected_names = set(expected) | {"MANIFEST.json"}
    missing = expected_names - actual
    extra = actual - expected_names
    if missing:
        raise VerifyError(f"manifest files missing: {sorted(missing)[:20]}")
    if extra:
        raise VerifyError(f"unmanifested files present: {sorted(extra)[:20]}")

    for path, entry in expected.items():
        file_path = root / path
        size = file_path.stat().st_size
        if size != entry.get("size"):
            raise VerifyError(f"size mismatch: {path} ({size} != {entry.get('size')})")
        if _sha256_file(file_path) != entry.get("sha256"):
            raise VerifyError(f"sha256 mismatch: {path}")
        mode = f"{stat.S_IMODE(file_path.stat().st_mode):04o}"
        if mode != entry.get("mode"):
            raise VerifyError(f"mode mismatch: {path} ({mode} != {entry.get('mode')})")

    if not (root / "SKILL.md").is_file() or not (root / "engine" / "pyproject.toml").is_file():
        raise VerifyError("payload missing SKILL.md or engine/pyproject.toml")
    return {
        "ok": True,
        "root": str(root),
        "fileCount": len(expected) + 1,
        "payloadBytes": document.get("payloadBytes"),
        "release": document.get("release"),
        "manifestSha256": _sha256_file(manifest_path),
        "runtimePathsTolerated": allow_runtime,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify an installed Bookify payload against its MANIFEST.json"
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="directory containing SKILL.md and MANIFEST.json (default: this script's directory)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="reject runtime-only paths such as engine/.venv and engine/work",
    )
    args = parser.parse_args(argv)
    try:
        result = verify(args.target, allow_runtime=not args.strict)
    except VerifyError as error:
        print(json.dumps({"ok": False, "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
