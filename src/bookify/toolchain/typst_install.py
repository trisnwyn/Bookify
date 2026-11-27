"""Cross-platform Typst binary resolution and pinned installer (Linux, macOS, Windows)."""

from __future__ import annotations

import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from bookify import runtime
from bookify.errors import BookifyError
from bookify.toolchain import pins

TYPST_VERSION = "0.15.1"

# Official Typst v0.15.1 GitHub release archives per (sys.platform, normalized arch).
PLATFORM_ARCHIVES: dict[tuple[str, str], tuple[str, str]] = {
    ("linux", "x86_64"): (
        f"https://github.com/typst/typst/releases/download/v{TYPST_VERSION}/typst-x86_64-unknown-linux-musl.tar.xz",
        "tar.xz",
    ),
    ("linux", "aarch64"): (
        f"https://github.com/typst/typst/releases/download/v{TYPST_VERSION}/typst-aarch64-unknown-linux-musl.tar.xz",
        "tar.xz",
    ),
    ("darwin", "arm64"): (
        f"https://github.com/typst/typst/releases/download/v{TYPST_VERSION}/typst-aarch64-apple-darwin.tar.xz",
        "tar.xz",
    ),
    ("darwin", "x86_64"): (
        f"https://github.com/typst/typst/releases/download/v{TYPST_VERSION}/typst-x86_64-apple-darwin.tar.xz",
        "tar.xz",
    ),
    ("win32", "x86_64"): (
        f"https://github.com/typst/typst/releases/download/v{TYPST_VERSION}/typst-x86_64-pc-windows-msvc.zip",
        "zip",
    ),
}

# Known SHA-256 digests for pinned release archives when recorded.
KNOWN_ARCHIVE_SHA256: dict[tuple[str, str], str] = {
    ("linux", "x86_64"): "a6d077d0a95eed5a2eba715b2dae06be954f624ccbf85758a03f389ded33118c",
}


def normalized_platform(
    system: str | None = None,
    machine: str | None = None,
) -> tuple[str, str]:
    plat = (system or sys.platform).lower()
    if plat.startswith("linux"):
        plat = "linux"
    elif plat == "darwin":
        plat = "darwin"
    elif plat.startswith("win") or plat in {"cygwin", "msys"}:
        plat = "win32"

    raw_arch = (machine or platform.machine()).lower()
    arch_map = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "x86_64": "x86_64",
        "arm64": "aarch64" if plat == "linux" else "arm64",
        "aarch64": "aarch64" if plat == "linux" else "arm64",
    }
    return plat, arch_map.get(raw_arch, raw_arch)


def binary_name(system: str | None = None) -> str:
    plat, _ = normalized_platform(system=system)
    return "typst.exe" if plat == "win32" else "typst"


def cached_binary(version: str = TYPST_VERSION, *, cache_root: Path | None = None) -> Path:
    base = cache_root or runtime.bin_cache_dir()
    return base / f"typst-{version}" / binary_name()


def resolve_typst(
    engine: Path,
    lock: pins.ToolchainLock,
    *,
    allow_portable: bool = True,
) -> tuple[Path, str] | None:
    """Locate Typst in precedence order: compatible vendored -> user cache -> PATH."""
    # The vendored binary in toolchain.lock.json is Linux x86_64 ELF.
    # On macOS/Windows/arm64 (in portable mode), prefer the cached OS-native binary.
    is_linux_x64 = normalized_platform() == ("linux", "x86_64")
    vendored = engine / lock.typst.binary
    if (is_linux_x64 or not allow_portable) and vendored.is_file():
        return vendored, "vendored"

    if not allow_portable:
        return None

    cached = cached_binary(lock.typst.version)
    if cached.is_file():
        return cached, "cache"

    on_path = shutil.which("typst")
    if on_path:
        return Path(on_path), "path"
    return None


def _extract_binary(archive: Path, fmt: str, dest: Path, exe_name: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=dest.parent, prefix=".typst-", delete=False) as handle:
        tmp_path = Path(handle.name)
    try:
        found = False
        if fmt == "zip":
            with zipfile.ZipFile(archive) as zf:
                for member in zf.infolist():
                    if Path(member.filename).name == exe_name and not member.is_dir():
                        with zf.open(member) as src, tmp_path.open("wb") as out:
                            shutil.copyfileobj(src, out)
                        found = True
                        break
        else:
            with tarfile.open(archive, "r:*") as tf:
                for member in tf.getmembers():
                    if member.isfile() and Path(member.name).name == exe_name:
                        extracted = tf.extractfile(member)
                        if extracted is None:
                            continue
                        with extracted, tmp_path.open("wb") as out:
                            shutil.copyfileobj(extracted, out)
                        found = True
                        break
        if not found:
            raise BookifyError("BUILD_FAILED", f"archive does not contain {exe_name}: {archive}", str(archive))
        if sys.platform != "win32":
            os.chmod(tmp_path, 0o755)
        tmp_path.replace(dest)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def install_typst(
    *,
    version: str = TYPST_VERSION,
    from_archive: Path | None = None,
    cache_root: Path | None = None,
) -> dict[str, object]:
    """Install the pinned Typst binary for the current OS/architecture into the user cache."""
    key = normalized_platform()
    if key not in PLATFORM_ARCHIVES:
        raise BookifyError(
            "BUILD_FAILED",
            f"unsupported platform for automatic Typst install: {key[0]}/{key[1]}; install typst {version} onto PATH manually",
            f"{key[0]}/{key[1]}",
        )
    url, fmt = PLATFORM_ARCHIVES[key]
    dest = cached_binary(version, cache_root=cache_root)
    if dest.is_file():
        return {
            "ok": True,
            "status": "already-installed",
            "version": version,
            "platform": f"{key[0]}/{key[1]}",
            "path": str(dest),
            "sha256": pins.file_sha256(dest),
        }

    with tempfile.TemporaryDirectory(prefix="bookify-typst-") as tmp_dir:
        if from_archive is not None:
            archive = from_archive.expanduser().resolve()
            if not archive.is_file():
                raise BookifyError("INPUT_INVALID", f"Typst archive not found: {archive}", str(archive))
            fmt = "zip" if archive.suffix.lower() == ".zip" else "tar.xz"
        else:
            archive = Path(tmp_dir) / Path(url).name
            try:
                urllib.request.urlretrieve(url, archive)
            except Exception as error:  # noqa: BLE001
                raise BookifyError(
                    "BUILD_FAILED",
                    f"failed to download Typst {version} from {url}: {error}",
                    url,
                ) from error
            expected_sha = KNOWN_ARCHIVE_SHA256.get(key)
            if expected_sha and pins.file_sha256(archive) != expected_sha:
                raise BookifyError("BUILD_FAILED", f"downloaded Typst archive sha256 mismatch for {key}", url)

        _extract_binary(archive, fmt, dest, binary_name())

    try:
        probe = subprocess.run([str(dest), "--version"], capture_output=True, text=True, timeout=30, check=False)
        reported = probe.stdout.strip()
    except OSError as error:
        raise BookifyError("BUILD_FAILED", f"installed Typst binary failed to run: {error}", str(dest)) from error

    return {
        "ok": True,
        "status": "installed",
        "version": reported or version,
        "platform": f"{key[0]}/{key[1]}",
        "path": str(dest),
        "sha256": pins.file_sha256(dest),
        "executable": bool(dest.stat().st_mode & stat.S_IXUSR) if sys.platform != "win32" else True,
    }
