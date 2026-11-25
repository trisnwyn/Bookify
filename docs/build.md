# Build and verification details

## What a build does

1. Loads and validates the manuscript (`schemas/manuscript.schema.json` + semantic rules).
2. Loads `toolchain.lock.json` and runs the doctor checks before any rendering: a tampered Typst binary, package tree or font fails with `FONT_MISSING`/`BUILD_FAILED`, and the locked binary path is the one compiled.
3. Renders charts to SVG and diagrams to CeTZ source from stored data.
4. Normalizes the document: section and figure numbering, resolved `{ref:…}` labels, captions, credits, notes.
5. Writes `build/<name>/book.json` and compiles `typst/templates/book.typ` with:
   - `--ignore-system-fonts --ignore-embedded-fonts --font-path assets/fonts`
   - `--package-path vendor/typst --package-cache-path .cache/empty-pkg`
   - `--creation-timestamp 1750000000`
   - `--root .` and `--input data=/build/<name>/book.json`
6. Compiles with a 180 s timeout, inside `bwrap --unshare-net`, so no network is available. `--offline` is required; omitting it fails.
7. Parses the PDF for section pages, numbered labels and illustration placements; writes `build-report.json` including `offline`, `networkAttempts` and the PDF/manuscript hashes.
8. If two illustrations land on one page, recompiles with the later one pushed to the next page (max three attempts, then `ILLUSTRATION_LIMIT`). A placement whose printed label cannot be found fails the build instead of being silently ignored.

The build directory must be inside the repository: Typst resolves `/build/...` asset paths against the project root. A clear `BUILD_FAILED` is raised otherwise.

## Equations

Equation `typst` is math source, not markup. It is parsed with `eval(source, mode: "math")`; validation rejects `$` (math delimiter), `#` (code escape) and `\` (markup escape) with `SCHEMA_INVALID`, so a manuscript can never execute Typst code through an equation.

## Reproducibility

- Layout facts are deterministic: two builds share page count, page text, placement map and numbering. With the pinned creation timestamp, the PDFs are byte-identical in the specimen.
- Byte identity is not required; a timestamp-only difference passes determinism and is reported as `bytesEqual: false`.
- Caches under `build/` are disposable. Deleting them changes neither validation nor output.

## Verify checks

| Check | Reads | Fails with |
| --- | --- | --- |
| offline | build report, bound to the PDF and manuscript hashes/versions | `NETWORK_DENIED` |
| determinism | current + previous PDF | `BUILD_FAILED` |
| glyphs | `pdffonts`, every rendered string vs font cmaps (including equations) | `GLYPH_MISSING` |
| docmeta | `pdfinfo` + `pdfinfo -meta`: `/Title`, `/Author`, language and any claimed standard against the manuscript | `BUILD_FAILED` |
| cover | manuscript metadata and rendered ink: title ≤ 3 lines, no folio, no chromatic pixels, ink inside the 60 pt block | `VERIFY_FAILED` |
| definitions | page text: inline `Term: definition` at body size | `VERIFY_FAILED` |
| text | `pdftotext` probes (title, scripts, labels, credit, notes) | `BUILD_FAILED` |
| pages | `pdfinfo`, rendered ink (per-page render, 10+ page safe) | `BUILD_FAILED` |
| captions | page text lines: one centred caption per visual, credit left and separate | `VERIFY_FAILED` |
| illustration-limit | page text: `Photograph N.` | `ILLUSTRATION_LIMIT` |
| rights | records + page text | `RIGHTS_INCOMPLETE` |
| xrefs | contents lines, numbered labels, `§` tokens | `XREF_MISSING` |
| rhythm | rendered lines at 300 dpi: line pitch and the white band below every heading | `VERIFY_FAILED` |
| plates | chapter openers and the measured width of each placed visual | `VERIFY_FAILED` |
| readability | words per page, tables per page and paragraph length, with bands | warning only |
| machine_read | manuscript `machineRead` blocks: region/method/confidence, never `verified`, table note, digit cross-check, no OCR chart | `SCHEMA_INVALID` |
| ocr_free_build | build report OCR boundary record | `BUILD_FAILED` |
| review | contact sheet + reviewer | `VERIFY_FAILED` |

Exit code 0 only when the gate passes; 3 when it fails.

## Intake notes

- `pdfimages -list` rows include soft masks. Extraction pairs the files positionally and stores only `image` rows; masks are not counted as illustrations.
- Manifests contain no timestamps and no absolute paths, so an unchanged source reproduces the same manifest byte for byte.
- `--changed-only` with an unchanged source extracts nothing and writes an empty `changes.json`.
- OCR runs only here. Pages with fewer than 40 non-space text characters are OCR'd whole at 300/450 dpi; otherwise image placements of at least 12,000 pt² are cropped and OCR'd. A page's `ocr.status` is `applied`, `uncertain`, `below_threshold`, `not_required`, `skipped` or `failed`; only adequate/uncertain lines are usable, digits need a recorded cross-check, and a below-threshold page stays unresolved with the measured reason.
- `--ocr-lang` accepts `eng` (default) or `eng+vie` (opt-in); `jpn` is refused. The release engine is the system Tesseract package.
- Intake is sandboxed by default: `pdfinfo`, `pdftotext`, `pdfimages`, `pdftohtml`, `pdftoppm` and Tesseract run under `bwrap --unshare-net` with only the intake output writable, each with a per-command timeout. `--allow-unsandboxed` is the explicit escape hatch for a trusted local source; `ocr/runlog.jsonl` records the actual sandbox state (extraction and OCR phases).
- A pin change (engine, data, raster, PSM/OEM/threads or trigger) invalidates every page OCR record and appears in `changes.json` as `ocrChangedPages`. An unchanged source and pin skips all work.
- A one-page edit produces exactly one entry in `changes.json`; unchanged page files keep their content.

## Authoring notes

- `author plan` compares source page hashes with the index written by the last successful `author apply`. Each work item carries `textSha256`, `promptVersion`, `schemaVersion`, `inputHash` and `cached`. A prompt or schema version change makes earlier pages work again. It never calls a model.
- `author apply` requires every draft page to echo the plan's `textSha256` and `inputHash`; a stale draft is rejected with `INPUT_INVALID` instead of writing old content. The page record stores the model and versions used.
- `author apply` validates the serialized manuscript in a uniquely named temporary file and replaces it atomically with `os.replace`, so a failed validation or write leaves the original bytes untouched.
- Reapplying an unchanged draft is skipped (`already applied`) and reports no model calls.
- Unreadable pages become one `unresolved` block with a note; draft blocks on an unreadable page are rejected. A manuscript block marked `confidence: unreadable` may not carry prose, diagram, table, list, equation or illustration payload.
- Deleting `build/cache/` does not invalidate the manuscript; it only makes the next plan treat pages as new.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `build requires --offline` | publishing without the flag | add `--offline` |
| `bwrap is required for an offline intake run` | no bubblewrap, or the default guard cannot start | install bubblewrap, or pass `--allow-unsandboxed` for a trusted local source |
| `draft for page N was authored from different content` | old draft or plan after a source/prompt change | run `author plan` again and re-author the page with the new `textSha256`/`inputHash` |
| `build directory must live inside the project root` | output build dir outside repo | use `build/<name>` |
| contents folio mismatch after a cover with the same title | verifier ignored cover and contents pages | fixed; rerun verify |
| CJK subtitle names show `ExtraLight` | variable font base instance name | visual weight is correct; cosmetic |
| intake reports image count mismatch | PDF uses soft masks | fixed by pairing all rows; reinstall no newer binary |
| `GLYPH_MISSING` | character not in the declared font chain | add a verified face or change the text |

## Pins

`toolchain.lock.json` records Typst binary and archive hashes, CeTZ/oxifmt tree hashes, nine font files, Python package versions and the `ocr` identity (engine/data/library/Leptonica hashes, raster, trigger and options). `toolchain doctor` verifies the build stack locally; OCR is intake-only, so a missing OCR engine does not fail a build. Nothing is downloaded at build time.
