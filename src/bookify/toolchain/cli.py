"""Thin CLI dispatcher with lazy module imports so light commands stay fast."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from bookify import runtime
from bookify.errors import BookifyError

ROOT = runtime.engine_root()
EXIT_CODES = {
    "INPUT_INVALID": 2,
    "SCHEMA_INVALID": 2,
    "SOURCE_UNREADABLE": 2,
    "BUILD_FAILED": 3,
    "VERIFY_FAILED": 3,
    "NETWORK_DENIED": 3,
    "MODEL_CALL_DENIED": 3,
    "FONT_MISSING": 3,
    "GLYPH_MISSING": 3,
    "RIGHTS_INCOMPLETE": 3,
    "ILLUSTRATION_LIMIT": 3,
    "XREF_MISSING": 2,
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bookify", description="Local authoring and offline publishing")
    parser.add_argument("--version", action="version", version=f"bookify {runtime.version()}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fonts = subparsers.add_parser("fonts", help="inspect or install optional font packs")
    fonts_sub = fonts.add_subparsers(dest="fonts_command", required=True)
    fonts_status = fonts_sub.add_parser("status", help="report bundled and cached optional font packs")
    fonts_status.add_argument("--json", action="store_true")
    fonts_install = fonts_sub.add_parser("install", help="install an optional font pack into the user cache")
    fonts_install.add_argument("pack", choices=("cjk",), help="font pack to install")
    fonts_install.add_argument("--from-file", type=Path, default=None, help="install from a local file instead of downloading")
    fonts_install.add_argument("--json", action="store_true")

    toolchain = subparsers.add_parser("toolchain", help="report or verify the local toolchain")
    toolchain_sub = toolchain.add_subparsers(dest="toolchain_command", required=True)
    doctor_parser = toolchain_sub.add_parser("doctor", help="report pins, fonts, packages and interpreter")
    doctor_parser.add_argument("--json", action="store_true", help="machine-readable report")
    doctor_parser.add_argument("--lock", type=Path, default=None)

    build = subparsers.add_parser("build", help="compile a manuscript to an offline PDF")
    build.add_argument("--manuscript", type=Path)
    build.add_argument("--out", type=Path)
    build.add_argument("--offline", action="store_true")
    build.add_argument("--draft", action="store_true", help="allow unconfirmed rights")
    build.add_argument("--build-dir", type=Path, default=Path("build"))
    build.add_argument("--workspace", type=Path, default=None, help="per-book workspace (or BOOKIFY_WORKSPACE)")
    build.add_argument("--json", action="store_true")

    manuscript = subparsers.add_parser("manuscript", help="check a manuscript against the contract")
    manuscript_sub = manuscript.add_subparsers(dest="manuscript_command", required=True)
    check = manuscript_sub.add_parser("check", help="validate a manuscript and its assets")
    check.add_argument("--manuscript", type=Path, required=True)
    check.add_argument("--workspace", type=Path, default=None, help="per-book workspace (or BOOKIFY_WORKSPACE)")
    check.add_argument("--json", action="store_true")
    schema_parser = manuscript_sub.add_parser("schema", help="print the normative schema")
    schema_parser.add_argument("--print", action="store_true", dest="print_schema")

    design = subparsers.add_parser("design", help="check tokens, presets and glyph coverage")
    design_sub = design.add_subparsers(dest="design_command", required=True)
    design_check = design_sub.add_parser("check", help="check a manuscript against the design layer")
    design_check.add_argument("--manuscript", type=Path, required=True)
    design_check.add_argument("--workspace", type=Path, default=None, help="per-book workspace (or BOOKIFY_WORKSPACE)")
    design_check.add_argument("--json", action="store_true")

    figures = subparsers.add_parser("figures", help="render charts and diagrams from a manuscript")
    figures_sub = figures.add_subparsers(dest="figures_command", required=True)
    figures_render = figures_sub.add_parser("render", help="write deterministic SVG and CeTZ assets")
    figures_render.add_argument("--manuscript", type=Path, required=True)
    figures_render.add_argument("--out", type=Path, required=True)
    figures_render.add_argument("--workspace", type=Path, default=None, help="per-book workspace (or BOOKIFY_WORKSPACE)")
    figures_render.add_argument("--json", action="store_true")

    verify = subparsers.add_parser("verify", help="check a built PDF against the acceptance gate")
    verify.add_argument("--pdf", type=Path, required=True)
    verify.add_argument("--manuscript", type=Path, required=True)
    verify.add_argument("--report", type=Path, default=Path("build/verify.json"))
    verify.add_argument("--previous-pdf", type=Path, default=None)
    verify.add_argument("--build-report", type=Path, default=Path("build/build-report.json"))
    verify.add_argument("--contact-sheet", type=Path, default=None)
    verify.add_argument("--reviewed-by", type=str, default=None)
    verify.add_argument("--reviewed-at", type=str, default=None)
    verify.add_argument("--review-notes", type=Path, default=None, help="JSON decisions for every warning")
    verify.add_argument("--workspace", type=Path, default=None, help="per-book workspace (or BOOKIFY_WORKSPACE)")
    verify.add_argument("--json", action="store_true")

    intake = subparsers.add_parser("intake", help="extract a source into a stable manifest")
    intake.add_argument("--source", type=Path, required=True)
    intake.add_argument("--out", type=Path, required=True)
    intake.add_argument("--changed-only", action="store_true")
    intake.add_argument(
        "--ocr",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="OCR image-borne text at intake (default; --no-ocr records a baseline)",
    )
    intake.add_argument("--ocr-lang", default="eng", help="pinned OCR language: eng (default) or eng+vie")
    intake.add_argument("--ocr-tesseract", type=Path, default=None, help="explicit Tesseract CLI (tests)")
    intake.add_argument("--ocr-tessdata", type=Path, default=None, help="explicit tessdata directory")
    intake.add_argument("--ocr-require-system", action="store_true", help="refuse the development copy")
    intake.add_argument("--keep-ocr-raster", action="store_true", help="retain per-region crop PNGs")
    intake.add_argument(
        "--offline",
        action="store_true",
        help="accepted for compatibility; intake is sandboxed by default",
    )
    intake.add_argument(
        "--allow-unsandboxed",
        action="store_true",
        help="trusted local source only: run extraction/OCR outside bwrap and record it",
    )
    intake.add_argument("--json", action="store_true")

    author = subparsers.add_parser("author", help="plan, apply and track authored content")
    author_sub = author.add_subparsers(dest="author_command", required=True)

    plan_parser = author_sub.add_parser("plan", help="list source pages that need work")
    plan_parser.add_argument("--intake", type=Path, required=True)
    plan_parser.add_argument("--manuscript", type=Path, required=True)
    plan_parser.add_argument("--out", type=Path, default=Path("build/author-plan.json"))
    plan_parser.add_argument("--cache-dir", type=Path, default=Path("build/cache/authoring"))
    plan_parser.add_argument("--workspace", type=Path, default=None, help="per-book workspace (or BOOKIFY_WORKSPACE)")
    plan_parser.add_argument("--json", action="store_true")

    apply_parser = author_sub.add_parser("apply", help="apply an agent draft to the manuscript")
    apply_parser.add_argument("--plan", type=Path, required=True)
    apply_parser.add_argument("--draft", type=Path, required=True)
    apply_parser.add_argument("--manuscript", type=Path, required=True)
    apply_parser.add_argument("--cache-dir", type=Path, default=Path("build/cache/authoring"))
    apply_parser.add_argument("--decisions", type=Path, default=Path("build/authoring/decisions.jsonl"))
    apply_parser.add_argument("--workspace", type=Path, default=None, help="per-book workspace (or BOOKIFY_WORKSPACE)")
    apply_parser.add_argument("--json", action="store_true")

    select_parser = author_sub.add_parser("select", help="record an illustration selection")
    select_parser.add_argument("--section", required=True)
    select_parser.add_argument("--illustration", required=True)
    select_parser.add_argument("--reason", required=True)
    select_parser.add_argument("--store", type=Path, default=Path("build/authoring/selections.json"))
    select_parser.add_argument("--workspace", type=Path, default=None, help="per-book workspace (or BOOKIFY_WORKSPACE)")
    select_parser.add_argument("--json", action="store_true")

    status_parser = author_sub.add_parser("status", help="report selections and rights")
    status_parser.add_argument("--manuscript", type=Path, required=True)
    status_parser.add_argument("--store", type=Path, default=Path("build/authoring/selections.json"))
    status_parser.add_argument("--section", default=None)
    status_parser.add_argument("--workspace", type=Path, default=None, help="per-book workspace (or BOOKIFY_WORKSPACE)")
    status_parser.add_argument("--json", action="store_true")

    contract = author_sub.add_parser("contract", help="validate the durable authoring record")
    contract_sub = contract.add_subparsers(dest="contract_command", required=True)
    contract_check = contract_sub.add_parser("check", help="check mode, provenance, coverage and enrichment")
    contract_check.add_argument("--workspace", type=Path, default=None, help="per-book workspace (or BOOKIFY_WORKSPACE)")
    contract_check.add_argument("--record", type=Path, default=None)
    contract_check.add_argument("--manuscript", type=Path, default=None)
    contract_check.add_argument("--source", type=Path, default=None)
    contract_check.add_argument("--json", action="store_true")
    return parser


def _toolchain_doctor(args: argparse.Namespace) -> int:
    from bookify.toolchain import doctor

    report = doctor.run(ROOT, args.lock)
    if args.json:
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    else:
        for check in report.checks:
            mark = "ok" if check.is_local else "FAIL"
            print(f"{mark:4} {check.identifier:20} {check.detail}")
    return 0 if report.ok else 3


def _manuscript_check(args: argparse.Namespace) -> int:
    from bookify.authoring import workspace as author_workspace
    from bookify.manuscript import model as manuscript_model

    workspace = author_workspace.resolve(args.workspace)
    manuscript = manuscript_model.load(args.manuscript, workspace=workspace)
    payload = {
        "ok": True,
        "id": manuscript.id,
        "revision": manuscript.revision,
        "sections": len(manuscript.sections),
        "blocks": sum(len(section["blocks"]) for section in manuscript.sections),
        "workspace": str(workspace) if workspace is not None else None,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"ok  {manuscript.id} revision {manuscript.revision}: {payload['sections']} sections, {payload['blocks']} blocks")
    return 0


def _manuscript_schema() -> int:
    from bookify.manuscript import schema as manuscript_schema

    print(json.dumps(manuscript_schema.load_document(), indent=2, sort_keys=True))
    return 0


def _author_plan(args: argparse.Namespace) -> int:
    from bookify.authoring import plan as author_plan
    from bookify.authoring import workspace as author_workspace
    from bookify.manuscript import model as manuscript_model

    workspace = author_workspace.resolve(args.workspace)
    intake = author_workspace.inside(workspace, args.intake, code="INPUT_INVALID", label="intake directory") if workspace else args.intake
    out = author_workspace.inside(workspace, args.out, label="author plan") if workspace else args.out
    cache_dir = author_workspace.inside(workspace, args.cache_dir, label="authoring cache") if workspace else args.cache_dir
    manuscript = manuscript_model.load(args.manuscript, workspace=workspace)
    plan = author_plan.build(intake, manuscript, cache_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(f"{len(plan['work'])} page(s) need work")
        for item in plan["work"]:
            print(f"  {item['sourceId']}#{item['page']} ({item['reason']}) blocks={list(item['blockIds'])}")
    return 0


def _author_apply(args: argparse.Namespace) -> int:
    from bookify.authoring import apply as author_apply
    from bookify.authoring import workspace as author_workspace

    workspace = author_workspace.resolve(args.workspace)
    plan_path = author_workspace.inside(workspace, args.plan, code="INPUT_INVALID", label="author plan") if workspace else args.plan
    draft_path = author_workspace.inside(workspace, args.draft, code="INPUT_INVALID", label="draft") if workspace else args.draft
    manuscript_path = author_workspace.inside(workspace, args.manuscript, code="INPUT_INVALID", label="manuscript") if workspace else args.manuscript
    cache_dir = author_workspace.inside(workspace, args.cache_dir, label="authoring cache") if workspace else args.cache_dir
    decisions_path = author_workspace.inside(workspace, args.decisions, label="decisions log") if workspace else args.decisions
    result = author_apply.apply(
        plan_path, draft_path, manuscript_path, cache_dir, decisions_path, workspace=workspace
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"revision {result['revision']}; applied {len(result['applied'])} page(s); {len(result['modelCalls'])} recorded model call(s)")
    return 0


def _author_select(args: argparse.Namespace) -> int:
    from bookify.authoring import illustrations as author_illustrations
    from bookify.authoring import workspace as author_workspace

    workspace = author_workspace.resolve(args.workspace)
    store = author_workspace.inside(workspace, args.store, label="selections store") if workspace else args.store
    result = author_illustrations.select(store, args.section, args.illustration, args.reason)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{'reused' if result['reused'] else 'selected'} {result['illustrationId']} for {result['sectionId']}")
    return 0


def _author_status(args: argparse.Namespace) -> int:
    from bookify.authoring import illustrations as author_illustrations
    from bookify.authoring import workspace as author_workspace
    from bookify.manuscript import model as manuscript_model

    workspace = author_workspace.resolve(args.workspace)
    store = author_workspace.inside(workspace, args.store, label="selections store") if workspace else args.store
    manuscript = manuscript_model.load(args.manuscript, workspace=workspace)
    rows = author_illustrations.status(store, manuscript.root, args.section)
    payload = {"ok": True, "selections": rows}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for row in rows:
            print(f"{row['sectionId']:24} {row['illustrationId']:16} {row['rightsStatus']:12} {row['reason']}")
    return 0


def _author_contract_check(args: argparse.Namespace) -> int:
    from bookify.authoring import record as author_record
    from bookify.authoring import workspace as author_workspace

    workspace = author_workspace.resolve(args.workspace)
    record_path = args.record
    if record_path is None:
        if workspace is None:
            raise BookifyError(
                "INPUT_INVALID",
                "contract check needs --workspace or --record",
                "--record",
            )
        record_path = workspace / "authoring" / "record.json"
    payload = author_record.check(
        record_path,
        manuscript_path=args.manuscript,
        workspace=workspace,
        source_path=args.source,
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        coverage = payload["coverage"]
        print(
            f"ok  {payload['bookId']} mode {payload['mode']}: "
            f"{coverage['covered']} covered, {coverage['merged']} merged, {coverage['excluded']} excluded"
        )
    return 0


def _intake_options(args: argparse.Namespace):
    from bookify.intake import ocr as intake_ocr

    return intake_ocr.OcrOptions(
        enabled=bool(args.ocr),
        lang=args.ocr_lang,
        # Sandboxed is the default; the flag is the documented escape hatch for
        # a trusted local source, and the run log records the actual state.
        offline=not bool(args.allow_unsandboxed),
        allow_unsandboxed=bool(args.allow_unsandboxed),
        keep_raster=bool(args.keep_ocr_raster),
        require_system=bool(args.ocr_require_system),
        tesseract=args.ocr_tesseract,
        tessdata=args.ocr_tessdata,
    )


def _ocr_payload(manifest: dict) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    pin: str | None = None
    for page in manifest.get("pages", []):
        record = page.get("ocr")
        if not isinstance(record, dict):
            continue
        status = record.get("status", "unknown")
        statuses[status] = statuses.get(status, 0) + 1
        pin = record.get("pinSha256") or pin
    return {"pages": sum(statuses.values()), "statuses": statuses, "pinSha256": pin}


def _intake(args: argparse.Namespace) -> int:
    from bookify.intake import changes as intake_changes
    from bookify.intake import extract as intake_extract
    from bookify.intake import manifest as intake_manifest
    from bookify.intake import ocr as intake_ocr

    out = args.out
    previous = intake_manifest.load(out)
    digest = intake_extract.source_sha256(args.source)
    options = _intake_options(args)
    previous_ocr = (previous or {}).get("ocr")
    previous_has_ocr = isinstance(previous_ocr, dict) and bool(previous_ocr.get("pinSha256"))
    pin: str | None = None
    if args.ocr and previous_has_ocr:
        # `--changed-only` may skip only when source and the whole OCR pin
        # (engine binary/source, data, raster, params) match.
        pin = intake_ocr.pin_for(options)
    if (
        args.changed_only
        and previous
        and previous.get("sourceSha256") == digest
        and (
            (args.ocr and previous_has_ocr and previous_ocr.get("pinSha256") == pin)
            or (not args.ocr and not previous_has_ocr)
        )
    ):
        intake_changes.write(out, intake_changes.empty(previous["sourceId"]))
        payload = {
            "ok": True,
            "skipped": True,
            "sourceId": previous["sourceId"],
            "pages": previous.get("pageCount", 0),
            "changedPages": [],
            "ocrChangedPages": [],
            "images": sum(len(page["images"]) for page in previous.get("pages", [])),
            "ocr": _ocr_payload(previous),
        }
    else:
        current = intake_manifest.build(args.source, out, ocr_options=options)
        diff = intake_changes.diff(previous, current)
        intake_changes.write(out, diff)
        payload = {
            "ok": True,
            "skipped": False,
            "sourceId": current["sourceId"],
            "pages": current["pageCount"],
            "changedPages": diff["changedPages"],
            "ocrChangedPages": diff["ocrChangedPages"],
            "images": sum(len(page["images"]) for page in current["pages"]),
            "ocr": _ocr_payload(current),
        }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            f"{'skipped' if payload['skipped'] else 'extracted'} {payload['sourceId']}: "
            f"{payload['pages']} pages, {payload['images']} images, changed {payload['changedPages']}"
        )
    return 0


def _verify(args: argparse.Namespace) -> int:
    from bookify.authoring import workspace as author_workspace
    from bookify.verify import runner as verify_runner

    workspace = author_workspace.resolve(args.workspace)
    pdf = args.pdf
    manuscript_path = args.manuscript
    report_path = args.report
    previous_pdf = args.previous_pdf
    build_report = args.build_report
    contact_sheet = args.contact_sheet
    review_notes = args.review_notes
    if workspace is not None:
        pdf = author_workspace.inside(workspace, pdf, label="PDF")
        manuscript_path = author_workspace.inside(workspace, manuscript_path, code="INPUT_INVALID", label="manuscript")
        report_path = author_workspace.inside(workspace, report_path, label="verify report")
        if previous_pdf is not None:
            previous_pdf = author_workspace.inside(workspace, previous_pdf, label="comparison PDF")
        if build_report is not None:
            build_report = author_workspace.inside(workspace, build_report, label="build report")
        if contact_sheet is not None:
            contact_sheet = author_workspace.inside(workspace, contact_sheet, label="contact sheet")
        if review_notes is not None:
            review_notes = author_workspace.inside(workspace, review_notes, label="review notes")
    report = verify_runner.run(
        pdf, manuscript_path, report_path,
        previous_pdf=previous_pdf,
        build_report=build_report,
        contact_sheet=contact_sheet,
        reviewed_by=args.reviewed_by,
        reviewed_at=args.reviewed_at,
        review_notes=review_notes,
        workspace=workspace,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for check in report["checks"]:
            print(f"{check['status']:6} {check['id']:20} {check['detail']}")
        print(f"gate: {report['gate']}")
    return 0 if report["gate"] == "pass" else 3


def _figures_render(args: argparse.Namespace) -> int:
    from bookify.authoring import workspace as author_workspace
    from bookify.figures import charts as chart_engine
    from bookify.figures import diagrams as diagram_engine
    from bookify.manuscript import model as manuscript_model

    workspace = author_workspace.resolve(args.workspace)
    manuscript = manuscript_model.load(args.manuscript, workspace=workspace)
    out_dir = (
        author_workspace.inside(workspace, args.out, label="figures directory")
        if workspace is not None
        else args.out
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, str]] = []
    for section in manuscript.sections:
        for block in section["blocks"]:
            if block["type"] == "chart":
                rendered = chart_engine.render(block, manuscript.engine, out_dir)
                entries.append({"kind": "chart", "blockId": block["id"], "path": str(rendered.path), "sha256": rendered.sha256})
            elif block["type"] == "diagram":
                rendered = diagram_engine.render(block, out_dir)
                entries.append({"kind": "diagram", "blockId": block["id"], "path": str(rendered.path), "sha256": rendered.sha256})
    payload = {"ok": True, "figures": entries}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for entry in entries:
            print(f"{entry['kind']:8} {entry['blockId']:24} {entry['path']}")
    return 0


def _design_check(args: argparse.Namespace) -> int:
    from bookify.authoring import workspace as author_workspace
    from bookify.design import coverage as design_coverage
    from bookify.design import lint as design_lint
    from bookify.manuscript import model as manuscript_model

    workspace = author_workspace.resolve(args.workspace)
    manuscript = manuscript_model.load(args.manuscript, workspace=workspace)
    result = design_coverage.check(manuscript, manuscript.engine)
    issues = design_lint.lint(manuscript.engine)
    missing = sorted(design_lint.missing_presets(manuscript.engine))
    payload = {
        "ok": result.ok and not issues and not missing,
        "coverage": {
            "characters": result.characters,
            "japanese": result.japanese,
            "missing": [code for _, code in result.missing],
        },
        "lint": [f"{issue.path.name}:{issue.line} {issue.message}" for issue in issues],
        "missingPresets": missing,
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"coverage: {design_coverage.describe(result)}")
        print(f"lint: {len(issues)} issue(s)")
        print(f"presets: {'complete' if not missing else 'missing ' + ', '.join(missing)}")
    return 0 if payload["ok"] else 3


def _build(args: argparse.Namespace) -> int:
    from bookify.authoring import workspace as author_workspace
    from bookify.publish import typst_driver

    if not args.manuscript or not args.out:
        raise BookifyError("INPUT_INVALID", "build needs --manuscript and --out")
    workspace = author_workspace.resolve(args.workspace)
    result = typst_driver.build(
        args.manuscript,
        args.out,
        args.build_dir,
        offline=args.offline,
        draft=args.draft,
        workspace=workspace,
    )
    summary = {
        "ok": True,
        "pdf": str(result.pdf),
        "pages": result.report["pdf"]["pages"],
        "placements": result.report["placements"],
        "warnings": result.report["warnings"],
        "deferredIllustrations": result.report["deferredIllustrations"],
    }
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"built {summary['pdf']} ({summary['pages']} pages)")
        for warning in summary["warnings"]:
            print(f"warning: {warning}")
    return 0


def _fonts_status(args: argparse.Namespace) -> int:
    from bookify.toolchain import fonts as fonts_mod

    payload = fonts_mod.cjk_status(runtime.engine_root())
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        state = f"installed ({payload['source']})" if payload["installed"] else "not installed"
        print(f"cjk: {state} — {payload['path']}")
    return 0


def _fonts_install(args: argparse.Namespace) -> int:
    from bookify.toolchain import fonts as fonts_mod

    payload = fonts_mod.install_cjk(from_file=args.from_file)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"{payload['pack']}: {payload['status']} at {payload['path']}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "fonts" and args.fonts_command == "status":
            return _fonts_status(args)
        if args.command == "fonts" and args.fonts_command == "install":
            return _fonts_install(args)
        if args.command == "toolchain" and args.toolchain_command == "doctor":
            return _toolchain_doctor(args)
        if args.command == "manuscript" and args.manuscript_command == "check":
            return _manuscript_check(args)
        if args.command == "manuscript" and args.manuscript_command == "schema":
            return _manuscript_schema()
        if args.command == "design" and args.design_command == "check":
            return _design_check(args)
        if args.command == "figures" and args.figures_command == "render":
            return _figures_render(args)
        if args.command == "verify":
            return _verify(args)
        if args.command == "intake":
            return _intake(args)
        if args.command == "author" and args.author_command == "plan":
            return _author_plan(args)
        if args.command == "author" and args.author_command == "apply":
            return _author_apply(args)
        if args.command == "author" and args.author_command == "select":
            return _author_select(args)
        if args.command == "author" and args.author_command == "status":
            return _author_status(args)
        if args.command == "author" and args.author_command == "contract":
            return _author_contract_check(args)
        if args.command == "build":
            return _build(args)
        raise BookifyError("INPUT_INVALID", f"unknown command: {args.command}")
    except BookifyError as error:
        print(json.dumps(error.as_dict(), sort_keys=True), file=sys.stderr)
        return EXIT_CODES.get(error.code, 1)


def entry() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entry()
