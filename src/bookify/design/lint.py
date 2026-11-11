"""Lint the Typst layer: no visual literals outside the theme, one preset per block type."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from bookify.design import tokens

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
POINTS = re.compile(r"\b\d+(?:\.\d+)?pt\b")
FONT_LITERALS = ("Spectral", "Noto Serif CJK JP", "STIX Two Math")
PRESET = re.compile(r"#let\s+preset-([a-z][a-z0-9-]*)\s*\(")


@dataclass(frozen=True)
class LintIssue:
    path: Path
    line: int
    message: str


def _scan(path: Path) -> list[LintIssue]:
    issues: list[LintIssue] = []
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        if line.lstrip().startswith("//"):
            continue
        if HEX.search(line):
            issues.append(LintIssue(path, number, "raw colour literal; use a token"))
        if POINTS.search(line):
            issues.append(LintIssue(path, number, "raw point size; use a token"))
        for family in FONT_LITERALS:
            if family in line:
                issues.append(LintIssue(path, number, f"font literal {family!r}; import it from the theme"))
    return issues


def lint(root: Path) -> list[LintIssue]:
    targets = [
        root / "typst" / "blocks.typ",
        *sorted((root / "typst" / "templates").glob("*.typ")),
        *sorted((root / "typst" / "cetz").glob("*.typ")),
    ]
    issues: list[LintIssue] = []
    for target in targets:
        if target.is_file():
            issues.extend(_scan(target))
    return issues


def presets(path: Path) -> set[str]:
    return set(PRESET.findall(path.read_text()))


def missing_presets(root: Path) -> set[str]:
    present = presets(root / "typst" / "blocks.typ")
    return set(tokens.BLOCK_TYPES) - present
