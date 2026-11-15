"""List-argv subprocess boundary for untrusted PDF tools.

Intake reads a PDF that the user supplied; the bytes are untrusted input. Every
Poppler and Tesseract invocation therefore goes through this module: list argv
only (never a shell), a per-command timeout, a fixed environment, and — by
default — a `bwrap --unshare-net` namespace with the source read-only and only
the intake output writable. A caller that genuinely trusts a local source can
pass ``allow_unsandboxed=True``; the run log then records that choice instead
of silently running outside the guard.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from bookify.errors import BookifyError


@dataclass(frozen=True)
class SandboxPolicy:
    """How intake commands run. Offline (sandboxed) is the default."""

    offline: bool = True
    timeout: float = 60.0
    env: dict[str, str] | None = None
    workdir: Path | None = None
    writable_dirs: tuple[Path, ...] = field(default_factory=tuple)
    allow_unsandboxed: bool = False

    def with_env(self, env: dict[str, str], workdir: Path | None = None) -> "SandboxPolicy":
        return SandboxPolicy(
            offline=self.offline,
            timeout=self.timeout,
            env=dict(env),
            workdir=workdir or self.workdir,
            writable_dirs=self.writable_dirs,
            allow_unsandboxed=self.allow_unsandboxed,
        )

    def writable(self, *paths: Path) -> "SandboxPolicy":
        merged = tuple(dict.fromkeys((*self.writable_dirs, *paths)))
        return SandboxPolicy(
            offline=self.offline,
            timeout=self.timeout,
            env=None if self.env is None else dict(self.env),
            workdir=self.workdir,
            writable_dirs=merged,
            allow_unsandboxed=self.allow_unsandboxed,
        )


def bwrap_path() -> str | None:
    return shutil.which("bwrap")


def sandbox_prefix(policy: SandboxPolicy, cwd: Path | None) -> list[str] | None:
    """The argv prefix, or ``None`` for an explicit unsandboxed run."""
    if not policy.offline:
        return None
    bwrap = bwrap_path()
    if not bwrap:
        if policy.allow_unsandboxed:
            return None
        raise BookifyError(
            "BUILD_FAILED",
            "bwrap is required for an offline intake run; install bubblewrap or "
            "pass --allow-unsandboxed for a trusted local source",
            "bwrap",
        )
    workdir = policy.workdir or cwd or Path.cwd()
    prefix = [
        bwrap,
        "--unshare-net",
        "--die-with-parent",
        "--ro-bind", "/", "/",
        "--tmpfs", "/run",
        "--dev", "/dev",
        "--proc", "/proc",
    ]
    for directory in policy.writable_dirs:
        if directory.exists():
            prefix += ["--bind", str(directory), str(directory)]
    if workdir.exists():
        prefix += ["--bind", str(workdir), str(workdir)]
    prefix += ["--chdir", str(cwd or workdir), "--"]
    return prefix


def run(
    argv: list[str],
    policy: SandboxPolicy,
    *,
    cwd: Path | None = None,
    timeout: float | None = None,
    locator: str = "intake",
    not_found_code: str = "INPUT_INVALID",
    timeout_code: str = "SOURCE_UNREADABLE",
) -> subprocess.CompletedProcess[bytes]:
    """Run one tool command under the intake boundary."""
    if not policy.offline and not policy.allow_unsandboxed:
        raise BookifyError(
            "BUILD_FAILED",
            "intake refused an unsandboxed run; pass --allow-unsandboxed for a "
            "trusted local source or install bubblewrap for the default guard",
            "bwrap",
        )
    prefix = sandbox_prefix(policy, cwd)
    command = argv if prefix is None else [*prefix, *argv]
    effective_timeout = max(0.1, timeout if timeout is not None else policy.timeout)
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=effective_timeout,
            env=policy.env,
            cwd=None if prefix is not None else cwd,
            check=False,
        )
    except FileNotFoundError as error:
        raise BookifyError(not_found_code, f"tool not found: {argv[0]}", locator) from error
    except subprocess.TimeoutExpired as error:
        raise BookifyError(
            timeout_code,
            f"timeout after {effective_timeout:g}s: {Path(argv[0]).name}",
            f"{locator}.timeout",
        ) from error
    if prefix is not None and result.returncode != 0:
        stderr = result.stderr.decode("utf-8", "replace").strip()
        if stderr.startswith("bwrap:"):
            raise BookifyError("BUILD_FAILED", f"intake sandbox failed: {stderr[:400]}", "bwrap")
    return result


def record(policy: SandboxPolicy) -> dict[str, object]:
    """The run-log record: what actually ran, not what was requested."""
    prefix = sandbox_prefix(policy, policy.workdir) if policy.offline else None
    return {
        "offline": bool(policy.offline and prefix is not None),
        "sandboxed": prefix is not None,
        "unsandboxedExplicit": bool(policy.offline is False and policy.allow_unsandboxed)
        or bool(prefix is None and policy.allow_unsandboxed),
        "bwrap": bwrap_path(),
        "argv": prefix or [],
        "writableDirs": [str(path) for path in policy.writable_dirs],
        "timeoutSeconds": policy.timeout,
    }


__all__ = ["SandboxPolicy", "bwrap_path", "record", "run", "sandbox_prefix"]
