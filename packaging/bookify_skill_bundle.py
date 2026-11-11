#!/usr/bin/env python3
"""Deterministic packaging and safe installation for the Bookify skill bundle.

Standard library only. The payload is an explicit allowlist; the archive has a
single top-level ``bookify/`` directory, sorted entries, fixed metadata, and a
``MANIFEST.json`` covering every payload file. Installation is no-clobber,
validated, staged, and atomic. Rebuilding is byte-identical on the same
interpreter and zlib build; the compressed SHA-256 can differ across zlib builds
while the uncompressed tar content stays identical.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import shutil
import stat
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "packaging" / "payload"
PREFIX = "bookify"
RELEASE = "2026-11-11"
CANONICAL_CATALOGUE_SHA = "b285d49f9263f85f45fbcbc20f6c61882b1ebbf125e0d6959d86a34c5e67c930"
MAX_MEMBER_BYTES = 1 << 30

# Explicit source allowlist. Nothing else from the working tree is packaged.
SOURCE_TREES = (
    "src",
    "schemas",
    "typst",
    "vendor",
    "assets",
    "content",
    "fixtures",
    "tests",
    "tools",
    "skill",
)
SOURCE_FILES = (
    "pyproject.toml",
    "uv.lock",
    "toolchain.lock.json",
)
# The test suite checks these probe scripts exist and are executable. Generated
# probe/out/ artifacts are deliberately not packaged.
PROBE_FILES = (
    ("probe/probe.sh", 0o755),
    ("probe/diagram.sh", 0o755),
    ("probe/chart.sh", 0o755),
    ("probe/chart.py", 0o644),
    ("probe/diagram.typ", 0o644),
    ("probe/probe.typ", 0o644),
)
EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "build",
    "dist",
    ".cache",
    ".git",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
RUNTIME_PREFIXES = (
    ("engine", ".venv"),
    ("engine", "work"),
    ("engine", "dist"),
    ("engine", "build"),
    ("engine", ".cache"),
    ("engine", ".pytest_cache"),
)

STATIC_FILES = (
    ("SKILL.md", PAYLOAD / "SKILL.md", 0o644),
    ("README.md", PAYLOAD / "README.md", 0o644),
    ("LICENCES.md", PAYLOAD / "LICENCES.md", 0o644),
    ("verify_manifest.py", PAYLOAD / "verify_manifest.py", 0o644),
    ("references/checklist.md", ROOT / "skill" / "bookify" / "references" / "checklist.md", 0o644),
    ("licences/OFL-1.1.txt", PAYLOAD / "licences" / "OFL-1.1.txt", 0o644),
    ("licences/fonts-metadata.md", PAYLOAD / "licences" / "fonts-metadata.md", 0o644),
    ("licences/python-dependencies.md", PAYLOAD / "licences" / "python-dependencies.md", 0o644),
)


class BundleError(RuntimeError):
    """A packaging or installation safety failure."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_excluded(rel: Path) -> bool:
    if any(part in EXCLUDED_DIR_NAMES for part in rel.parts):
        return True
    return rel.suffix.lower() in EXCLUDED_SUFFIXES


def _walk_tree(base: Path, rel_base: Path) -> list[tuple[str, Path, int]]:
    entries: list[tuple[str, Path, int]] = []
    for path in sorted(base.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(base)
        if _is_excluded(rel):
            continue
        if path.is_symlink():
            raise BundleError(f"refusing to package a symlink: {path}")
        if not path.is_file():
            raise BundleError(f"refusing to package a non-regular file: {path}")
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o111:
            mode = 0o755
        else:
            mode = 0o644
        entries.append(((rel_base / rel).as_posix(), path, mode))
    return entries


def _collect_payload() -> dict[str, tuple[Path, int]]:
    """Return arcname (below bookify/) -> (source path, mode)."""
    payload: dict[str, tuple[Path, int]] = {}

    for name, source, mode in STATIC_FILES:
        if not source.is_file():
            raise BundleError(f"missing packaging input: {source}")
        payload[name] = (source, mode)

    example = ROOT / "examples" / "catalogue.pdf"
    if not example.is_file():
        example = ROOT / "dist" / "catalogue.pdf"
    if not example.is_file():
        raise BundleError(
            "missing reviewed example: examples/catalogue.pdf (or dist/catalogue.pdf)"
        )
    example_sha = _sha256_file(example)
    if example_sha != CANONICAL_CATALOGUE_SHA:
        raise BundleError(
            f"{example.relative_to(ROOT)} is not the reviewed canonical catalogue: "
            f"{example_sha} != {CANONICAL_CATALOGUE_SHA}"
        )
    payload["examples/catalogue.pdf"] = (example, 0o644)

    for tree in SOURCE_TREES:
        base = ROOT / tree
        if not base.is_dir():
            raise BundleError(f"missing source tree: {base}")
        for arcname, source, mode in _walk_tree(base, Path("engine") / tree):
            payload[arcname] = (source, mode)

    for name in SOURCE_FILES:
        source = ROOT / name
        if not source.is_file():
            raise BundleError(f"missing source file: {source}")
        payload[f"engine/{name}"] = (source, 0o644)

    for name, mode in PROBE_FILES:
        source = ROOT / name
        if not source.is_file():
            raise BundleError(f"missing probe file: {source}")
        payload[f"engine/{name}"] = (source, mode)

    return payload


def _manifest_bytes(payload: dict[str, tuple[Path, int]]) -> bytes:
    files = []
    total = 0
    for arcname in sorted(payload):
        source, mode = payload[arcname]
        size = source.stat().st_size
        total += size
        files.append(
            {
                "path": arcname,
                "sha256": _sha256_file(source),
                "size": size,
                "mode": f"{mode:04o}",
            }
        )
    document = {
        "schemaVersion": "1.0",
        "id": PREFIX,
        "displayName": "Bookify",
        "release": RELEASE,
        "engine": {
            "version": "0.1.0",
            "python": "3.13.16",
            "typst": "0.15.1",
            "cetz": "0.5.3",
            "oxifmt": "1.0.0",
        },
        "platform": {
            "os": "linux",
            "arch": "x86_64",
            "typstBinary": "x86_64-unknown-linux-musl",
        },
        "entrypoints": {
            "skill": "SKILL.md",
            "engine": "engine/",
            "doctor": "cd engine && uv run bookify toolchain doctor --json",
        },
        "fileCount": len(files),
        "payloadBytes": total,
        "files": files,
    }
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def _tarinfo(arcname: str, size: int, mode: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(arcname)
    info.size = size
    info.mtime = 0
    info.mode = mode
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.type = tarfile.REGTYPE
    return info


def _write_archive(destination: Path, payload: dict[str, tuple[Path, int]], manifest: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0, filename="") as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.GNU_FORMAT) as archive:
                for arcname in sorted(payload):
                    source, mode = payload[arcname]
                    info = _tarinfo(f"{PREFIX}/{arcname}", source.stat().st_size, mode)
                    with source.open("rb") as handle:
                        archive.addfile(info, handle)
                info = _tarinfo(f"{PREFIX}/MANIFEST.json", len(manifest), 0o644)
                archive.addfile(info, io.BytesIO(manifest))


def _safe_member_name(name: str) -> PurePosixPath:
    if not name or "\x00" in name or "\\" in name:
        raise BundleError(f"unsafe archive path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute():
        raise BundleError(f"absolute archive path: {name}")
    if any(part in {"", ".."} for part in path.parts):
        raise BundleError(f"traversal archive path: {name}")
    if path.parts[0] != PREFIX:
        raise BundleError(f"archive path outside {PREFIX}/: {name}")
    if len(name) > 4096:
        raise BundleError(f"overlong archive path: {name}")
    return path


def _validate_archive(archive_path: Path) -> list[tarfile.TarInfo]:
    if not archive_path.is_file():
        raise BundleError(f"archive not found: {archive_path}")
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
    except (tarfile.TarError, OSError) as error:
        raise BundleError(f"cannot read archive: {error}") from error
    if not members:
        raise BundleError("archive is empty")
    seen: set[str] = set()
    for member in members:
        _safe_member_name(member.name)
        if member.name in seen:
            raise BundleError(f"duplicate archive entry: {member.name}")
        seen.add(member.name)
        if member.mode & 0o7000:
            raise BundleError(f"unsafe permission bits on {member.name}: {member.mode:04o}")
        if member.isdir():
            continue
        if not member.isfile():
            raise BundleError(f"non-regular archive entry: {member.name}")
        if member.size < 0 or member.size > MAX_MEMBER_BYTES:
            raise BundleError(f"implausible size on {member.name}: {member.size}")
    required = {f"{PREFIX}/SKILL.md", f"{PREFIX}/engine/pyproject.toml", f"{PREFIX}/MANIFEST.json"}
    missing = required - seen
    if missing:
        raise BundleError(f"archive missing required entries: {sorted(missing)}")
    return members


def _verify_manifest(root: Path, *, allow_runtime: bool) -> dict:
    manifest_path = root / "MANIFEST.json"
    if not manifest_path.is_file():
        raise BundleError(f"missing manifest: {manifest_path}")
    try:
        document = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise BundleError(f"invalid manifest: {error}") from error
    if document.get("schemaVersion") != "1.0" or document.get("id") != PREFIX:
        raise BundleError("manifest schema/id mismatch")
    entries = document.get("files")
    if not isinstance(entries, list) or not entries:
        raise BundleError("manifest has no files")

    expected: dict[str, dict] = {}
    for entry in entries:
        path = entry.get("path")
        if not isinstance(path, str):
            raise BundleError("manifest entry without a path")
        _safe_member_name(f"{PREFIX}/{path}")
        if path == "MANIFEST.json" or path in expected:
            raise BundleError(f"bad manifest path: {path}")
        expected[path] = entry

    root_resolved = root.resolve()
    actual: set[str] = set()
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if allow_runtime and any(
            rel.parts[: len(prefix)] == prefix for prefix in RUNTIME_PREFIXES
        ):
            continue
        if allow_runtime and any(part in {"__pycache__", ".pytest_cache"} for part in rel.parts):
            continue
        if path.is_dir():
            continue
        if path.is_symlink():
            raise BundleError(f"symlink in installed payload: {path}")
        if not path.is_file():
            raise BundleError(f"non-regular file in installed payload: {path}")
        resolved = path.resolve()
        try:
            resolved.relative_to(root_resolved)
        except ValueError as error:
            raise BundleError(f"payload file escapes its root: {path}") from error
        actual.add(rel.as_posix())

    expected_names = set(expected) | {"MANIFEST.json"}
    missing = expected_names - actual
    extra = actual - expected_names
    if missing:
        raise BundleError(f"manifest files missing: {sorted(missing)[:20]}")
    if extra:
        raise BundleError(f"unmanifested files present: {sorted(extra)[:20]}")

    for path, entry in expected.items():
        file_path = root / path
        size = file_path.stat().st_size
        if size != entry.get("size"):
            raise BundleError(f"size mismatch: {path} ({size} != {entry.get('size')})")
        digest = _sha256_file(file_path)
        if digest != entry.get("sha256"):
            raise BundleError(f"sha256 mismatch: {path}")
        mode = f"{stat.S_IMODE(file_path.stat().st_mode):04o}"
        if mode != entry.get("mode"):
            raise BundleError(f"mode mismatch: {path} ({mode} != {entry.get('mode')})")

    if not (root / "SKILL.md").is_file() or not (root / "engine" / "pyproject.toml").is_file():
        raise BundleError("payload missing SKILL.md or engine/pyproject.toml")
    return {
        "ok": True,
        "root": str(root),
        "fileCount": len(expected) + 1,
        "payloadBytes": document.get("payloadBytes"),
        "release": document.get("release"),
    }


def _extract_to_stage(archive_path: Path, parent: Path) -> tuple[Path, Path]:
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise BundleError(f"cannot prepare install parent {parent}: {error}") from error
    target = parent / PREFIX
    if os.path.lexists(target):
        raise BundleError(f"refusing to overwrite existing target: {target}")
    members = _validate_archive(archive_path)
    try:
        stage = Path(tempfile.mkdtemp(prefix=".bookify-extract-", dir=parent))
    except OSError as error:
        raise BundleError(f"cannot create staging directory in {parent}: {error}") from error
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(path=stage, members=members, filter="data")
        payload_root = stage / PREFIX
        if not payload_root.is_dir():
            raise BundleError("archive did not produce the bookify/ directory")
        _verify_manifest(payload_root, allow_runtime=False)
        return stage, payload_root
    except BundleError:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    except (OSError, tarfile.TarError) as error:
        shutil.rmtree(stage, ignore_errors=True)
        raise BundleError(f"cannot extract archive: {error}") from error
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def extract(archive_path: Path, into: Path) -> dict:
    stage, payload_root = _extract_to_stage(archive_path, into)
    target = into / PREFIX
    try:
        os.rename(payload_root, target)
    except OSError as error:
        raise BundleError(f"cannot move payload into place: {error}") from error
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    summary = _verify_manifest(target, allow_runtime=False)
    summary["target"] = str(target)
    return summary


def install(archive_path: Path, target: Path) -> dict:
    raw_target = target.expanduser()
    # Check the raw path before resolve(): resolve() follows a symlink, and a
    # broken link would otherwise be treated as a free target path and replaced.
    if os.path.lexists(raw_target):
        raise BundleError(f"refusing to overwrite existing skill: {raw_target}")
    target = raw_target.resolve()
    parent = target.parent
    stage, payload_root = _extract_to_stage(archive_path, parent)
    try:
        if os.path.lexists(target):
            raise BundleError(f"target appeared during install: {target}")
        try:
            os.rename(payload_root, target)
        except OSError as error:
            raise BundleError(f"cannot move payload into place: {error}") from error
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    summary = _verify_manifest(target, allow_runtime=False)
    summary["target"] = str(target)
    return summary


def inspect(archive_path: Path) -> dict:
    members = _validate_archive(archive_path)
    with tarfile.open(archive_path, "r:gz") as archive:
        manifest_file = archive.extractfile(f"{PREFIX}/MANIFEST.json")
        if manifest_file is None:
            raise BundleError("manifest entry is not a regular file")
        manifest = json.loads(manifest_file.read().decode())
    return {
        "ok": True,
        "archive": str(archive_path),
        "archiveSha256": _sha256_file(archive_path),
        "archiveBytes": archive_path.stat().st_size,
        "members": len(members),
        "files": manifest.get("fileCount"),
        "payloadBytes": manifest.get("payloadBytes"),
        "release": manifest.get("release"),
        "firstMembers": [member.name for member in members[:12]],
    }


def pack(output: Path, *, check_determinism: bool) -> dict:
    payload = _collect_payload()
    manifest = _manifest_bytes(payload)
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="bookify-pack-") as directory:
        first = Path(directory) / "first.tar.gz"
        _write_archive(first, payload, manifest)
        first_sha = _sha256_file(first)
        if check_determinism:
            second = Path(directory) / "second.tar.gz"
            _write_archive(second, payload, manifest)
            second_sha = _sha256_file(second)
            if first_sha != second_sha:
                raise BundleError(f"archive is not deterministic: {first_sha} != {second_sha}")
        else:
            second_sha = None
        staging = output.with_name(output.name + ".tmp")
        shutil.copyfile(first, staging)
        os.replace(staging, output)

    summary = inspect(output)
    summary["determinism"] = {
        "checked": check_determinism,
        "secondSha256": second_sha,
        "identical": second_sha == first_sha if check_determinism else None,
    }
    summary["manifest"] = json.loads(manifest.decode())
    summary["manifest"].pop("files", None)
    return summary


def verify_install(target: Path) -> dict:
    raw_target = target.expanduser()
    if raw_target.is_symlink():
        raise BundleError(f"refusing to verify a symlinked target: {raw_target}")
    if not raw_target.is_dir():
        raise BundleError(f"target is not a directory: {raw_target}")
    return _verify_manifest(raw_target.resolve(), allow_runtime=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and safely install the Bookify skill bundle")
    sub = parser.add_subparsers(dest="command", required=True)

    pack_parser = sub.add_parser("pack", help="build the deterministic archive")
    pack_parser.add_argument("--out", type=Path, default=ROOT / "dist" / "bookify-skill.tar.gz")
    pack_parser.add_argument("--check-determinism", action="store_true")

    inspect_parser = sub.add_parser("inspect", help="validate and summarize an archive")
    inspect_parser.add_argument("--archive", type=Path, required=True)

    extract_parser = sub.add_parser("extract", help="extract into an empty directory")
    extract_parser.add_argument("--archive", type=Path, required=True)
    extract_parser.add_argument("--into", type=Path, required=True)

    install_parser = sub.add_parser("install", help="install as a new skill directory, never overwriting")
    install_parser.add_argument("--archive", type=Path, required=True)
    install_parser.add_argument("--target", type=Path, required=True)

    verify_parser = sub.add_parser("verify-install", help="re-check an installed payload")
    verify_parser.add_argument("--target", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "pack":
            result = pack(args.out, check_determinism=args.check_determinism)
        elif args.command == "inspect":
            result = inspect(args.archive)
        elif args.command == "extract":
            result = extract(args.archive, args.into)
        elif args.command == "install":
            result = install(args.archive, args.target)
        elif args.command == "verify-install":
            result = verify_install(args.target)
        else:  # pragma: no cover
            raise BundleError(f"unknown command: {args.command}")
    except BundleError as error:
        print(json.dumps({"ok": False, "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
