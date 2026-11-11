"""Compile a manuscript to PDF with Typst, offline, and return the build report."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from bookify.errors import BookifyError
from bookify.figures import charts, diagrams
from bookify.manuscript import model
from bookify.publish import illustrations, normalize, report
from bookify.toolchain import doctor, guard, pins

CREATION_TIMESTAMP = "1750000000"
COMPILE_TIMEOUT_SECONDS = 180


@dataclass(frozen=True)
class BuildResult:
    pdf: Path
    report: dict


def _relative(root: Path, path: Path) -> str:
    try:
        return "/" + path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise BookifyError("BUILD_FAILED", f"asset outside the project root: {path}", str(path)) from error


def _render_figures(manuscript: model.Manuscript, build_dir: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    figure_dir = build_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    assets: list[dict[str, str]] = []
    for section in manuscript.sections:
        for block in section["blocks"]:
            if block["type"] == "chart":
                rendered = charts.render(block, manuscript.root, figure_dir)
                paths[block["id"]] = _relative(manuscript.root, rendered.path)
                assets.append({"blockId": block["id"], "kind": "chart", "path": paths[block["id"]], "sha256": rendered.sha256})
            elif block["type"] == "diagram":
                rendered = diagrams.render(block, figure_dir)
                paths[block["id"]] = rendered.snippet
                assets.append({"blockId": block["id"], "kind": "diagram", "path": _relative(manuscript.root, rendered.path), "sha256": rendered.sha256})
    return paths, assets


def _compile(root: Path, build_dir: Path, out_pdf: Path, lock: pins.ToolchainLock) -> None:
    typst = root / lock.typst.binary
    if not shutil.which("bwrap"):
        raise BookifyError("BUILD_FAILED", "bwrap is required to prove an offline build", "bwrap")
    if not typst.is_file():
        raise BookifyError("BUILD_FAILED", "typst binary missing", lock.typst.binary)
    data = "/" + (build_dir / "book.json").resolve().relative_to(root.resolve()).as_posix()
    command = [
        "bwrap", "--unshare-net", "--bind", "/", "/", "--chdir", str(root), "--",
        str(typst), "compile",
        "--ignore-system-fonts", "--ignore-embedded-fonts",
        "--font-path", "assets/fonts",
        "--package-path", "vendor/typst",
        "--package-cache-path", ".cache/empty-pkg",
        "--creation-timestamp", CREATION_TIMESTAMP,
        "--root", ".",
        "--input", f"data={data}",
        "typst/templates/book.typ", str(out_pdf),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=COMPILE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as error:
        raise BookifyError("BUILD_FAILED", f"typst compile timed out after {COMPILE_TIMEOUT_SECONDS}s", str(out_pdf)) from error
    if result.returncode != 0:
        raise BookifyError("BUILD_FAILED", result.stderr.strip()[:2000] or "typst compile failed", str(out_pdf))


def build(
    manuscript_path: Path,
    out_pdf: Path,
    build_dir: Path,
    *,
    offline: bool,
    draft: bool = False,
    lock_path: Path | None = None,
) -> BuildResult:
    if not offline:
        raise BookifyError("BUILD_FAILED", "publishing requires --offline", "--offline")
    manuscript = model.load(manuscript_path)
    build_dir = build_dir if build_dir.is_absolute() else manuscript.root / build_dir
    try:
        build_dir.resolve().relative_to(manuscript.root.resolve())
    except ValueError as error:
        raise BookifyError(
            "BUILD_FAILED",
            "build directory must live inside the project root so Typst can resolve assets",
            str(build_dir),
        ) from error

    lock_file = lock_path if lock_path is not None else manuscript.root / "toolchain.lock.json"
    lock = pins.load(lock_file)
    doctor.run_or_fail(manuscript.root, lock_file)

    out_pdf = out_pdf if out_pdf.is_absolute() else manuscript.root / out_pdf
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    with guard.offline():
        figure_paths, figure_assets = _render_figures(manuscript, build_dir)
        document = normalize.build(manuscript, figure_paths, draft=draft)
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / "book.json").write_text(json.dumps(document.data, indent=2, sort_keys=True) + "\n")
        _compile(manuscript.root, build_dir, out_pdf, lock)

        attempts = 0
        deferred: list[str] = []
        while True:
            data = report.analyse(
                out_pdf, document.data, figure_assets,
                offline=guard.active(), draft=draft, manuscript_path=manuscript_path,
                network_attempts=guard.attempts(),
            )
            unplaced = [item["illustrationId"] for item in data["placements"] if item["page"] is None]
            if unplaced:
                raise BookifyError(
                    "BUILD_FAILED",
                    f"illustration label not found on any page: {', '.join(unplaced)}",
                    str(out_pdf),
                )
            conflicting = illustrations.conflicts(data["placements"])
            if not conflicting:
                break
            attempts += 1
            if attempts > illustrations.MAX_ATTEMPTS:
                illustrations.require_limit(conflicting)
                raise BookifyError("ILLUSTRATION_LIMIT", "placement did not stabilise", str(out_pdf))
            deferred.extend(illustrations.defer_later(document.data, conflicting))
            (build_dir / "book.json").write_text(json.dumps(document.data, indent=2, sort_keys=True) + "\n")
            _compile(manuscript.root, build_dir, out_pdf, lock)

    data["pins"] = {"typst": lock.typst.version, "python": lock.python.version, "fonts": len(lock.fonts)}
    data["deferredIllustrations"] = sorted(set(deferred))
    report.write(data, build_dir / "build-report.json")
    return BuildResult(pdf=out_pdf, report=data)
