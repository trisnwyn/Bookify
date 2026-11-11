"""Per-script glyph coverage against the vendored fonts.

A character with no glyph in its script chain is a `GLYPH_MISSING` build
error. Nothing falls back to a system font.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterator

import yaml
from fontTools.ttLib import TTCollection, TTFont

from bookify.errors import BookifyError
from bookify.figures import checks as figure_checks
from bookify.manuscript import model

JAPANESE_RANGES = figure_checks.CJK_RANGES


@dataclass(frozen=True)
class Coverage:
    characters: int
    japanese: int
    missing: tuple[tuple[str, str], ...]

    @property
    def ok(self) -> bool:
        return not self.missing


def _is_japanese(codepoint: int) -> bool:
    return any(low <= codepoint <= high for low, high in JAPANESE_RANGES)


@lru_cache(maxsize=None)
def _cmap(path: Path) -> frozenset[int]:
    if path.suffix.lower() == ".ttc":
        fonts = TTCollection(str(path)).fonts
        covered: set[int] = set()
        for font in fonts:
            covered.update(font.getBestCmap().keys())
        return frozenset(covered)
    return frozenset(TTFont(str(path)).getBestCmap().keys())


def _chain_paths(root: Path, script: str) -> list[Path]:
    manifest = yaml.safe_load((root / "assets" / "fonts" / "fonts.yaml").read_text())
    families = {family["family"]: family for family in manifest["families"]}
    chain = manifest["scripts"][script]["chain"]
    paths: list[Path] = []
    for name in chain:
        paths.extend(root / entry["path"] for entry in families[name]["files"])
    return paths


def _record_strings(root: Path, illustration_id: str) -> list[str]:
    path = root / "assets" / "illustrations" / illustration_id / "record.yaml"
    if not path.is_file():
        return []
    record = yaml.safe_load(path.read_text())
    if not isinstance(record, dict):
        return []
    return [record[key] for key in ("credit", "caption") if isinstance(record.get(key), str)]


def _segments(manuscript: model.Manuscript) -> Iterator[tuple[str, str]]:
    """Every string that reaches the page, tagged with its script chain."""
    metadata = manuscript.data["metadata"]
    for key in ("title", "subtitle", "institution"):
        value = metadata.get(key)
        if isinstance(value, str):
            yield value, "text"
    for section in manuscript.sections:
        for key in ("title", "kicker", "standfirst"):
            value = section.get(key)
            if isinstance(value, str):
                yield value, "text"
        for block in section["blocks"]:
            kind = block["type"]
            for key in ("text", "caption", "definition", "term", "title", "attribution", "note"):
                value = block.get(key)
                if isinstance(value, str):
                    yield value, "text"
            for item in block.get("items", []):
                yield item, "text"
            if kind == "table":
                for cell in block.get("header", []):
                    yield cell, "text"
                for row in block.get("rows", []):
                    for cell in row:
                        yield cell, "text"
            elif kind == "chart":
                chart = block["chart"]
                for category in chart.get("categories", []):
                    yield category, "latin"
                for series in chart.get("series", []):
                    yield series["label"], "latin"
                if chart.get("notes"):
                    yield chart["notes"], "latin"
                axis = chart.get("axis", {})
                unit = axis.get("unit") if isinstance(axis, dict) else None
                if isinstance(unit, str):
                    yield unit, "latin"
                x_axis = chart.get("xAxis", {})
                x_unit = x_axis.get("unit") if isinstance(x_axis, dict) else None
                if isinstance(x_unit, str):
                    yield x_unit, "latin"
            elif kind == "diagram":
                diagram = block["diagram"]
                for node in diagram.get("nodes", []):
                    yield node["label"], "text"
                    if node.get("sub"):
                        yield node["sub"], "text"
                for group in diagram.get("groups", []):
                    yield group["label"], "text"
                for edge in diagram.get("edges", []):
                    if edge.get("label"):
                        yield edge["label"], "text"
                for event in diagram.get("events", []):
                    yield event["label"], "text"
                    if event.get("sub"):
                        yield event["sub"], "text"
                for value in diagram.get("rows", []):
                    yield value, "text"
                for value in diagram.get("columns", []):
                    yield value, "text"
                for row in diagram.get("cells", []):
                    for value in row:
                        yield value, "text"
                for item in diagram.get("sets", []):
                    yield item["label"], "text"
                for region in diagram.get("overlaps", []):
                    yield region["label"], "text"
                for item in diagram.get("lanes", []):
                    yield item["label"], "text"
                for item in diagram.get("stages", []):
                    yield item["label"], "text"
            elif kind == "equation":
                yield block["typst"], "maths"
            elif kind == "illustration":
                for value in _record_strings(manuscript.root, block["illustrationId"]):
                    yield value, "text"


def manuscript_text(manuscript: model.Manuscript) -> str:
    return "\n".join(text for text, _script in _segments(manuscript))


def check(manuscript: model.Manuscript, root: Path) -> Coverage:
    latin = frozenset().union(*(_cmap(path) for path in _chain_paths(root, "latin-vietnamese")))
    japanese = frozenset().union(*(_cmap(path) for path in _chain_paths(root, "japanese")))
    maths = frozenset().union(*(_cmap(path) for path in _chain_paths(root, "maths")))

    checked = 0
    japanese_count = 0
    missing: list[tuple[str, str]] = []
    for text, script in _segments(manuscript):
        for character in text:
            if character.isspace():
                continue
            codepoint = ord(character)
            checked += 1
            if script == "maths":
                if codepoint not in maths:
                    missing.append((character, f"U+{codepoint:04X}"))
                continue
            if script == "latin":
                if codepoint not in latin:
                    missing.append((character, f"U+{codepoint:04X}"))
                continue
            if _is_japanese(codepoint):
                japanese_count += 1
                if codepoint not in japanese:
                    missing.append((character, f"U+{codepoint:04X}"))
            elif codepoint not in latin and codepoint not in japanese:
                missing.append((character, f"U+{codepoint:04X}"))
    return Coverage(characters=checked, japanese=japanese_count, missing=tuple(sorted(set(missing))))


def require_coverage(manuscript: model.Manuscript, root: Path) -> Coverage:
    coverage = check(manuscript, root)
    if not coverage.ok:
        summary = ", ".join(f"{char} ({code})" for char, code in coverage.missing[:10])
        raise BookifyError("GLYPH_MISSING", f"no glyph for: {summary}", str(manuscript.path))
    return coverage


def describe(coverage: Coverage) -> str:
    return (
        f"{coverage.characters} characters checked "
        f"({coverage.japanese} Japanese), {len(coverage.missing)} missing"
    )
