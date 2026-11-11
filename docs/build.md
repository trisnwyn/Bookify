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
| text | `pdftotext` probes (title, scripts, labels, credit, notes) | `BUILD_FAILED` |
| pages | `pdfinfo`, rendered ink (per-page render, 10+ page safe) | `BUILD_FAILED` |
| illustration-limit | page text: `Photograph N.` | `ILLUSTRATION_LIMIT` |
| rights | records + page text | `RIGHTS_INCOMPLETE` |
| xrefs | contents lines, numbered labels | `XREF_MISSING` |
| review | contact sheet + reviewer | `VERIFY_FAILED` |

Exit code 0 only when the gate passes; 3 when it fails.

## Intake notes

- `pdfimages -list` rows include soft masks. Extraction pairs the files positionally and stores only `image` rows; masks are not counted as illustrations.
- Manifests contain no timestamps and no absolute paths, so an unchanged source reproduces the same manifest byte for byte.
- `--changed-only` with an unchanged source extracts nothing and writes an empty `changes.json`.
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
| `draft for page N was authored from different content` | old draft or plan after a source/prompt change | run `author plan` again and re-author the page with the new `textSha256`/`inputHash` |
| `build directory must live inside the project root` | output build dir outside repo | use `build/<name>` |
| contents folio mismatch after a cover with the same title | verifier ignored cover and contents pages | fixed; rerun verify |
| CJK subtitle names show `ExtraLight` | variable font base instance name | visual weight is correct; cosmetic |
| intake reports image count mismatch | PDF uses soft masks | fixed by pairing all rows; reinstall no newer binary |
| `GLYPH_MISSING` | character not in the declared font chain | add a verified face or change the text |

## Pins

`toolchain.lock.json` records Typst binary and archive hashes, CeTZ/oxifmt tree hashes, nine font files and Python package versions. `toolchain doctor` verifies all of them locally; nothing is downloaded at build time.
