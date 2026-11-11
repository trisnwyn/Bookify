# SPEC-source-intake

Module id: `source-intake` · depends on: `build-toolchain` · build step 6 · status: approved 2026-11-10.

## Objective

Turn supplied PDFs and slides into exact, addressable evidence without interpreting them. Every extracted unit must point back to a file, a page and a hash, so later authoring can cite it and re-check it. Deterministic: the same input produces the same manifest, byte for byte, with no model and no network.

## Tech stack

Poppler binaries verified present: `pdfinfo`, `pdftotext -layout`, `pdfimages -list`, `pdfimages -png`, `pdfdetach`, `pdftoppm`. Pillow 12.3.0 verifies extracted rasters. No OCR engine is installed, and this module does not pretend to read text from images.

## Commands (proposed, not implemented)

```bash
uv run bookify intake --source fixtures/decks --out build/intake --changed-only
uv run bookify intake --source fixtures/decks/one-deck.pdf --out build/intake --changed-only --json
```

## Project structure

```
src/bookify/intake/
  extract.py                 # pdftotext / pdfimages wrappers, no shell string building
  manifest.py                # stable JSON writer, sorted keys, no timestamps
  changes.py                 # hash comparison, per-page diff
  images.py                  # naming, dedupe, format checks
build/intake/<sourceId>/
  manifest.json              # pages, text hashes, image inventory, source sha256
  text/page-012.txt
  images/page-012-img-01.png
  runlog.jsonl               # timestamps and durations live here only
```

## Manifest contract (v1)

```json
{
  "schemaVersion": "1.0",
  "sourceId": "example-source",
  "sourcePath": "fixtures/sources/example-source.pdf",
  "sourceSha256": "13e1ca50...",
  "pageCount": 36,
  "pages": [
    { "page": 12, "textSha256": "...", "charCount": 480, "isImageOnly": false,
      "images": [{ "index": 1, "file": "images/page-012-img-01.png", "width": 1028, "height": 938 }] }
  ]
}
```

Rules: `sourceId` is stable and kebab-case; `page` is 1-based and identical to the printed slide/page number only when the file has no cover offset (record `pageOffset` when it does); `isImageOnly` is true only when extraction yields no characters; `text/page-NNN.txt` is the raw `-layout` output, never rewritten.

## Change detection

1. Hash the source file. If it equals the stored `sourceSha256`, skip the source entirely (`changed-only`).
2. Otherwise extract to a temporary directory, then diff per page: unchanged pages keep their existing text/image files and hashes.
3. Emit `changes.json`: `{ addedPages, removedPages, changedPages, addedImages, removedImages }`.
4. Replace the manifest atomically; never leave a partially written one.

No timestamps or absolute paths in `manifest.json`, so a rerun with unchanged inputs rewrites an identical file.

## Code style

```python
def extract_page_text(pdf: Path, page: int) -> str:
    """Return layout-preserving text for one page; empty string if image-only."""
    result = run(["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(pdf), "-"])
    return result.stdout.replace("\r\n", "\n")
```

Rules: subprocess arguments are lists, never interpolated strings; paths are resolved once; every failure becomes `SOURCE_UNREADABLE` with the source id and page.

## Testing strategy

`pytest` under `tests/intake/`:

- Golden manifest for a small fixture PDF; second run is byte-identical.
- Unchanged source with `--changed-only` performs no extraction and writes no new files.
- A modified page changes only that page's hash and files; `changes.json` lists exactly that page.
- Image-only page: `isImageOnly: true`, empty text, no invented text.
- Image count and dimensions match `pdfimages -list` for the fixture.
- No network: guard active; no model import in the module.

## Boundaries

- Always: keep raw extraction separate from interpretation; keep anchors stable; dedupe images by content hash; write atomically.
- Ask first: supporting a new input format (docx, pptx), applying OCR, changing the manifest shape.
- Never: summarise, translate or "fix" extracted text; invent text for an image-only page; store absolute paths; include timestamps in the manifest; call a model.

## Success criteria

1. Running twice on unchanged inputs produces identical manifests and zero extra work.
2. Every page in the fixture has an addressable anchor and a text hash.
3. Image-only pages are flagged and contain no fabricated text.
4. A one-page change produces exactly one changed page in `changes.json`.
5. Extraction performs no network or model access.
