"""Report whether the pinned local stack is actually present."""

from __future__ import annotations

import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from bookify import runtime
from bookify.errors import BookifyError
from bookify.toolchain import fonts as fonts_mod
from bookify.toolchain import pins, typst_install

POPPLER_TOOLS: tuple[str, ...] = (
    "pdfinfo",
    "pdftotext",
    "pdftohtml",
    "pdftoppm",
    "pdfimages",
    "pdffonts",
)
REQUIRED_SYSTEM_TOOLS: tuple[str, ...] = ("bwrap", *POPPLER_TOOLS)


def _poppler_hint() -> str:
    if sys.platform == "darwin":
        return "brew install poppler"
    if sys.platform == "win32":
        return "winget install oschwartz10612.Poppler"
    return "sudo apt install poppler-utils  # or: sudo dnf install poppler-utils"


@dataclass(frozen=True)
class Check:
    identifier: str
    detail: str
    is_local: bool
    code: str | None = None


@dataclass(frozen=True)
class Report:
    checks: tuple[Check, ...]

    @property
    def ok(self) -> bool:
        return all(check.is_local for check in self.checks)

    def summary(self) -> str:
        failures = [f"{c.identifier}: {c.detail}" for c in self.checks if not c.is_local]
        return "all local" if not failures else "; ".join(failures)

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "checks": [
                {"id": c.identifier, "local": c.is_local, "code": c.code, "detail": c.detail}
                for c in self.checks
            ],
        }


def _result(identifier: str, ok: bool, detail: str, code: str) -> Check:
    return Check(identifier=identifier, detail=detail, is_local=ok, code=None if ok else code)


def _check_python(root: Path, lock: pins.ToolchainLock, *, strict: bool = True) -> Check:
    if not strict:
        ok = (3, 12) <= sys.version_info[:2] < (3, 14)
        return _result(
            "python",
            ok,
            f"{platform.python_version()} at {sys.executable}" + ("" if ok else " (requires Python 3.12–3.13)"),
            "BUILD_FAILED",
        )
    expected = root / lock.python.executable
    version_ok = platform.python_version() == lock.python.version
    path_ok = Path(sys.executable).resolve() == expected.resolve()
    if version_ok and path_ok:
        return _result("python", True, f"{lock.python.version} at {lock.python.executable}", "BUILD_FAILED")
    return _result(
        "python",
        False,
        f"running {platform.python_version()} at {sys.executable}, pinned {lock.python.version} at {expected}",
        "BUILD_FAILED",
    )


def _check_python_packages(lock: pins.ToolchainLock, *, strict: bool = True) -> list[Check]:
    checks: list[Check] = []
    for name, version in lock.python.packages.items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            checks.append(_result(f"package:{name}", False, "not installed", "BUILD_FAILED"))
            continue
        ok = (actual == version) if strict else True
        detail = f"{actual} (pinned {version})" if strict else f"{actual} (compatible)"
        checks.append(_result(f"package:{name}", ok, detail, "BUILD_FAILED"))
    return checks


def _check_typst(root: Path, lock: pins.ToolchainLock, *, strict: bool = True) -> Check:
    resolved = typst_install.resolve_typst(root, lock, allow_portable=not strict)
    if resolved is None:
        hint = (
            f"missing binary: {lock.typst.binary}"
            if strict
            else "typst not found; run 'bookify toolchain install' or install typst onto PATH"
        )
        return _result("typst", False, hint, "BUILD_FAILED")
    binary, source = resolved
    try:
        output = subprocess.run(
            [str(binary), "--version"], capture_output=True, text=True, timeout=30, check=False
        ).stdout.strip()
    except OSError as error:
        return _result("typst", False, f"cannot run binary: {error}", "BUILD_FAILED")
    if strict:
        version_ok = lock.typst.version in output
        digest_ok = pins.file_sha256(binary) == lock.typst.sha256
        if version_ok and digest_ok:
            return _result("typst", True, f"{lock.typst.version} sha256 ok", "BUILD_FAILED")
        return _result("typst", False, f"version={output!r} hash_ok={digest_ok}", "BUILD_FAILED")
    ok = bool(output) and "typst" in output.lower()
    return _result("typst", ok, f"{output} ({source}: {binary})", "BUILD_FAILED")


def _check_package(root: Path, package: pins.PackagePin, *, strict: bool = True) -> Check:
    directory = root / package.path
    if not directory.is_dir():
        return _result(f"package:{package.name}", False, f"missing directory: {package.path}", "BUILD_FAILED")
    digest_ok = pins.tree_sha256(directory) == package.sha256
    if not digest_ok and not strict and (directory / "typst.toml").is_file():
        # Windows git checkouts with autocrlf can rewrite LF -> CRLF in vendored text files.
        return _result(f"package:{package.name}", True, f"{package.version} present (portable)", "BUILD_FAILED")
    return _result(
        f"package:{package.name}",
        digest_ok,
        f"{package.version} tree hash {'ok' if digest_ok else 'mismatch'}",
        "BUILD_FAILED",
    )


def _check_font(root: Path, font: pins.FontPin, *, strict: bool = True) -> Check:
    path = runtime.resolve_font_path(root, font.path)
    if path is None or not path.is_file():
        if not strict and font.path == fonts_mod.CJK_FONT_RELATIVE:
            return _result(
                f"font:{font.family}",
                True,
                "optional CJK pack not installed (run 'bookify fonts install cjk' when authoring Japanese books)",
                "FONT_MISSING",
            )
        return _result(f"font:{font.family}", False, f"missing file: {font.path}", "FONT_MISSING")
    digest_ok = pins.file_sha256(path) == font.sha256
    return _result(
        f"font:{font.family}",
        digest_ok,
        f"{font.weight} sha256 {'ok' if digest_ok else 'mismatch'}",
        "FONT_MISSING",
    )


def _check_system_tools(*, strict: bool = True) -> list[Check]:
    checks: list[Check] = []
    if strict:
        for name in REQUIRED_SYSTEM_TOOLS:
            found = shutil.which(name)
            checks.append(
                _result(
                    f"tool:{name}",
                    found is not None,
                    found if found is not None else f"missing system tool: {name}",
                    "BUILD_FAILED",
                )
            )
        return checks

    bwrap = shutil.which("bwrap") if sys.platform.startswith("linux") else None
    checks.append(
        _result(
            "tool:bwrap",
            True,
            bwrap if bwrap else f"not active on {sys.platform} (using local env-isolated Typst offline mode)",
            "BUILD_FAILED",
        )
    )
    hint = _poppler_hint()
    for name in POPPLER_TOOLS:
        found = shutil.which(name)
        checks.append(
            _result(
                f"tool:{name}",
                found is not None,
                found if found is not None else f"missing {name}; install Poppler ({hint})",
                "BUILD_FAILED",
            )
        )
    return checks


def run(root: Path, lock_path: Path | None = None, *, strict: bool | None = None) -> Report:
    if strict is None:
        use_strict = (
            not runtime.is_installed_wheel(root)
            and os.environ.get("BOOKIFY_PORTABLE") != "1"
            and sys.platform.startswith("linux")
        )
    else:
        use_strict = strict
    lock = pins.load(lock_path or root / "toolchain.lock.json")
    checks: list[Check] = [_check_python(root, lock, strict=use_strict)]
    checks.extend(_check_python_packages(lock, strict=use_strict))
    checks.append(_check_typst(root, lock, strict=use_strict))
    checks.extend(_check_package(root, package, strict=use_strict) for package in lock.packages)
    checks.extend(_check_font(root, font, strict=use_strict) for font in lock.fonts)
    checks.extend(_check_system_tools(strict=use_strict))
    return Report(checks=tuple(checks))


def run_or_fail(root: Path, lock_path: Path | None = None, *, strict: bool | None = None) -> Report:
    report = run(root, lock_path, strict=strict)
    if not report.ok:
        failure = next(check for check in report.checks if not check.is_local)
        raise BookifyError(failure.code or "BUILD_FAILED", report.summary(), failure.identifier)
    return report
