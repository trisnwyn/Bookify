# Teachable example evidence

This directory holds the rendered evidence for the teachable-textbook trial
(`book.yaml`, `authoring/record.json`). All paths below are relative to the
repository root.

- `teachable-textbook.pdf` — the built book (6 A4 pages, revision 2), the
  verified PDF. SHA-256
  `57dab763047c0dab30e1ab0cdcb2895708d26265feb7669d8a119035db5d1bf3`,
  97,366 bytes.
- `book-2.pdf` — the second offline build, byte-identical, referenced by
  `verify.json` as the determinism comparison.
- `contact-sheet.png` — the six rendered pages in reading order.
- `pages/page-1.png` … `pages/page-6.png` — individual 110 dpi renders.
- `review-notes.json` — decisions for the page-5 readability warning and the
  unmeasured h3 rhythm band.
- `verify.json` — the verify gate result (`pass`); every path is
  workspace-relative (`evidence/teachable-textbook.pdf`), so the shipped files
  replay. Review status `manual`, i.e. agent inspection, not human sign-off.
- `build-report.json` — section pages, contents pages and manuscript hash from
  the build. The cover records `composition: cover-3`, `selection:
  engine-fallback` (no cover was authored) and `artwork: not-applicable`.
- `measurements.json` — independently measured per page: the page's extracted
  character count, the SHA-256 of its `pdftotext` output, the dark-pixel ink
  fraction at 72 dpi (threshold 200) and the vertical ink extent divided by the
  721.89 pt text block.

Rebuild from a checkout (external workspace, offline):

```sh
bookify build --workspace <workspace> --manuscript <workspace>/book.yaml \
  --out <workspace>/evidence/teachable-textbook.pdf --offline   --build-dir <workspace>/build/book
bookify build --workspace <workspace> --manuscript <workspace>/book.yaml \
  --out <workspace>/evidence/book-2.pdf --offline \
  --build-dir <workspace>/build/book-rebuild
bookify verify --workspace <workspace> --pdf <workspace>/evidence/teachable-textbook.pdf \
  --manuscript <workspace>/book.yaml --previous-pdf <workspace>/evidence/book-2.pdf \
  --build-report <workspace>/evidence/build-report.json \
  --contact-sheet <workspace>/evidence/contact-sheet.png \
  --review-notes <workspace>/evidence/review-notes.json
```

The workspace needs `book.yaml`, `authoring/record.json` and the `intake/`
manifest/pages copied from this example. The PDF is a rendered artifact, not a
source: edit `book.yaml` and rebuild.

No absolute private or workspace paths are recorded in this example.
