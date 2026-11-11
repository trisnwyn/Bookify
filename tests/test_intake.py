"""Task 15: deterministic extraction, anchors, images and stable manifests."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from helpers import ROOT, compile_typ
from bookify.intake import extract, manifest

SOURCE = '''
#set page(paper: "a4", margin: 40pt)
#set text(font: "Spectral", size: 11pt)
Page one has readable text.
#image("/assets/illustrations/photo-1/original.jpg", width: 40%)
#pagebreak()
Page two mentions the second class.
#pagebreak()
#image("/assets/illustrations/photo-1/original.jpg", width: 60%)
'''


@pytest.fixture(scope="module")
def source_pdf() -> Path:
    return compile_typ(SOURCE, "intake-base")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_manifest_is_stable_and_addressable(source_pdf: Path, tmp_path: Path) -> None:
    first = manifest.build(source_pdf, tmp_path)
    first_bytes = _sha(tmp_path / "manifest.json")
    second = manifest.build(source_pdf, tmp_path)

    assert _sha(tmp_path / "manifest.json") == first_bytes
    assert first == second
    assert first["pageCount"] == 3
    assert [page["page"] for page in first["pages"]] == [1, 2, 3]
    assert first["sourceName"] == source_pdf.name
    assert all(page["textSha256"] for page in first["pages"])
    assert (tmp_path / "pages" / "page-001.txt").is_file()


def test_image_only_page_is_flagged_without_text(source_pdf: Path, tmp_path: Path) -> None:
    built = manifest.build(source_pdf, tmp_path)
    third = built["pages"][2]

    assert third["isImageOnly"] is True
    assert third["charCount"] == 0
    assert (tmp_path / "pages" / "page-003.txt").read_text() == ""


def test_image_inventory_matches_pdfimages(source_pdf: Path, tmp_path: Path) -> None:
    built = manifest.build(source_pdf, tmp_path)
    listing = subprocess.run(
        ["pdfimages", "-list", str(source_pdf)], capture_output=True, text=True, check=True
    ).stdout
    listed = [line.split() for line in listing.splitlines()[2:] if line.split()[2] == "image"]

    recorded = [image for page in built["pages"] for image in page["images"]]
    assert len(recorded) == len(listed)
    for image, row in zip(recorded, listed):
        assert (image["width"], image["height"]) == (int(row[3]), int(row[4]))
        assert (tmp_path / image["file"]).is_file()


def test_duplicate_images_share_one_file(source_pdf: Path, tmp_path: Path) -> None:
    built = manifest.build(source_pdf, tmp_path)
    files = [image["file"] for page in built["pages"] for image in page["images"]]

    assert len(files) == 2
    assert files[0] == files[1]
    assert len(list((tmp_path / "images").glob("*.png"))) == 1


def test_manifest_stores_no_absolute_paths(source_pdf: Path, tmp_path: Path) -> None:
    built = manifest.build(source_pdf, tmp_path)
    text = (tmp_path / "manifest.json").read_text()

    assert str(tmp_path) not in text
    assert built["sourceName"] == source_pdf.name


def test_leftover_temp_image_does_not_poison_the_next_run(tmp_path: Path) -> None:
    source = compile_typ('#set page(paper: "a4", margin: 40pt)\nText only.\n', "intake-text-only")
    stale = tmp_path / ".tmp" / "page-001"
    stale.mkdir(parents=True)
    (stale / "img-099.png").write_bytes(b"stale")

    built = manifest.build(source, tmp_path)

    assert built["pages"][0]["images"] == []
    assert not (tmp_path / ".tmp").exists()


def test_retry_after_a_failed_extraction_succeeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = compile_typ('#set page(paper: "a4", margin: 40pt)\nText only.\n', "intake-retry")
    original = extract.list_images
    calls = {"count": 0}

    def flaky(path: Path, page: int):
        calls["count"] += 1
        rows = original(path, page)
        if calls["count"] == 1:
            return rows + [extract.ImageInfo(index=99, width=1, height=1, page=page, kind="image")]
        return rows

    monkeypatch.setattr(extract, "list_images", flaky)
    with pytest.raises(Exception) as error:
        manifest.build(source, tmp_path)
    assert getattr(error.value, "code", "") == "SOURCE_UNREADABLE"
    assert not (tmp_path / ".tmp").exists()

    built = manifest.build(source, tmp_path)

    assert built["pages"][0]["images"] == []
    assert not (tmp_path / ".tmp").exists()
    assert list((tmp_path / "images").glob("*.png")) == []


def test_image_count_mismatch_is_source_unreadable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = compile_typ('#set page(paper: "a4", margin: 40pt)\nText only.\n', "intake-count-mismatch")
    original = extract.list_images

    def extra(path: Path, page: int):
        rows = original(path, page)
        return rows + [extract.ImageInfo(index=99, width=1, height=1, page=page, kind="image")]

    monkeypatch.setattr(extract, "list_images", extra)

    with pytest.raises(Exception) as error:
        manifest.build(source, tmp_path)

    assert getattr(error.value, "code", "") == "SOURCE_UNREADABLE"


def test_soft_mask_image_pairs_one_image_and_stores_no_mask(tmp_path: Path) -> None:
    work = ROOT / ".cache" / "verify-snippets"
    work.mkdir(parents=True, exist_ok=True)
    image_path = work / "mask-source.png"
    image = Image.new("RGBA", (160, 120), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle([10, 10, 150, 110], fill=(220, 40, 40, 180))
    draw.ellipse([40, 30, 120, 90], fill=(40, 80, 220, 90))
    image.save(image_path)

    pdf = compile_typ(
        '#set page(paper: "a4", margin: 40pt)\n'
        "Text on a page.\n"
        '#image("/.cache/verify-snippets/mask-source.png", width: 60%)\n',
        "intake-smask",
    )
    listing = subprocess.run(["pdfimages", "-list", str(pdf)], capture_output=True, text=True, check=True).stdout
    rows = [line.split() for line in listing.splitlines()[2:] if line.split()]
    assert any(row[2] == "smask" for row in rows), "fixture must produce a soft mask"

    built = manifest.build(pdf, tmp_path)

    images = built["pages"][0]["images"]
    assert len(images) == 1
    assert (images[0]["width"], images[0]["height"]) == (160, 120)
    stored = sorted((tmp_path / "images").glob("*.png"))
    assert len(stored) == 1
    assert stored[0].name.endswith("img-00.png")


def test_pair_keeps_the_image_row_in_either_order() -> None:
    image = extract.ImageInfo(index=0, width=10, height=10, page=1, kind="image")
    mask = extract.ImageInfo(index=1, width=10, height=10, page=1, kind="smask")

    assert manifest._pair([Path("img-0.png"), Path("img-1.png")], [image, mask]) == [(Path("img-0.png"), image)]
    assert manifest._pair([Path("img-0.png"), Path("img-1.png")], [mask, image]) == [(Path("img-1.png"), image)]


def test_intake_modules_do_not_import_network_or_models() -> None:
    for path in (ROOT / "src" / "bookify" / "intake").glob("*.py"):
        source = path.read_text()
        for forbidden in ("import socket", "import requests", "urllib", "openai", "anthropic"):
            assert forbidden not in source, f"{path.name} imports {forbidden}"


def test_cli_intake_reports_pages(source_pdf: Path, tmp_path: Path, capsys) -> None:
    from bookify.toolchain.cli import main

    assert main(["intake", "--source", str(source_pdf), "--out", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True and payload["pages"] == 3 and payload["images"] == 2
