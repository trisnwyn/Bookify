"""Task 44: charts centre their visible ink, not their text boxes.

The shared pass in `figures.charts` grows the shorter horizontal canvas side by
the measured visible-ink asymmetry. These tests render the real catalogue
charts, insert the SVGs at the production 72 % width into a Typst page, and
measure the ink of the rasterised PDF. A bypassed pass is kept as a negative
control: it must leave the vector files and the rendered page off-centre.
"""

from __future__ import annotations

import copy
import re
import shutil
import subprocess
import uuid
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from bookify.figures import charts, checks, presets
from bookify.manuscript import model

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "content" / "catalogue.yaml"
TYPST = ROOT / "tools" / "typst" / "typst"
NATIVE_WIDTH_PT = presets.CHART_FIGSIZE[0] * 72.0
NATIVE_HEIGHT_PT = presets.CHART_FIGSIZE[1] * 72.0
PAGE_CENTRE_PT = 595.2756 / 2.0
RASTER_DPI = 200
INK_THRESHOLD = 245
GATE_PT = 2.0  # captions.TOLERANCE_PT; never relaxed
OBSERVED_PT = 1.0  # the balanced result must be much tighter than the gate
MAX_SHRINK = 0.05  # approved chart-content shrink budget


def _catalogue_chart_blocks() -> list[dict]:
    manuscript = model.load(CATALOGUE)
    return [
        block
        for section in manuscript.sections
        for block in section["blocks"]
        if block["type"] == "chart"
    ]


@pytest.fixture(scope="module")
def catalogue_charts() -> list[dict]:
    blocks = _catalogue_chart_blocks()
    kinds = [block["chart"]["kind"] for block in blocks]
    assert len(blocks) == 16
    assert set(kinds) == set(checks.CHART_KINDS)
    assert kinds.count("pie") == 2  # pie + donut
    return blocks


@pytest.fixture(scope="module")
def rendered_catalogue(catalogue_charts, tmp_path_factory) -> list[charts.ChartRender]:
    out_dir = tmp_path_factory.mktemp("layout-chart-svgs")
    return [charts.render(block, ROOT, out_dir) for block in catalogue_charts]


def _compile_pages(svgs: list[Path], work: Path) -> Path:
    """One A4 page per SVG, image at the production 72 % width, centred."""
    work.mkdir(parents=True, exist_ok=True)
    lines = ['#set page(paper: "a4", margin: 60pt)', "#set par(justify: false)"]
    for index, svg in enumerate(svgs):
        copied = work / f"image-{index}.svg"
        shutil.copyfile(svg, copied)
        relative = copied.relative_to(ROOT).as_posix()
        lines.append(f'#align(center, image("/{relative}", width: 72%))')
        if index < len(svgs) - 1:
            lines.append("#pagebreak()")
    source = "\n".join(lines) + "\n"
    typ = work / "charts.typ"
    typ.write_text(source)
    pdf = work / "charts.pdf"
    result = subprocess.run(
        [
            "bwrap", "--unshare-net", "--bind", "/", "/", "--chdir", str(ROOT), "--",
            str(TYPST), "compile",
            "--ignore-system-fonts", "--font-path", "assets/fonts",
            "--package-path", "vendor/typst",
            "--package-cache-path", ".cache/empty-pkg",
            "--root", ".", str(typ.relative_to(ROOT)), str(pdf.relative_to(ROOT)),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, f"typst failed: {result.stderr}"
    return pdf


def _page_geometry(svgs: list[Path]) -> list[dict]:
    """Rasterise the compiled pages and return each page's visible-ink geometry."""
    work = ROOT / ".cache" / "layout-charts-tests" / uuid.uuid4().hex
    try:
        pdf = _compile_pages(svgs, work)
        prefix = work / "page"
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(RASTER_DPI), str(pdf), str(prefix)],
            check=True,
        )
        pages = sorted(work.glob("page-*.png"))
        assert len(pages) == len(svgs), f"expected {len(svgs)} pages, got {len(pages)}"
        scale = RASTER_DPI / 72.0
        geometry: list[dict] = []
        for page in pages:
            pixels = np.asarray(Image.open(page).convert("L"))
            ink = pixels < INK_THRESHOLD
            columns = np.flatnonzero(ink.any(axis=0))
            rows = np.flatnonzero(ink.any(axis=1))
            assert columns.size and rows.size, f"no visible ink on {page.name}"
            width_pt = pixels.shape[1] / scale
            x0, x1 = columns[0] / scale, (columns[-1] + 1) / scale
            geometry.append(
                {
                    "page_width_pt": width_pt,
                    "x0": x0,
                    "x1": x1,
                    "left": x0,
                    "right": width_pt - x1,
                    "centre": (x0 + x1) / 2.0,
                    "page_centre": width_pt / 2.0,
                }
            )
        return geometry
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _svg_size(svg: str) -> tuple[float, float]:
    match = re.search(r'width="([0-9.]+)pt" height="([0-9.]+)pt"', svg)
    assert match, "SVG has no declared point size"
    return float(match.group(1)), float(match.group(2))


def _svg_ink_width_pt(path: Path) -> tuple[float, float]:
    """Visible ink width in SVG points, via an independent ImageMagick raster."""
    png = path.with_suffix(".measure.png")
    try:
        subprocess.run(
            ["magick", str(path), "-background", "white", "-flatten", str(png)],
            check=True,
            capture_output=True,
        )
        pixels = np.asarray(Image.open(png).convert("L"))
        columns = np.flatnonzero((pixels < INK_THRESHOLD).any(axis=0))
        assert columns.size
        width_pt, _ = _svg_size(path.read_text())
        scale = pixels.shape[1] / width_pt
        return (columns[-1] - columns[0] + 1) / scale, width_pt
    finally:
        png.unlink(missing_ok=True)


def test_catalogue_visible_ink_is_centred_in_the_rendered_page(rendered_catalogue) -> None:
    geometry = _page_geometry([render.path for render in rendered_catalogue])
    measurements = []
    for render, page in zip(rendered_catalogue, geometry):
        delta = page["centre"] - page["page_centre"]
        asymmetry = page["left"] - page["right"]
        measurements.append(
            f"{render.block_id}: centre delta {delta:+.2f} pt, left-right {asymmetry:+.2f} pt"
        )
        assert page["left"] > 0 and page["right"] > 0, "ink must stay inside the canvas"
        assert abs(asymmetry) <= OBSERVED_PT, "; ".join(measurements)
        assert abs(delta) <= OBSERVED_PT, "; ".join(measurements)
        # The page-centre gate is the catalogue contract; it is not relaxed here.
        assert abs(delta) <= GATE_PT, "; ".join(measurements)

    worst = max(abs(page["centre"] - page["page_centre"]) for page in geometry)
    assert worst < OBSERVED_PT, f"worst visible-ink delta {worst:.2f} pt"


def test_catalogue_charts_render_twice_to_identical_vector_files(
    catalogue_charts, tmp_path: Path
) -> None:
    for block in catalogue_charts:
        first_dir = tmp_path / f"first-{block['id']}"
        second_dir = tmp_path / f"second-{block['id']}"
        first = charts.render(copy.deepcopy(block), ROOT, first_dir)
        second = charts.render(copy.deepcopy(block), ROOT, second_dir)

        assert first.path.name == second.path.name
        assert first.sha256 == second.sha256
        assert first.path.read_bytes() == second.path.read_bytes()
        svg = first.path.read_text()
        assert "<svg" in svg and "<path" in svg
        assert "<image" not in svg


def test_canvas_grows_only_horizontally_and_within_the_shrink_budget(
    rendered_catalogue,
) -> None:
    for render in rendered_catalogue:
        width, height = _svg_size(render.path.read_text())
        assert height == pytest.approx(NATIVE_HEIGHT_PT, abs=1e-6), render.block_id
        assert width >= NATIVE_WIDTH_PT - 1e-6, render.block_id
        assert width <= NATIVE_WIDTH_PT * (1.0 + MAX_SHRINK), render.block_id


def test_growth_adds_margin_without_rescaling_or_cropping_content(
    catalogue_charts, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bubble = next(block for block in catalogue_charts if block["chart"]["kind"] == "bubble")

    balanced = charts.render(copy.deepcopy(bubble), ROOT, tmp_path / "balanced")
    monkeypatch.setattr(charts, "_balance_horizontal_ink", lambda figure, axes: None)
    unbalanced = charts.render(copy.deepcopy(bubble), ROOT, tmp_path / "unbalanced")

    balanced_width, balanced_height = _svg_size(balanced.path.read_text())
    unbalanced_width, unbalanced_height = _svg_size(unbalanced.path.read_text())
    balanced_ink, _ = _svg_ink_width_pt(balanced.path)
    unbalanced_ink, _ = _svg_ink_width_pt(unbalanced.path)

    assert balanced_height == pytest.approx(unbalanced_height, abs=1e-6)
    assert balanced_width > unbalanced_width
    # Same marks, same scale: the extra space is margin, not a crop or rescale.
    assert balanced_ink == pytest.approx(unbalanced_ink, abs=0.5)
    # No stored value, label, gap, cell or bin may change with the layout pass.
    assert balanced.bars == unbalanced.bars
    assert balanced.gaps == unbalanced.gaps
    assert balanced.labels == unbalanced.labels
    assert balanced.series_labels == unbalanced.series_labels
    assert balanced.cells == unbalanced.cells
    assert balanced.bins == unbalanced.bins


def test_bypassing_the_pass_leaves_the_rendered_ink_off_centre(
    catalogue_charts, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bubble = next(block for block in catalogue_charts if block["chart"]["kind"] == "bubble")

    fixed = charts.render(copy.deepcopy(bubble), ROOT, tmp_path / "fixed")
    monkeypatch.setattr(charts, "_balance_horizontal_ink", lambda figure, axes: None)
    raw = charts.render(copy.deepcopy(bubble), ROOT, tmp_path / "raw")

    raw_page, fixed_page = _page_geometry([raw.path, fixed.path])
    raw_delta = raw_page["centre"] - raw_page["page_centre"]
    raw_asymmetry = raw_page["left"] - raw_page["right"]
    fixed_delta = fixed_page["centre"] - fixed_page["page_centre"]

    # Negative control: without the shared pass the real rendered page fails the
    # catalogue ±2 pt gate and the margins are visibly unequal.
    assert abs(raw_delta) > GATE_PT, f"raw centre delta {raw_delta:+.2f} pt"
    assert abs(raw_asymmetry) > GATE_PT, f"raw margin asymmetry {raw_asymmetry:+.2f} pt"
    assert abs(fixed_delta) <= OBSERVED_PT, f"balanced centre delta {fixed_delta:+.2f} pt"
