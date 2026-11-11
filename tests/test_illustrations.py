"""Task 9: illustration placement and the hard one-per-page limit."""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from bookify.publish import illustrations, typst_driver

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "adversarial" / "illustrations.yaml"


def _work(name: str) -> Path:
    path = ROOT / ".cache" / f"illustrations-{name}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_conflicts_only_reports_pages_with_two() -> None:
    placements = [
        {"illustrationId": "a", "page": 4},
        {"illustrationId": "b", "page": 4},
        {"illustrationId": "c", "page": 6},
    ]
    assert illustrations.conflicts(placements) == {4: ["a", "b"]}


def test_defer_later_moves_the_later_illustration() -> None:
    document = {
        "illustrations": [{"id": "a", "pagebreak": False}, {"id": "b", "pagebreak": False}],
        "sections": [{"blocks": [
            {"id": "ba", "type": "illustration", "illustrationId": "a"},
            {"id": "bb", "type": "illustration", "illustrationId": "b"},
        ]}],
    }
    deferred = illustrations.defer_later(document, {4: ["a", "b"]})

    assert deferred == ["b"]
    assert document["illustrations"][1]["pagebreak"] is True
    assert document["sections"][0]["blocks"][1]["pagebreak"] is True


def test_adversarial_build_defers_exactly_one_illustration() -> None:
    work = _work("adversarial")
    result = typst_driver.build(FIXTURE, work / "adversarial.pdf", work / "build", offline=True)

    placements = result.report["placements"]
    assert len(placements) == 2
    assert len({item["page"] for item in placements}) == 2
    assert result.report["deferredIllustrations"] == ["photo-b"]

    texts = []
    for page in sorted({item["page"] for item in placements}):
        text = subprocess.run(
            ["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(result.pdf), "-"],
            capture_output=True, text=True, check=True,
        ).stdout
        texts.append(text)
    for text in texts:
        assert text.count("Photograph") <= 1, text


def test_multiline_caption_still_maps_and_defers(tmp_path: Path) -> None:
    data = yaml.safe_load(FIXTURE.read_text())
    first = next(
        block for section in data["sections"] for block in section["blocks"]
        if block.get("illustrationId") == "photo-a"
    )
    first["caption"] = "First placement\nphotograph."

    manuscript = _work("multiline") / "multiline.yaml"
    manuscript.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    result = typst_driver.build(manuscript, manuscript.parent / "multiline.pdf", manuscript.parent / "build", offline=True)

    placements = result.report["placements"]
    assert all(item["page"] is not None for item in placements)
    assert len({item["page"] for item in placements}) == 2
    assert result.report["deferredIllustrations"] == ["photo-b"]


def test_both_multiline_captions_still_map_and_defer() -> None:
    data = yaml.safe_load(FIXTURE.read_text())
    blocks = [
        block for section in data["sections"] for block in section["blocks"]
        if block.get("illustrationId")
    ]
    first, second = blocks[0], blocks[1]
    first["caption"] = "First placement\nphotograph."
    second["caption"] = "Second placement\nphotograph."

    manuscript = _work("multiline-both") / "multiline-both.yaml"
    manuscript.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    result = typst_driver.build(manuscript, manuscript.parent / "out.pdf", manuscript.parent / "build", offline=True)

    placements = result.report["placements"]
    assert all(item["page"] is not None for item in placements), placements
    assert len({item["page"] for item in placements}) == 2
    assert result.report["deferredIllustrations"] == ["photo-b"]


def test_specimen_has_one_illustration_on_one_page() -> None:
    work = _work("specimen")
    result = typst_driver.build(
        ROOT / "content" / "specimen.yaml", work / "specimen.pdf", work / "build", offline=True
    )

    assert len(result.report["placements"]) == 1
    assert result.report["deferredIllustrations"] == []
