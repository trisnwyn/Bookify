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
| Type | `type.body`, `type.lead`, `type.h1`, `type.h2`, `type.h3`, `type.caption`, `type.small`, `type.credit` | one serif family; sizes taken from the verified reference scale |
| Space | `space.page.margin`, `space.before.heading`, `space.after.block`, `space.figure` | generous; no rules used as spacing |
| Rules | `rule.table.top`, `rule.table.head`, `rule.table.bottom`, `rule.figure.stroke` | hairlines only; a line must carry meaning |
| Accent | `accent.ink`, `accent.tint-1..3` | **one restrained hue**, semantic only |
| Semantic roles | `role.definition`, `role.example`, `role.case`, `role.assessment` | map to accent tint + weight, not four hues |
| Block presets | `preset.chapter-opener`, `preset.body`, `preset.definition`, `preset.example`, `preset.case`, `preset.assessment`, `preset.caption`, `preset.credit` | every block type has exactly one preset |

Accent proposal for approval: a single deep indigo used at hairline strength for role labels and rules, with three tints distinguishing the four roles; body text stays ink. If a different semantic model is preferred, only `theme.typ` and this table change.

## Code style

```typst
#let role-label(role, body) = {
  set text(size: tokens.type.small.size, fill: tokens.accent.tint-2)
  set par(leading: tokens.space.after.block)
  block(above: tokens.space.before.block, body)
}
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
