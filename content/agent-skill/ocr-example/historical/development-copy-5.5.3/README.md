# Historical OCR evidence: development-copy run (Tesseract 5.5.3)

This folder keeps the manifest from the 2026-11-13 capability run, which used
the rootless development copy because this container had no system Tesseract CLI
at that time. It is history, not the reference evidence.

- Engine: `tools/ocr/tesseract` 5.5.3, libtesseract `a792384a…`
- `engine.source: "environment"`, `developmentOnly: true`
- Pin: `aeb95412add09e5eb7f7c3779e79e937162d97de6b9ed63e14e9a096fa9403be`
- Manifest SHA-256: `0d50f18df9f8489e1fb776601b73ed45cc9647dfc2a42a3babc796bd2367d477`

The canonical `../intake/` is the 2026-11-14 system-engine run
(`/usr/bin/tesseract` 5.5.4, `--ocr-require-system`, `developmentOnly: false`,
pin `ff92b6ea08c267805f3f6c4887be31a243de194147fda67a7ac788f9437488b9`).

The measured statuses, confidences, agreements and line texts are identical
between the two runs. Only the engine envelope, the pin, and one line bounding
box in the page-2 and page-3 TSVs differ; the TSV/TXT/raster files of the old
run are therefore not duplicated here.
