"""Task 3 contract: measured pins, local doctor, offline/model guard, dispatcher."""

from __future__ import annotations

import json
import shutil
import socket
from pathlib import Path

import pytest

from bookify.errors import BookifyError
from bookify.publish import typst_driver
from bookify.toolchain import doctor, guard, pins
from bookify.toolchain.cli import main

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "toolchain.lock.json"
SPECIMEN = ROOT / "content" / "specimen.yaml"


def test_lock_file_records_measured_local_stack() -> None:
    lock = pins.load(LOCK)

    assert lock.typst.version == "0.15.1"
    assert lock.python.version.startswith("3.13")
    assert lock.package("cetz").version == "0.5.3"
    assert lock.package("oxifmt").version == "1.0.0"
    assert {f.family for f in lock.fonts} == {"Spectral", "Noto Serif CJK JP", "STIX Two Math"}
    assert all(len(f.sha256) == 64 for f in lock.fonts)


def test_lock_rejects_evidence_without_hash(tmp_path: Path) -> None:
    data = json.loads(LOCK.read_text())
    del data["fonts"][0]["sha256"]
    broken = tmp_path / "lock.json"
    broken.write_text(json.dumps(data))

    with pytest.raises(BookifyError) as error:
        pins.load(broken)

    assert error.value.code == "INPUT_INVALID"


def test_guard_denies_network_and_restores_socket() -> None:
    original = socket.create_connection

    with pytest.raises(BookifyError) as error:
        with guard.offline():
            socket.create_connection(("example.com", 80))

    assert error.value.code == "NETWORK_DENIED"
    assert socket.create_connection is original


def test_guard_denies_model_calls_outside_authoring() -> None:
    with guard.offline():
        with pytest.raises(BookifyError) as error:
            guard.model_call("chart interpretation")

    assert error.value.code == "MODEL_CALL_DENIED"


def test_guard_records_denied_attempts() -> None:
    with pytest.raises(BookifyError):
        with guard.offline():
            assert guard.active() is True
            socket.create_connection(("example.com", 80))

    assert guard.attempts() == 1
    assert guard.active() is False


def test_doctor_reports_a_fully_local_stack() -> None:
    report = doctor.run(ROOT, LOCK)

    assert report.ok, report.summary()
    assert report.checks, "doctor must actually check something"
    assert all(check.is_local for check in report.checks)
    assert {check.identifier for check in report.checks} >= {
        "python",
        "typst",
        "package:cetz",
        "font:Spectral",
    }


def test_doctor_detects_a_tampered_font(tmp_path: Path) -> None:
    data = json.loads(LOCK.read_text())
    data["fonts"][0]["sha256"] = "0" * 64
    broken = tmp_path / "lock.json"
    broken.write_text(json.dumps(data))

    report = doctor.run(ROOT, broken)

    assert not report.ok
    assert any("FONT_MISSING" == check.code for check in report.checks)


def test_doctor_rejects_missing_typst_binary(tmp_path: Path) -> None:
    data = json.loads(LOCK.read_text())
    data["typst"]["binary"] = "tools/does-not-exist/typst"
    broken = tmp_path / "lock.json"
    broken.write_text(json.dumps(data))

    report = doctor.run(ROOT, broken)

    assert not report.ok
    assert any("typst" in check.identifier for check in report.checks)


def test_build_refuses_a_tampered_lock_before_compiling(tmp_path: Path) -> None:
    data = json.loads(LOCK.read_text())
    data["fonts"][0]["sha256"] = "0" * 64
    broken = tmp_path / "lock.json"
    broken.write_text(json.dumps(data))
    work = ROOT / ".cache" / "tampered-lock"
    work.mkdir(parents=True, exist_ok=True)
    out = work / "should-not-exist.pdf"

    with pytest.raises(BookifyError) as error:
        typst_driver.build(SPECIMEN, out, work / "build", offline=True, lock_path=broken)

    assert error.value.code == "FONT_MISSING"
    assert not out.exists()


def test_build_refuses_a_tampered_typst_binary_hash_before_compiling(tmp_path: Path) -> None:
    data = json.loads(LOCK.read_text())
    data["typst"]["sha256"] = "0" * 64
    broken = tmp_path / "lock.json"
    broken.write_text(json.dumps(data))
    work = ROOT / ".cache" / "tampered-typst"
    work.mkdir(parents=True, exist_ok=True)
    out = work / "should-not-exist.pdf"

    with pytest.raises(BookifyError) as error:
        typst_driver.build(SPECIMEN, out, work / "build", offline=True, lock_path=broken)

    assert error.value.code == "BUILD_FAILED"
    assert "typst" in error.value.message
    assert not out.exists()


def test_cli_doctor_json_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["toolchain", "doctor", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_cli_build_requires_manuscript_and_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["build"]) == 2
    payload = json.loads(capsys.readouterr().err)
    assert payload["code"] == "INPUT_INVALID"


def test_probe_scripts_are_present_and_executable() -> None:
    scripts = [ROOT / "probe" / name for name in ("probe.sh", "diagram.sh", "chart.sh")]
    for script in scripts:
        assert script.is_file(), f"missing probe script: {script.name}"
        assert script.stat().st_mode & 0o111, f"probe script not executable: {script.name}"
