"""Thin dispatcher: toolchain commands now, publishing commands as they land."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from bookify.errors import BookifyError
from bookify.design import coverage as design_coverage
from bookify.design import lint as design_lint
from bookify.figures import charts as chart_engine
from bookify.figures import diagrams as diagram_engine
from bookify.manuscript import model as manuscript_model
from bookify.manuscript import schema as manuscript_schema
from bookify.authoring import apply as author_apply
from bookify.authoring import illustrations as author_illustrations
from bookify.authoring import plan as author_plan
from bookify.intake import changes as intake_changes
from bookify.intake import extract as intake_extract
from bookify.intake import manifest as intake_manifest
from bookify.publish import typst_driver
from bookify.verify import runner as verify_runner
from bookify.toolchain import doctor

ROOT = Path(__file__).resolve().parents[3]
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
    subparsers = parser.add_subparsers(dest="command", required=True)

    toolchain = subparsers.add_parser("toolchain", help="report or verify the local toolchain")
    toolchain_sub = toolchain.add_subparsers(dest="toolchain_command", required=True)
    doctor_parser = toolchain_sub.add_parser("doctor", help="report pins, fonts, packages and interpreter")
    doctor_parser.add_argument("--json", action="store_true", help="machine-readable report")
    doctor_parser.add_argument("--lock", type=Path, default=None)

    build = subparsers.add_parser("build", help="compile a manuscript (not implemented yet)")
    build.add_argument("--manuscript", type=Path)
    build.add_argument("--out", type=Path)
    build.add_argument("--offline", action="store_true")
    build.add_argument("--draft", action="store_true", help="allow unconfirmed rights")
    build.add_argument("--build-dir", type=Path, default=Path("build"))
    build.add_argument("--json", action="store_true")

    manuscript = subparsers.add_parser("manuscript", help="check a manuscript against the contract")
    manuscript_sub = manuscript.add_subparsers(dest="manuscript_command", required=True)
    check = manuscript_sub.add_parser("check", help="validate a manuscript and its assets")
    check.add_argument("--manuscript", type=Path, required=True)
    check.add_argument("--json", action="store_true")
    schema_parser = manuscript_sub.add_parser("schema", help="print the normative schema")
    schema_parser.add_argument("--print", action="store_true", dest="print_schema")

    design = subparsers.add_parser("design", help="check tokens, presets and glyph coverage")
    design_sub = design.add_subparsers(dest="design_command", required=True)
    design_check = design_sub.add_parser("check", help="check a manuscript against the design layer")
    design_check.add_argument("--manuscript", type=Path, required=True)
    design_check.add_argument("--json", action="store_true")

    figures = subparsers.add_parser("figures", help="render charts and diagrams from a manuscript")
    figures_sub = figures.add_subparsers(dest="figures_command", required=True)
    figures_render = figures_sub.add_parser("render", help="write deterministic SVG and CeTZ assets")
    figures_render.add_argument("--manuscript", type=Path, required=True)
    figures_render.add_argument("--out", type=Path, required=True)
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
    verify.add_argument("--json", action="store_true")

    intake = subparsers.add_parser("intake", help="extract a source into a stable manifest")
    intake.add_argument("--source", type=Path, required=True)
    intake.add_argument("--out", type=Path, required=True)
    intake.add_argument("--changed-only", action="store_true")
    intake.add_argument("--json", action="store_true")

    author = subparsers.add_parser("author", help="plan, apply and track authored content")
    author_sub = author.add_subparsers(dest="author_command", required=True)

    plan_parser = author_sub.add_parser("plan", help="list source pages that need work")
    plan_parser.add_argument("--intake", type=Path, required=True)
    plan_parser.add_argument("--manuscript", type=Path, required=True)
    plan_parser.add_argument("--out", type=Path, default=Path("build/author-plan.json"))
    plan_parser.add_argument("--cache-dir", type=Path, default=Path("build/cache/authoring"))
    plan_parser.add_argument("--json", action="store_true")

    apply_parser = author_sub.add_parser("apply", help="apply an agent draft to the manuscript")
    apply_parser.add_argument("--plan", type=Path, required=True)
    apply_parser.add_argument("--draft", type=Path, required=True)
    apply_parser.add_argument("--manuscript", type=Path, required=True)
    apply_parser.add_argument("--cache-dir", type=Path, default=Path("build/cache/authoring"))
    apply_parser.add_argument("--decisions", type=Path, default=Path("build/authoring/decisions.jsonl"))
    apply_parser.add_argument("--json", action="store_true")

    select_parser = author_sub.add_parser("select", help="record an illustration selection")
    select_parser.add_argument("--section", required=True)
    select_parser.add_argument("--illustration", required=True)
    select_parser.add_argument("--reason", required=True)
    select_parser.add_argument("--store", type=Path, default=Path("build/authoring/selections.json"))
    select_parser.add_argument("--json", action="store_true")

    status_parser = author_sub.add_parser("status", help="report selections and rights")
    status_parser.add_argument("--manuscript", type=Path, required=True)
    status_parser.add_argument("--store", type=Path, default=Path("build/authoring/selections.json"))
    status_parser.add_argument("--section", default=None)
    status_parser.add_argument("--json", action="store_true")
    return parser


def _toolchain_doctor(args: argparse.Namespace) -> int:
    report = doctor.run(ROOT, args.lock)
    if args.json:
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    else:
        for check in report.checks:
            mark = "ok" if check.is_local else "FAIL"
            print(f"{mark:4} {check.identifier:20} {check.detail}")
    return 0 if report.ok else 3


def _manuscript_check(args: argparse.Namespace) -> int:
    manuscript = manuscript_model.load(args.manuscript)
    payload = {
        "ok": True,
        "id": manuscript.id,
        "revision": manuscript.revision,
        "sections": len(manuscript.sections),
        "blocks": sum(len(section["blocks"]) for section in manuscript.sections),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"ok  {manuscript.id} revision {manuscript.revision}: {payload['sections']} sections, {payload['blocks']} blocks")
    return 0


def _manuscript_schema() -> int:
    print(json.dumps(manuscript_schema.load_document(), indent=2, sort_keys=True))
    return 0


def _author_plan(args: argparse.Namespace) -> int:
    manuscript = manuscript_model.load(args.manuscript)
    plan = author_plan.build(args.intake, manuscript, args.cache_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(f"{len(plan['work'])} page(s) need work")
        for item in plan["work"]:
            print(f"  {item['sourceId']}#{item['page']} ({item['reason']}) blocks={list(item['blockIds'])}")
    return 0


def _author_apply(args: argparse.Namespace) -> int:
    result = author_apply.apply(
        args.plan, args.draft, args.manuscript, args.cache_dir, args.decisions
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"revision {result['revision']}; applied {len(result['applied'])} page(s); {len(result['modelCalls'])} recorded model call(s)")
    return 0


def _author_select(args: argparse.Namespace) -> int:
    result = author_illustrations.select(args.store, args.section, args.illustration, args.reason)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{'reused' if result['reused'] else 'selected'} {result['illustrationId']} for {result['sectionId']}")
    return 0


def _author_status(args: argparse.Namespace) -> int:
    manuscript = manuscript_model.load(args.manuscript)
    rows = author_illustrations.status(args.store, manuscript.root, args.section)
    payload = {"ok": True, "selections": rows}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for row in rows:
            print(f"{row['sectionId']:24} {row['illustrationId']:16} {row['rightsStatus']:12} {row['reason']}")
    return 0


def _intake(args: argparse.Namespace) -> int:
    out = args.out
    previous = intake_manifest.load(out)
    digest = intake_extract.source_sha256(args.source)
    if args.changed_only and previous and previous.get("sourceSha256") == digest:
        intake_changes.write(out, intake_changes.empty(previous["sourceId"]))
        payload = {
            "ok": True,
            "skipped": True,
            "sourceId": previous["sourceId"],
            "pages": previous.get("pageCount", 0),
            "changedPages": [],
            "images": sum(len(page["images"]) for page in previous.get("pages", [])),
        }
    else:
        current = intake_manifest.build(args.source, out)
        diff = intake_changes.diff(previous, current)
        intake_changes.write(out, diff)
        payload = {
            "ok": True,
            "skipped": False,
            "sourceId": current["sourceId"],
            "pages": current["pageCount"],
            "changedPages": diff["changedPages"],
            "images": sum(len(page["images"]) for page in current["pages"]),
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
    report = verify_runner.run(
        args.pdf, args.manuscript, args.report,
        previous_pdf=args.previous_pdf,
        build_report=args.build_report,
        contact_sheet=args.contact_sheet,
        reviewed_by=args.reviewed_by,
        reviewed_at=args.reviewed_at,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for check in report["checks"]:
            print(f"{check['status']:6} {check['id']:20} {check['detail']}")
        print(f"gate: {report['gate']}")
    return 0 if report["gate"] == "pass" else 3


def _figures_render(args: argparse.Namespace) -> int:
    manuscript = manuscript_model.load(args.manuscript)
    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, str]] = []
    for section in manuscript.sections:
        for block in section["blocks"]:
            if block["type"] == "chart":
                rendered = chart_engine.render(block, manuscript.root, out_dir)
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
    manuscript = manuscript_model.load(args.manuscript)
    result = design_coverage.check(manuscript, manuscript.root)
    issues = design_lint.lint(manuscript.root)
    missing = sorted(design_lint.missing_presets(manuscript.root))
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
    if not args.manuscript or not args.out:
        raise BookifyError("INPUT_INVALID", "build needs --manuscript and --out")
    result = typst_driver.build(
        args.manuscript, args.out, args.build_dir, offline=args.offline, draft=args.draft
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


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
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
