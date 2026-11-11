"""Task 6: token discipline, glyph coverage, presets and the CJK weight fix."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml
from PIL import Image

from bookify.design import coverage, lint, tokens
from bookify.errors import BookifyError
from bookify.manuscript import model

ROOT = Path(__file__).resolve().parents[1]
SPECIMEN = ROOT / "content" / "specimen.yaml"
TYPST = ROOT / "tools" / "typst" / "typst"


def _compile_text(text: str, name: str) -> Path:
    work = ROOT / ".cache" / "design-tests"
    work.mkdir(parents=True, exist_ok=True)
    source = work / f"{name}.typ"
    pdf = work / f"{name}.pdf"
    source.write_text(text)
    subprocess.run(
        [
            "bwrap", "--unshare-net", "--bind", "/", "/", "--chdir", str(ROOT), "--",
            str(TYPST), "compile",
            "--ignore-system-fonts", "--ignore-embedded-fonts",
            "--font-path", "assets/fonts",
            "--package-path", "vendor/typst",
            "--package-cache-path", ".cache/empty-pkg",
            "--root", ".",
            str(source.relative_to(ROOT)), str(pdf),
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    return pdf


def test_every_block_type_has_exactly_one_preset() -> None:
    assert lint.missing_presets(ROOT) == set()


def test_figure_caption_uses_the_shared_centred_preset() -> None:
    theme = (ROOT / "typst" / "theme.typ").read_text()
    blocks = (ROOT / "typst" / "blocks.typ").read_text()

    assert "caption_align: center" in theme
    assert "#let preset-figure-caption(caption)" in blocks
    assert "align(tokens.figure.caption_align" in blocks
    assert "set par(justify: false)" in blocks

    for preset in ("preset-chart", "preset-illustration"):
        body = blocks.split(f"#let {preset}(", 1)[1].split("#let ", 1)[0]
        assert "preset-figure-caption(caption)" in body, f"{preset} must use the shared centred caption"

    diagram_body = blocks.split("#let preset-diagram(", 1)[1].split("#let ", 1)[0]
    assert "preset-chart(figure, caption: caption" in diagram_body, "preset-diagram must delegate to the shared caption path"

    for preset in ("preset-table", "preset-equation"):
        body = blocks.split(f"#let {preset}(", 1)[1].split("#let ", 1)[0]
        assert "preset-figure-caption" not in body, f"{preset} captions must stay unchanged"


def test_blocks_contain_no_visual_literals() -> None:
    issues = lint.lint(ROOT)

    assert issues == [], "\n".join(f"{i.path.name}:{i.line} {i.message}" for i in issues)


def test_theme_defines_every_named_token() -> None:
    theme = (ROOT / "typst" / "theme.typ").read_text()
    missing = [name for name in tokens.LEAF_NAMES if not re.search(rf"\b{re.escape(name)}:", theme)]

    assert missing == [], f"tokens missing from theme.typ: {missing}"
    assert "accent" in theme and "role" in theme


def test_specimen_glyph_coverage_passes() -> None:
    manuscript = model.load(SPECIMEN)
    result = coverage.require_coverage(manuscript, ROOT)

    assert result.ok
    assert result.japanese > 50
    assert result.characters > result.japanese


def test_missing_glyph_fails_with_named_code(tmp_path: Path) -> None:
    data = yaml.safe_load(SPECIMEN.read_text())
    data["sections"][0]["blocks"][0]["text"] += " " + chr(0x1F9EA)
    target = tmp_path / "manuscript.yaml"
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    manuscript = model.load(target, root=ROOT)
    with pytest.raises(BookifyError) as error:
        coverage.require_coverage(manuscript, ROOT)

    assert error.value.code == "GLYPH_MISSING"
    assert "U+1F9EA" in error.value.message


def _specimen(tmp_path: Path, mutate) -> model.Manuscript:
    data = yaml.safe_load(SPECIMEN.read_text())
    mutate(data)
    target = tmp_path / "manuscript.yaml"
    target.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return model.load(target, root=ROOT)


def _block(data: dict, kind: str) -> dict:
    return next(block for section in data["sections"] for block in section["blocks"] if block["type"] == kind)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data["metadata"].__setitem__("title", data["metadata"]["title"] + " 🧪"),
        lambda data: data["metadata"].__setitem__("subtitle", data["metadata"]["subtitle"] + " 🧪"),
        lambda data: data["metadata"].__setitem__("institution", data["metadata"]["institution"] + " 🧪"),
        lambda data: _block(data, "table")["header"].__setitem__(0, _block(data, "table")["header"][0] + " 🧪"),
        lambda data: _block(data, "table")["rows"][0].__setitem__(0, _block(data, "table")["rows"][0][0] + " 🧪"),
        lambda data: _block(data, "chart")["chart"]["categories"].__setitem__(0, "Alder 🧪"),
        lambda data: _block(data, "chart")["chart"]["series"][0].__setitem__(
            "label", _block(data, "chart")["chart"]["series"][0]["label"] + " 🧪"
        ),
        lambda data: _block(data, "diagram")["diagram"]["nodes"][0].__setitem__(
            "label", _block(data, "diagram")["diagram"]["nodes"][0]["label"] + " 🧪"
        ),
        lambda data: _block(data, "diagram")["diagram"]["nodes"][0].__setitem__(
            "sub", _block(data, "diagram")["diagram"]["nodes"][0]["sub"] + " 🧪"
        ),
        lambda data: _block(data, "diagram")["diagram"]["groups"][0].__setitem__(
            "label", _block(data, "diagram")["diagram"]["groups"][0]["label"] + " 🧪"
        ),
        lambda data: _block(data, "equation").__setitem__("typst", _block(data, "equation")["typst"] + " 🧪"),
    ],
)
def test_glyph_coverage_collects_every_rendered_string(tmp_path: Path, mutate) -> None:
    manuscript = _specimen(tmp_path, mutate)

    result = coverage.check(manuscript, ROOT)

    assert ("🧪", "U+1F9EA") in result.missing


def test_glyph_coverage_collects_the_illustration_credit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(coverage, "_record_strings", lambda _root, _id: ["🧪 credit"])
    manuscript = model.load(SPECIMEN)

    result = coverage.check(manuscript, ROOT)

    assert ("🧪", "U+1F9EA") in result.missing


def test_cjk_weight_axis_is_honoured() -> None:
    pdf = _compile_text(
        '#import "/typst/theme.typ": book_base\n'
        "#show: book_base\n"
        "#set page(width: 220pt, height: 120pt, margin: 20pt)\n"
        "#set text(size: 22pt)\n"
        '#text(weight: 400)[日本語の見出し]\n'
        "#pagebreak()\n"
        '#text(weight: 700)[日本語の見出し]\n',
        "weights",
    )
    prefix = pdf.with_suffix("")
    subprocess.run(["pdftoppm", "-png", "-r", "300", str(pdf), str(prefix)], check=True)

    def ink(path: str) -> int:
        image = Image.open(path).convert("L")
        pixels = image.load()
        width, height = image.size
        return sum(1 for y in range(height) for x in range(width) if pixels[x, y] < 128)

    regular = ink(f"{prefix}-1.png")
    bold = ink(f"{prefix}-2.png")
    assert regular > 0 and bold > 0
    assert bold / regular > 1.2, f"bold/regular ink ratio too low: {bold / regular:.2f}"


def test_every_preset_compiles() -> None:
    pdf = _compile_text(
        '#import "/typst/theme.typ": book_base\n'
        '#import "/typst/blocks.typ": *\n'
        "#show: book_base\n"
        "#preset-paragraph[A paragraph.]\n"
        "#preset-lead[A lead.]\n"
        '#preset-quote([A quotation.], attribution: "Source")\n'
        '#preset-definition[Protocol][The agreed order of an encounter.]\n'
        '#preset-example(title: "Example")[Body.]\n'
        '#preset-case(title: "Case")[Body.]\n'
        '#preset-assessment(title: "Check")[Question?]\n'
        "#preset-list(([One], [Two]))\n"
        '#preset-table(([A], [B]), (([1], [2]),), caption: "Table.")\n'
        '#preset-equation($overline(x) = 1/n sum_(i=1)^n x_i$, caption: "Equation.")\n'
        '#preset-chart(rect(width: 40pt, height: 20pt), caption: "Chart.")\n'
        '#preset-diagram(rect(width: 40pt, height: 20pt), caption: "Diagram.")\n'
        '#preset-illustration(rect(width: 40pt, height: 20pt), caption: "Photo.", credit: "Credit")\n',
        "presets",
    )

    assert pdf.is_file() and pdf.stat().st_size > 0
    text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    assert "A paragraph." in text
    assert "Protocol" in text
    assert "A quotation." in text and "Source" in text
    assert "Credit" in text


def test_cli_design_check_passes(capsys: pytest.CaptureFixture[str]) -> None:
    from bookify.toolchain.cli import main

    assert main(["design", "check", "--manuscript", str(SPECIMEN), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["coverage"]["missing"] == []
    assert payload["lint"] == []
    assert payload["missingPresets"] == []
