# SPEC-agent-skill

Status: **revised specification approved for planning 2026-11-12**;
implementation plan approval pending. This is a specification only. It records
the user-confirmed Phase 2 intent in `.opencode/phase2-skill-intake.md` and the
approved revised command/voice contract. It does not approve a plan or
implementation.

Owning boundary: the existing `authoring-pipeline` module, with the existing
`design-system`, `publish-engine`, `verify-harness` and packaging boundaries
unchanged. This is **one agent-facing authoring capability with two policies**,
not a new module, service, framework, capability map, or set of user-facing
pipelines. No new module id is proposed.

On approval, this spec supersedes only the *authoring-guide/skill* portion of
`SPEC-authoring-pipeline.md`. The historical spec, `SPEC-INDEX.md`, the approved
capability map, `tasks/plan.md` and `tasks/todo.md` remain unchanged until a
separately approved plan says otherwise.

## 1. Objective

Give an AI agent a reusable, compact instruction surface for turning a supplied
source into an aesthetic, textbook-alike A4 PDF, without asking the user to
author YAML, operate a CLI, manage caches, or follow a mandatory
extract → plan → apply → build pipeline.

The agent must understand the source, own the editorial and visual decisions,
render the book, inspect every rendered page, revise it, and verify the result.
The existing tested renderer, schema, fonts, glyph coverage, text probes, rights
rules, one-illustration-per-page rule, grouped captions, column centring,
`full`/`side-left`/`side-right` compositions and current house aesthetic are
reused. They are not rewritten, bypassed, or replaced with a new design system.

Exactly two authoring modes exist:

| Machine token | Display name | Contract |
| --- | --- | --- |
| `source-faithful` | Source-faithful | Follow the supplied material's order, coverage and meaning. Improve presentation without adding factual content, teaching apparatus, or outside material. |
| `teachable` | Teachable textbook | Reorganise and rewrite into coherent teachable chapters with explanations, examples and learning aids. Source-grounded by default; outside enrichment only when the user explicitly requests it and every added source is recorded. |

Enrichment is a **permission inside `teachable`**, not a third mode. There are
no study-guide, workbook, handbook, or other extra modes. The primary entry is
three slash commands for these two modes: `/bookify` (source-faithful default
alias), `/bookify-source-faithful`, and `/bookify-teachable-textbook`. The alias
is not a third mode. Teachable mode must read as a natural standalone authorial
coursebook, not as a report on “the provided materials/course/slides”; citations,
attribution and real uncertainty remain visible and unobtrusive.

Success means the agent can produce both kinds of book from the same supplied
source, with materially different and testable authoring contracts, while
publishing stays a deterministic function of the stored manuscript, assets and
pins. Build and verify remain offline and model-free. Authoring and research may
use agent tools, but only with recorded provenance and, for outside material,
explicit permission.

### Non-goals

- No hosted service, database, queue, auth, web UI, EPUB/HTML output, OCR engine,
  automatic image search, or new AI-provider service.
- No mandatory user pipeline, no user-authored YAML/JSON, and no mandatory
  `author plan` / `author apply` page workflow. Those remain optional internal
  helpers where they genuinely help.
- No new source-format claim. Verified intake is PDF via Poppler
  (`pdfinfo`, `pdftotext -layout`, `pdfimages`); image-only pages are unresolved,
  never OCR guesses. DOCX, PPTX, HTML and similar formats are not claimed.
- One source per intake invocation is the verified path. Multiple supplied
  sources require an approved extension; they are not silently combined.
- No claim that independent agent rewrites produce byte-identical books. The
  guarantee is: the same approved manuscript, design data, assets and pins
  produce the same layout and, where the current engine proves it, the same PDF
  bytes.
- No new design system, no quota of figures or pages, and no requirement that a
  real book resemble `content/catalogue.yaml`.

## 2. Interface contracts

### 2.1 Command entry and mode authority

The primary entry is three OpenCode slash commands for two modes. Three entry
commands, not three modes; `/bookify` is the source-faithful default alias.

| Command | Mode established | Contract |
| --- | --- | --- |
| `/bookify` | `source-faithful` | Default alias. No mode interview and no model guess. |
| `/bookify-source-faithful` | `source-faithful` | Explicit strict entry. |
| `/bookify-teachable-textbook` | `teachable` | Explicit teachable entry. |

The selected command establishes the mode for that run. The agent must not ask
“which mode?” again, infer a mode from tone, or silently change the mode because
the arguments sound pedagogical or strict. A mode conflict inside `$ARGUMENTS`
is not a mode interview: state the conflict and ask for one brief resolution
(use the named command, or switch to the other entry command). A requested mode
change is a new authoring decision, not a silent transformation of an existing
revision.

The three command templates must:

- state the mode and “do not ask which mode”;
- include `$ARGUMENTS` verbatim and preserve any language, audience, length,
  citation-style, output-path and other preferences in it;
- treat composer attachments as the supplied source; stored templates do not
  expand `@path`, so the template must not rely on that expansion;
- never place `$ARGUMENTS`, a source path or any untrusted text inside a `!`
  shell block; shell blocks run outside the tool permission flow;
- omit `agent`, `model`, `subagent`, `subtask` and similar overrides unless a
  later approval explicitly requires them;
- ask once for a source only when neither an attachment nor an argument names
  one; and
- state the conflict rule without inviting a redundant mode conversation.

Direct skill load without a slash command is a fallback entry, not the primary
contract. It uses the documented `source-faithful` default only when no mode is
explicit; an explicit mode in the request is honoured, never inferred. A conflict
between a loaded default and explicit words is resolved briefly, not silently.

The command entry must not be replaced by CLI mode flags, a new web UI, JSON
command duplication, or a mandatory mode prompt. Outside enrichment remains
permissioned: asking for the permission or source is allowed; guessing a mode or
searching for sources is not.

### 2.2 Mode contracts

Both modes share: source read-only, provenance, no invention, rights, offline
build/verify, page inspection, and repeatability. They differ materially:

| Contract | `source-faithful` | `teachable` |
| --- | --- | --- |
| Source order | Flattened content follows source page order; within-page order is preserved and reviewed. Front matter/contents generated by the renderer may precede the body. | May reorder, merge, split and regroup source units into chapters. Every reorder/merge/split/omission is recorded. |
| Source coverage | Every source unit is covered, merged, or explicitly excluded with a reason. | Every source unit is covered, merged, or explicitly excluded with a reason; omission is allowed only when recorded as an editorial decision. |
| Additions | Presentation-only text: headings, standfirsts, captions, cross-references and connective wording that add no factual proposition. No added teaching apparatus unless it is present in the source and retained as source content. | Teaching apparatus is allowed: objectives, explanations, definitions, worked examples, analogies, checks, summaries and glossaries. Factual content must remain source-grounded or properly enriched. |
| Factual provenance | Every content block carries a source anchor. Presentation-only text contains no new fact. Unsupported material is absent or unresolved. | Every factual claim carries a source anchor or an approved external citation. Original pedagogical framing must be labelled as framing, not as a source fact. |
| External enrichment | Forbidden. Source-supplied URLs/citations may be quoted only as source content. | Allowed only with explicit per-book permission. Every external source has a citation, creator/publisher where available, access date, and a local hash or stable locator. No permission means no external enrichment; permission to use a source is not permission to invent. |
| Uncertainty | Unreadable labels, values and names become `unresolved`/`null` with a note. Never guessed. | Same rule. An illustrative example is labelled illustrative; it is never presented as a real observation. |
| Visuals | Use source evidence, redrawn source figures, or already verified illustrations. Generated diagrams/reconstructions are labelled and must not masquerade as documentary evidence. | Use teaching visuals where they clarify. Charts and diagrams may be synthetic/illustrative when labelled. Source and rights rules still apply. |
| Decisions | Record every omission, merge, unresolved item and redraw. | Record every reorder, merge, split, omission, explanation, example, assessment, enrichment and redraw. |
| Testable distinction | No external-enrichment record; no teaching block absent from the source; page anchors monotonic. | Reordering/regrouping and teaching blocks are allowed and recorded; unsourced external claims and unpermitted enrichment fail. |

“Presentation-only” is deliberately narrow. A sentence that asserts a fact, a
number, a name, a date, a category, a causal claim or a citation is content and
must be anchored. Good presentation may improve transitions, headings and
captions; it may not smuggle in new knowledge.

### 2.3 Authoring record (durable, not a cache)

A skill-authored book keeps a durable authoring record beside the manuscript.
It is internal support for the agent and for contract tests; the user is not
expected to author it. It is separate from the closed manuscript schema and does
not require a `schemaVersion` migration.

Minimum fields, proposed as `authoring/record.json` in the workspace:

```json
{
  "schemaVersion": "1.0",
  "bookId": "book-slug",
  "mode": "source-faithful",
  "source": {
    "id": "source-slug",
    "sha256": "<source hash>",
    "pages": 6,
    "intakeManifest": "intake/manifest.json"
  },
  "enrichment": {
    "requested": false,
    "permission": null,
    "sources": []
  },
  "coverage": [
    {
      "sourceId": "source-slug",
      "page": 1,
      "status": "covered",
      "blockIds": ["b-001"],
      "reason": null
    }
  ],
  "derivations": [
    {
      "kind": "heading",
      "blockIds": ["b-001"],
      "anchors": [{"sourceId": "source-slug", "page": 1}],
      "citation": null,
      "decision": "Heading derived from the page's own topic sentence."
    }
  ],
  "manuscriptSha256": "<hash of the stored manuscript>",
  "manuscriptRevision": 1
}
```

Rules:

- `mode` is exactly `source-faithful` or `teachable`.
- Coverage names every source page exactly once with `covered`, `merged` or
  `excluded`; a non-covered status carries a reason.
- `derivations[].kind` is a closed vocabulary: `heading`, `caption`, `merge`,
  `split`, `reorder`, `condense`, `explain`, `example`, `assessment`, `glossary`,
  `external`.
- `source-faithful` rejects `external` and rejects teaching kinds (`explain`,
  `example`, `assessment`, `glossary`) unless the same kind is explicitly present
  in the source and recorded as retained source content.
- `teachable` rejects `external` when `enrichment.requested` is false or when a
  source lacks a citation. External source entries record a stable locator and a
  local hash where the material is stored.
- Decisions that explain why a chapter was reordered, an item omitted, a figure
  redrawn, or an example added are durable. They do not live only in a disposable
  `build/` cache.
- Existing `build/authoring/decisions.jsonl` remains supported for compatibility;
  new skill books write the durable record in the workspace.

### 2.4 Workspace contract

There is no true per-book workspace in the current installed bundle. The current
bundle instructs the agent to change into `engine/` and write `work/` and `dist/`
there. That keeps the engine relocatable, but mixes books and lets a book write
into the installed skill tree. The current engine also discovers its root from
`pyproject.toml` and requires the build directory inside that root.

Proposed safe behaviour:

```text
<workspace>/                 # one book, outside the installed engine
  book.yaml                  # manuscript (the only publishing input)
  assets/illustrations/...   # book-owned records and images
  intake/                    # source extraction evidence
  authoring/record.json      # durable mode/provenance/coverage/decisions
  authoring/decisions.jsonl  # optional append-only human-readable log
  build/                     # disposable
  dist/                      # built PDFs and inspection evidence
```

- The engine remains read-only for book content. Templates, fonts, vendored
  packages, the Typst binary and the Python environment come from the engine.
  `assets/fonts` is engine-owned; book illustrations live in the workspace.
- A workspace must not be inside the installed engine tree. Legacy commands that
  default to the source repository root keep working; the workspace is an
  explicit, additive path for skill use.
- Build output and the build directory must resolve inside the workspace. The
  source file is read-only and may live outside the workspace; its hash, intake
  manifest and anchors are recorded.
- Two workspaces for two books must not share mutable state. Deleting
  `build/` or a cache never changes the manuscript, the authoring record, or the
  built PDF.
- The agent must never write into the user's unrelated repository. It writes
  only inside the explicitly chosen workspace, and asks before creating a
  workspace inside a repository it was not asked to modify.

Proposed interface: optional `--workspace <dir>` on the commands that need root
resolution (`manuscript check`, `design check`, `figures render`, `build`,
`verify`), or `BOOKIFY_WORKSPACE` as the environment equivalent. When absent, the
current root-discovery behaviour is unchanged. This is additive; existing
commands and tests remain valid.

### 2.5 Error and compatibility contract

- No new error code. Mode/record violations use `INPUT_INVALID` with a locator
  into `authoring/record.json`; manuscript shape violations keep
  `SCHEMA_INVALID`; workspace escape stays `BUILD_FAILED`; rights, network,
  model and glyph errors keep their existing codes.
- Exit codes remain as documented in `SPEC-INDEX.md`.
- The manuscript schema stays `schemaVersion: "1.0"` with no required new field.
  Existing manuscripts without an authoring record still validate, build and
  verify; the record is required only for books authored through the new skill
  contract.
- Existing CLI defaults, `author plan/apply/select/status`, the specimen,
  catalogue, trial fixture, schema, fonts and design tokens are not removed or
  renamed.

### 2.6 Agent-facing entry and progressive disclosure

One compact entry teaches the default loop. Detail lives in references, not in
an expanding entry.

| File (proposed) | Purpose |
| --- | --- |
| `skill/bookify/SKILL.md` | Compact entry: when to use, command entry, source handling, authoring loop, self-critique, tool selection, hard rules. Target ≤ 250 lines; no full command transcript. |
| `skill/bookify/references/modes-and-playbooks.md` | Two mode contracts, selection examples, strict/teachable playbooks, enrichment permission and negative cases. |
| `skill/bookify/references/source-and-provenance.md` | PDF-only intake, anchors, source indices, coverage/order, unreadable material, citations, rights. |
| `skill/bookify/references/editorial.md` | Chapter architecture, explanation, examples, checks, summaries, strict vs teachable editing, no-fake-facts rules. |
| `skill/bookify/references/visual-design.md` | House style, typography, hierarchy, whitespace, full/side compositions, chart/diagram/illustration selection, no quota, page inspection rubric. |
| `skill/bookify/references/render-verify.md` | Exact build/verify/inspect recipes, double build, contact sheet, failure handling, evidence to record. |
| `skill/bookify/references/limits.md` | Verified source formats, no OCR, platform/tool limits, deterministic/byte-identity boundaries, rights limits. |
| `skill/bookify/references/checklist.md` | Retained name; rewritten as the agent's self-critique checklist rather than a universal developer gate. |

The packaged entry `packaging/payload/SKILL.md` must carry the same normative
mode/contract text and point to packaged reference copies. It may differ only in
path/setup sections. Packaging must not drift into a second, contradictory
skill.

The entry is a skill, not a command manual. It must not present
extract → plan → apply → build → verify as the only permissible sequence.
Internal helpers may be used selectively; the agent may author the manuscript
directly, then validate, render, inspect, revise and verify.

### 2.7 OpenCode command assets (proposed, not installed)

OpenCode V2 command facts verified from the actual documentation on 2026-11-12:
Markdown commands live in `.opencode/commands/` or
`~/.config/opencode/commands/`; the filename determines the slash name; the
Markdown body is the prompt template; `$ARGUMENTS` is the complete argument
string; frontmatter may carry `description`, `agent`, `model`, `subagent`;
stored templates do not expand `@path`; composer attachments are preserved;
shell blocks introduced by `!` run outside the agent tool-permission flow;
commands reload automatically; project sources replace global commands with the
same name. Commands are prompt templates, not CLI executables.

Canonical source assets are proposed at a public-safe, tracked path, because
`.opencode/` is ignored wholesale in this repository:

```text
skill/bookify/commands/
  bookify.md                     # default alias -> source-faithful
  bookify-source-faithful.md     # explicit source-faithful
  bookify-teachable-textbook.md  # explicit teachable
```

Future bundle/install mapping, explicitly approved later:

```text
skill/bookify/commands/*.md              # canonical source, public-safe
packaging/payload/commands/*.md          # packaged copies
~/.config/opencode/commands/*.md         # global install (reusable skill)
<project>/.opencode/commands/*.md        # optional project install, with permission
```

No command file is created or installed in this stage. The future installer must
be collision-safe: validate names and contents, refuse an existing non-Bookify
command or an unexpected existing file, never overwrite another command or global
configuration silently, and allow an explicit replace decision only after
approval. A project install writes into an ignored directory and is therefore
not a substitute for the tracked canonical source. The global install is a
separate packaging release concern; it is not part of this spec's approval.

#### 2.7.1 Proposed prompt templates

`skill/bookify/commands/bookify.md`:

```markdown
---
description: Make a Bookify PDF from a source; defaults to source-faithful.
---

Make a Bookify book from the supplied source in `source-faithful` mode.

This command establishes `source-faithful`: follow the source's order, coverage
and meaning; improve presentation only; add no teaching apparatus and no outside
material. Do not ask which mode to use.

$ARGUMENTS

Treat the user's composer attachments as the supplied source. Preserve requested
language, audience, length, citation style and output path. Do not rely on `@path`
expansion in this template and never put `$ARGUMENTS`, a source path or other
untrusted text inside a `!` shell block.

If `$ARGUMENTS` explicitly requests teachable mode or outside enrichment, do not
silently override this command's mode. State the conflict and ask for one brief
resolution: use this source-faithful entry, or switch to
`/bookify-teachable-textbook`. If no source is attached or named, ask for it
once. Then load the Bookify skill and follow its workspace, provenance, build,
inspection and verification contract.
```

`skill/bookify/commands/bookify-source-faithful.md`:

```markdown
---
description: Make a source-faithful Bookify PDF from a source.
---

Make a Bookify book in `source-faithful` mode: preserve the source's order,
coverage and meaning; improve presentation only; add no teaching apparatus and no
outside material. Do not ask which mode to use.

$ARGUMENTS

Preserve attachments and requested language, audience, length, citation style and
output path. Do not rely on `@path` expansion in this template and never place
`$ARGUMENTS`, source paths or other untrusted text inside a `!` shell block.

If the arguments explicitly request teachable mode or outside enrichment, state
the conflict and ask for one brief resolution; do not switch modes silently. If
no source is attached or named, ask for it once. Then load the Bookify skill and
follow its source-faithful, workspace, provenance, build, inspection and
verification contract.
```

`skill/bookify/commands/bookify-teachable-textbook.md`:

```markdown
---
description: Make a teachable textbook PDF from a source.
---

Make a Bookify book in `teachable` mode: reorganise and rewrite the supplied
source into a coherent, standalone authorial coursebook with explanations,
examples and learning aids. Remain source-grounded. Use outside enrichment only
when the user explicitly requests it here and supplies a source to cite. Do not
ask which mode to use.

$ARGUMENTS

Preserve attachments and requested language, audience, length, citation style and
output path. Do not rely on `@path` expansion in this template and never place
`$ARGUMENTS`, source paths or other untrusted text inside a `!` shell block.

Write natural coursebook prose. Do not narrate the input with phrases such as
"the provided materials suggest", "the course says", "the slides explain" or
"based on the provided content". State the teaching point directly, support it
with a citation in a note/reference or the authoring record, and keep required
attribution, quotations and uncertainty visible.

If the arguments explicitly request source-faithful mode, state the conflict and
ask for one brief resolution; do not switch modes silently. If outside
enrichment is requested without a source or permission, ask for both once. If no
source is attached or named, ask for it once. Then load the Bookify skill and
follow its teachable, workspace, provenance, build, inspection and verification
contract.
```

These templates are proposed prompt text. They are not registered commands and
must not be described as installed. The command entry is the primary interface;
the skill entry documents it and the direct-load fallback.

## 3. Commands

All engine commands below are existing public commands unless marked
**proposed**. None of the proposed forms exists yet. The three slash commands are
also **proposed** and not registered.

### 3.1 Command entry status

| Entry | Status | Mode |
| --- | --- | --- |
| `/bookify` | Proposed; not installed | `source-faithful` default alias |
| `/bookify-source-faithful` | Proposed; not installed | `source-faithful` |
| `/bookify-teachable-textbook` | Proposed; not installed | `teachable` |

No `/bookify*` command exists in the inspected project or global command
directories as of 2026-11-12. The command templates are specified in §2.7.1.
The canonical files are proposed for `skill/bookify/commands/`; installation is a
later, separately approved packaging step.

### 3.2 Existing engine commands (verified in the public source and installed bundle interface)

| Purpose | Command |
| --- | --- |
| Setup | `cd "$BOOKIFY_ENGINE" && uv sync --python 3.13.16 --frozen` |
| Toolchain check | `uv run bookify toolchain doctor --json` |
| Extract a PDF source | `uv run bookify intake --source <source.pdf> --out <workspace>/intake --changed-only --json` |
| Optional page-diff helper | `uv run bookify author plan --intake <workspace>/intake --manuscript <workspace>/book.yaml --out <workspace>/build/author-plan.json --cache-dir <workspace>/build/cache/authoring --json` |
| Optional draft merge helper | `uv run bookify author apply --plan <workspace>/build/author-plan.json --draft <draft>.json --manuscript <workspace>/book.yaml --cache-dir <workspace>/build/cache/authoring --decisions <workspace>/authoring/decisions.jsonl --json` |
| Optional illustration record helper | `uv run bookify author select --section <section-id> --illustration <id> --reason "<why>" --store <workspace>/authoring/selections.json --json` |
| Manuscript check | `uv run bookify manuscript check --manuscript <workspace>/book.yaml --json` |
| Design check | `uv run bookify design check --manuscript <workspace>/book.yaml --json` |
| Figures render | `uv run bookify figures render --manuscript <workspace>/book.yaml --out <workspace>/build/figures --json` |
| Offline build | `uv run bookify build --manuscript <workspace>/book.yaml --out <workspace>/dist/book.pdf --offline --build-dir <workspace>/build/book --json` |
| Comparison build | `uv run bookify build --manuscript <workspace>/book.yaml --out <workspace>/dist/book-rebuild.pdf --offline --build-dir <workspace>/build/book-rebuild --json` |
| Render pages | `pdftoppm -png -r 110 <workspace>/dist/book.pdf <workspace>/build/pages/page` |
| Contact sheet | `magick montage <workspace>/build/pages/page-*.png -tile 4x <workspace>/build/contact.png` |
| Verify | `uv run bookify verify --pdf <workspace>/dist/book.pdf --manuscript <workspace>/book.yaml --previous-pdf <workspace>/dist/book-rebuild.pdf --build-report <workspace>/build/book/build-report.json --contact-sheet <workspace>/build/contact.png --reviewed-by "<agent>" --reviewed-at "<ISO time>" --report <workspace>/build/verify.json` |
| Full suite | `uv run python -m pytest -q` |
| Package the skill | `python packaging/bookify_skill_bundle.py pack --out dist/bookify-skill.tar.gz --check-determinism` |

### 3.3 Proposed engine commands (not implemented; additive only)

| Purpose | Proposed form | Notes |
| --- | --- | --- |
| Workspace root | `--workspace <dir>` or `BOOKIFY_WORKSPACE=<dir>` on check/build/verify/figures commands | Existing root discovery remains the default. |
| Authoring-record check | `uv run bookify author contract check --workspace <workspace> --json` | Optional internal helper. Validates mode, coverage, provenance, enrichment permission, workspace layout and source hash. No model/network. Not required for third-party manuscripts that only build. |

No new user-facing pipeline command is proposed.

### 3.4 User invocation examples

The same supplied source, selected by command. Attachments are added in the
composer; they are not `@path` expansions in the stored template.

```text
/bookify
(composer attachment: <source.pdf>)

Write in Vietnamese for first-year undergraduates. A4, PDF at
<workspace-a>/dist/book.pdf. Keep the source order and coverage.
```

`/bookify` selects `source-faithful`; it is not a third mode.

```text
/bookify-source-faithful
(composer attachment: <source.pdf>)

Use British English and keep the source's chapter order. No outside sources.
```

```text
/bookify-teachable-textbook
(composer attachment: <source.pdf>)

Reorganise into six chapters for advanced secondary students. No outside
sources. Write a standalone coursebook, not a report on the source.
```

```text
/bookify-teachable-textbook
(composer attachments: <source.pdf>, <note.md>)

Use <note.md> only for the final section. Cite it and record its provenance.
```

Conflict example:

```text
/bookify
(composer attachment: <source.pdf>)

Make this a teachable textbook with exercises.
```

The command selects `source-faithful`, but the arguments explicitly ask for
teachable. The agent must state the conflict and ask for one brief resolution
(use this command as source-faithful, or run
`/bookify-teachable-textbook`); it must not silently switch modes and must not
turn the default alias into a third mode. A missing source produces one request
for the source, not a mode interview.

## 4. Structure

Proposed changes, all within existing boundaries:

```text
skill/bookify/
  SKILL.md                         # compact agent entry (rewrite)
  commands/                        # canonical public-safe command source
    bookify.md                     # default alias -> source-faithful
    bookify-source-faithful.md
    bookify-teachable-textbook.md
  references/                      # progressive guides (new/rewritten)
    modes-and-playbooks.md
    source-and-provenance.md
    editorial.md
    visual-design.md
    render-verify.md
    limits.md
    checklist.md

packaging/payload/
  SKILL.md                         # bundle entry, same normative contract
  commands/                        # packaged command copies, installed later
  references/                      # packaged copies of the guides
  README.md                        # setup/use wording updated later if needed

src/bookify/
  authoring/record.py              # proposed internal: record load/validate, coverage, mode checks
  authoring/workspace.py           # proposed internal: workspace root/layout checks
  publish/typst_driver.py          # proposed: engine assets read-only + workspace book assets
  manuscript/model.py              # proposed: explicit workspace root, legacy fallback unchanged
  toolchain/cli.py                 # proposed: optional --workspace / author contract check

tests/
  test_skill.py                    # content/discoverability checks (extend)
  test_skill_commands.py           # proposed: actual command assets, expansion, conflict rules
  test_skill_modes.py              # proposed: strict/teachable contracts, mode leakage
  test_skill_voice.py              # proposed: natural coursebook voice and semantic review
  test_skill_enrichment.py         # proposed: permission and citation cases
  test_skill_workspace.py          # proposed: isolation, read-only engine, two books
  test_skill_acceptance.py         # proposed: same-source command-driven end-to-end evidence
  test_visual_acceptance.py        # proposed: page-inspection evidence completeness
  test_author_*.py                 # retained; no weakening

packaging/test_bookify_skill_bundle.py  # extend for packaged references and contract text
fixtures/agent-skill/                   # proposed later: one public-safe source fixture
```

No new module id, service, dependency, font, asset, design system, or
capability-map gate is proposed. A new reference file is not a new module. The
catalogue remains one regression fixture and a vocabulary reference, not a
required book shape.

## 5. Style example

### 5.1 Entry instruction style

Short, imperative, decision-oriented, with a safe refusal. Example excerpt:

```markdown
# Bookify — make a book from a source

Read the source before choosing a structure. Do not ask the user to write YAML,
run commands, or manage caches; the agent owns the book workspace and evidence.

Entry:
- `/bookify` selects `source-faithful`; `/bookify-source-faithful` also selects
  `source-faithful` explicitly; `/bookify-teachable-textbook` selects teachable.
- The selected command establishes the mode. Do not ask which mode; do not infer
  a mode from tone. If the arguments explicitly demand the other mode, state the
  conflict and ask for one brief resolution.
- Direct skill load is a fallback: source-faithful by default only when no mode
  is explicit; an explicit mode is honoured, never inferred.
- Outside enrichment is never implicit. In `source-faithful`, it is forbidden.

Every factual claim needs a source anchor or an approved external citation.
Unreadable material is unresolved, never guessed. Build and verify offline.
Inspect every rendered page before delivery.
```

### 5.2 Editorial and visual instruction style

The guide must give judgement criteria, not only mechanical recipes:

```markdown
Choose the chapter architecture that the material can carry. In
`source-faithful`, keep the source's order and coverage; improve headings,
transitions, captions and typography. In `teachable`, group material into
chapters that build understanding: say what the reader will learn, define terms
where they are needed, work through one concrete example, and give a short check
that uses the chapter's own vocabulary.

Choose a visual only when it does real work: a chart for a relationship, a
diagram for structure or sequence, an illustration for evidence or recognition.
There is no quota. A book with zero illustrations is valid when the material
does not need one. Never add a figure to fill a page.

After rendering, look at every page. A page can pass every text probe and still
fail: a split composition, an orphaned heading, a caption detached from its
figure, a cramped label, a repetitive page rhythm, or a paragraph that says
nothing. Fix those before calling the book finished.
```

### 5.3 Record style

Use stable machine tokens, explicit decisions and no invented provenance:

```json
{
  "schemaVersion": "1.0",
  "bookId": "harbour-field-notes",
  "mode": "teachable",
  "source": {"id": "harbour-notes", "sha256": "<sha256>", "pages": 6,
             "intakeManifest": "intake/manifest.json"},
  "enrichment": {"requested": true, "permission": "user asked for <note.md> only",
                 "sources": [{"citation": "<note.md>", "localSha256": "<sha256>"}]},
  "coverage": [{"sourceId": "harbour-notes", "page": 1, "status": "covered",
                "blockIds": ["b-001"], "reason": null}],
  "derivations": [{"kind": "explain", "blockIds": ["b-010"],
                   "anchors": [{"sourceId": "harbour-notes", "page": 2}],
                   "citation": null,
                   "decision": "Explained the source's own distinction; no new fact."}],
  "manuscriptSha256": "<sha256>",
  "manuscriptRevision": 2
}
```

### 5.4 Natural coursebook voice

Teachable mode must read like a standalone authorial coursebook, not a report on
the input. This is an affirmative prose requirement, not a two-string blacklist.
The agent should state the teaching point directly, use pedagogical transitions,
make clear claims, define terms where they are needed, and support examples with
provenance. Exact banned-phrase checks are regression aids only; the real check
is a semantic review of paraphrases and page-level voice.

Weak, input-narrating prose:

```text
The materials provided suggest that a definition matters. The slides explain
that a definition fixes a term. Based on the provided content, we can see that
examples are useful for learning.
```

Better, direct coursebook prose:

```text
A definition fixes the meaning of a term so later claims can be tested against
it. An example then turns that abstract distinction into something a reader can
inspect. [source note or reference]
```

Weak:

```text
The course says the label cannot be read. The provided materials leave this
unclear.
```

Better, with uncertainty kept visible:

```text
One label cannot be read. The book marks the gap as unresolved rather than
guessing a value. [uncertainty note]
```

Rules:

- Do not narrate the input with recurring constructions such as “the provided
  materials suggest”, “the course says”, “the slides explain”, “based on the
  provided content”, or paraphrases of the same stance.
- Required attribution, direct quotation, an uncertainty note, an inferred-
  reconstruction label, or an enrichment citation may name the source when that
  naming is the point. That is not intrusive metanarration.
- Put citations and provenance in legitimate places: footnotes/endnotes,
  references, captions/credits, source index, or the authoring record. Do not
  delete essential attribution or hide uncertainty to make the prose sound more
  confident.
- Never upgrade inferred or unreadable evidence into a verified claim, and never
  imply that an unsourced statement is source-verified.
- Clearly marked actual uncertainty, inferred reconstruction and permissioned
  enrichment remain allowed; only the constant “what the input says” frame is
  rejected.

Semantic review: for every teachable chapter, read the rendered prose and ask
whether it teaches the concept directly, whether each factual claim has a
legitimate anchor/citation, whether attribution and uncertainty remain visible,
and whether the chapter keeps repeating “the source/material/course/slides”
instead of making its own argument. Record the page/chapter finding and revise
paraphrases, not only exact banned strings.

## 6. Testing strategy

All existing tests are retained. New tests are additive; no test is skipped,
deleted or weakened to make the new skill pass.

### 6.1 Content and interface tests

- `tests/test_skill.py`: entry frontmatter, discoverability, command-entry
  documentation, workspace wording, reference links, absence of hardcoded
  catalogue/specimen paths, absence of stale “pipeline-only” and stale licence
  claims, and the local/global skill boundary.
- `tests/test_skill_commands.py`: load the **actual** command asset from the
  canonical/installed command directory, not just a mention in `SKILL.md`.
  Assert the three names, description, mode text, `$ARGUMENTS`, conflict rule,
  no dependency on `@path` expansion, no `!` shell block containing arguments or
  paths, and no hardcoded `agent`/`model`. Expand `$ARGUMENTS` with a quoted
  fixture that includes language, audience and output preferences and assert the
  expanded prompt preserves them. If an installed copy exists, compare it with
  the canonical source; a string mention alone does not pass.
- Packaging tests: both published entries carry the same normative mode contract;
  all three command assets and every documented reference exist in the archive;
  the archive contains no source-root path and no private material; existing
  relocation/safety tests stay green.

### 6.2 Command-selected mode contract tests

Using one public-safe synthetic source PDF and its intake manifest, run the
same-source exercise through the commands:

- `/bookify`: records `mode: source-faithful`; it is not a third mode. The strict
  contract applies.
- `/bookify-source-faithful`: also records `mode: source-faithful`; no redundant
  mode question; argument/attachment preferences preserved.
- `/bookify-teachable-textbook`: records `mode: teachable`; no redundant mode
  question; argument/attachment preferences preserved.
- A conflicting argument (for example `/bookify` plus “make this teachable”)
  triggers one brief resolution, not a silent mode switch and not a redundant
  mode interview.
- `source-faithful`: page anchors are monotonic; every source page is
  covered/merged/excluded with a reason; every content block has an anchor; no
  external enrichment; no teaching block absent from the source; unreadable
  material is unresolved.
- `teachable`: a documented reorder/regroup is accepted; a teaching block is
  accepted and recorded; an unrecorded external claim fails; a recorded external
  claim without permission fails; the same claim with permission and citation
  passes.
- Mode leakage: strict + external citation fails; strict + added learning aid
  fails; teachable + unpermitted enrichment fails; both + invented number/name/
  date fail through existing manuscript/no-invention checks.
- Material difference: the strict and teachable outputs differ in structure
  (order/grouping), teaching apparatus and authorial voice, and both remain
  source-grounded. This is a fixture acceptance requirement, not a required shape
  for every real book.

### 6.3 Voice tests

- Exact banned-phrase checks are regression aids, not the whole test. The
  positive examples in §5.4 must pass and the weak examples must fail a semantic
  review.
- A reviewer reads every teachable chapter/page and records whether it teaches
  directly, preserves citations/attribution and uncertainty, avoids recurring
  input narration, and makes its own argument. A paraphrase of “the provided
  materials suggest” fails even when the exact words differ.
- Voice review must not accept deleting attribution, hiding uncertainty,
  upgrading inferred/unreadable evidence, or implying unsourced facts are
  verified.
- A human or agent reviewer may judge naturalness; the record states who reviewed
  and which pages were sampled. This is not a claim of objective aesthetic proof
  or human sign-off.

### 6.4 Workspace and repeatability tests

- Engine tree hash is unchanged after a full authoring/build cycle; all writes
  are inside the chosen workspace.
- Two workspaces produce two independent books with no shared mutable state.
- Build directory/output outside the workspace fails with the existing clear
  error.
- Legacy no-workspace commands still resolve the repository root and pass.
- Two offline builds from the same manuscript/assets/pins agree on page facts
  and, where the engine currently proves it, bytes; cache deletion changes
  neither.
- Build/verify are model-free and network-denied; authoring records are durable;
  no model call is required for a repeat build.

### 6.5 Visual acceptance evidence

Visual acceptance is not a figure count, a page count, or a catalogue inventory.
For each evidence book:

- Render every page at a readable resolution and inspect it; record a per-page
  result and the evidence path.
- Review the visual dimensions in AC-7 and the editorial/visual guidance in §5.2.
  A blocking defect blocks delivery; an “attention” result carries a reason and
  a decision.
- Confirm material faithfulness, readability, design coherence, intentional
  hierarchy, white space, varied composition, typography, fitted labels,
  caption/credit integrity, one-illustration-per-page, rights and cross-references.
- Check that the layout is page-flow, not page-quota: a chapter may start a new
  page, but a minor section must flow unless a full plate or deliberate
  back-matter unit earns `breakBefore: page`. A source page boundary is not a
  chapter boundary. No near-empty minor-section page, no forced blank verso.
- Check the intended rhythm on the rendered page: body pitch 15.3 pt, paragraph
  gaps wider than the line pitch, headings tighter than the old default, table
  headers repeated after a split, and no clipped/oversize keep group.
- Record that this is agent visual inspection, not human PDF sign-off.

**Section hierarchy and page flow (Phase 2 amendment, 2026-11-13).** User
authorization, verbatim: “Proceed with the coordinated line-spacing and
page-break layout changes.” A manuscript section may declare `level: 1|2|3` and
`breakBefore: auto|page`. Level 1 is a chapter and defaults to a fresh page
(except the first body section); levels 2 and 3 are minor sections and flow by
default. Use the hierarchy to keep a coherent reading sequence, not to chase a
page count: merge one-sentence fragments where meaning is unchanged, keep real
chapters and full plates as page units, and never map source pagination to
chapter breaks or infer chapters from titles. A plate unit (heading, unresolved
note, illustration, caption, credit) stays together or the build fails by name.
Contents lists all three levels and may paginate; section titles are unique so
entries cannot collapse.

### 6.6 End-to-end evidence (proposed later, not executed now)

Later acceptance produces a report (proposed `docs/agent-skill-report.md`) with:

- the same source fixture, its hash and page count; its stored facts are neutral
  and synthetic, its source indices are stable, and the base evidence uses no
  external research;
- the actual command assets and expanded-prompt transcripts for `/bookify`,
  `/bookify-source-faithful` and `/bookify-teachable-textbook`, including one
  conflict-resolution transcript; the default alias is recorded as
  source-faithful, not a third mode;
- the strict manuscript/PDF and the teachable manuscript/PDF, with the
  command-selected mode recorded in each authoring record;
- a teachable voice review with before/after excerpts and semantic paraphrase
  findings, not just exact-phrase checks;
- double-build hashes/page facts, verify gate, glyph/text/rights evidence;
- per-page inspection table and contact sheet path;
- enrichment positive/negative cases;
- workspace isolation evidence;
- the full test command and actual result;
- limitations and unverified items, stated plainly.

The catalogue is rebuilt or tested only as a regression. It is not required to
be the evidence book and its 19-page/30-figure inventory is not acceptance.

## 7. Boundaries

### Always

- Read the source before choosing structure; keep the source read-only.
- Let the selected slash command establish the mode; direct skill load falls back
  to the documented source-faithful default only when no mode is explicit.
- Resolve a genuine argument/entry conflict briefly; never silently switch modes.
- Record provenance, coverage, decisions and rights durably.
- Use the workspace for writes; never write into the engine install or an
  unrelated repository.
- Validate at the boundary; build and verify offline and model-free.
- Inspect every rendered page and keep the evidence.
- Preserve the public/private split and the current house aesthetic.
- Prefer reuse of proven helpers, tests, fonts, schemas and templates.

### Ask first

- Any external enrichment: permission, sources, citation detail.
- Any new source format, OCR capability, dependency, schema change, or
  multi-source intake.
- Any change to house-style tokens, approved compositions, rights policy, or
  the one-illustration-per-page rule.
- Installing or updating the global skill, publishing, pushing, or changing the
  packaging archive.
- Writing a workspace inside a repository the user did not designate.

### Never

- Silently transform a source-faithful request into teachable mode, or the
  reverse; silently override the mode established by the selected command.
- Add outside enrichment to `source-faithful`, or unpermitted enrichment to
  `teachable`.
- Replace the requested slash-command entry with CLI mode flags, a new web UI,
  duplicated JSON commands, or a redundant mode interview.
- Put `$ARGUMENTS`, source paths or other untrusted text inside `!` shell blocks,
  or hardcode `agent`/`model` in the command templates.
- Invent facts, values, labels, names, dates, categories, citations, licences,
  rights, or human review.
- OCR-guess an image-only page or claim a source format the tools do not verify.
- Require the user to author YAML, operate the CLI, or manage caches.
- Impose a mandatory developer pipeline or a universal approval gate on every
  skill user.
- Hardcode the catalogue, specimen, or original repository root as the required
  book shape.
- Apply a figure/page quota, filler illustration, or “same 19 pages” target.
- Rewrite the design system, delete proven helpers, or weaken tests.
- Claim byte-identical results from independent agent rewrites.
- Write into the engine, touch private history, or modify `pdf-book-design`.
- Merge private `main`/history into `public-main`, or publish private material.

### This specification stage

No product code, schema, dependency, font, asset, plan, task, package, global
skill, commit or push change is made. No test or build is claimed as executed.
The only artifacts are this file and
`.opencode/phase2-skill-specification.md`.

## 8. Measurable acceptance

Acceptance is deferred until approval and a separately approved plan. Each item
must be evidenced by a command, a test, a recorded inspection, or a file; no item
is satisfied by prose alone.

| ID | Acceptance criterion | Evidence required |
| --- | --- | --- |
| AC-1 | The agent entry is compact and discoverable: valid frontmatter, ≤ 250 lines, links to every reference, no full command transcript, no hardcoded catalogue/specimen requirement. | `tests/test_skill.py`; file inspection; packaged entry parity check. |
| AC-2 | The three slash entries work as specified: `/bookify` is the `source-faithful` default alias, `/bookify-source-faithful` is explicit strict, `/bookify-teachable-textbook` is explicit teachable. The selected command establishes the mode; no redundant mode interview or inference; a conflicting argument gets one brief resolution; `$ARGUMENTS` and composer attachments preserve source/language/audience/output preferences; the default alias is not a third mode. | Actual command assets loaded and expanded in `tests/test_skill_commands.py`; same-source command-driven exercise; conflict-transcript evidence. A `SKILL.md` string mention alone fails. |
| AC-3 | `source-faithful` follows source order/coverage: monotonic page anchors, every page covered/merged/excluded with a reason, every content block anchored, no external enrichment, no added teaching apparatus, unresolved material preserved. | Contract-check test on the same-source fixture; manuscript check; page/claim review. |
| AC-4 | `teachable` restructures and teaches without fake facts: documented reorder/regroup, teaching blocks recorded, every factual claim anchored or externally cited, unreadable material unresolved, no invented example presented as fact. | Contract-check test; manuscript check; page/claim review. |
| AC-5 | Enrichment is permissioned: strict rejects external material; teachable rejects unpermitted or uncited external material; teachable accepts a recorded, cited external source only after explicit permission. | Negative/positive tests with a local enrichment note; authoring-record assertions. |
| AC-6 | Provenance is complete: 100% of content blocks have a source anchor or approved citation; every coverage entry has a valid status/reason; every external source has a citation and stable locator; sampled claims from every page have zero unsupported assertions. | Contract checker + recorded agent fidelity review. |
| AC-7 | Visual quality is inspected, not counted: every rendered page has an inspection result; no blocking defect; material faithfulness, readability, hierarchy, whitespace, varied composition, typography, fitted labels, caption/credit integrity, one illustration per page, rights and xrefs are reviewed. | Per-page inspection table, contact sheet, verify report; no fixed page/figure quota. |
| AC-8 | Workspaces are safe: the engine tree is unchanged after a cycle; all book writes are inside the workspace; two books do not share mutable state; out-of-workspace build output fails clearly; legacy root behaviour still works. | Workspace tests with before/after engine hash; two temp workspaces; negative path test. |
| AC-9 | Repeat builds are reproducible without a model: two offline builds from the same manuscript/assets/pins agree on page facts and current byte-identity guarantee; deleting caches changes neither; build/verify make no model/network call. | Double build, cache-deletion run, guard/offline evidence. |
| AC-10 | Compatibility is preserved: no manuscript schema migration; existing manuscripts still validate/build; existing commands/defaults remain; the full existing suite passes without deleted/skipped tests. | Full suite result; schema diff review; old-fixture builds. |
| AC-11 | Packaging is safe and public: both entries carry the same contract; all three command assets and all references are packaged; manifest/relocation/source-denial tests pass; no private material or source-root path; `pdf-book-design` and global config untouched. | Packaging tests, archive inspection, manifest verification, preservation hashes. |
| AC-12 | Claims are sober: the report distinguishes agent inspection from human sign-off; no OCR/new-format/offline-install/byte-identical-rewrite claim; unsupported source input fails clearly; limitations are listed. | Report review against the limits section; unsupported-format negative test. |
| AC-13 | Teachable voice is natural standalone coursebook prose, not input metanarration: the §5.4 positive examples pass and weak examples fail a semantic review; paraphrases are reviewed, not only exact banned strings; citations, attribution, uncertainty and enrichment labels stay visible; inferred/unreadable evidence is never upgraded; permissioned enrichment remains cited. | `tests/test_skill_voice.py`; recorded voice review with before/after excerpts and paraphrase findings; provenance/uncertainty spot-checks. |
| AC-14 | Layout is legible page flow, not a page quota: measured body pitch 15.3 pt (Latin/Vietnamese) with the documented CJK residual, paragraph gaps wider than the line pitch, every role at its intended total, headings tighter than the old default, and chapter/minor-section hierarchy honoured. Level 1 starts a page (first body section never blanks), levels 2/3 flow, `breakBefore: page` is explicit, kickers stay with headings, plate units stay whole or fail by block id, table headers repeat, oversize units fail closed, contents lists all levels and may paginate, one illustration per page survives reflow. | Rendered `pdftotext -bbox-layout` measurements and hierarchy/keep/table fixtures (`tests/test_layout_correction.py`); public specimen and catalogue regressions; per-page inspection. |

## 9. Migration boundaries

- **Existing specs:** `SPEC-authoring-pipeline.md` stays as the historical
  approved spec. `SPEC-agent-skill.md` is additive; `SPEC-INDEX.md`,
  `capability-map.md`, `tasks/plan.md` and `tasks/todo.md` change only in a later
  approved plan.
- **Schema:** `schemas/manuscript.schema.json` remains `schemaVersion: "1.0"` and
  unchanged in this stage. The authoring record is a sidecar; if implementation
  later prefers manuscript metadata, that is an additive proposal needing
  approval, not a silent migration.
- **Workspace:** the current engine-root/build-dir rules stay as the default.
  `--workspace`/`BOOKIFY_WORKSPACE` is additive. The legacy `engine/work` path
  remains for existing commands but is not the new skill's default.
- **Command assets:** the three slash commands are proposed canonical files at
  `skill/bookify/commands/`, packaged later under `packaging/payload/commands/`.
  `.opencode/commands/` is ignored wholesale, so it cannot be the tracked
  canonical source; project-local installs there are optional and disposable.
  The future install step is separate from the skill-directory installer and
  must be collision-safe: no silent overwrite of an existing command or global
  config, explicit replace only after approval. No `/bookify*` command exists in
  the inspected project/global directories on 2026-11-12. No command is installed
  in this stage.
- **Decisions:** existing `build/authoring/decisions.jsonl` remains accepted.
  New durable records live in `authoring/`; no old book is rewritten.
- **Skill files:** `skill/bookify/SKILL.md` and `references/checklist.md` are
  rewritten later; existing composition/one-per-page/caption/verify tests stay.
- **Packaging:** `packaging/payload/SKILL.md`, `README.md` and the reference
  allowlist are updated later. The current helper packages only
  `references/checklist.md` from the local skill as a top-level reference; new
  references need explicit packaging entries. The installed global v1 skill has
  stale pipeline/licence wording and must not be edited in place; a future
  release replaces it only after approval.
- **Global skill:** `~/.config/opencode/skills/bookify` is prior v1 and is not
  modified in this stage. `pdf-book-design` remains separate and untouched.
- **Public/private:** `public-main` and public history stay public-safe. Private
  `main`/history, private development material, ignored `.opencode/` and
  `tasks/` history remain local and are never merged or pushed. No private
  lecture data returns to public fixtures.
- **Catalogue/specimen:** `content/catalogue.yaml` and `content/specimen.yaml`
  remain regression fixtures. The catalogue is not a mandatory book shape or
  figure inventory.
- **Tests and packaging:** existing reproducibility, security, rights,
  composition, offline and relocation tests are retained; new tests are
  additive. No test deletion or tolerance relaxation.

## 10. Open questions

Recommended defaults are stated; approval or correction is requested before
planning.

1. **Command installation scope.** Recommended: canonical source at
   `skill/bookify/commands/`, packaged under `packaging/payload/commands/`, and
   installed globally to `~/.config/opencode/commands/` for the reusable skill,
   with optional project-local copies into `.opencode/commands/` only with
   permission. Both install targets are collision-safe and no-clobber. Is the
   global install the intended default, or should commands be project-local only?
2. **Workspace mechanism.** Recommended: optional `--workspace` /
   `BOOKIFY_WORKSPACE`, engine assets read-only, book assets in the workspace.
   Alternative: copy the engine per book. The recommended option touches root
   discovery and build resolution; the alternative avoids engine changes but
   duplicates 100+ MB per book. Which is approved?
3. **Authoring record location.** Recommended: a sidecar
   `authoring/record.json` so the closed manuscript schema stays `1.0`.
   Alternative: additive manuscript metadata. The sidecar loses mode context if
   a manuscript is copied alone; the metadata route changes the contract. Which
   is preferred?
4. **Enrichment permission scope.** Recommended: per book, per source, recorded,
   with citation and local hash; no global “always allow”. Is a broader
   user-level preference wanted?
5. **First-release source formats.** The current intake code supports PDF text
   and embedded rasters only, with no OCR. Recommended: claim PDF only; treat
   DOCX/PPTX/HTML as later approved extensions. Confirm.
6. **Human visual review.** Recommended: agent inspects every page and records
   evidence; the user may review the final PDF, but no universal per-phase human
   gate is imposed. Is a mandatory human approval point wanted for each book?

## 11. Stage record

- Read: `.opencode/phase2-skill-intake.md`, including the appended “User
  specification refinements — commands and textbook voice”; current public
  `README.md`, `SPEC-INDEX.md`, `capability-map.md`,
  `SPEC-authoring-pipeline.md`, local and packaged skill entries,
  `skill/bookify/references/checklist.md`, `docs/build.md`,
  `docs/skill-bundle.md`, CLI, manuscript model, authoring helpers, intake,
  publish driver, schema, specimen and synthetic-trial fixtures, relevant tests,
  packaging helper and packaging tests.
- Consulted the actual OpenCode V2 commands documentation at
  `https://opencode.ai/v2/docs/commands` on 2026-11-12 for Markdown/JSON
  discovery, filename-to-slash-name mapping, `$ARGUMENTS`, positions, fallback,
  attachments, shell-block permission warning, frontmatter fields, reload and
  project-over-global precedence.
- Inspected the current project and global command directories: no `/bookify*`
  command exists; the global directory has unrelated commands. No command was
  created, installed or modified.
- Read `tasks/plan.md` and `tasks/todo.md` as ignored historical context only.
- Working tree was clean on `public-main` at `048d323` before the two spec files
  were created; this revision changes only those two spec files.
- No code, schema, dependency, font, asset, plan, task, package, global skill,
  commit or push change was made. No build or test was run or claimed.
- Status: **revised specification approved for planning 2026-11-12**;
  implementation plan approval pending at that stage. **Superseded
  2026-11-13 — see §13:** the user approved the plan; implementation,
  packaging and the verified global install are complete. Independent
  re-verification and human PDF sign-off remain unclaimed.

## 12. Stage record — Phase 2 layout correction (2026-11-13)

- User authorization, verbatim: “Proceed with the coordinated line-spacing and page-break layout changes.” Scope: `.opencode/phase2-layout-correction-scope.md` and `.opencode/phase2-layout-fix-intake.md`; pre-fix evidence: `.opencode/phase2-layout-review.md`, `.opencode/phase2-typography-diagnosis.md`, `.opencode/phase2-pagination-diagnosis.md`.
- Additive amendment: optional section `level` (1|2|3) and `breakBefore` (auto|page), `schemaVersion: "1.0"` retained; hierarchy semantics in `SPEC-manuscript-model.md`; leading/token semantics in `SPEC-design-system.md`; contents/table/unit-fit semantics in `SPEC-publish-engine.md`.
- This stage does not claim final Task 69 review, independent Task 71 tests, human PDF sign-off, packaging/global install, commit or push. **Superseded 2026-11-13 (see §13):** the later release stage packaged and installed the candidate with manifest `c2c354ebb1b7294a15a3cfdc97a896c37f29ac7837fa2094ab610bca518848f0`; Task 69 review is complete in `.opencode/agent-skill-review.md`, and Task 70 iteration 1 applies the R1–R4 fixes. Independent Task 71 re-verification and human PDF sign-off remain unclaimed.
- The two trial books are not re-authored in this stage; their mode authors restyle after the engine correction is proven. The source fixture remains unchanged.

## 13. Status reconciliation — approved, implemented, reviewed and released (2026-11-13, append-only)

Sections 11–12 above are retained as history. Current evidence-backed state:

- **Approval.** The user approved the revised specification and the
  implementation plan; `.opencode/phase2-skill-execution.md` records “User
  approved spec and plan”. The earlier “plan approval pending” status is
  superseded, not deleted.
- **Implementation.** Tasks 57–68 and 73–76 are implemented: the three slash
  commands and six guides, the durable authoring record and contracts, the
  external engine-read-only workspace, the packaging helper and no-clobber
  command install, the public-safe same-source fixture, both mode books, and
  the command-driven acceptance suite. The independent layout stage is
  `.opencode/phase2-layout-tests.md`.
- **Review and fix.** Task 69 review is `.opencode/agent-skill-review.md`
  (REQUEST CHANGES, Required R1–R4). Task 70 iteration 1 fixes R1–R4 with
  focused regression tests; details and commands are in
  `.opencode/agent-skill-fixed.md`. No tolerance was relaxed and no test was
  deleted or skipped to obtain green.
- **Verified release.** Archive `dist/bookify-skill-plan2-layout.tar.gz`
  SHA-256 `4beb973a481a689b5f06010aa9505586403b29a1f84b87fb9f433eeb646f4c36`,
  58,420,387 bytes, 251 members; manifest
  `c2c354ebb1b7294a15a3cfdc97a896c37f29ac7837fa2094ab610bca518848f0`;
  `--check-determinism` identical. Installed by successive verified-ownership
  upgrades from the prior manifests `aaff7de7…` and `99f409bd…`, with the
  final backup `~/.config/opencode/backups/bookify-agent-skill-fix1b-2026-11-13`;
  `verify-install` reports 251 files and `verify-commands` passes.
- **Rebuilt books (page counts unchanged).** Specimen 5 pp
  `2d687e08f902c945e13bac0d4b7e130a145781ed8266a772a842eb6897297372`;
  catalogue/example 19 pp
  `3f5055c4902e11228843dc322ed910d120c63e9b5c799e3139c27b63c32541ed`;
  source-faithful 5 pp
  `b72fac8ad40cb133001101d30cdc8c00e1d02efbce60dc912b35f71c1a666299`;
  teachable 5 pp
  `7ae08d4bd11840922bb191798e5686d4fbf6b7f4814d0d4f50a27e7d0d75323d`.
  R1’s level-1 deck gap measures 32.74–32.75 pt with a 3.36–3.60 pt 300 dpi
  white band; body 15.30, Japanese 15.99 and paragraph gap 20.70 are unchanged.
- **Not claimed.** Task 71 independent re-test, Task 72 final closure,
  Checkpoint Q/R and final human PDF sign-off remain open. No commit, push,
  dependency, font or mode was added. Optional O1/O3/O5 are recorded, not
  forced.

## Amendment — Bookify v2 design guidance (2026-11-14)

Owner-approved guidance update per `SPEC-bookify-v2.md` §8. The skill keeps
three commands and two modes; no new mode, command, dependency or mandatory
pipeline is added. OCR guidance is a separate workstream and is not claimed here.

### Guides changed

| File | Change |
| --- | --- |
| `SKILL.md` | States the generated design defaults (cover, numbering, definitions, openers, plates, captions, rhythm) and the readability/warning contract, and links the expanded visual guide. |
| `references/visual-design.md` | Adds the D1–D7 defaults and a readability-judgement section; updates the caption/provenance rule and the common-failure list. |
| `references/editorial.md` | Defines the inline definition convention and when a collated glossary is allowed; no transform, no invented numbers. |
| `references/checklist.md` | Adds D1–D7 self-checks and the readability review with answered warnings. |
| `packaging/payload/SKILL.md` | Carries the same default summary in the portable entry point; the bundle is regenerated by the integrator. |

### Authoring defaults the agent must apply

1. Never render a definition as a label. A glossary is a deliberate collated
   table, not a transform.
2. The cover is generated from metadata and the resolved chapter index; never
   write cover markup or invent a year, edition, ISBN or city.
3. Numbering is structural. Never type numbers into titles; author appendices
   with `role: appendix`.
4. Choose one plate per chapter where the material supports a visual; record a
   `no-plate` reason otherwise. Never fabricate a visual or a number.
5. Description and provenance share one centred caption; credits stay separate.
6. Do not add manual heading spacing; no stacked headings.
7. Read every rendered page and record a readability result. Answer every verify
   warning id in the review notes with a reason or fix the page. Density is not a
   target and never a quota.
