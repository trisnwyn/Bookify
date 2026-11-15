# OCR engine setup (system Tesseract)

Capability setup for Bookify v2 **intake only**. Nothing here is read by
`bookify build` or `bookify verify`; the OCR-free build boundary is unchanged.

**Release policy:** the release engine is the **system Tesseract package**, like
Poppler. The copy at `tools/ocr/tesseract` and the vendored data at
`vendor/ocr/tessdata/` are **development and test artefacts only** and must
never appear in the public bundle.

## Supported install (release)

```sh
# Fedora
sudo dnf install tesseract tesseract-langpack-eng
# only when Vietnamese OCR is enabled:
sudo dnf install tesseract-langpack-vie
```

The system paths are `/usr/bin/tesseract` and
`/usr/share/tesseract/tessdata/`. The language data is **not** vendored for
release; it comes from the distribution.

Version note: the lock pins Tesseract **5.5.4** with
`libtesseract.so.5.5.4` and Leptonica **1.87.0**, measured on this host on
2026-11-14 (`tesseract-5.5.4-1.fc44`, `tesseract-libs-5.5.4-1.fc44`,
`tesseract-langpack-eng-4.1.0-12.fc44`, `leptonica-1.87.0-4.fc44`;
`rpm -V` exits 0 for all four). The pin check refuses a mixed set: CLI,
library, Leptonica and data are re-pinned together. Do not mix a newer CLI with
an older library.

Measured pins:

| Component | Version | Path | sha256 |
| --- | --- | --- | --- |
| Tesseract CLI | 5.5.4 | `/usr/bin/tesseract` (53,336 B) | `2e54bf61c56a3ca1ac11758a7d9764f52333b5777a74272b4e083b016cefa74a` |
| libtesseract | 5.5.4 | `/usr/lib64/libtesseract.so.5.5.4` | `7cc5ff7e31dcdc612f963792e5ad57ac24af5a2c4d51bacc912530dd64f537fb` |
| Leptonica | 1.87.0 | `/usr/lib64/libleptonica.so.6.0.0` | `27f70f645a88e57cc5be893913933c8bd3a92de934093f5d8d5f82ccf5fb6c63` |
| `eng.traineddata` | 4.1.0 | `/usr/share/tesseract/tessdata/eng.traineddata` (4,113,088 B) | `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2` |

`vie.traineddata` is not installed on this host; `eng+vie` therefore fails with
`OCR_DATA_MISSING` instead of silently falling back. Install
`tesseract-langpack-vie` and re-measure before enabling it.

## Engine resolution in the harness

`tools/ocr/ocr_harness.py` resolves the CLI in this order:

1. `--tesseract <path>` (explicit; `--engine` is a compatibility alias)
2. `$BOOKIFY_TESSERACT`
3. `tesseract` on `PATH`
4. `tools/ocr/tesseract` — **development only**, and only when
   `BOOKIFY_OCR_ALLOW_DEV=1`

If none is available, the harness exits 2 with a named setup error:

```
ERROR INPUT_INVALID OCR_ENGINE_MISSING: no Tesseract CLI found. Release uses
the system Tesseract package. Fedora: sudo dnf install tesseract
tesseract-langpack-eng [tesseract-langpack-vie]. ... The OCR harness is
intake-only: bookify build and bookify verify never need OCR.
```

There is no silent development fallback. The dev copy requires the explicit
`BOOKIFY_OCR_ALLOW_DEV=1` and the JSON records
`engine.source: "development-copy"` and `engine.developmentOnly: true`.
`--require-system` refuses the dev copy even when the env gate is set, so a
release check can assert the system engine.

Tessdata resolution: `--tessdata` if given, otherwise the system directory
(`/usr/share/tesseract/tessdata`, with `/usr/share/tessdata` and
`/usr/local/share/tessdata` as fallbacks); when the development engine is used,
`vendor/ocr/tessdata` is the default.

## Development copy (never shipped)

| Artefact | Version | Path (git-ignored) | sha256 |
| --- | --- | --- | --- |
| Tesseract CLI | 5.5.4 (`5.5.4-1.fc44`) | `tools/ocr/tesseract` | `2e54bf61c56a3ca1ac11758a7d9764f52333b5777a74272b4e083b016cefa74a` |
| `eng.traineddata` | 4.1.0 | `vendor/ocr/tessdata/eng.traineddata` | `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2` |
| `vie.traineddata` | 4.1.0 | `vendor/ocr/tessdata/vie.traineddata` | `79df64caf7bcfb2a27df5042ecb6121e196eada34da774956995747636d5bfa1` |

System dependencies (not redistributed, pinned by hash): libtesseract 5.5.4
`7cc5ff7e…`, Leptonica 1.87.0 `27f70f64…`, Poppler 26.01.0.

`tools/ocr/.gitignore` ignores `/tesseract`; `vendor/ocr/.gitignore` ignores
`/tessdata/`.

**Provenance.** The development CLI is now a **byte copy of the installed
Fedora CLI** (`cmp` against `/usr/bin/tesseract` is clean), so a development run
and a release run measure the same engine binary; only the recorded `source`,
`developmentOnly` and pin differ. It is git-ignored and excluded from the public
bundle. Its `eng` data is the same bytes as the system langpack; `vie` is the
signed Fedora langpack data, kept because the system package for `vie` is not
installed here.

Until 2026-11-14 the copy was a rootless extraction of the **unsigned** Koji
`tesseract-5.5.3-2.fc44` RPM (`1462dc4b…`). That history is kept in the lock
fragment's `provenance.historicalDevelopmentCopy` and in
`.opencode/bookify-v2-ocr-capability.md` §0/§11; it is superseded by the signed
5.5.4 package.

### Public bundle exclusion (for the packaging track)

The bundle must exclude `tools/ocr/tesseract`, any `tools/ocr/tesseract*`
binary, `vendor/ocr/tessdata/**` and any `*.traineddata`. Keep
`tools/ocr/ocr_harness.py`, `tools/ocr/ocr.lock.fragment.json`,
`tools/ocr/README.md`, `tools/ocr/LICENSE`, `tools/ocr/.gitignore`, and the
public fixture `fixtures/ocr-capability/**` (except its `build/`). The exact
assertion text for the integrator is in
`.opencode/bookify-v2-ocr-capability.md` §11.4.

## Runtime contract

- System release: `--tessdata-dir /usr/share/tesseract/tessdata` (and
  `TESSDATA_PREFIX` to the same directory); dev: the vendored directory.
- `OMP_THREAD_LIMIT=1`.
- TSV is produced with `-c tessedit_create_tsv=1`; no `configs/` directory is
  needed and no config file is read.
- No user words, patterns, plugins, or `~/.tesseract` state. `HOME` and
  `TMPDIR` point at a scratch directory.
- The CLI is dynamically linked to system `libtesseract.so.5.5` and
  `libleptonica.so.6`; a mismatch with the lock is `INPUT_INVALID` before any
  page is written.
- The CLI links `libcurl`, but OCR makes no network call. Offline execution is
  enforced with `bwrap --unshare-net` and verified by a failed connection and a
  failed DNS lookup inside the namespace.

Sanity check (release, measured 2026-11-14):

```sh
tesseract --version
# tesseract 5.5.4
#  leptonica-1.87.0
OMP_THREAD_LIMIT=1 tesseract \
  --tessdata-dir /usr/share/tesseract/tessdata --list-langs
# eng
# vie   (only when tesseract-langpack-vie is installed)
```

Development copy:

```sh
BOOKIFY_OCR_ALLOW_DEV=1 tools/ocr/tesseract --version
```

### Verified end to end

The system engine has now been measured through the product intake path, not
only the harness: `bookify intake --ocr-require-system` on the public F1 fixture
in an external workspace produced `engine.version: "5.5.4"`,
`engine.source: "path"`, `developmentOnly: false`, library
`7cc5ff7e…`, data `location: "system"`, pin `ff92b6ea…`, statuses
`applied: 2 / below_threshold: 1 / not_required: 1`, and a byte-identical
manifest on every repeat run. Details and comparisons are in
`.opencode/bookify-v2-system-ocr.md`.

## Harness

`tools/ocr/ocr_harness.py` is a standalone, stdlib-only capability probe. It is
not imported by the product. It renders one PDF page (or one `pdftohtml` image
region) at 300 and 450 dpi with `pdftoppm`, OCRs both, and emits deterministic
JSON with per-line confidence and cross-scale agreement.

Release engine (system package):

```sh
python3 tools/ocr/ocr_harness.py --pdf fixtures/ocr-capability/fixture.pdf --page 1
```

Development copy, explicitly:

```sh
BOOKIFY_OCR_ALLOW_DEV=1 python3 tools/ocr/ocr_harness.py \
  --pdf fixtures/ocr-capability/fixture.pdf --page 1 \
  --tesseract tools/ocr/tesseract
```

Other useful runs:

```sh
python3 tools/ocr/ocr_harness.py --pdf fixtures/ocr-capability/fixture.pdf --page 1 --regions
python3 tools/ocr/ocr_harness.py --pdf fixtures/ocr-capability/fixture.pdf --page 2 --sandbox
python3 tools/ocr/ocr_harness.py --pdf fixtures/ocr-capability/fixture.pdf --page 1 --require-system
```

`--sandbox` writes only to stdout unless `--out` is given; because the namespace
mounts a fresh `/tmp`, `--out` must live outside `/tmp` (the repository
`build/` directory is the documented location).

Exit codes: `0` success, `2` `INPUT_INVALID`/`SOURCE_UNREADABLE`, `3`
`BUILD_FAILED`. Errors print `ERROR <CODE> <message>` to stderr and nothing to
stdout. Setup failures are named `OCR_ENGINE_MISSING` or `OCR_DATA_MISSING`;
pin mismatches are `OCR_PIN_MISMATCH`.

The JSON shape, bands, failure modes and determinism boundary are documented in
`.opencode/bookify-v2-ocr-capability.md` §6 and §11.

## Defaults and measured policy

These are deliberate configuration defaults, not preferences:

- **Languages:** `eng` only. `vie` is opt-in. Vietnamese OCR produced
  tone-mark errors and measured cross-scale agreement **0.8429** (below the
  adequate band); do not make it default until calibrated.
- **Agreement is corroboration, not correctness.** Ruled tables at PSM 6
  produced agreement **1.000** on shared garbage (mean confidence 37.38). Keep
  confidence, per-line eligibility and digit cross-checks.
- **Region PSM:** 6 by default, but 4 for ruled tables. PSM 6 assumes one
  uniform block; calibrate per region shape.
- **Resolution:** 300/450 dpi. 96 dpi passed on the fixture and 84 dpi failed;
  the gate is agreement, not a DPI constant.
- **Time budget:** measured dual-pass **11.65 s/page** end-to-end, so 200 whole
  pages is **~39 min**, not 30; 200 regions is **~13 min**. Revise the budget
  rather than dropping the second pass.

## Rollback / uninstall

Release is a normal package install:

```sh
sudo dnf remove tesseract tesseract-langpack-eng tesseract-langpack-vie
```

Development artefacts are local and git-ignored:

```sh
rm -f tools/ocr/tesseract
rm -rf vendor/ocr/tessdata
```

Remove the whole development tree only if the harness, lock and documentation
are no longer wanted (`rm -rf tools/ocr vendor/ocr`). No service, daemon, PATH
entry, environment file, or user config is installed.

## Licence

Tesseract and the `tessdata` language data are **Apache-2.0**;
`tools/ocr/LICENSE` is the licence text from the RPM. Leptonica is
BSD-2-Clause, a system dependency, not redistributed. `LICENCES.md` records
both rows.
