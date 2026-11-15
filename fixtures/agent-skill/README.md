# Agent-skill source fixture

Status: **Task 64 fixture only.** This directory provides one public-safe
synthetic source for the later same-source two-mode authoring evidence (Tasks
65–66). No mode book, manuscript, authoring record or final PDF has been authored
from it yet.

## What this is

`source.typ` is authored synthetic source material. It uses neutral vocabulary
(sample, label, record, detail, setting, warrant, unresolved) and contains
several concepts, a concrete case, two small tables with invented counts, and a
deliberately unreadable image-only plate. It is not extracted from a lecture,
book, dataset or external document, and it makes no measurement or real-world
claim.

`source.pdf` is compiled from `source.typ` with the repository's pinned Typst
binary and vendored Spectral fonts. It is A4 and six pages. Page 6 is the only
image-only page: a synthetic raster plate with no text layer. No OCR was run and
no label, date, place or warrant was invented for it. Page 5 says plainly that
the plate remains unresolved.

## Reproduction

Run this from the repository root: the directory containing `pyproject.toml`
and `tools/typst/typst`. In a checkout, `cd "$(git rev-parse --show-toplevel)"`;
in an extracted bundle, `cd bookify/engine`. The command uses `$PWD`, so no
original checkout path is stored.

```sh
SOURCE_DATE_EPOCH=1700000000 \
bwrap --unshare-net --bind / / --chdir "$PWD" -- \
  tools/typst/typst compile \
  --ignore-system-fonts \
  --font-path assets/fonts \
  --package-path vendor/typst \
  --package-cache-path .cache/empty-pkg \
  --root . \
  fixtures/agent-skill/source.typ \
  fixtures/agent-skill/source.pdf
```

Pins: Typst 0.15.1 (`toolchain.lock.json`), the vendored Spectral faces in
`assets/fonts/`, `SOURCE_DATE_EPOCH=1700000000` for deterministic PDF metadata,
and `bwrap --unshare-net` to deny network. No package is downloaded and no
system font is used. Compiling with a different epoch changes the PDF metadata
and therefore the bytes; that is not a layout difference, but it is not the
tracked fixture either. Typst formats the creation date in the host local time
zone, so a host with a different time zone can change metadata bytes even when
the layout and text do not.

Test command:

```sh
uv run python -m pytest tests/test_skill_fixture.py -q
```

## Source units

| Page | Heading | Role | Text | Image |
| --- | --- | --- | --- | --- |
| 1 | A sample arrives | Concrete case; two labels, a moved sample, unknown origin | readable | none |
| 2 | The record | Method; four fields and a synthetic checklist table | readable | none |
| 3 | Three levels of reading | Definitions: detail, setting, warrant | readable | none |
| 4 | Comparing counts | Synthetic comparison table and a coverage relationship | readable | none |
| 5 | When the evidence stops | Uncertainty, quote, short check; points to the plate | readable | none |
| 6 | (no heading) | Unreadable image-only plate | none | one synthetic raster |

The source order is deliberately not the most pedagogical order: the concrete
case and the record come before the definitions they use. A source-faithful
author must keep pages 1–6 in order; a teachable author may regroup them. Every
page remains anchored to its source page.

## Evidence map

<!-- evidence:start -->
```json
{
  "schemaVersion": "1.0",
  "sourceId": "source",
  "authoredSynthetic": true,
  "externalResearch": false,
  "privateMaterial": false,
  "ocrPerformed": false,
  "inventedLabels": false,
  "sourceTyp": "fixtures/agent-skill/source.typ",
  "sourcePdf": "fixtures/agent-skill/source.pdf",
  "sourceTypSha256": "66953d5c88be28df0e73f9cf386a1280f324fd12b7b4cf017c4e8d909981f4c8",
  "sourcePdfSha256": "2c751d32ba89126b996db5045814e6ed2dc03468f0785ba74c3d28077f4ae1be",
  "pageCount": 6,
  "strictPageOrder": [
    1,
    2,
    3,
    4,
    5,
    6
  ],
  "teachableReorganisationExample": [
    3,
    1,
    2,
    4,
    5,
    6
  ],
  "pages": [
    {
      "page": 1,
      "heading": "A sample arrives",
      "unit": "case example and unknown origin",
      "textCharCount": 827,
      "textSha256": "38a6634d27401c55f1d569e4f5a696a726779dabb59d21035a24e0a0b5abe6f7",
      "imageOnly": false,
      "imageCount": 0
    },
    {
      "page": 2,
      "heading": "The record",
      "unit": "method and synthetic checklist table",
      "textCharCount": 814,
      "textSha256": "3bc9546480ec70332a8968470c7c202d44a3974e811b5267e90a64277358011d",
      "imageOnly": false,
      "imageCount": 0
    },
    {
      "page": 3,
      "heading": "Three levels of reading",
      "unit": "definitions: detail, setting, warrant",
      "textCharCount": 723,
      "textSha256": "bafbd5e4bcc3123ffc4cf56c009abb053af7020b2123f634bfd52d71a8e50978",
      "imageOnly": false,
      "imageCount": 0
    },
    {
      "page": 4,
      "heading": "Comparing counts",
      "unit": "synthetic comparison table and coverage relationship",
      "textCharCount": 902,
      "textSha256": "2e4717f2c44b5c73302115a9582453ce190b97874f6f47a2f3586ba889ad4041",
      "imageOnly": false,
      "imageCount": 0
    },
    {
      "page": 5,
      "heading": "When the evidence stops",
      "unit": "uncertainty, quote, short check and plate reference",
      "textCharCount": 755,
      "textSha256": "6f2c141a70a8abef702b21004d30938e74e91070d613a122b14d1357b82bd2fb",
      "imageOnly": false,
      "imageCount": 0
    },
    {
      "page": 6,
      "heading": null,
      "unit": "unreadable image-only plate",
      "textCharCount": 0,
      "textSha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "imageOnly": true,
      "imageCount": 1,
      "note": "No text layer; no label assigned; no OCR."
    }
  ]
}
```
<!-- evidence:end -->

`textSha256` values are the page text hashes produced by `bookify intake` from
the tracked `source.pdf` with the pinned Poppler tools. `charCount` counts the
extracted characters (the form feed is stripped). Page 6 has the SHA-256 of the
empty string and one 72×48 image. These are evidence indices, not measurements.

## Pedagogical possibilities (for Tasks 65–66)

- **Source-faithful:** page order 1→6, every content block anchored, page 6 left
  unresolved, no lesson apparatus and no external enrichment.
- **Teachable:** one documented reorganisation could begin with the definitions
  on page 3, then the case on page 1, then the record on page 2, the counts on
  page 4, the limits on page 5, and the plate on page 6. That is an example, not
  a required book shape.
- The same source can support a short teaching sequence on reading a sample, a
  worked case, a record template, a data table and an explicit uncertainty
  exercise. A teachable author may add explanations and questions; it must keep
  the page anchors, the unknown origin and the unreadable plate's status.
- No external enrichment is pre-approved. If a later trial requests research,
  the authoring record must record permission and citations.

## Trial use and limits

- **Trial use:** Tasks 65–66 may consume this source; Task 64 does not author
  either mode book.
- The counts are invented (12/15/+3, 7/7/0, 4/6/+2) and are not measurements.
- The plate is intentionally unreadable. Do not OCR it and do not assign it a
  label, date, place or warrant. Page 5's prose says why.
- No private lecture, dataset, URL, external image or real-world claim is used.
- No new font, dependency, package, service or network access is introduced.
- Text hashes depend on the pinned Poppler extraction; they are stable in the
  tested environment and are recorded as fixture evidence, not as a claim about
  another extraction stack.
- This fixture is not a visual acceptance book and does not claim human review
  or book-level voice quality.
