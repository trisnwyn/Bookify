"""Task 11: the verifier's report, gate, offline evidence and determinism."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from helpers import ROOT, SPECIMEN, build_report_path, specimen_build
from bookify.verify import runner
from bookify.verify.checks import determinism


def _review(sheet: Path) -> dict[str, str]:
    return {"contact_sheet": sheet, "reviewed_by": "agent", "reviewed_at": "2026-11-10T18:00:00"}


def test_gate_passes_with_a_recorded_review() -> None:
    pdf, previous, sheet = specimen_build()

    report = runner.run(
        pdf, SPECIMEN, ROOT / ".cache" / "verify.json",
        previous_pdf=previous, build_report=build_report_path(),
        contact_sheet=sheet, reviewed_by="agent", reviewed_at="2026-11-10T18:00:00",
    )

    assert report["gate"] == "pass"
    assert report["pins"] == {"typst": "0.15.1", "python": "3.13.16"}
    assert report["generatedFrom"]["pdfSha256"]
    assert {check["id"] for check in report["checks"]} == {
        "offline", "determinism", "glyphs", "text", "pages", "captions",
        "illustration-limit", "rights", "xrefs", "review",
    }
    assert (ROOT / ".cache" / "verify.json").is_file()


def test_cli_exit_codes(capsys) -> None:
    from bookify.toolchain.cli import main

    pdf, previous, sheet = specimen_build()
    base = [
        "verify", "--pdf", str(pdf), "--manuscript", str(SPECIMEN),
        "--previous-pdf", str(previous), "--build-report", str(build_report_path()),
        "--json",
    ]
    assert main(base) == 3
    assert json.loads(capsys.readouterr().out)["gate"] == "fail"
    assert main(base + ["--contact-sheet", str(sheet), "--reviewed-by", "agent", "--reviewed-at", "now"]) == 0
    assert json.loads(capsys.readouterr().out)["gate"] == "pass"


def test_offline_failure_is_named_not_silent(tmp_path: Path) -> None:
    pdf, previous, sheet = specimen_build()
    report_data = json.loads(build_report_path().read_text())
    report_data["offline"] = False
    tampered = tmp_path / "report.json"
    tampered.write_text(json.dumps(report_data))

    report = runner.run(pdf, SPECIMEN, None, previous_pdf=previous, build_report=tampered)
    offline = next(check for check in report["checks"] if check["id"] == "offline")

    assert report["gate"] == "fail"
    assert offline["code"] == "NETWORK_DENIED"
    assert "guard" in offline["detail"]


def test_missing_build_report_fails_offline_check() -> None:
    pdf, previous, _sheet = specimen_build()
    report = runner.run(pdf, SPECIMEN, None, previous_pdf=previous, build_report=None)

    offline = next(check for check in report["checks"] if check["id"] == "offline")
    assert offline["code"] == "NETWORK_DENIED"


def test_report_for_another_pdf_or_manuscript_fails_offline_check(tmp_path: Path) -> None:
    pdf, previous, _sheet = specimen_build()
    report_data = json.loads(build_report_path().read_text())
    assert report_data["networkAttempts"] == 0
    report_data["pdf"]["sha256"] = "0" * 64
    report_data["manuscript"]["revision"] = 999
    tampered = tmp_path / "report.json"
    tampered.write_text(json.dumps(report_data))

    report = runner.run(pdf, SPECIMEN, None, previous_pdf=previous, build_report=tampered)
    offline = next(check for check in report["checks"] if check["id"] == "offline")

    assert report["gate"] == "fail"
    assert offline["code"] == "NETWORK_DENIED"
    assert "not bound" in offline["detail"]


def test_reported_network_attempts_fail_the_offline_check(tmp_path: Path) -> None:
    pdf, previous, _sheet = specimen_build()
    report_data = json.loads(build_report_path().read_text())
    report_data["networkAttempts"] = 1
    tampered = tmp_path / "report.json"
    tampered.write_text(json.dumps(report_data))

    report = runner.run(pdf, SPECIMEN, None, previous_pdf=previous, build_report=tampered)
    offline = next(check for check in report["checks"] if check["id"] == "offline")

    assert report["gate"] == "fail"
    assert offline["code"] == "NETWORK_DENIED"
    assert "network attempts" in offline["detail"]


def test_report_bound_to_another_manuscript_hash_fails(tmp_path: Path) -> None:
    pdf, previous, _sheet = specimen_build()
    work = ROOT / ".cache" / "verify-other-manuscript"
    work.mkdir(parents=True, exist_ok=True)
    other = work / "other.yaml"
    data = json.loads(json.dumps(yaml.safe_load(SPECIMEN.read_text())))
    data["sections"][0]["blocks"][0]["text"] += "  An extra sentence changes the manuscript hash."
    other.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    report = runner.run(pdf, other, None, previous_pdf=previous, build_report=build_report_path())
    offline = next(check for check in report["checks"] if check["id"] == "offline")

    assert report["gate"] == "fail"
    assert offline["code"] == "NETWORK_DENIED"
    assert "not bound" in offline["detail"]


def test_timestamp_only_difference_still_passes_determinism(tmp_path: Path) -> None:
    pdf, _previous, _sheet = specimen_build()
    rewrite = tmp_path / "rewritten.pdf"
    rewrite.write_bytes(pdf.read_bytes() + b"\n% comment-only difference\n")

    result = determinism.check(pdf, rewrite)

    assert result.status == "pass"
    assert result.evidence["bytesEqual"] is False
    assert "bytes differ" in result.detail


def test_page_count_difference_fails_determinism() -> None:
    pdf, _previous, _sheet = specimen_build()
    from bookify.publish import typst_driver
    from helpers import ADVERSARIAL

    work = ROOT / ".cache" / "verify-adversarial"
    other = typst_driver.build(ADVERSARIAL, work / "adversarial.pdf", work / "build", offline=True)

    result = determinism.check(pdf, other.pdf)
    assert result.status == "fail"
    assert "page count differs" in result.detail
