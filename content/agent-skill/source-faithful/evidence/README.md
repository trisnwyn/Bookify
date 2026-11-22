# Source-faithful reviewer evidence

This directory is a reviewer convenience copy, not a build workspace. The
portable example itself is `book.yaml`, `authoring/record.json`, `assets/` and
`intake/`; builds, renders, the contact sheet and the verify report normally
live in an external workspace outside the engine tree.

## Files

- `source-faithful.pdf` — final agent-built PDF (the verified PDF).
  - SHA-256 `76d090235ce6043e40ecb85720b0e42b4005edb945d1155f06b122eafe67fc79`
  - 5 A4 pages, 78,868 bytes
  - manuscript revision 2,
    SHA-256 `15ea936af749784528bf13fed135be4b9be3154c42a7c534870674e771eaf889`
- `book-2.pdf` — the second offline build; byte-identical to
  `source-faithful.pdf` (`76d09023…`), referenced by `verify.json` as the
  determinism comparison.
- `build-report.json` — offline build report for the recorded manuscript; its
  nested-section plate is measured at 475.82 pt on page 5. The cover records
  `composition: cover-3`, `selection: engine-fallback` (no cover was authored)
  and `artwork: not-applicable`.
- `verify.json` — the verify gate result; every path in it is workspace-relative
  (`evidence/source-faithful.pdf`, `evidence/book-2.pdf`,
  `evidence/contact-sheet.png`), so the shipped files replay.
- `review-notes.json` — the decision for every warning id, including the h3
  rhythm sample this short book cannot measure.
- `contact-sheet.png` — the five rendered pages in reading order.
- `pages/page-1.png` … `pages/page-5.png` — individual 110 dpi renders.
- `measurements.json` — independently measured per page: the page's extracted
  character count, the SHA-256 of its `pdftotext` output, the dark-pixel ink
  fraction at 72 dpi (threshold 200) and the vertical ink extent divided by the
  721.89 pt text block.

## Build and verification

- Two offline builds from the same stored manuscript, assets, fonts and pins
  are byte-identical (`76d09023…`).
- Engine pins: Typst 0.15.1, Python 3.13.16.
- `bookify verify` gate: **pass** — offline, determinism, glyphs, text, pages,
  captions, illustration-limit, rights, xrefs, definitions and plates all pass.
  Page 5 is a plate page (the nested-section photograph), so the earlier
  thin-page readability warning is gone. The one unmeasured h3 rhythm band is
  answered in `review-notes.json`; the review check is `manual` (agent
  inspection, not human sign-off).
- Source: the supplied fixture `source.pdf`, SHA-256
  `2c751d32ba89126b996db5045814e6ed2dc03468f0785ba74c3d28077f4ae1be`, unchanged.
- Mode: `source-faithful`; coverage 6/6 source pages; one uncertainty entry
  naming the unreadable plate on source page 6.
- Measurements from the rendered PDF: body pitch 15.30 pt (Latin), paragraph
  gap 20.70 pt, lead 16.40 pt; every heading clears at least one body blank line
  (measured white band 15.60–18.48 pt, minimum above the 15.30 pt line pitch). Hierarchy levels 1, 2, 2, 3, 2, 3 with only the full
  plate unit using a deliberate `breakBefore: page`.

No absolute private or workspace paths are recorded in this example.
