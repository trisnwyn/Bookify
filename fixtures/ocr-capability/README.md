# OCR capability fixture (synthetic)

A four-page A4 PDF proving the hard intake cases for Bookify v2 OCR. Every word,
number, rule and raster in it was authored for this repository. There is no
third-party text, no third-party image, no scan, and no private source. The only
third-party assets are the project's own Spectral font files, already recorded
in `LICENCES.md` under the SIL Open Font License 1.1.

## Pages

| Page | Content | Text layer | Purpose |
| --- | --- | --- | --- |
| 1 | Prose about trial balances, plus a raster image of a trial-balance table and a caption | Prose and caption only; no table text | The accounting-course case: substantive table trapped in an image on a page that also has prose |
| 2 | A full-width raster image of a cash-receipts journal, nothing else | Empty | Fully image-only table page; adequate OCR must make it extracted-with-uncertainty, not unresolved |
| 3 | The trial-balance image rendered at 45 dpi and embedded at full width | Empty | Degraded/illegible page that must remain unresolved under the confidence + agreement bands |
| 4 | A short Vietnamese paragraph | Vietnamese text | Proves `vie.traineddata` loads and reads Latin-script Vietnamese; not one of the three hard cases |

No CJK appears anywhere in the fixture.

The numbers are internally consistent but invented: the trial balance totals
65,485.50 on both sides, and the cash receipts total 15,281.50.

## Provenance and build

`source/trial-balance.typ` and `source/cash-receipts.typ` typeset the two table
images; `source/fixture.typ` places them and adds the prose and Vietnamese page.
`build_fixture.py` compiles the sources with the pinned Typst 0.15.1, rasterises
with Poppler 26.01.0, and writes `fixture.pdf`.

```sh
cd fixtures/ocr-capability
python3 build_fixture.py --check
```

`--check` builds the fixture twice and fails if the bytes differ. `SOURCE_DATE_EPOCH`
is fixed at `1767225600`, so the PDF is reproducible. Current hashes:

| Artefact | sha256 |
| --- | --- |
| `fixture.pdf` (214,787 B) | `c3c09d6f57b57f04dd3eefc6724a5b51dcb8466fbaa42ff0ca6333941ba3481d` |
| `build/trial-balance.png` (300 dpi) | `fbfac1e494022b196ae2313ffde836414b1fbd707d921f5e1ee79553dc28cb7b` |
| `build/cash-receipts.png` (300 dpi) | `b5ca7c4b013cfc3ac50e0a3b6a37113274e25cc4a3d3ca64e97aac1b53986a2e` |
| `build/trial-balance-45.png` (45 dpi) | `d08a776f270ab1dd44887cfe5a6c05241cc71cf1a7b57608cd61d75b2d634ad3` |

`build/` is regenerable and ignored by git; the PDF and sources are committed.

## Why no vertical table rules

The first draft used vertical rules. On the clean 300 dpi page they were read as
`|` and low-confidence garbage, and region OCR at PSM 6 concatenated the columns
(mean confidence 37). The fixture now uses horizontal rules only, so the clean
pages test OCR rather than a table-border artefact. Ruled-table behaviour is a
known limitation, recorded in the capability report; it is not hidden by the
fixture.

## Expected results with `tools/ocr/ocr_harness.py`

| Run | Expected |
| --- | --- |
| page 1, 300/450 dpi | `adequate`, agreement ≥ 0.98 |
| page 2, 300/450 dpi | `adequate`, agreement 1.0 |
| page 3, 300/450 dpi | `below_threshold`, mean confidence well under 80 |
| page 1 at 84 dpi vs 300 dpi | mean ≥ 90 and low-confidence share ≤ 0.05, but agreement < 0.90: confidence alone would pass, agreement rejects |
| page 1 `--regions` | one image region, bbox ≈ 57–539 × 223–483 pt, table rows recovered, page text layer has none of that text |
| page 4 `--lang eng+vie` | Vietnamese text is produced; cross-scale agreement is below 0.90, so the page is not adequate under the provisional bands |

The measured values and commands are in
`.opencode/bookify-v2-ocr-capability.md` §5.

## Rights

This fixture is original synthetic material, published for testing. It is not a
reproduction of the owner's accounting course or of any other source. It grants
no rights in any real document and carries no third-party content.
