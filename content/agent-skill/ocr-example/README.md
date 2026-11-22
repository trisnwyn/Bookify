# OCR intake example (F1)

A public-safe, end-to-end OCR example: an image-borne trial balance on a prose
page, an image-only cash-receipts page, and a deliberately degraded page that
stays unresolved. Every input is the repository's synthetic fixture; no private
or third-party content is present.

The canonical evidence is now a **system-engine run** (`/usr/bin/tesseract`
5.5.4, `--ocr-require-system`, no `BOOKIFY_*` override). The earlier
development-copy run is kept as history, not as the reference.

## Contents

| Path | What |
| --- | --- |
| `fixture.pdf` | The synthetic four-page source, copied from `fixtures/ocr-capability/fixture.pdf` (SHA-256 `c3c09d6f57b57f04dd3eefc6724a5b51dcb8466fbaa42ff0ca6333941ba3481d`). |
| `intake/` | Stable intake evidence from the system engine: `manifest.json`, page text, extracted images, OCR TSV/TXT, retained crops and `runlog.jsonl`. |
| `historical/development-copy-5.5.3/manifest.json` | The 2026-11-13 development-copy manifest (Tesseract 5.5.3, pin `aeb95412…`), kept only so the earlier claim can be checked. Its TSV/TXT/raster files are not duplicated. |
| `book.yaml` | The authored source-faithful manuscript (4 source pages, 5 PDF pages). It also exercises D1/D4/D5/D6: an inline definition, a full-measure diagram plate with one merged caption, and measured h2/h3/deck samples. Unchanged by the engine re-run: every measured value it cites is identical at 5.5.4. |
| `authoring/record.json` | Durable mode, coverage, OCR basis, derivations, the glossary entry and digit cross-checks. Unchanged. |
| `evidence/book.pdf` | The verified PDF, 5 A4 pages. |
| `evidence/book-2.pdf` | The second offline build, byte-identical, referenced as `previousPdf`. |
| `evidence/build-report.json` | Offline build report with `machineRead[]`, plates, definitions, captions and the **measured** OCR boundary record. |
| `evidence/verify.json` | Verify gate result (`pass`), every path workspace-relative so the shipped files replay. |
| `evidence/review-notes.json` | Decisions for every warning id (the two digit-only machine-read tables). |
| `evidence/contact-sheet.png`, `evidence/pages/` | Rendered inspection evidence. |

## Recorded hashes

| Artefact | SHA-256 |
| --- | --- |
| `fixture.pdf` | `c3c09d6f57b57f04dd3eefc6724a5b51dcb8466fbaa42ff0ca6333941ba3481d` |
| `intake/manifest.json` (system 5.5.4) | `92e148895d6991df1cb95c221306459f6a0e5e3b6f86c1574ddf6f73a9bb3ba0` |
| `book.yaml` | `e88eefc8b6db0f8f3ec310db1c374181ee14d1dcc658e37afd9021b43b987fb2` |
| `authoring/record.json` | `f218a2562bd6dbb7d2bc217d17cb5f4234bd21503f884b1519a969f01e0cf223` |
| OCR pin (`manifest.ocr.pinSha256`), system | `ff92b6ea08c267805f3f6c4887be31a243de194147fda67a7ac788f9437488b9` |
| `historical/development-copy-5.5.3/manifest.json` | `0d50f18df9f8489e1fb776601b73ed45cc9647dfc2a42a3babc796bd2367d477` |
| OCR pin, development copy 5.5.3 | `aeb95412add09e5eb7f7c3779e79e937162d97de6b9ed63e14e9a096fa9403be` |
| `evidence/book.pdf` and `evidence/book-2.pdf` | `ca9d6e4f6b6ac36f8a9936bdf58096b9db2ee6154c2152f0583fe82c74edcfac` |
| `evidence/build-report.json` | `c2e35b8ee15045d13fc77c517b86ee7888e4a3e7af0be795a9125963b9ef5eca` |
| `evidence/verify.json` | `a3e158a931b29f0b72f5998c64b95ce3ef22febbbd780838fc567624c0090a50` |
| `evidence/contact-sheet.png` | `99fab2b54e3057d4cbf782df182edd04c410b7a1c3da9ed93b1a267e57eef16e` |
| `evidence/measurements.json` | `d929a475bbc0d9dcf92e5cbdc4fb94cad5fadefbc772b31d9f61d512a3ed4ba1` |

The manifest is byte-identical across four independent system-engine runs
(`--ocr-require-system`); only `ocr/runlog.jsonl` differs, because it records
timings and the run timestamp.

## Measurement

Intake result: 4 pages, 3 image placements, statuses `applied: 2`,
`below_threshold: 1`, `not_required: 1`.

- Page 1, `scope: images`, `applied`: agreement 1.0, mean confidence 95.02.
- Page 2, `scope: page`, `applied`: agreement 1.0, mean confidence 95.34.
- Page 3, `scope: page`, `below_threshold`: agreement 0.6667, mean confidence
  43.25, low-confidence share 0.76, zero eligible lines. No text or number is
  used from it.
- Page 4 has a Vietnamese text layer and is `not_required` for this English
  book; it is excluded in the record.

The two reconstructed tables are `confidence: inferred` with
`machineRead.method: "ocr-table-v1"` and the mandatory note
`Reconstructed from an image by OCR`. Page 1's digit cross-check is a second
450 dpi read; page 2's is the table's own arithmetic
(`2,450.00 + 1,980.50 + 3,215.75 + 875.00 + 4,120.25 + 2,640.00 = 15,281.50`).

The page-1 image's `Owner's capital` line measured mean confidence 77.58
(second pass 80.34) and is **below the eligible line band**. It is therefore
omitted from the reconstructed table, and an explicit unresolved note on page 3
records the omission and says the table is not a complete balance. No value is
guessed or rescued by the second read.

### 5.5.3 development copy vs 5.5.4 system engine

| Field | 5.5.3 dev copy | 5.5.4 system | Same? |
| --- | --- | --- | --- |
| `engine.source` / `developmentOnly` | `environment` / `true` | `path` / `false` | expected change |
| `engine.version` / `library.version` | 5.5.3 | 5.5.4 | expected change |
| `engine.binarySha256` | `1462dc4b…` | `2e54bf61c56a3ca1ac11758a7d9764f52333b5777a74272b4e083b016cefa74a` | expected change |
| library SHA-256 | `a792384a…` | `7cc5ff7e31dcdc612f963792e5ad57ac24af5a2c4d51bacc912530dd64f537fb` | expected change |
| data `location` | `vendored` | `system` | expected change |
| pin | `aeb95412…` | `ff92b6ea…` | expected change |
| page statuses | applied 2 / below_threshold 1 / not_required 1 | identical | yes |
| page/region confidences and agreements | 95.02 / 95.34 / 43.25; 1.0 / 1.0 / 0.6667 | identical | yes |
| every line confidence, band and text | — | identical | yes |
| `Owner's capital` line | 77.58 (2nd 80.34), ineligible | 77.58 (2nd 80.34), ineligible | yes |
| page 3 eligible lines | 0 | 0 | yes |
| TSV bytes | — | pages 2 and 3 differ in one line-box row (`top` 458→462, `bottom` 481→477 at 300 dpi); page 1 identical | **no** |
| text projections (`.txt`) | — | identical on all three pages | yes |

The only measurement difference is a line bounding box: 5.5.4 reports the
level-3 line box of one row on pages 2 and 3 about 1 pt taller at the top and
shorter at the bottom. No word box, text, confidence or band changed, so no
authoring decision changed. This is why the manifest keeps the same statuses and
the book needed no edit.

`evidence/build-report.json` records a measured boundary —
`ocr {invoked: false, engineInvocations: 0, vendorRead: false, measured: true,
probe: "subprocess.run+io.open"}` — so the build/verify OCR-free claim is a
probe, not a constant, even though a working system `tesseract` was installed
for the intake step. The diagram is labelled synthetic and captioned; it is a
presentation visual, not a chart built from OCR numbers.

## Reproduce

All commands are relative to a workspace containing this directory's files. The
build and verify evidence paths are workspace-relative. `intake/ocr/runlog.jsonl`
is a faithful record of the original run and therefore contains the absolute
external-workspace path used for that run; it contains no private content and no
`/tmp` path.

```sh
# 1. Intake (OCR is on by default). Release path: the system Tesseract package,
#    resolved from PATH; --ocr-require-system refuses the development copy.
uv run bookify intake --source fixture.pdf --out intake \
  --ocr-require-system --keep-ocr-raster --json

# 2. Two offline builds from the same manuscript.
uv run bookify build --workspace . --manuscript book.yaml \
  --out evidence/book.pdf --offline --build-dir build/book --json
uv run bookify build --workspace . --manuscript book.yaml \
  --out evidence/book-2.pdf --offline --build-dir build/book2 --json

# 3. Verify with the recorded review decisions (paths stay workspace-relative).
uv run bookify verify --workspace . --pdf evidence/book.pdf \
  --manuscript book.yaml --previous-pdf evidence/book-2.pdf \
  --build-report evidence/build-report.json \
  --contact-sheet evidence/contact-sheet.png \
  --review-notes evidence/review-notes.json \
  --reviewed-by agent-ocr-f1-system --reviewed-at 2026-11-14T11:05:40Z \
  --report build/verify.json --json
```

Expected: `gate: pass`; the two builds are byte-identical. The intake manifest
records `engine.source: "path"` and `developmentOnly: false`; with
`$BOOKIFY_TESSERACT` set it records `"environment"` instead. A missing system
package fails with `OCR_ENGINE_MISSING`, exit 2, before a manifest is written.

## Honest limits of this evidence

- **System engine verified on one host.** Tesseract 5.5.4, libtesseract 5.5.4
  and Leptonica 1.87.0 from Fedora 44 packages were measured here, with
  `rpm -V` clean. A different package build, CPU or Poppler is a new pin.
- **Development copy is development-only.** `tools/ocr/tesseract` is a byte copy
  of the same installed CLI so the source test suite can run without a system
  package; it is git-ignored and excluded from the public bundle. It is never
  the reference evidence.
- **Cross-host determinism is unproven.** Same host and same pins produce
  byte-identical manifests, TSVs and TXT projections; that was measured across
  four runs here, not across hosts.
- **Agreement is corroboration, not correctness.** Two passes can agree on the
  same misread; ruled tables at PSM 6 are the measured example.
- **`vie` is opt-in.** Tone-mark errors measured agreement 0.8429; `eng` is the
  default. The `vie` package is not installed on this host, so `eng+vie` fails
  with `OCR_DATA_MISSING` rather than silently using another language.
- **No CJK OCR.** An image-only CJK page cannot be classified before OCR and is
  a recorded limitation.
- **Region PSM is a default, not a per-shape guarantee.** The fixture uses
  horizontal rules only; ruled tables may need PSM 4.
- **OCR text is evidence, never truth.** Adequate text is `inferred`; digits
  need a recorded cross-check; no OCR number becomes a chart value.
- **Page-4 h1 overlap: fixed (not OCR).** The h1 "A page that is only an image"
  used to be struck through by its first body line: the heading's descender ink
  reached 6.00 pt below the baseline while `block(below:)` reserved only 4.50 pt,
  so the next line's ascenders rose 2.41 pt into the descender ink (the raster
  ink bands touched, with no white row; the font-metric boxes overlapped by
  11.11 pt). The theme now derives each heading's below gap from the pinned
  face's metrics (descender ink + the next line's ascender overhang + 0.5 pt),
  and `verify` measures the rendered white row below every heading. Page 4 now
  keeps a measured 0.48 pt white row (2 raster rows at 300 dpi; 0.54 pt at
  1200 dpi) and the h1→body baseline delta moved from 26.95 pt to 29.90 pt. Only
  this book's PDF changed; `specimen`, `catalogue`, the trial and both other
  trials stay byte-identical. The `book.yaml`, intake manifest and record are
  unchanged. The old PDF `4d15590d…` is superseded by `18517b02…`.
- **No human sign-off.** The review is agent inspection (`review: manual`), not
  a human acceptance of the rendered pages.
