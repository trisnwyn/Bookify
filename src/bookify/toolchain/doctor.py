"""Report whether the pinned local stack is actually present."""

from __future__ import annotations

import importlib.metadata
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from bookify.errors import BookifyError
from bookify.toolchain import pins


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


def _check_python(root: Path, lock: pins.ToolchainLock) -> Check:
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


def _check_python_packages(lock: pins.ToolchainLock) -> list[Check]:
    checks: list[Check] = []
    for name, version in lock.python.packages.items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            checks.append(_result(f"package:{name}", False, "not installed", "BUILD_FAILED"))
            continue
        checks.append(_result(f"package:{name}", actual == version, f"{actual} (pinned {version})", "BUILD_FAILED"))
    return checks


def _check_typst(root: Path, lock: pins.ToolchainLock) -> Check:
    binary = root / lock.typst.binary
    if not binary.is_file():
        return _result("typst", False, f"missing binary: {lock.typst.binary}", "BUILD_FAILED")
    try:
        output = subprocess.run(
            [str(binary), "--version"], capture_output=True, text=True, timeout=30, check=False
        ).stdout.strip()
    except OSError as error:
        return _result("typst", False, f"cannot run binary: {error}", "BUILD_FAILED")
    version_ok = lock.typst.version in output
    digest_ok = pins.file_sha256(binary) == lock.typst.sha256
    if version_ok and digest_ok:
        return _result("typst", True, f"{lock.typst.version} sha256 ok", "BUILD_FAILED")
    return _result("typst", False, f"version={output!r} hash_ok={digest_ok}", "BUILD_FAILED")


def _check_package(root: Path, package: pins.PackagePin) -> Check:
    directory = root / package.path
    if not directory.is_dir():
        return _result(f"package:{package.name}", False, f"missing directory: {package.path}", "BUILD_FAILED")
    digest_ok = pins.tree_sha256(directory) == package.sha256
    return _result(
        f"package:{package.name}",
        digest_ok,
        f"{package.version} tree hash {'ok' if digest_ok else 'mismatch'}",
        "BUILD_FAILED",
    )


def _check_font(root: Path, font: pins.FontPin) -> Check:
    path = root / font.path
    if not path.is_file():
        return _result(f"font:{font.family}", False, f"missing file: {font.path}", "FONT_MISSING")
    digest_ok = pins.file_sha256(path) == font.sha256
    return _result(
        f"font:{font.family}",
        digest_ok,
        f"{font.weight} sha256 {'ok' if digest_ok else 'mismatch'}",
        "FONT_MISSING",
    )


def run(root: Path, lock_path: Path | None = None) -> Report:
    lock = pins.load(lock_path or root / "toolchain.lock.json")
    checks: list[Check] = [_check_python(root, lock)]
    checks.extend(_check_python_packages(lock))
    checks.append(_check_typst(root, lock))
    checks.extend(_check_package(root, package) for package in lock.packages)
    checks.extend(_check_font(root, font) for font in lock.fonts)
    return Report(checks=tuple(checks))


def run_or_fail(root: Path, lock_path: Path | None = None) -> Report:
    report = run(root, lock_path)
    if not report.ok:
        failure = next(check for check in report.checks if not check.is_local)
        raise BookifyError(failure.code or "BUILD_FAILED", report.summary(), failure.identifier)
    return report
