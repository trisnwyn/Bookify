"""Shared build fixtures for verification tests."""

from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path

from bookify.figures import contact_sheet
from bookify.publish import typst_driver

ROOT = Path(__file__).resolve().parents[1]
SPECIMEN = ROOT / "content" / "specimen.yaml"
ADVERSARIAL = ROOT / "fixtures" / "adversarial" / "illustrations.yaml"
TYPST = ROOT / "tools" / "typst" / "typst"


@lru_cache(maxsize=1)
def specimen_build() -> tuple[Path, Path, Path]:
    """First build, comparison build, and a rendered contact sheet."""
    work = ROOT / ".cache" / "verify-base"
    work.mkdir(parents=True, exist_ok=True)
    first = typst_driver.build(SPECIMEN, ROOT / "dist" / "verify-specimen.pdf", work / "build", offline=True)
    second = typst_driver.build(SPECIMEN, ROOT / "dist" / "verify-specimen-2.pdf", work / "rebuild", offline=True)
    sheet = work / "contact.png"
    contact_sheet.build_contact_sheet(pdf=first.pdf, out_path=sheet, cols=3, dpi=50, tile_width=240)
    return first.pdf, second.pdf, sheet


def build_report_path() -> Path:
    return ROOT / ".cache" / "verify-base" / "build" / "build-report.json"


def compile_typ(source: str, name: str, standards: str | None = None) -> Path:
    work = ROOT / ".cache" / "verify-snippets"
    work.mkdir(parents=True, exist_ok=True)
    typ = work / f"{name}.typ"
    pdf = work / f"{name}.pdf"
    typ.write_text(source)
    command = [
        "bwrap", "--unshare-net", "--bind", "/", "/", "--chdir", str(ROOT), "--",
        str(TYPST), "compile",
        "--ignore-system-fonts", "--font-path", "assets/fonts",
        "--package-path", "vendor/typst",
        "--package-cache-path", ".cache/empty-pkg",
    ]
    if standards is not None:
        command += ["--pdf-standard", standards]
    command += ["--root", ".", str(typ.relative_to(ROOT)), str(pdf)]
    subprocess.run(command, check=True, capture_output=True, text=True, cwd=ROOT)
    return pdf


def manuscript_with(anchor_source: str, path: Path) -> Path:
    """A minimal manuscript whose blocks anchor to pages 1 and 2 of a source."""
    data = {
        "schemaVersion": "1.0",
        "revision": 1,
        "id": "author-fixture",
        "metadata": {"title": "Author fixture", "languages": ["en"]},
        "sections": [
            {
                "id": "sec-src",
                "title": "Source",
                "blocks": [
                    {
                        "id": "b-one",
                        "type": "paragraph",
                        "text": "Existing text for page one.",
                        "sourceAnchors": [{"sourceId": anchor_source, "page": 1}],
                    },
                    {
                        "id": "b-fig",
                        "type": "diagram",
                        "caption": "Existing reconstruction.",
                        "confidence": "inferred",
                        "sourceAnchors": [{"sourceId": anchor_source, "page": 2}],
                        "diagram": {
                            "preset": "process",
                            "nodes": [{"id": "n-a", "label": "A"}, {"id": "n-b", "label": "B"}],
                            "edges": [{"from": "n-a", "to": "n-b"}],
                        },
                    },
                ],
            }
        ],
    }
    import yaml

    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return path
