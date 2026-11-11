"""Task 8: assemble the specimen, offline, with numbering and a build report."""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

import pytest
import yaml

from bookify.errors import BookifyError
from bookify.manuscript import model
from bookify.publish import typst_driver

ROOT = Path(__file__).resolve().parents[1]
SPECIMEN = ROOT / "content" / "specimen.yaml"


def _work() -> Path:
    path = ROOT / ".cache" / f"publish-{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture(scope="module")
def built() -> typst_driver.BuildResult:
    work = _work()
    return typst_driver.build(SPECIMEN, work / "specimen.pdf", work / "build", offline=True)


def test_pdf_is_a4_and_has_expected_pages(built: typst_driver.BuildResult) -> None:
    info = subprocess.run(["pdfinfo", str(built.pdf)], capture_output=True, text=True, check=True).stdout
    assert "595.276 x 841.89 pts (A4)" in info
    assert built.report["pdf"]["pages"] == 6
    assert built.report["offline"] is True
    assert built.report["draft"] is False


def test_report_lists_sections_figures_and_placement(built: typst_driver.BuildResult) -> None:
    assert [section["page"] for section in built.report["sections"]] == [3, 6]
    assert set(built.report["numbered"]) >= {"Figure 1", "Figure 2", "Table 1", "Photograph 1"}
    assert len(built.report["placements"]) == 1
    assert built.report["placements"][0]["page"] == 4
    assert {figure["kind"] for figure in built.report["figures"]} == {"chart", "diagram"}


def test_text_contains_every_required_element(built: typst_driver.BuildResult) -> None:
    text = subprocess.run(["pdftotext", "-layout", str(built.pdf), "-"], capture_output=True, text=True, check=True).stdout

    for expected in (
        "Reading a sample",
        "Tiếng Việt có đủ dấu",
        "日本語の文章",
        "Special characters survive the pipeline",
        "Figure 1.",
        "Figure 2.",
        "Table 1.",
        "Photograph 1.",
        "Photo: William Ng / US Department of State",
        "Synthetic diagram",
        "§1",
    ):
        assert expected in text, f"missing from PDF: {expected}"


def test_recorded_notes_reach_the_pdf(built: typst_driver.BuildResult) -> None:
    text = subprocess.run(["pdftotext", "-layout", str(built.pdf), "-"], capture_output=True, text=True, check=True).stdout
    normalised = " ".join(text.split())

    assert "Authored synthetic values; not measurements." in normalised
    assert "Synthetic diagram authored for this specimen; no original figure was traced." in normalised


def test_chart_gap_notes_reach_the_pdf() -> None:
    data = yaml.safe_load(SPECIMEN.read_text())
    chart = next(
        block for section in data["sections"] for block in section["blocks"] if block["type"] == "chart"
    )
    chart["chart"]["values"] = [[72], [None], [58]]
    chart["chart"]["notes"] = "BIRCH-DID-NOT-REPORT-UNIQUE"
    chart["note"] = "BLOCK-LEVEL-NOTE-UNIQUE"
    work = ROOT / ".cache" / "chart-gap-notes"
    work.mkdir(parents=True, exist_ok=True)
    manuscript = work / "manuscript.yaml"
    manuscript.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    result = typst_driver.build(manuscript, work / "out.pdf", work / "build", offline=True)
    text = subprocess.run(["pdftotext", "-layout", str(result.pdf), "-"], capture_output=True, text=True, check=True).stdout
    normalised = " ".join(text.split())

    assert "BIRCH-DID-NOT-REPORT-UNIQUE" in normalised
    assert "BLOCK-LEVEL-NOTE-UNIQUE" in normalised


def test_equation_that_calls_a_file_reader_never_produces_a_pdf() -> None:
    # Defence in depth: validation rejects `#` (the code escape), but a bare
    # math-mode call must still fail at compile rather than read a project file.
    data = yaml.safe_load(SPECIMEN.read_text())
    equation = next(
        block for section in data["sections"] for block in section["blocks"] if block["type"] == "equation"
    )
    equation["typst"] = 'read("/pyproject.toml")'
    work = _work()
    manuscript = work / "manuscript.yaml"
    manuscript.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    model.load(manuscript)

    out = work / "should-not-exist.pdf"
    with pytest.raises(BookifyError) as error:
        typst_driver.build(manuscript, out, work / "build", offline=True)

    assert error.value.code == "BUILD_FAILED"
    assert "read" in error.value.message
    assert not out.exists()


def test_prose_block_notes_reach_the_pdf() -> None:
    data = yaml.safe_load(SPECIMEN.read_text())
    paragraph = next(
        block for section in data["sections"] for block in section["blocks"] if block["type"] == "paragraph"
    )
    paragraph["note"] = "PROSE-NOTE-UNIQUE recorded uncertainty."
    work = _work()
    manuscript = work / "manuscript.yaml"
    manuscript.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    result = typst_driver.build(manuscript, work / "out.pdf", work / "build", offline=True)
    text = subprocess.run(["pdftotext", "-layout", str(result.pdf), "-"], capture_output=True, text=True, check=True).stdout

    assert "PROSE-NOTE-UNIQUE" in " ".join(text.split())


def test_build_is_refused_without_offline() -> None:
    work = _work()
    with pytest.raises(BookifyError) as error:
        typst_driver.build(SPECIMEN, work / "x.pdf", work / "build", offline=False)
    assert error.value.code == "BUILD_FAILED"


def test_two_builds_share_layout_facts(built: typst_driver.BuildResult) -> None:
    work = _work()
    second = typst_driver.build(SPECIMEN, work / "again.pdf", work / "build", offline=True)

    assert second.report["pdf"]["pages"] == built.report["pdf"]["pages"]
    first_text = subprocess.run(["pdftotext", "-layout", str(built.pdf), "-"], capture_output=True, text=True, check=True).stdout
    second_text = subprocess.run(["pdftotext", "-layout", str(second.pdf), "-"], capture_output=True, text=True, check=True).stdout
    assert first_text == second_text
    assert second.report["placements"] == built.report["placements"]
    assert second.report["pdf"]["sha256"] == built.report["pdf"]["sha256"]
    assert (work / "build" / "build-report.json").is_file()
