# Voice and source review — teachable textbook trial (revision 2)

Status: **agent-authored, agent-inspected; not human review.** Mode `teachable`,
entered through `/bookify-teachable-textbook`. The book is
`content/agent-skill/teachable/book.yaml`; the built PDF is
`content/agent-skill/teachable/evidence/teachable-textbook.pdf`.

Revision 2 re-authors the same six-page source under the corrected leading and
the additive section hierarchy. It changes grouping, paragraph boundaries and
the closing apparatus; it does not add a source fact, an outside source or a new
asset. This file records the semantic voice read, the real before/after
excerpts, the source-fact mapping, the reflowed page inspection, the defects
fixed here, and the limits of the evidence.

## What was read

- `fixtures/agent-skill/source.pdf` was read directly, not only through its
  README: all six pages were rendered at 100 dpi and inspected, and the intake
  text and image facts were checked against `intake/manifest.json`.
- Page 6 is image-only, with no text layer. No OCR was run and no label, date,
  place or warrant was assigned to it.
- The source order is deliberately not pedagogical: page 1 is the case, page 2
  the record, page 3 the three definitions, page 4 the counts, page 5 the
  uncertainty note and page 6 the unreadable plate. Page 3 refers back to “the
  case of the two labels”, so the case has to be available before that
  application is read.
- Inputs for this revision: `.opencode/phase2-layout-tests.md` (READY; body
  15.30, paragraph gap 20.70, heading hierarchy working),
  `.opencode/phase2-layout-fixed.md`, `.opencode/phase2-layout-correction-scope.md`,
  the existing teachable artifact and `phase2-skill-teachable.md`.

## Reorganisation and hierarchy

The book uses the source pages in the order **3, 1, 2, 4, 5, 6**:

1. page 3's definitions and three questions come first (concept before case);
2. page 3's application paragraph is split off and follows page 1's case;
3. page 2's record follows the reading it is meant to keep;
4. pages 4–6 keep their source order: counts, uncertainty, plate.

Revision 2 changes the *grouping*, not the order. One level-1 chapter now holds
eight level-2 sections that flow instead of one long chapter plus a page-broken
source note. Printed pages from the build report:

| Section | Level | Page |
| --- | ---: | ---: |
| Reading a sample | 1 | 3 |
| Three levels of reading | 2 | 3 |
| Two labels and a moved sample | 2 | 3 |
| The record | 2 | 3 |
| Comparing counts | 2 | 4 |
| When the evidence stops | 2 | 4 |
| What the chapter established | 2 | 4 |
| Key terms | 2 | 5 |
| Source note | 2 | 5 |

The source note is a **flowing minor closing section**, not a page-broken
standalone unit. The four terms recap in `Key terms` is a source-anchored
learning aid: the same definitions and the same Count statement, no new claim.
It is kept whole on page 5 so the recap and the source note close the book as a
reference unit; the recorded reason is `d-reference` in the authoring record.

## Voice review: real before and after

The “before” excerpts are the stored revision-1 text. The “after” excerpts are
the revision-2 manuscript and the rendered PDF.

### Opening: a roadmap sentence became a teaching sentence

Before:

> Three levels do that work: the visible detail, the setting that gives it
> meaning, and the warrant that supports the reading. This chapter sets out the
> levels, applies them to a small case, and keeps the result in a record that
> can carry its own limits.

After:

> Three levels do that work: the visible detail, the setting that gives it
> meaning, and the warrant that supports the reading. This chapter applies them
> to a small case, keeps the result in a record that can carry its own limits,
> and shows what a count of that record can and cannot support.

Critique: the old last sentence listed the chapter's contents. The new one names
the chapter's movement and, in the same breath, the limit of the count that the
chapter will teach. The source fact is unchanged; the sentence now does work
instead of announcing work.

### Application: a one-sentence fragment rejoined its paragraph

Before, two paragraphs:

> A visible detail is not yet a setting, and a setting is not yet a warrant. The
> two labels are details. Their order is part of the setting. The recorded order
> is the warrant for reading them as a sequence rather than a contradiction.
>
> Those three terms carry the rest of the book: what is here, what it means
> here, and why the reading should be accepted.

After, one paragraph:

> A visible detail is not yet a setting, and a setting is not yet a warrant. The
> two labels are details. Their order is part of the setting. The recorded order
> is the warrant for reading them as a sequence rather than a contradiction.
> Those three terms carry the rest of the book: what is here, what it means
> here, and why the reading should be accepted.

Critique: the source's closing sentence is a paragraph-terminating claim, not a
new thought. As its own paragraph it looked like an orphaned aphorism. Rejoined,
it returns the reader to the three terms without changing a word of the claim.

### Record: the unresolved rule and its consequence share a paragraph

Before, two paragraphs:

> If a field cannot be filled, write unresolved. An empty field is not a zero
> and not a guess. The origin in the case stays unresolved because no record
> supplies it.
>
> The levels test a reading; the record keeps the reading and its limits
> together. A later reader can see what was observed and what stayed open.

After, one paragraph:

> If a field cannot be filled, write unresolved. An empty field is not a zero
> and not a guess. The origin in the case stays unresolved because no record
> supplies it. The levels test a reading; the record keeps the reading and its
> limits together. A later reader can see what was observed and what stayed open.

Critique: the second paragraph is the consequence of the first. The old break
made the consequence sound like a new topic; the merge makes one argument:
rule → consequence → reader.

### Counts: the caution belongs with the reading

Before, two paragraphs:

> The totals are small and invented. The second pass added details and warrants,
> but the count of settings did not change. A longer list of details does not by
> itself add warrants.
>
> Read the table as a question about coverage, not as evidence that the sample
> is better understood.

After, one paragraph:

> The totals are small and invented. The second pass added details and warrants,
> but the count of settings did not change. A longer list of details does not by
> itself add warrants. Read the table as a question about coverage, not as
> evidence that the sample is better understood.

Critique: the one-sentence second paragraph read as a caption outside its
figure. Merged, the sequence is totals → change → warning → how to read, and the
synthetic values are still marked as invented.

### Case heading: no duplicate title

Revision 2 introduces a level-2 heading “Two labels and a moved sample”. The
case block therefore no longer repeats that title as its role label; it is
labelled “The case”. This is a presentation fix, not a content change: the same
case text and synthetic note follow.

## Paraphrase critique, not a string blacklist

The test applied remains: **if the source document did not exist, would this
sentence still teach the subject?** A sentence that only makes sense as
commentary on an input fails, even without a banned string.

No input-report grammar was introduced in revision 2. The following paraphrases
were rejected while drafting:

- “The notes show that…” / “The source's account of…” / “The material argues
  that…” — still a report on a document.
- “As the reading exercise explains…” — frames the book as commentary.
- “According to the supplied text…” — distances the reader from the claim.
- “This page argues…” — confuses the source page with the book's page.

Three kinds of source reference are deliberately kept:

1. the source note (“This book teaches from the six-page synthetic source *Notes
   on Reading a Sample*”), where attribution is the point;
2. the page index and the split decision (“Page 3 is split…”), which are
   provenance statements, not teaching prose;
3. the direct quotation “A claim should carry its evidence.” with its
   “Synthetic source note” attribution.

“The record can be summarised as counts” was kept because it is the subject's
own claim about the method, anchored to page 4 — not a report about what an
input says.

## Source-fact mapping

Legend: **direct** = stated in the source, rephrased for the page; **condensed**
= several source sentences compressed; **derived** = a logical application of
the source's own definitions, labelled as such; **framing** = the book's own
pedagogical connective, asserting no source fact.

| Book claim or block | Source | Status |
| --- | --- | --- |
| Detail / setting / warrant definitions | p3 | direct |
| Key terms recap of the same definitions | p3 | direct |
| The three questions (“What is here?”, …) | p3 | direct |
| “A description can be right at one level and unsupported at another.” | p3 | direct |
| Two labels, one before the move and one after | p1 | direct |
| “The difference is a change of place, not a contradiction.” | p1 | direct |
| Origin not recorded; remains unknown | p1 | direct (unresolved value kept unresolved) |
| The labels are details; their order is the setting; the recorded order is the warrant | p3 | direct |
| Four record fields: label, time, place, status | p2 | direct |
| Record table is a checklist, not a measurement | p2 | direct (caption) |
| “If a field cannot be filled, write unresolved.” | p2 | direct |
| “An empty field is not a zero and not a guess.” | p2 | direct |
| Counts 12/15/+3, 7/7/0, 4/6/+2 | p4 | direct; explicitly synthetic |
| “A count records how many entries were made, not how strong they are.” | p4 | direct (Count definition and Key terms) |
| “A longer list of details does not by itself add warrants.” | p4 | direct |
| “Read the table as a question about coverage…” | p4 | direct |
| Plate is image-only, no text layer, unresolved | p5, p6 | direct; no OCR or label |
| “A claim should carry its evidence.” | p5 | direct quotation, attributed |
| “This is not a gap to fill with a plausible name.” | p5 | direct |
| Short check on the plate | p5 | direct, rephrased as a task |
| Model answer: the image can be recorded as a detail; no setting or warrant can be read | p5, p6 | derived from the source's definitions; block is `inferred` with a note |
| Chapter summary | p2–p5 | framing; compresses the chapter, adds no fact |
| Source note and source index table | p1–p6 | attribution/index; no interpretive claim |
| “Synthetic case, written for this exercise…” note | p1 | direct |
| Count definition / counts synthetic statements | p4 | direct |

No fact is presented as a measurement. The counts are the only numeric claims;
they are labelled synthetic in the caption, the introduction and the source
note.

## Page inspection after reflow (all five rendered pages)

Rendered with `pdftoppm -png -r 110`; every page was opened individually, not
only viewed on the contact sheet. Occupancy is the content bottom measured
inside the 60 pt text frame, not a density target.

| Page | Result | Occupancy | What was seen |
| --- | --- | ---: | --- |
| 1 Cover | pass | 0.42 | Title and subtitle on a quiet page; no invented author, institution or affiliation. |
| 2 Contents | pass | 0.22 | Nine entries, chapter plus indented level-2 sections; printed pages 3–5; xrefs confirm all nine. |
| 3 Chapter opening | pass with attention | 0.96 | Chapter title, standfirst, opening lead; three level-2 headings; definitions, question list, the case, and the record table with its caption at the foot. No overflow. Attention: the h1 descender sits close to the standfirst (engine h1→standfirst gap 26.74 pt); the same tightness is visible on the public specimen rebuilt under the same correction, so it is a shared house-token observation, not a revision-2 defect. |
| 4 Counts and limits | pass | 0.91 | Record close and first check, counts definition/intro/table/reading, the quotation, the unresolved note, the plate check and model answer, and the chapter summary. Role labels break the units; nothing overflows. |
| 5 Key terms and source note | pass | 0.58 | The four-term recap, then the source note and six-row index table close the book. The empty space below is the end of the book, not a deferred composition; the page previously fell to about a third when the source note was isolated or left flowing with only a paragraph tail. |

No split composition, orphaned heading, detached caption, cramped role label or
broken cross-reference was found. There are no illustrations, so the
one-illustration-per-page and credit checks are vacuous and pass.

## Defects found and fixed during this revision

1. **Near-empty closing page.** The first reflow left the source note flowing
   after the summary, so page 5 held only a paragraph tail and the index (about
   a third of the text frame). Isolating the source note on its own page was
   about 35 %. Fixed by keeping the source note as a flowing minor section and
   adding the source-anchored `Key terms` recap, kept whole on page 5; the page
   now reads as a deliberate reference close at 58 % occupancy.
2. **Four one-sentence fragments.** The terms sentence, the record close, the
   count caution and the plate-reproduction sentence were merged into the
   paragraphs they belong to (meaning unchanged; recorded as `merge`
   derivations).
3. **Duplicate case title in draft.** The level-2 heading and the case role
   label both said “Two labels and a moved sample”. The role label is now “The
   case”.
4. **Key terms split at a page foot.** With the recap flowing, only “Detail”
   fitted at the bottom of page 4. A deliberate `breakBefore: page` keeps the
   four-term recap together on page 5 (recorded as the reference-unit decision).
5. **Split source-note paragraph.** Before the final grouping, the first source
   note paragraph broke after “none is” and continued “a measurement.” on the
   next page. The final page keeps the attribution paragraph intact.
6. **Record caption under-stated the source.** The source says the record table
   is “a checklist, not a measurement”; the caption now says so, rather than
   only calling the entries synthetic.

## Limits and non-claims

- This is agent visual inspection and a semantic read, **not human sign-off**.
- No outside research was used or permitted. `enrichment.requested` is `false`,
  `permission` is `null`, and there are no external derivations.
- No OCR was run. Page 6 remains unresolved; no label, date, place or warrant
  was guessed. The plate is not reproduced: it has no text layer, and a copy
  would add no evidence the record can use.
- No new image, font, dependency, service or network call was introduced. The
  tables are vector text in the existing house style.
- The counts are invented for the exercise and are not measurements.
- The same stored manuscript, assets and pins rebuilt byte-identical PDFs in the
  two offline builds. That is not a claim that two independent agent rewrites
  from the same source would be byte-identical.
- The record proves traceable decisions, coverage and mode mechanics. It cannot
  prove that the prose is true or that a worked example is pedagogically sound;
  those remain the agent's semantic review, recorded here.
- The h1→standfirst gap (26.74 pt) is tight against a descender. It is a shared
  design-token observation also visible on the public specimen rebuilt under the
  same correction; no engine or token was changed in this authoring revision.

## Hashes and size

| Artifact | Value |
| --- | --- |
| Source PDF | `2c751d32ba89126b996db5045814e6ed2dc03468f0785ba74c3d28077f4ae1be` |
| `book.yaml` (revision 2) | `cfdd084660f6f24935ce1b700b7e90c451c336acf1e10444228432d8c3ef0b5a` |
| `authoring/record.json` | `80e6c12782955a910bdb687f1fc5465cbc75a453592afee57adc7d36ad52fc4b` |
| `evidence/teachable-textbook.pdf` | `a678b1a4c9d1c8f59a62f6aaf18430727d11780aaa898aca70fd97c069a7608f` (5 pages, 85,313 bytes) |
| Rebuild PDF | same hash (byte-identical) |
| Contact sheet | `c6df2cdc87469727c03d90b07ba992d938af5d0f6befd9d4169ce4983e29156f` |
| Verify report | `b9534ee862b37ca42a78a701476497361b8a976bf4ffd37693d3b19989d3c371` |
| Build report | `16b79095ff98b82cef9de9f7077ebcde93c6a9d00997b45bbf052d91f02d165c` |
| Measurements | `3a6dd3ddd565ebce6dd43aa66d3bbe25ade00c75ab5f4bc9f24818bf3616919d` |

Book page text (`pdftotext -layout`, form feed and trailing newline removed):

| Page | Characters | Text SHA-256 |
| --- | ---: | --- |
| 1 | 92 | `b5dfa667408ed8fecea4ecb019f583e161cf606f53192c26fd3203766ed6b7e3` |
| 2 | 1,995 | `7a3f6d3d11f99f5d543c634e6fab7a54f2cd0b2eb8a12c14bd20cbe5b7c4bee2` |
| 3 | 2,797 | `392297fa015666acc60311efdeef351b44bfa2363045943a1ee813b4d4f93e4b` |
| 4 | 2,989 | `a5c8c6a8bea6ccae90ba05d3debba36781b19e7fb47a4af038dd08a096b74816` |
| 5 | 1,771 | `6d4aeeb10e3a6a3646d21fe38fd93b1d1b3468486421b5718659eb4483b5873f` |

## Command and mode record

- Entry: `/bookify-teachable-textbook` (the canonical command asset was read and
  followed). Mode: `teachable`; it was not inferred from tone and no mode
  interview was held.
- Supplied source: `fixtures/agent-skill/source.pdf`, attached for this trial.
  No `@path` expansion was relied on; the path was resolved by the agent.
- Arguments preserved: English; standalone coursebook; no external research;
  preserve source coverage, page index and uncertainty; teach from source facts.
  There was no mode conflict to resolve.
- Build and verify ran in the external workspace
  `/tmp/opencode/phase2-books/teachable-rework`, offline, with pinned Typst
  0.15.1 and Python 3.13.16. No build ran inside the engine tree.
- This is an authoring-agent trial, not a registered command-runner execution.
  The packager/command tests prove command registration separately.
