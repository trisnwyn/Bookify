"""Task 64: the public-safe same-source fixture and its evidence map.

The fixture is one authored synthetic source that later strict and teachable
authoring trials consume unchanged. These tests compile it offline, compare the
tracked PDF byte-for-byte, extract page text and images, and check the recorded
source-unit index. They do not author either mode book.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from bookify.intake import manifest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "agent-skill"
SOURCE_TYP = FIXTURE / "source.typ"
SOURCE_PDF = FIXTURE / "source.pdf"
README = FIXTURE / "README.md"
TYPST = ROOT / "tools" / "typst" / "typst"
PINNED_EPOCH = "1700000000"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
EVIDENCE_BLOCK = re.compile(
    r"<!-- evidence:start -->\s*```json\s*(?P<data>.*?)\s*```\s*<!-- evidence:end -->",
    re.S,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _compile(source: Path, out: Path) -> None:
    """Compile with the repository pins, no system fonts and no network."""
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "bwrap", "--unshare-net", "--bind", "/", "/", "--chdir", str(ROOT), "--",
            str(TYPST), "compile",
            "--ignore-system-fonts",
            "--font-path", "assets/fonts",
            "--package-path", "vendor/typst",
            "--package-cache-path", ".cache/empty-pkg",
            "--root", ".",
            str(source.relative_to(ROOT)), str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={**os.environ, "SOURCE_DATE_EPOCH": PINNED_EPOCH},
    )


def _pdfinfo(pdf: Path) -> str:
    return subprocess.run(
        ["pdfinfo", str(pdf)], capture_output=True, text=True, check=True
    ).stdout


def _page_text(pdf: Path, page: int) -> str:
    raw = subprocess.run(
        ["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(pdf), "-"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return raw.replace("\r\n", "\n").replace("\f", "")


def _normalised(text: str) -> str:
    return " ".join(text.split())


def _evidence() -> dict:
    match = EVIDENCE_BLOCK.search(README.read_text())
    assert match, "fixtures/agent-skill/README.md must carry the evidence JSON block"
    return json.loads(match.group("data"))


@pytest.fixture(scope="module")
def compiled(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("skill-fixture-build") / "source.pdf"
    _compile(SOURCE_TYP, out)
    return out


@pytest.fixture(scope="module")
def intake(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = tmp_path_factory.mktemp("skill-fixture-intake")
    return manifest.build(SOURCE_PDF, out)


def test_source_typ_compiles_offline_to_the_tracked_pdf(compiled: Path) -> None:
    assert SOURCE_TYP.is_file()
    assert SOURCE_PDF.is_file()
    assert compiled.read_bytes() == SOURCE_PDF.read_bytes()
    assert _sha256(compiled) == _sha256(SOURCE_PDF)


def test_tracked_pdf_is_six_a4_pages() -> None:
    info = _pdfinfo(SOURCE_PDF)

    assert re.search(r"^Pages:\s+6$", info, re.M)
    assert "595.276 x 841.89 pts (A4)" in info


def test_page_text_indices_match_the_evidence_map(intake: dict) -> None:
    evidence = _evidence()

    assert intake["sourceId"] == evidence["sourceId"]
    assert intake["pageCount"] == evidence["pageCount"] == 6
    assert [page["page"] for page in intake["pages"]] == [1, 2, 3, 4, 5, 6]

    for recorded, actual in zip(evidence["pages"], intake["pages"], strict=True):
        assert actual["page"] == recorded["page"]
        assert actual["charCount"] == recorded["textCharCount"]
        assert actual["textSha256"] == recorded["textSha256"]
        assert actual["isImageOnly"] is recorded["imageOnly"]
        assert len(actual["images"]) == recorded["imageCount"]


def test_page_headings_are_in_source_order() -> None:
    expected = {
        1: "A sample arrives",
        2: "The record",
        3: "Three levels of reading",
        4: "Comparing counts",
        5: "When the evidence stops",
    }

    for page, heading in expected.items():
        text = _page_text(SOURCE_PDF, page)
        assert heading in text, f"page {page} must start its source unit: {heading}"
        assert text.strip(), f"page {page} must be readable"

    assert _page_text(SOURCE_PDF, 6) == ""


def test_image_only_plate_has_no_text_layer_and_no_invented_label(intake: dict) -> None:
    page = intake["pages"][5]
    evidence = _evidence()

    assert page["isImageOnly"] is True
    assert page["charCount"] == 0
    assert page["textSha256"] == EMPTY_SHA256
    assert len(page["images"]) == 1
    image = page["images"][0]
    assert (image["width"], image["height"]) == (72, 48)

    assert _page_text(SOURCE_PDF, 6) == ""
    listing = subprocess.run(
        ["pdfimages", "-list", "-f", "6", "-l", "6", str(SOURCE_PDF)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    rows = [line.split() for line in listing.splitlines()[2:] if line.split()]
    assert len(rows) == 1
    assert rows[0][2] == "image"

    plate_evidence = evidence["pages"][5]
    assert plate_evidence["imageOnly"] is True
    assert plate_evidence["imageCount"] == 1
    assert "no ocr" in plate_evidence["note"].lower()
    assert evidence["ocrPerformed"] is False
    assert evidence["inventedLabels"] is False

    page_five = _normalised(_page_text(SOURCE_PDF, 5))
    assert "not readable" in page_five
    assert "no text layer" in page_five
    assert "remains unresolved" in page_five


def test_evidence_map_matches_the_tracked_files_and_order() -> None:
    evidence = _evidence()

    assert evidence["authoredSynthetic"] is True
    assert evidence["externalResearch"] is False
    assert evidence["privateMaterial"] is False
    assert evidence["sourceTypSha256"] == _sha256(SOURCE_TYP)
    assert evidence["sourcePdfSha256"] == _sha256(SOURCE_PDF)
    assert evidence["pageCount"] == 6

    strict = evidence["strictPageOrder"]
    teachable = evidence["teachableReorganisationExample"]
    assert strict == [1, 2, 3, 4, 5, 6]
    assert sorted(teachable) == strict
    assert teachable != strict
    assert teachable.index(3) < teachable.index(1), "the example starts with the definitions"
    assert teachable[-1] == 6, "the unreadable plate stays an explicit final unit"


def test_source_contains_multiple_teachable_concepts_and_synthetic_data() -> None:
    pages = {page: _page_text(SOURCE_PDF, page) for page in range(1, 7)}
    page_three = _normalised(pages[3])

    for term in ("Detail", "Setting", "Warrant"):
        assert term in page_three
    assert "What is here?" in page_three
    assert "What does it mean here?" in page_three
    assert "Why should the reading be accepted?" in page_three

    for term in ("Detail recorded", "Setting recorded", "Warrant recorded", "12", "15", "+3"):
        assert term in pages[4]
    assert "synthetic" in pages[4]
    assert "invented" in pages[4]
    assert "not to report an observation" in pages[4]

    assert "checklist, not a measurement" in pages[2]
    assert "unresolved" in pages[2]
    assert "A claim should carry its evidence." in pages[5]
    assert "which of the three levels" in pages[5]


def test_source_typ_is_self_contained_and_offline() -> None:
    source = SOURCE_TYP.read_text()

    assert "http://" not in source
    assert "https://" not in source
    assert "#include" not in source
    assert "#read" not in source
    assert "plugin(" not in source
    assert '#image(plate, format: "png"' in source
    assert '#image("' not in source, "the plate must be embedded, not an external file"
    assert 'font: "Spectral"' in source
    assert "bytes((" in source
    assert str(ROOT) not in source


def test_readme_documents_reproduction_trial_use_and_limits() -> None:
    readme = README.read_text()
    lowered = readme.lower()

    assert "task 64 fixture only" in lowered
    assert "no mode book" in lowered
    assert "tasks\n65–66" in lowered or "tasks 65–66" in lowered
    assert "## source units" in lowered
    assert "## pedagogical possibilities" in lowered
    assert "## trial use and limits" in lowered
    assert "no ocr" in lowered
    assert "not measurements" in lowered
    assert "source_date_epoch=1700000000" in lowered
    assert "--unshare-net" in lowered
    assert "--ignore-system-fonts" in lowered
    assert "uv run python -m pytest tests/test_skill_fixture.py -q" in lowered
    assert str(ROOT) not in readme
    assert '"$PWD"' in readme
    assert "run this from the repository root" in lowered
