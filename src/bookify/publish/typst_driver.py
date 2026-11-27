"""Compile a manuscript to PDF with Typst, offline, and return the build report."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from bookify import runtime
from bookify.authoring import workspace as workspace_mod
from bookify.design import coverage as design_coverage
from bookify.errors import BookifyError
from bookify.figures import charts, diagrams
from bookify.manuscript import model
from bookify.publish import illustrations, normalize, report, rights
from bookify.toolchain import audit
from bookify.toolchain import doctor, guard, pins, typst_install

CREATION_TIMESTAMP = "1750000000"
COMPILE_TIMEOUT_SECONDS = 180
SANDBOX_MODES = ("auto", "bwrap", "none")


@lru_cache(maxsize=1)
def _bwrap_works() -> bool:
    if not sys.platform.startswith("linux"):
        return False
    bwrap = shutil.which("bwrap")
    if not bwrap:
        return False
    probe_bin = "/bin/true" if Path("/bin/true").exists() else "/usr/bin/true"
    if not Path(probe_bin).exists():
        return False
    try:
        res = subprocess.run(
            [bwrap, "--unshare-net", "--ro-bind", "/", "/", "--", probe_bin],
            capture_output=True,
            timeout=10,
            check=False,
        )
        return res.returncode == 0
    except OSError:
        return False


def _use_bwrap(sandbox: str) -> bool:
    if sandbox not in SANDBOX_MODES:
        raise BookifyError("INPUT_INVALID", f"unsupported sandbox mode: {sandbox}", sandbox)
    if sandbox == "none":
        return False
    if sandbox == "bwrap":
        if not shutil.which("bwrap"):
            raise BookifyError("BUILD_FAILED", "bwrap is required to prove an offline build", "bwrap")
        return True
    return _bwrap_works()


def _materialize_stage_non_bwrap(manuscript: model.Manuscript, stage: Path) -> None:
    """Copy small Typst templates and book assets into stage when bwrap is inactive.

    Typst enforces that source/image files resolve inside ``--root`` (rejecting
    symlinks that escape it), whereas ``--font-path`` and ``--package-path``
    may point directly at the read-only engine directories without copying.
    """
    typst_src = manuscript.engine / "typst"
    if not typst_src.is_dir():
        raise BookifyError("BUILD_FAILED", f"engine asset missing: {typst_src}", str(typst_src))
    typst_dst = stage / "typst"
    if typst_dst.is_symlink() or typst_dst.is_file():
        typst_dst.unlink()
    elif typst_dst.is_dir():
        shutil.rmtree(typst_dst)
    shutil.copytree(typst_src, typst_dst)

    root = manuscript.root.resolve()
    for asset in _book_assets(manuscript):
        target = stage / asset.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset, target)
    (stage / ".cache" / "empty-pkg").mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class BuildResult:
    pdf: Path
    report: dict


def _relative(root: Path, path: Path) -> str:
    try:
        return "/" + path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise BookifyError("BUILD_FAILED", f"asset outside the project root: {path}", str(path)) from error


def _render_figures(
    manuscript: model.Manuscript,
    figure_dir: Path,
    path_root: Path,
) -> tuple[dict[str, str], list[dict[str, str]]]:
    figure_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    assets: list[dict[str, str]] = []
    for section in manuscript.sections:
        for block in section["blocks"]:
            if block["type"] == "chart":
                rendered = charts.render(block, manuscript.engine, figure_dir)
                paths[block["id"]] = _relative(path_root, rendered.path)
                assets.append({"blockId": block["id"], "kind": "chart", "path": paths[block["id"]], "sha256": rendered.sha256})
            elif block["type"] == "diagram":
                rendered = diagrams.render(block, figure_dir)
                paths[block["id"]] = rendered.snippet
                assets.append({"blockId": block["id"], "kind": "diagram", "path": _relative(path_root, rendered.path), "sha256": rendered.sha256})
    return paths, assets


def _book_assets(manuscript: model.Manuscript) -> list[Path]:
    """Every image file the manuscript's rights records point at.

    A record is the only way an image reaches a page, so this is the exact set the
    compile needs. Each path must resolve inside the book root; a record that
    escapes it is refused rather than staged.
    """
    root = manuscript.root.resolve()
    paths: set[Path] = set()
    for section in manuscript.sections:
        for block in section["blocks"]:
            if block["type"] == "illustration":
                record = rights.load(manuscript.root, block["illustrationId"])
                paths.add(root / record.path)
    selection = manuscript.data["metadata"].get("cover") or {}
    artwork = selection.get("artwork")
    if artwork:
        record = rights.load(manuscript.root, artwork)
        paths.add(root / record.path)
    resolved: list[Path] = []
    for path in sorted(paths):
        try:
            candidate = path.resolve()
            candidate.relative_to(root)
        except (ValueError, OSError) as error:
            raise BookifyError(
                "BUILD_FAILED",
                f"book asset resolves outside the book root: {path}",
                str(path),
            ) from error
        if not candidate.is_file():
            raise BookifyError("BUILD_FAILED", f"book asset is not a file: {path}", str(candidate))
        resolved.append(candidate)
    return resolved


def _workspace_mounts(manuscript: model.Manuscript, stage: Path) -> tuple[tuple[Path, Path], ...]:
    """Stage the read-only engine beside the book inside the disposable build dir.

    The illustration folder is mounted whole. A rights record may point outside it
    (the catalogue's artwork lives under `assets/catalogue/artwork`), so each such
    file is bound individually at its own relative path. Nothing else under the
    book root is exposed to the compile.
    """
    engine = manuscript.engine
    directories: list[tuple[Path, Path]] = [
        (engine / "typst", stage / "typst"),
        (engine / "assets" / "fonts", stage / "engine-assets" / "fonts"),
        (engine / "vendor" / "typst", stage / "engine-vendor" / "typst"),
    ]
    illustrations = (manuscript.root / "assets" / "illustrations").resolve()
    if illustrations.is_dir():
        directories.append((illustrations, stage / "assets" / "illustrations"))
    files: list[tuple[Path, Path]] = []
    for asset in _book_assets(manuscript):
        try:
            asset.relative_to(illustrations)
            continue  # already covered by the folder mount
        except ValueError:
            pass
        if asset.is_relative_to(manuscript.engine.resolve()):
            raise BookifyError(
                "BUILD_FAILED",
                f"book asset is inside the engine tree: {asset}",
                str(asset),
            )
        target = stage / asset.relative_to(manuscript.root.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        files.append((asset, target))
    for source, target in directories:
        if not source.is_dir():
            raise BookifyError("BUILD_FAILED", f"engine asset missing: {source}", str(source))
        target.mkdir(parents=True, exist_ok=True)
    (stage / ".cache" / "empty-pkg").mkdir(parents=True, exist_ok=True)
    return tuple(directories + files)


def _compile(
    manuscript: model.Manuscript,
    compile_root: Path,
    document_path: Path,
    out_pdf: Path,
    lock: pins.ToolchainLock,
    mounts: tuple[tuple[Path, Path], ...] = (),
    *,
    sandbox: str = "auto",
) -> dict[str, object]:
    allow_portable = runtime.is_installed_wheel(manuscript.engine) or sandbox != "bwrap"
    resolved = typst_install.resolve_typst(manuscript.engine, lock, allow_portable=allow_portable)
    if resolved is None:
        raise BookifyError(
            "BUILD_FAILED",
            "typst binary missing; run 'bookify toolchain install' or install typst onto PATH",
            lock.typst.binary,
        )
    typst, typst_source = resolved
    use_bwrap = _use_bwrap(sandbox)
    data = _relative(compile_root, document_path)
    out_dir = out_pdf.resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)
    empty_pkg = compile_root / ".cache" / "empty-pkg"
    empty_pkg.mkdir(parents=True, exist_ok=True)

    if use_bwrap:
        if mounts:
            font_paths = ["engine-assets/fonts"]
            package_path = "engine-vendor/typst"
        else:
            font_paths = ["assets/fonts"]
            package_path = "vendor/typst"
    else:
        if mounts:
            _materialize_stage_non_bwrap(manuscript, compile_root)
            font_paths = [str((manuscript.engine / "assets" / "fonts").resolve())]
            package_path = str((manuscript.engine / "vendor" / "typst").resolve())
        else:
            font_paths = ["assets/fonts"]
            package_path = "vendor/typst"
    cached_fonts = runtime.fonts_cache_dir()
    if cached_fonts.is_dir():
        font_paths.append(str(cached_fonts))
    font_args: list[str] = []
    for fp in font_paths:
        font_args.extend(["--font-path", fp])

    typst_cmd = [
        str(typst), "compile",
        "--ignore-system-fonts", "--ignore-embedded-fonts",
        *font_args,
        "--package-path", package_path,
        "--package-cache-path", ".cache/empty-pkg",
        "--creation-timestamp", CREATION_TIMESTAMP,
        # Archival conformance, claimed and then verified by `docmeta`. Typst
        # refuses to write a file that breaks the profile, so a future asset
        # that cannot be archived fails the build instead of silently shipping.
        "--pdf-standard", "a-2b",
        "--root", ".",
        "--input", f"data={data}",
        "typst/templates/book.typ", str(out_pdf.resolve()),
    ]

    env = dict(os.environ)
    for proxy_key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(proxy_key, None)
    resolved_pkg = Path(package_path) if Path(package_path).is_absolute() else (compile_root / package_path)
    env["TYPST_PACKAGE_PATH"] = str(resolved_pkg.resolve())
    env["TYPST_PACKAGE_CACHE_PATH"] = str(empty_pkg.resolve())

    if use_bwrap:
        prefix = [
            "bwrap",
            "--unshare-net",
            "--die-with-parent",
            "--ro-bind", "/", "/",
            "--bind", str(out_dir), str(out_dir),
        ]
        for source, target in mounts:
            prefix.extend(["--ro-bind", str(source), str(target)])
        command = [*prefix, "--chdir", str(compile_root), "--", *typst_cmd]
        cwd = None
    else:
        command = typst_cmd
        cwd = str(compile_root)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=COMPILE_TIMEOUT_SECONDS,
            cwd=cwd,
            env=env,
        )
    except subprocess.TimeoutExpired as error:
        raise BookifyError("BUILD_FAILED", f"typst compile timed out after {COMPILE_TIMEOUT_SECONDS}s", str(out_pdf)) from error
    if result.returncode != 0:
        raise BookifyError("BUILD_FAILED", result.stderr.strip()[:2000] or "typst compile failed", str(out_pdf))
    return {
        "mode": "bwrap-unshare-net" if use_bwrap else "env-isolated",
        "bwrap": use_bwrap,
        "platform": sys.platform,
        "typstSource": typst_source,
    }


def build(
    manuscript_path: Path,
    out_pdf: Path,
    build_dir: Path,
    *,
    offline: bool,
    draft: bool = False,
    lock_path: Path | None = None,
    workspace: Path | None = None,
    engine: Path | None = None,
    sandbox: str = "auto",
) -> BuildResult:
    if not offline:
        raise BookifyError("BUILD_FAILED", "publishing requires --offline", "--offline")
    manuscript = model.load(manuscript_path, workspace=workspace, engine=engine)
    root = manuscript.root
    external_book = manuscript.workspace is not None or manuscript.root.resolve() != manuscript.engine.resolve()
    if external_book:
        if manuscript.workspace is not None:
            build_dir = workspace_mod.inside(root, build_dir, label="build directory")
            out_pdf = workspace_mod.inside(root, out_pdf, label="output PDF")
        else:
            build_dir = build_dir if build_dir.is_absolute() else root / build_dir
            out_pdf = out_pdf if out_pdf.is_absolute() else root / out_pdf
        stage = build_dir / "typst-root"
        compile_root = stage
        document_path = stage / "book.json"
        figure_dir = stage / "figures"
    else:
        build_dir = build_dir if build_dir.is_absolute() else root / build_dir
        try:
            build_dir.resolve().relative_to(root.resolve())
        except ValueError as error:
            raise BookifyError(
                "BUILD_FAILED",
                "build directory must live inside the project root so Typst can resolve assets",
                str(build_dir),
            ) from error
        compile_root = root
        document_path = build_dir / "book.json"
        figure_dir = build_dir / "figures"

    lock_file = lock_path if lock_path is not None else manuscript.engine / "toolchain.lock.json"
    lock = pins.load(lock_file)
    doctor.run_or_fail(manuscript.engine, lock_file)

    if not external_book:
        out_pdf = out_pdf if out_pdf.is_absolute() else root / out_pdf
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    mounts = _workspace_mounts(manuscript, stage) if external_book else ()
    design_coverage.require_coverage(manuscript, manuscript.engine)
    with guard.offline(), audit.boundary() as boundary:
        figure_paths, figure_assets = _render_figures(manuscript, figure_dir, compile_root)
        document = normalize.build(manuscript, figure_paths, draft=draft)
        document_path.parent.mkdir(parents=True, exist_ok=True)
        document_path.write_text(json.dumps(document.data, indent=2, sort_keys=True) + "\n")
        sandbox_info = _compile(manuscript, compile_root, document_path, out_pdf, lock, mounts, sandbox=sandbox)

        attempts = 0
        deferred: list[str] = []
        seen: set[tuple[tuple[str, int | None], ...]] = set()
        while True:
            placements = report.placement_entries(out_pdf, document.data)
            unplaced = [item["illustrationId"] for item in placements if item["page"] is None]
            if unplaced:
                raise BookifyError(
                    "BUILD_FAILED",
                    f"illustration label not found on any page: {', '.join(unplaced)}",
                    str(out_pdf),
                )
            conflicting = illustrations.conflicts(placements)
            if not conflicting:
                break
            # The stop condition is agreement, not an attempt count: a pass is
            # repeated only while the placement map still changes. A map that
            # comes back to a previous state will never settle, so it fails now
            # instead of spending the remaining attempts.
            layout = illustrations.signature(placements)
            if layout in seen:
                illustrations.require_limit(conflicting)
                raise BookifyError(
                    "ILLUSTRATION_LIMIT",
                    f"placement oscillates: pass {attempts + 1} repeats an earlier page map",
                    str(out_pdf),
                )
            seen.add(layout)
            attempts += 1
            if attempts > illustrations.MAX_ATTEMPTS:
                illustrations.require_limit(conflicting)
                raise BookifyError(
                    "ILLUSTRATION_LIMIT",
                    f"placement did not converge after {attempts} passes",
                    str(out_pdf),
                )
            deferred.extend(illustrations.defer_later(document.data, conflicting))
            document_path.write_text(json.dumps(document.data, indent=2, sort_keys=True) + "\n")
            sandbox_info = _compile(manuscript, compile_root, document_path, out_pdf, lock, mounts, sandbox=sandbox)

        data = report.analyse(
            out_pdf, document.data, figure_assets,
            offline=guard.active(), draft=draft, manuscript_path=manuscript_path,
            network_attempts=guard.attempts(),
        )

    data["pins"] = {"typst": lock.typst.version, "python": lock.python.version, "fonts": len(lock.fonts)}
    data["deferredIllustrations"] = sorted(set(deferred))
    data["placementPasses"] = attempts
    data["ocr"] = boundary.evidence()
    data["sandbox"] = sandbox_info
    report.write(data, build_dir / "build-report.json")
    return BuildResult(pdf=out_pdf, report=data)
