#!/usr/bin/env python3
"""Deterministic packaging and safe installation for the Bookify skill bundle.

Standard library only. The payload is an explicit allowlist; the archive has a
single top-level ``bookify/`` directory, sorted entries, fixed metadata, and a
``MANIFEST.json`` covering every payload file. Skill installation is no-clobber,
validated, staged, and atomic. A verified-ownership upgrade backs up the previous
payload and rolls back on failure. Command installation is no-clobber per file,
preflighted, staged and rolled back on failure; there is no ``--force``.
Rebuilding is byte-identical on the same interpreter and zlib build; the
compressed SHA-256 can differ across zlib builds while the uncompressed tar
content stays identical.
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
RELEASE = "2026-11-14"
CANONICAL_CATALOGUE_SHA = "614cf15108a760e3ddf6ceedcd0098c88220949b352e6f7b9657aeae0fc73b37"
MAX_MEMBER_BYTES = 1 << 30

# The three slash entries. Two modes; ``bookify`` is the default alias, not a
# third mode. The physical payload copies are byte-compared with the canonical
# tracked assets at pack time.
COMMAND_NAMES = (
    "bookify",
    "bookify-source-faithful",
    "bookify-teachable-textbook",
)
COMMAND_MODES = {
    "bookify": "source-faithful",
    "bookify-source-faithful": "source-faithful",
    "bookify-teachable-textbook": "teachable",
}
COMMAND_DEFAULT_ALIAS = "bookify"

# Guides shipped at the payload top level so the installed skill carries them
# outside ``engine/`` as well.
REFERENCE_NAMES = (
    "checklist",
    "modes-and-playbooks",
    "source-and-provenance",
    "editorial",
    "visual-design",
    "limits",
)

# Future same-source books and trial workspaces are owned by their authoring
# tracks. They must never leak into a packaging release from this tree.
EXCLUDED_TREE_PREFIXES = {
    "content": ("agent-skill",),
    "examples": ("agent-skill",),
}

# Explicit source allowlist. Nothing else from the working tree is packaged.
SOURCE_TREES = (
    "src",
    "schemas",
    "typst",
    "vendor",
    "assets",
    "fixtures",
    "tools",
    "skill",
)
SOURCE_FILES = (
    "pyproject.toml",
    "uv.lock",
    "toolchain.lock.json",
)
# ``content/trial.yaml`` derives from a private lecture deck and is ignored in
# git for rights/privacy; only the public manuscripts are packaged.
CONTENT_FILES = (
    "content/catalogue.yaml",
    "content/specimen.yaml",
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
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".traineddata"}
# Development-only OCR artefacts. The release engine is the system Tesseract
# package; the extracted CLI and vendored language data must never be published.
# See .opencode/bookify-v2-ocr-capability.md §11.4 for the canonical exclusion.
# Files the public bundle must retain for OCR intake. They are validated at pack
# time so a future allowlist edit cannot silently drop the capability.
REQUIRED_OCR_FILES = (
    "engine/src/bookify/intake/ocr.py",
    "engine/src/bookify/verify/checks/machine_read.py",
    "engine/src/bookify/verify/checks/ocr_free.py",
    "engine/tools/ocr/ocr_harness.py",
    "engine/tools/ocr/ocr.lock.fragment.json",
    "engine/tools/ocr/README.md",
    "engine/tools/ocr/LICENSE",
    "engine/fixtures/ocr-capability/fixture.pdf",
    "engine/fixtures/ocr-capability/README.md",
    "engine/fixtures/ocr-capability/build_fixture.py",
    "engine/fixtures/ocr-capability/source/fixture.typ",
)
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
    ("LICENSE", ROOT / "LICENSE", 0o644),
    ("LICENCES.md", PAYLOAD / "LICENCES.md", 0o644),
    ("verify_manifest.py", PAYLOAD / "verify_manifest.py", 0o644),
    ("licences/OFL-1.1.txt", PAYLOAD / "licences" / "OFL-1.1.txt", 0o644),
    ("licences/fonts-metadata.md", PAYLOAD / "licences" / "fonts-metadata.md", 0o644),
    ("licences/python-dependencies.md", PAYLOAD / "licences" / "python-dependencies.md", 0o644),
)

# Packaged command copies live under ``packaging/payload/commands/`` and must
# stay byte-identical to the canonical tracked assets. Each tuple is
# (command name, packaged copy, canonical source).
COMMAND_FILES = tuple(
    (
        name,
        PAYLOAD / "commands" / f"{name}.md",
        ROOT / "skill" / "bookify" / "commands" / f"{name}.md",
    )
    for name in COMMAND_NAMES
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


def _is_ocr_excluded(rel: Path, tree: str | None) -> bool:
    """Exclude development-only OCR artefacts from the public bundle."""
    if tree == "tools":
        parts = rel.parts
        return len(parts) >= 2 and parts[0] == "ocr" and parts[1].startswith("tesseract")
    if tree == "vendor":
        return rel.parts[:2] == ("ocr", "tessdata")
    if tree == "fixtures":
        return rel.parts[:2] == ("ocr-capability", "build")
    return False


def _is_excluded(rel: Path, tree: str | None = None) -> bool:
    if any(part in EXCLUDED_DIR_NAMES for part in rel.parts):
        return True
    if rel.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    if tree is not None:
        prefixes = EXCLUDED_TREE_PREFIXES.get(tree, ())
        if prefixes and rel.parts[:1] and rel.parts[0] in prefixes:
            return True
        if _is_ocr_excluded(rel, tree):
            return True
    return False


def _walk_tree(base: Path, rel_base: Path, tree: str | None = None) -> list[tuple[str, Path, int]]:
    entries: list[tuple[str, Path, int]] = []
    for path in sorted(base.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(base)
        if _is_excluded(rel, tree):
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

    for name, packaged, canonical in COMMAND_FILES:
        if not packaged.is_file():
            raise BundleError(f"missing packaged command copy: {packaged}")
        if not canonical.is_file():
            raise BundleError(f"missing canonical command asset: {canonical}")
        if packaged.read_bytes() != canonical.read_bytes():
            raise BundleError(
                f"packaged command {name}.md drifted from the canonical asset: {canonical}"
            )
        payload[f"commands/{name}.md"] = (packaged, 0o644)

    for name in REFERENCE_NAMES:
        source = ROOT / "skill" / "bookify" / "references" / f"{name}.md"
        if not source.is_file():
            raise BundleError(f"missing reference guide: {source}")
        payload[f"references/{name}.md"] = (source, 0o644)

    # The payload ships the engine, not its test suite. The suite reads
    # source-only `content/agent-skill` workspaces and the development OCR copy,
    # both deliberately outside the allowlist, so a shipped copy could not pass.
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
        for arcname, source, mode in _walk_tree(base, Path("engine") / tree, tree):
            payload[arcname] = (source, mode)

    for name in CONTENT_FILES:
        source = ROOT / name
        if not source.is_file():
            raise BundleError(f"missing public manuscript: {source}")
        payload[f"engine/{name}"] = (source, 0o644)

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

    for required in REQUIRED_OCR_FILES:
        if required not in payload:
            raise BundleError(f"missing required OCR support file in bundle: {required}")

    return payload


def _manifest_bytes(payload: dict[str, tuple[Path, int]]) -> bytes:
    files = []
    total = 0
    by_path: dict[str, dict] = {}
    for arcname in sorted(payload):
        source, mode = payload[arcname]
        size = source.stat().st_size
        total += size
        entry = {
            "path": arcname,
            "sha256": _sha256_file(source),
            "size": size,
            "mode": f"{mode:04o}",
        }
        files.append(entry)
        by_path[arcname] = entry

    commands = {}
    for name in COMMAND_NAMES:
        entry = by_path.get(f"commands/{name}.md")
        if entry is None:
            continue
        commands[name] = {
            "path": entry["path"],
            "mode": COMMAND_MODES[name],
            "defaultAlias": name == COMMAND_DEFAULT_ALIAS,
            "sha256": entry["sha256"],
        }
    guides = sorted(
        path for path in by_path if path.startswith("references/") and path.endswith(".md")
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
            "commands": "commands/",
            "doctor": "cd engine && uv run bookify toolchain doctor --json",
        },
        "commands": commands,
        "guides": guides,
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

    declared_commands = document.get("commands")
    if declared_commands is not None:
        if not isinstance(declared_commands, dict) or set(declared_commands) != set(COMMAND_NAMES):
            raise BundleError("manifest command entries are incomplete or unknown")
        for name, entry in declared_commands.items():
            path = f"commands/{name}.md"
            if entry.get("path") != path or path not in expected:
                raise BundleError(f"manifest command path mismatch: {name}")
            if entry.get("mode") != COMMAND_MODES[name]:
                raise BundleError(f"manifest command mode mismatch: {name}")
            if entry.get("sha256") != expected[path].get("sha256"):
                raise BundleError(f"manifest command hash mismatch: {name}")
    guides = document.get("guides")
    if guides is not None:
        if not isinstance(guides, list) or not guides:
            raise BundleError("manifest guides entry is empty or invalid")
        for guide in guides:
            if not isinstance(guide, str) or guide not in expected or not guide.startswith("references/"):
                raise BundleError(f"manifest guide path mismatch: {guide!r}")

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


def _extract_to_stage(
    archive_path: Path, parent: Path, *, allow_existing_target: bool = False
) -> tuple[Path, Path]:
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise BundleError(f"cannot prepare install parent {parent}: {error}") from error
    target = parent / PREFIX
    if not allow_existing_target and os.path.lexists(target):
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
        "commands": sorted((manifest.get("commands") or {})),
        "guides": manifest.get("guides"),
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


def _is_within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _prepare_commands_directory(target: Path, *, create: bool) -> Path:
    raw_target = target.expanduser()
    if raw_target.is_symlink():
        raise BundleError(f"refusing a symlinked commands target: {raw_target}")
    if os.path.lexists(raw_target) and not raw_target.exists():
        raise BundleError(f"commands target is a broken link: {raw_target}")
    if raw_target.exists():
        if not raw_target.is_dir():
            raise BundleError(f"commands target is not a directory: {raw_target}")
    else:
        if not create:
            raise BundleError(
                f"commands directory does not exist: {raw_target} "
                "(pass --create to create only the final directory)"
            )
        parent = raw_target.parent
        if parent.is_symlink() or not parent.is_dir():
            raise BundleError(
                f"refusing to create commands under {parent}: parent must be an existing directory"
            )
        try:
            raw_target.mkdir(mode=0o755)
        except OSError as error:
            raise BundleError(f"cannot create commands directory {raw_target}: {error}") from error
    return raw_target.resolve()


def _archive_commands(archive_path: Path) -> tuple[dict[str, bytes], dict, str]:
    """Read and cross-check the three command payloads from an archive."""
    _validate_archive(archive_path)
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            handle = archive.extractfile(f"{PREFIX}/MANIFEST.json")
            if handle is None:
                raise BundleError("manifest entry is not a regular file")
            manifest_bytes = handle.read()
            manifest = json.loads(manifest_bytes.decode())
            files = {
                entry.get("path"): entry
                for entry in manifest.get("files", [])
                if isinstance(entry, dict)
            }
            declared = manifest.get("commands")
            if not isinstance(declared, dict):
                raise BundleError("archive manifest declares no command assets")
            blobs: dict[str, bytes] = {}
            for name in COMMAND_NAMES:
                path = f"commands/{name}.md"
                entry = files.get(path)
                command_entry = declared.get(name)
                if entry is None or not isinstance(command_entry, dict):
                    raise BundleError(f"archive is missing command asset: {path}")
                if command_entry.get("path") != path:
                    raise BundleError(f"archive command path mismatch: {name}")
                if command_entry.get("mode") != COMMAND_MODES[name]:
                    raise BundleError(f"archive command mode mismatch: {name}")
                command_file = archive.extractfile(f"{PREFIX}/{path}")
                if command_file is None:
                    raise BundleError(f"archive command entry is not a regular file: {path}")
                data = command_file.read()
                digest = _sha256_bytes(data)
                if digest != entry.get("sha256") or digest != command_entry.get("sha256"):
                    raise BundleError(f"archive command hash mismatch: {name}")
                blobs[name] = data
    except (tarfile.TarError, OSError, json.JSONDecodeError) as error:
        raise BundleError(f"cannot read command payloads: {error}") from error
    return blobs, manifest, _sha256_bytes(manifest_bytes)


def install_commands(archive_path: Path, target: Path, *, create: bool = False) -> dict:
    """Install the three slash command assets without overwriting anything."""
    directory = _prepare_commands_directory(target, create=create)
    blobs, manifest, manifest_sha = _archive_commands(archive_path)
    destinations = {name: directory / f"{name}.md" for name in COMMAND_NAMES}

    unchanged: list[str] = []
    for name, destination in destinations.items():
        if not os.path.lexists(destination):
            continue
        if destination.is_symlink():
            raise BundleError(f"refusing a symlinked command target: {destination}")
        if not destination.is_file():
            raise BundleError(f"refusing a non-regular command target: {destination}")
        if _sha256_file(destination) != _sha256_bytes(blobs[name]):
            raise BundleError(
                "refusing to overwrite an existing command that is not this "
                f"Bookify release: {destination} (no --force is provided; move "
                "or edit the file deliberately)"
            )
        unchanged.append(name)

    staging = Path(tempfile.mkdtemp(prefix=".bookify-commands-", dir=directory))
    installed: list[Path] = []
    try:
        for name, data in blobs.items():
            staged = staging / f"{name}.md"
            staged.write_bytes(data)
            staged.chmod(0o644)
        for name, destination in destinations.items():
            if name in unchanged:
                continue
            try:
                os.rename(staging / f"{name}.md", destination)
            except OSError as error:
                raise BundleError(f"cannot install command {destination}: {error}") from error
            installed.append(destination)
    except BaseException:
        for installed_path in installed:
            try:
                installed_path.unlink()
            except OSError:
                pass
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    summary = verify_commands(archive_path, directory)
    summary["installed"] = [path.name for path in installed]
    summary["unchanged"] = unchanged
    summary["manifestSha256"] = manifest_sha
    summary["release"] = manifest.get("release")
    return summary


def verify_commands(archive_path: Path, target: Path) -> dict:
    raw_target = target.expanduser()
    if raw_target.is_symlink():
        raise BundleError(f"refusing to verify a symlinked commands target: {raw_target}")
    if not raw_target.is_dir():
        raise BundleError(f"commands target is not a directory: {raw_target}")
    directory = raw_target.resolve()
    blobs, manifest, manifest_sha = _archive_commands(archive_path)
    for name in COMMAND_NAMES:
        destination = directory / f"{name}.md"
        if destination.is_symlink():
            raise BundleError(f"refusing a symlinked installed command: {destination}")
        if not destination.is_file():
            raise BundleError(f"missing installed command: {destination}")
        if _sha256_file(destination) != _sha256_bytes(blobs[name]):
            raise BundleError(f"installed command drifted from the archive: {destination}")
    return {
        "ok": True,
        "target": str(directory),
        "manifestSha256": manifest_sha,
        "release": manifest.get("release"),
        "commands": [f"{name}.md" for name in COMMAND_NAMES],
    }


def upgrade(
    archive_path: Path,
    target: Path,
    *,
    expect_manifest_sha256: str,
    backup: Path,
) -> dict:
    """Replace a verified Bookify install, keeping an atomic backup.

    The explicit expected manifest hash is the ownership proof. A payload whose
    manifest hash differs, or whose files no longer match its own manifest, is
    refused rather than replaced. Runtime-only directories created by setup are
    tolerated, exactly as in ``verify-install``. There is no ``--force``.
    """
    expected = expect_manifest_sha256.strip().lower()
    if len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
        raise BundleError("--expect-manifest-sha256 must be a lowercase SHA-256 hex digest")

    raw_target = target.expanduser()
    if raw_target.is_symlink():
        raise BundleError(f"refusing to upgrade a symlinked skill: {raw_target}")
    if not raw_target.is_dir():
        raise BundleError(f"skill target is not a directory: {raw_target}")
    target_dir = raw_target.resolve()
    manifest_path = target_dir / "MANIFEST.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise BundleError(f"missing or symlinked install manifest: {manifest_path}")
    previous_sha = _sha256_file(manifest_path)
    if previous_sha != expected:
        raise BundleError(
            "refusing to upgrade: installed MANIFEST.json does not match the "
            f"expected release hash ({previous_sha} != {expected})"
        )
    # Detects a user-edited payload: the manifest hash can still match while a
    # file does not. Runtime-only directories created by setup are tolerated.
    _verify_manifest(target_dir, allow_runtime=True)

    backup_path = backup.expanduser()
    if os.path.lexists(backup_path):
        raise BundleError(f"refusing to overwrite existing backup: {backup_path}")
    if backup_path.parent.is_symlink() or not backup_path.parent.is_dir():
        raise BundleError(f"backup parent is not an existing directory: {backup_path.parent}")
    backup_dir = backup_path.parent.resolve() / backup_path.name
    if _is_within(backup_dir, target_dir) or _is_within(target_dir, backup_dir):
        raise BundleError("backup and skill target must not contain each other")

    stage, payload_root = _extract_to_stage(
        archive_path, target_dir.parent, allow_existing_target=True
    )
    try:
        try:
            os.rename(target_dir, backup_dir)
        except OSError as error:
            raise BundleError(f"cannot move the existing install to backup: {error}") from error
        try:
            os.rename(payload_root, target_dir)
            summary = _verify_manifest(target_dir, allow_runtime=False)
        except (OSError, BundleError) as error:
            try:
                if os.path.lexists(target_dir):
                    os.rename(target_dir, stage / "failed-new")
                os.rename(backup_dir, target_dir)
            except OSError as rollback_error:
                raise BundleError(
                    f"upgrade failed ({error}) and rollback failed "
                    f"({rollback_error}); restore {backup_dir} to {target_dir} manually"
                ) from error
            raise BundleError(f"upgrade failed and was rolled back: {error}") from error
    finally:
        shutil.rmtree(stage, ignore_errors=True)

    summary["target"] = str(target_dir)
    summary["backup"] = str(backup_dir)
    summary["previousManifestSha256"] = previous_sha
    summary["manifestSha256"] = _sha256_file(target_dir / "MANIFEST.json")
    return summary


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

    upgrade_parser = sub.add_parser(
        "upgrade", help="replace a verified Bookify skill install, keeping a backup"
    )
    upgrade_parser.add_argument("--archive", type=Path, required=True)
    upgrade_parser.add_argument("--target", type=Path, required=True)
    upgrade_parser.add_argument("--expect-manifest-sha256", required=True)
    upgrade_parser.add_argument("--backup", type=Path, required=True)

    install_commands_parser = sub.add_parser(
        "install-commands", help="install the three slash commands without overwriting"
    )
    install_commands_parser.add_argument("--archive", type=Path, required=True)
    install_commands_parser.add_argument("--target", type=Path, required=True)
    install_commands_parser.add_argument(
        "--create", action="store_true", help="create the final commands directory (parent must exist)"
    )

    verify_commands_parser = sub.add_parser(
        "verify-commands", help="re-check installed slash commands against an archive"
    )
    verify_commands_parser.add_argument("--archive", type=Path, required=True)
    verify_commands_parser.add_argument("--target", type=Path, required=True)

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
        elif args.command == "upgrade":
            result = upgrade(
                args.archive,
                args.target,
                expect_manifest_sha256=args.expect_manifest_sha256,
                backup=args.backup,
            )
        elif args.command == "install-commands":
            result = install_commands(args.archive, args.target, create=args.create)
        elif args.command == "verify-commands":
            result = verify_commands(args.archive, args.target)
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
