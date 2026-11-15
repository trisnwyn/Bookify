"""Task 59: source, editorial, visual and limits guidance, and the voice check.

The voice requirement is semantic. Exact phrase patterns are regression aids
only: they detect a few known constructions, they do not judge a chapter. These
tests therefore check the guide teaches the judgement (positive/weak examples,
paraphrase review, citation and uncertainty exceptions) and demonstrate — with a
test-local matcher — that an exact check passes paraphrases that must still fail
a semantic review. Nothing here claims that review is automated.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "skill" / "bookify" / "references"
EDITORIAL = REFERENCES / "editorial.md"
SOURCE = REFERENCES / "source-and-provenance.md"
VISUAL = REFERENCES / "visual-design.md"
LIMITS = REFERENCES / "limits.md"

WEAK_EXAMPLES = (
    "The materials provided suggest that a definition matters.",
    "The slides explain that a definition fixes a term.",
    "Based on the provided content, we can see that examples are useful.",
    "The course says the label cannot be read.",
)

BETTER_EXAMPLES = (
    "A definition fixes the meaning of a term so later claims can be tested against it.",
    "One label cannot be read. The book marks the gap as unresolved rather than guessing a value.",
)

# Exact regression aid, deliberately narrow. It is not the quality gate.
EXACT_WEAK_PATTERN = re.compile(
    r"\b(the provided materials?|the provided content|the (materials|slides?|course|source) "
    r"(provided|say|says|explain|explains|suggest|suggests|describe|describes))\b",
    re.IGNORECASE,
)


def flat(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split()).lower()


def test_editorial_guide_requires_affirmative_coursebook_prose() -> None:
    text = flat(EDITORIAL)
    assert "natural" in text and "coursebook" in text
    assert "positive" in text or "better" in text
    assert "standalone" in text or "stand on its own" in text
    for phrase in (
        "state the teaching point directly",
        "define",
        "example",
        "check",
        "summary",
    ):
        assert phrase in text
    assert "do not narrate the input" in text or "input narration" in text


def test_editorial_guide_contains_positive_and_weak_before_after_examples() -> None:
    raw = EDITORIAL.read_text(encoding="utf-8")
    for phrase in BETTER_EXAMPLES:
        assert phrase in raw, f"missing positive example: {phrase!r}"
    for phrase in WEAK_EXAMPLES:
        assert phrase in raw, f"missing weak example: {phrase!r}"
        index = raw.find(phrase)
        window = raw[max(0, index - 400) : index + 400].lower()
        assert "weak" in window, f"weak example is not labelled weak: {phrase!r}"

    # At least two labelled Weak/Better pairs, not one token example.
    assert raw.lower().count("weak") >= 3
    assert raw.lower().count("better") >= 2


def test_editorial_guide_requires_semantic_paraphrase_review() -> None:
    text = flat(EDITORIAL)
    assert "semantic" in text
    assert "paraphrase" in text
    assert "every" in text and ("chapter" in text or "page" in text)
    assert "record" in text
    assert "regression" in text
    assert "not the whole" in text or "not the gate" in text
    assert "automated" in text  # the guide must state what is not automated
    assert not re.search(r"automatically (detect|check|grade|judge|pass)", text)


def test_editorial_guide_keeps_citations_attribution_and_uncertainty() -> None:
    text = flat(EDITORIAL)
    for phrase in ("citation", "attribution", "quotation", "uncertainty", "enrichment"):
        assert phrase in text
    assert "never upgrade" in text or "do not upgrade" in text
    assert "hide" in text  # must forbid hiding uncertainty
    assert "source index" in text or "authoring record" in text


def test_exact_phrase_check_is_insufficient_and_says_so() -> None:
    for phrase in WEAK_EXAMPLES:
        assert EXACT_WEAK_PATTERN.search(phrase), phrase
    for phrase in BETTER_EXAMPLES:
        assert not EXACT_WEAK_PATTERN.search(phrase), phrase

    paraphrase = (
        "As the supplied reading indicates, a definition matters for later claims."
    )
    # The regression aid misses this on purpose; only a semantic read catches it.
    assert not EXACT_WEAK_PATTERN.search(paraphrase)
    text = flat(EDITORIAL)
    assert "paraphrase" in text
    assert "fails even" in text or "must still fail" in text or "still fail" in text


def test_source_guide_covers_intake_anchors_coverage_and_rights() -> None:
    text = flat(SOURCE)
    for phrase in (
        "pdf",
        "intake",
        "anchor",
        "coverage",
        "source index",
        "unreadable",
        "citation",
        "rights",
        "ocr",
        "machine-read",
    ):
        assert phrase in text, f"source guide lacks {phrase!r}"
    assert "read-only" in text
    assert "never invent" in text or "do not invent" in text
    assert "stable" in text and ("hash" in text or "locator" in text)


def test_visual_guide_covers_house_style_composition_and_page_inspection() -> None:
    text = flat(VISUAL)
    for phrase in (
        "typography",
        "hierarchy",
        "white space",
        "side-left",
        "side-right",
        "unbreakable",
        "every rendered page",
        "no quota",
        "chart",
        "diagram",
        "illustration",
        "credit",
        "rights",
    ):
        assert phrase in text, f"visual guide lacks {phrase!r}"
    assert "contact sheet" in text
    assert "agent visual inspection" in text or "not human" in text


def test_limits_guide_makes_no_unsupported_capability_claim() -> None:
    text = flat(LIMITS)
    for phrase in (
        "ocr",
        "no cjk",
        "linux x86_64",
        "byte-identical",
        "rights",
        "tagged",
        "offline",
    ):
        assert phrase in text, f"limits guide lacks {phrase!r}"
    assert "not claimed" in text or "not support" in text
    assert "independent" in text and "rewrite" in text
    assert "windows" in text and "macos" in text
