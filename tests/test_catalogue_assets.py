"""Tasks 37-38: catalogue illustration assets, rights records and frozen evidence.

Ownership: illustrations worker. These tests cover only the four catalogue
illustration families and the two local original SVG files.
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml
from PIL import Image

from bookify.publish import rights

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
PHOTO_DIR = ASSETS / "illustrations" / "photo-1"
ART_DIR = ASSETS / "illustrations" / "art-1"
REC_DIR = ASSETS / "illustrations" / "rec-1"
HIST_DIR = ASSETS / "illustrations" / "hist-1"
ARTWORK_DIR = ASSETS / "catalogue" / "artwork"

# Frozen before Tasks 37-38 so any edit to the reused photograph is visible.
PHOTO_1 = {
    "id": "photo-1",
    "path": "assets/illustrations/photo-1/original.jpg",
    "originUrl": "https://commons.wikimedia.org/wiki/File:Barack_Obama_and_Emperor_Akihito_20140424.jpg",
    "creator": "William Ng, US Department of State",
    "licence": "Public domain (US Government work)",
    "credit": "Photo: William Ng / US Department of State (public domain)",
    "kind": "contemporary_photograph",
    "rightsStatus": "verified",
    "retrievedAt": "2026-11-10",
    "sha256": "3ba10038ae93d38995496345d4bb654e9bba020b6d27fc88a99370b7c03ce93d",
}


def _record(directory: Path) -> dict:
    return yaml.safe_load((directory / "record.yaml").read_text())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_photo_1_is_reused_without_edits() -> None:
    record = _record(PHOTO_DIR)

    for field, expected in PHOTO_1.items():
        assert record[field] == expected, field
    assert record["alt"].strip()
    assert record["caption"].strip()
    assert _sha256(PHOTO_DIR / "original.jpg") == PHOTO_1["sha256"]


def test_local_original_records_are_complete_and_local() -> None:
    for directory, illustration_id, path, kind in (
        (ART_DIR, "art-1", "assets/catalogue/artwork/art-1.svg", "conceptual_artwork"),
        (REC_DIR, "rec-1", "assets/catalogue/artwork/rec-1.svg", "reconstruction"),
    ):
        record = _record(directory)

        assert record["id"] == illustration_id
        assert record["path"] == path
        assert record["originUrl"] == f"local:{path}"
        assert record["licence"] == "Original work created for this catalogue"
        assert record["kind"] == kind
        assert record["rightsStatus"] == "verified"
        assert record["creator"].strip()
        assert record["credit"].strip()
        assert record["caption"].strip()
        assert record["alt"].strip()
        assert (ROOT / record["path"]).is_file()


def test_editorial_caption_names_original_artwork_and_is_not_documentary() -> None:
    caption = _record(ART_DIR)["caption"].lower()

    assert "original artwork" in caption
    assert "not" in caption
    assert _record(ART_DIR)["kind"] == "conceptual_artwork"


def test_reconstruction_caption_states_no_original_was_traced() -> None:
    record = rights.load(ROOT, "rec-1")
    caption = rights.caption(record, None).lower()

    assert "reconstruction" in caption
    assert "no original" in caption
    assert "traced" in caption


@pytest.mark.parametrize("name", ["art-1.svg", "rec-1.svg"])
def test_local_artwork_is_vector_without_raster_or_live_text(name: str) -> None:
    path = ARTWORK_DIR / name
    raw = path.read_text(encoding="utf-8").lower()

    assert "<svg" in raw
    assert "<image" not in raw
    assert "data:image" not in raw
    assert ".png" not in raw and ".jpg" not in raw and ".jpeg" not in raw

    root = ET.fromstring(path.read_text(encoding="utf-8"))
    assert root.tag.endswith("svg")
    tags = {element.tag.rsplit("}", 1)[-1].lower() for element in root.iter()}
    # No live text: the caption and alt carry the words, so the artwork cannot
    # depend on an SVG font or leak an unchecked glyph into the PDF.
    assert "text" not in tags
    assert "image" not in tags
    assert "foreignobject" not in tags


def test_historical_record_freezes_a_verified_public_domain_period_photograph() -> None:
    record = _record(HIST_DIR)

    assert record["kind"] == "contemporary_photograph"
    assert record["rightsStatus"] == "verified"
    assert record["path"] == "assets/illustrations/hist-1/original.jpg"
    assert record["originUrl"].startswith("https://commons.wikimedia.org/wiki/File:")
    assert "Macarthur" in record["originUrl"].replace("_", " ")
    assert record["licenceUrl"].startswith("https://commons.wikimedia.org/wiki/")
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["retrievedAt"])
    assert record["creator"].strip()
    assert record["credit"].strip()
    assert record["caption"].strip()
    assert record["alt"].strip()
    assert "public domain" in record["licence"].lower()
    evidence = record["evidence"]
    assert evidence["licenceShortName"] == "Public domain"
    assert evidence["usageTerms"] == "Public domain"
    assert "Wikimedia Commons" in evidence["source"]
    assert evidence["downloadUrl"].startswith("https://upload.wikimedia.org/")

    local_sha1 = hashlib.sha1((ROOT / record["path"]).read_bytes()).hexdigest()
    assert evidence["commonsSha1"] == local_sha1

    image = ROOT / record["path"]
    assert image.is_file()
    assert record["sha256"] == _sha256(image)


def test_historical_directory_holds_exactly_one_frozen_image() -> None:
    images = [
        path
        for path in HIST_DIR.iterdir()
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff"}
    ]

    assert [path.name for path in images] == ["original.jpg"]
    with Image.open(images[0]) as image:
        assert image.format == "JPEG"
        assert image.width >= 800 and image.height >= 800


def test_historical_licence_evidence_file_matches_the_record() -> None:
    record = _record(HIST_DIR)
    licence = (HIST_DIR / "LICENCE.md").read_text(encoding="utf-8")

    assert record["originUrl"] in licence
    assert record["licenceUrl"] in licence
    assert record["sha256"] in licence
    assert "public domain" in licence.lower()
    assert "PD-USGov-Military-Army" in licence


def test_all_four_catalogue_families_load_through_the_rights_boundary() -> None:
    loaded = {name: rights.load(ROOT, name) for name in ("photo-1", "hist-1", "art-1", "rec-1")}

    assert {item.kind for item in loaded.values()} == {
        "contemporary_photograph",
        "conceptual_artwork",
        "reconstruction",
    }
    assert {item.rights_status for item in loaded.values()} == {"verified"}
    assert len({item.path for item in loaded.values()}) == 4
