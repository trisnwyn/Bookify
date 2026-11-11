# Specimen report — synthetic public specimen

Built 2026-11-11 from `content/specimen.yaml`. This is the **public synthetic**
specimen; it replaces the earlier lecture-derived specimen in the public tree.
The original manuscript and its report are retained only in the ignored local
backup and in the private local history.

## Build

```bash
uv run bookify build --manuscript content/specimen.yaml --out build/public-specimen.pdf \
  --offline --build-dir build/public-specimen --json
uv run bookify build --manuscript content/specimen.yaml \
  --out build/public-specimen-2.pdf --offline --build-dir build/public-specimen-2 --json
```

Both builds: **6 A4 pages**, byte-identical, SHA-256
`3adf5c37b268f8b57c7decb860fd629412692e20b58a7a31958f0b039be62776`.
Offline, no network, no model calls.

## Page map

| Page | Content |
| --- | --- |
| 1 | Cover: Example Institute, *Reading a Sample*, synthetic subtitle |
| 2 | Contents with folios: *Reading a sample* 3, *Evidence and limits* 6 |
| 3 | Chapter opener, definition, Vietnamese and Japanese paragraphs, special characters, assessment, equation, Figure 1 |
| 4 | Figure 2 synthetic process diagram, Photograph 1 with caption and credit, list, worked example |
| 5 | Continuation of section 1: synthetic specimen notes |
| 6 | Section 2 opener, lead, synthetic context and limits, case, Table 1, quote, closing |

## Required elements

| Element | Where | Evidence |
| --- | --- | --- |
| Chapter opener / body | 3, 6 | kicker, h1, standfirst, prose presets |
| Vietnamese | 3 | `Tiếng Việt có đủ dấu` extracted intact |
| Japanese | 3 | `日本語の文章`; 91 Japanese characters covered |
| Special characters | 3 | `— – ‘and’ → ≤ ≥ ∑` |
| Equation | 3 | `x̄ = 1/n ∑ x_i`, STIX Two Math embedded |
| Grouped bars | 3 | Figure 1, synthetic values `72/64/58`, caption says synthetic |
| Synthetic process diagram | 4 | Figure 2, authored for the specimen, not traced |
| Sourced photograph | 4 | Photograph 1, public-domain record with URL/creator/licence/alt |
| Table | 6 | Table 1, three hairlines, caption |
| Cross-reference | 3, 6 | `§1`, `Figure 2`, `Table 1`, `Photograph 1` resolved |
| One illustration per page | 4 only | verifier reads printed labels from the PDF |

## Verify gate

`uv run bookify verify` returned `gate: pass`:

```text
offline              pass
determinism          pass (two byte-identical builds)
glyphs               pass (all faces embedded; 4,707 characters; 91 Japanese)
text                 pass (12 probes extracted intact)
pages                pass (6 A4 pages, none blank)
captions             pass (3 wrapped captions; max centre delta 0.784 pt)
illustration-limit   pass (one photograph, page 4)
rights               pass (1 complete credited record)
xrefs                pass (2 contents entries match pages)
review               manual (rendered pages inspected for this check)
```

## Difference from the previous specimen

- **Same:** 6 pages; section starts on pages 3 and 6; one photograph on page 4;
  the same block-type coverage (paragraph, definition, scripts, special
  characters, assessment, equation, chart, diagram, illustration, list, example,
  lead, case, table, quote, closing, cross-reference).
- **Changed:** title, subtitle, institution, course, all prose, chart caption,
  chart categories/series/values, diagram caption/node labels, table wording and
  quote. The chart is explicitly `verification: synthetic` with no source
  anchor; the diagram is labelled synthetic. The old specimen's lecture-derived
  chart and private source anchor are not present in the public tree.
- The previous manuscript is backed up under `.opencode/private-backup/`
  (ignored); the previous canonical PDF remains at `dist/specimen.pdf`. Both
  are local and unmodified.
- Human PDF sign-off is still pending; the inspection above is a preflight
  check, not an independent human review.
