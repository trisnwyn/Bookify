# SPEC-design-system

Module id: `design-system` · depends on: `build-toolchain` · build step 2 · status: approved 2026-11-10.

## Objective

Carry the quiet Spectral typography — generous spacing, restrained rules, hierarchy by size and weight — into a reusable token layer, and extend it with shared semantic accent tokens and reusable block presets. One theme file is the only place visual values live, so captions, credits, definitions, examples, cases and assessments cannot drift apart.

## Tech stack

Typst theme (`typst/theme.typ`) plus a machine-readable `assets/fonts/fonts.yaml`. Type baseline comes from the verified reference system (A4, 60 pt margins, Spectral 10.1/15.3 body, 25 pt chapter title, 0.6/0.4 hairlines). Accent colour is new and provisional.

## Commands (proposed, not implemented)

```bash
uv run bookify design check --manuscript content/specimen.yaml --json
uv run bookify build --manuscript content/specimen.yaml --out dist/specimen.pdf --offline
```

## Project structure

```
typst/theme.typ              # tokens: type scale, spacing, rules, accents, block presets
typst/blocks.typ             # definition / example / case / assessment / caption / credit
assets/fonts/fonts.yaml      # family, file, scripts covered, fallback order, licence
assets/fonts/LICENCES.md
src/bookify/design/
  tokens.py                  # token names and lookups for checks
  coverage.py                # script/glyph coverage against actual manuscript text
  lint.py                    # rejects literals outside theme.typ
```

## Token set (v1)

| Group | Tokens | Rule |
| --- | --- | --- |
| Type | `type.body`, `type.lead`, `type.h1`, `type.h2`, `type.h3`, `type.caption`, `type.small`, `type.credit`, `type.table`, `type.table_head`, `type.note`, `type.quote` | one serif family; sizes taken from the verified reference scale |
| Leading | `leading_extra.body`, `.lead`, `.caption`, `.table`, `.note`, `.small`, `.quote`, `.h1`, `.h2`, `.h3` | **Typst `par.leading` is extra beyond the font's natural line height, not a total.** Each value is derived from the intended total and the measured natural height (Spectral 0.660 em; Noto Serif CJK JP 0.729 em) |
| Space | `space.page_margin`, `space.before_heading`, `space.before_role`, `space.after_heading`, `space.before_standfirst`, `space.after_block`, `space.between_paragraphs`, `space.after_lead`, `space.after_figure`, `space.after_caption`, `space.side_gutter` | `before_*`/`after_heading` are **absolute** gaps; `between_paragraphs` is body prose rhythm (`leading_extra.body + after_block`), not a raw total; `before_standfirst` is added to `after_heading` for a level-1 deck because Typst combines adjacent block spacing with `max()` |
| Rules | `rule.table.top`, `rule.table.head`, `rule.table.bottom`, `rule.figure.stroke` | hairlines only; a line must carry meaning |
| Accent | `accent.ink`, `accent.tint-1..3` | **one restrained hue**, semantic only |
| Semantic roles | `role.definition`, `role.example`, `role.case`, `role.assessment` | map to accent tint + weight, not four hues |
| Block presets | `preset.chapter-opener`, `preset.body`, `preset.definition`, `preset.example`, `preset.case`, `preset.assessment`, `preset.caption`, `preset.credit` | every block type has exactly one preset |

Accent proposal for approval: a single deep indigo used at hairline strength for role labels and rules, with three tints distinguishing the four roles; body text stays ink. If a different semantic model is preferred, only `theme.typ` and this table change.

## Code style

```typst
#let role-label(role, body) = block(
  above: tokens.space.before_role,
  below: tokens.space.after_block,   // absolute gap: label to its own body
  {
    set text(size: tokens.type.small, fill: tokens.role.at(role), weight: 600)
    set par(leading: tokens.leading_extra.small)
    body
  },
)
```

Templates call presets; they never contain raw sizes, greys, hex colours or font names. A lint test enforces that.

## Font manifest

`fonts.yaml` declares, for each script, the ordered chain and the licence:

```yaml
scripts:
  latin-vietnamese: { family: Spectral, files: [...7 cuts...], licence: OFL-1.1 }
  japanese: { family: "<verified local face>", fallback: [...], licence: "<verified>" }
  maths: { family: "<verified local maths face>", licence: "<verified>" }
```

Verified today: Spectral covers all 134 precomposed Vietnamese characters and basic maths symbols, and has no CJK. The Japanese face is chosen after Typst validation; the spec does not name a pin that has not been proven to load and embed.

## Testing strategy

`pytest` under `tests/design/`:

- Lint: no raw hex colour, font name or absolute size in `typst/templates/` or `typst/blocks.typ`; only token references.
- Coverage: every character in the manuscript is covered by its declared script chain; a missing glyph fails with `GLYPH_MISSING`.
- Presets: every block type resolves to exactly one preset, and every preset is used by the specimen.
- Rendering: caption/credit/role labels appear at the declared size and colour; checked on rendered pages during the specimen gate.

## Boundaries

- Always: keep visual values in `theme.typ`; keep the type family single; keep spacing generous and rules meaningful; record each font's licence.
- Ask first: changing the accent model, adding a second family, changing the page geometry or type scale, introducing a decoration.
- Never: colour-code chart series with a palette; add boxes/shadows/background fills; let a template hard-code a colour; ship a font without a licence note.

## Success criteria

1. One theme file holds every visual value; a lint test proves no literals leak into templates.
2. The specimen renders chapter opener, body, definition, example, case, assessment, caption and credit through presets only.
3. Vietnamese and Japanese text render with no missing glyph and no silent fallback.
4. Accent use is semantic and limited to role labels/rules; body text remains ink.
5. Visual changes require editing tokens, not templates.

## Amendment — Phase 2 layout correction (2026-11-13)

User authorization, verbatim: “Proceed with the coordinated line-spacing and page-break layout changes.” This amendment is additive to the approved 2026-11-10 design system; it does not claim earlier approval of the fields or tokens below. Scope: `.opencode/phase2-layout-correction-scope.md`, `.opencode/phase2-layout-fix-intake.md`, `.opencode/phase2-layout-review.md`.

Measured Typst semantics (Typst 0.15.1, pinned fonts, `pdftotext -bbox-layout`):

- `set par(leading: L)` realises a line pitch of `size × natural + L`, where the measured natural height is **0.660 em** for Spectral (Latin and Vietnamese) and **0.729 em** for Noto Serif CJK JP.
- A block's `below`/`above` value is a gap added before the natural line box. Two adjacent block gaps collapse to the larger value; they do not sum.
- Headings do not inherit the body leading. Their pitch is set explicitly with `set par(leading: tokens.leading_extra.hN)` inside a `show heading.where(level: n)` rule, and absolute `set block(above:, below:)` provides the heading space. Wrapping a heading in a block keep-group is not required and would lose native keep-with-next.

Leading extras (derived from the intended totals and the measured Latin natural height; one value is applied per role because Typst applies one `par.leading` to the whole font list):

| Role | Size | Intended total | `leading_extra` | Latin realised | CJK realised |
| --- | ---: | ---: | ---: | ---: | ---: |
| body | 10.1 | 15.3 | 8.63 pt | 15.30 | 15.99 |
| lead | 10.6 | 16.4 | 9.40 pt | 16.40 | 17.13 |
| caption | 8.2 | 11.2 | 5.79 pt | 11.20 | 11.77 |
| table | 8.6 | 11.6 | 5.92 pt | 11.60 | 12.19 |
| note | 9.2 | 13.6 | 7.53 pt | 13.60 | 14.24 |
| small | 8.4 | 12.0 | 6.46 pt | 12.00 | 12.58 |
| quote | 10.2 | 15.4 | 8.67 pt | 15.40 | 16.11 |
| h1 | 25 | 30.0 | 13.50 pt | 30.00 | — |
| h2 | 12.6 | 16.5 | 8.18 pt | 16.50 | — |
| h3 | 10.3 | 14.0 | 7.20 pt | 14.00 | — |

The CJK residual (+0.69 pt at body) is a font-metric fact, not a defect to hide. Tests assert Latin/Vietnamese and Japanese separately and bound the difference; the body tolerance is not widened.

Space semantics are classified rather than globally converted:

- **Prose rhythm (converted):** `space.between_paragraphs = leading_extra.body + space.after_block` for paragraph, the definition/example/case/assessment body, and list blocks. A paragraph baseline gap is therefore pitch + 5.4 pt.
- **Absolute gap (kept):** `space.before_heading`, `space.before_role`, `space.after_heading`, `role-label.below`, and `preset-note.below`. A lead's `space.after_lead` and a figure's `space.after_figure` remain absolute display gaps; converting them would loosen the very elements the correction is meant to tighten.
- **Level-1 deck gap:** a section standfirst, or a level-1 section's first-block lead, uses `preset-standfirst`, whose `above` is `space.after_heading + space.before_standfirst` (4.5 + 6 = 10.5 pt). Typst uses the larger of adjacent block spacings, so the additive token is required to open a real white band; level-2/3 standfirsts and later leads keep `preset-lead`.
- **Quote:** `preset-quote` is set at `type.quote` (10.2 pt) with `leading_extra.quote`; its below gap uses `leading_extra.quote + space.after_block` so the quote-to-prose gap stays wider than the quote's own line pitch.

Limits recorded by this amendment: a credit line is single-line and has no separate leading token; per-script leading overrides are not implemented because a 0.660 em box would overlap CJK ink at this leading. Re-measure the 0.660/0.729 em constants whenever the Typst or font pin changes.

## Amendment — Bookify v2 design defaults (2026-11-14)

Additive to the approved design contract, per the owner-approved
`SPEC-bookify-v2.md` §5. No colour, font, mode or dependency is added, and no
per-book design profile exists.

### D1 — definitions inline

`preset-definition(term, definition)` is one paragraph: bold `term`, a colon,
the definition, body size 10.1 pt and body leading. There is no role label, no
grey, no standalone term line. `role.definition` stays as a token name for
compatibility but no preset reads it. A glossary is an ordinary authored table
with a caption; there is no transform from definitions to rows.

### D2 — designed typographic cover

Cover tokens: `type.cover_title` 34 pt (total pitch 41 pt),
`type.cover_subtitle` 12.6 pt, `type.cover_meta` 8.4 pt,
`type.cover_index` 8.6 pt (total 11.6 pt), `space.cover_rule` 12 pt,
`space.cover_footer` 24 pt, `rule.cover` 0.6 pt, `rule.cover_index` 0.4 pt,
`measure.page_height` 297 mm. The cover is left-aligned on the 60 pt margin:
institution meta line, title (≤ 3 lines), optional subtitle, one full-measure
rule, the real level-1 chapter index (or the ledger motif beyond
`COVER_INDEX_LIMIT` = 12 entries), and a footer rule with author and course when
present. It carries no folio, no colour, no image and no invented year, edition,
ISBN or city. The fit guard requires the title to consume at most three lines and
the footer ink to keep ≥ 24 pt of slack above the bottom margin; a miss is
`BUILD_FAILED` with the `metadata.title`/metadata locator. Nothing is shrunk or
truncated silently.

### D4 — chapter openers and plates

`type.opener_numeral` 40 pt (total 48 pt), `space.opener_rule` 12 pt,
`space.opener_title` 14 pt, `rule.opener` 0.6 pt. Every level-1 section renders
the printed number, a full-measure rule 12 pt below it, the title at 25/30, then
the authored standfirst or lead with the unchanged ≥ 32.7 pt deck gap. Front
matter (the contents title) keeps the plain level-1 treatment with no number and
no rule. `measure.plate` equals `measure.body` 475.28 pt: charts, diagrams and
full illustrations are placed at the measure; side compositions remain
illustration-only at 46 % with the 16 pt gutter. Charts are authored at the
measure (6.6011 in wide) so a plate is placed at 100 % without scaling its type.
A chapter with a visual should carry one plate; a gap is recorded in the build
report and warned in verify, and the review must answer it. No decorative filler
and no fabricated figure.

### D5 — one caption carrying description and provenance

For charts, diagrams and full illustrations the description and the
provenance/source line are one centred caption block at `type.caption` 8.2 pt
(total 11.2 pt), separated by a line break. The block's/record's existing note is
merged there and no longer printed as a separate 9.2 pt left note. Credits remain
a separate left-aligned 7.6 pt line. Table and equation captions keep their own
treatment. The caption+provenance block is one keep unit with its figure.

### D6 — heading rhythm

`space.before_h2` 32 pt and `space.before_h3` 25 pt replace the single
`before_heading` 17 pt for levels 2 and 3. Level 2/3 gaps therefore exceed the
20.70 pt paragraph gap and Typst's `max()` yields a real blank band:
level-1 17 pt (flowed chapters only), level-2 32 pt, level-3 25 pt. Body 15.30,
paragraph 20.70, h1/h2/h3 pitches 30/16.5/14 and the 32.7 pt deck gap are
unchanged. Measured bands (300 dpi): h2 baseline delta ≥ 36.0 pt and white band
≥ 8.0 pt; h3 ≥ 31.0 pt and band ≥ 5.0 pt; no heading immediately followed by
another heading with no content between.

### D7 — density guidance, not a target

The design system states the reading intention; verify measures it. Body measure
stays 475.28 pt and is never shortened to lower a word count. A dense reference
page and a sparse plate page may both be correct. The only density rules are the
named bands in `SPEC-bookify-v2.md` §7.2 and they warn, never fail. No page,
word, figure or table quota exists.

### Compatibility and residual limits

All values are addressed by token name in one theme, so a later per-book profile
could overlay values without a manuscript field; v2 designs no such mechanism.
Existing definition, chart, diagram and illustration blocks render in the new
defaults without migration. Residual limits: the precedent-slack guard measures
inked text, so a full-bleed image outside its declared box is still caught by the
composition/unit checks rather than by the cover guard; the cover index is capped
at twelve entries by design, not by available space.
