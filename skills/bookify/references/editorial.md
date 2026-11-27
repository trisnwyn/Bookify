# Editorial judgement and coursebook voice

The book is written for its reader, not about its input. This guide covers the
editorial decisions the agent owns: chapter architecture, explanation, examples,
checks, summaries, and the natural coursebook voice required in `teachable`
mode. Provenance mechanics live in `source-and-provenance.md`; mode contracts in
`modes-and-playbooks.md`.

## The voice principle

Teachable prose is natural, standalone coursebook prose. The reader should meet
the subject directly, not a report on what a source file said.

- State the teaching point directly. Lead with the claim or question, then
  support it.
- Use pedagogical transitions (“First”, “This matters because”, “A worked case
  makes the distinction concrete”), not source-report transitions.
- Define a term where the reader first needs it. A definition is printed inline
  as one body paragraph: bold term, colon, definition. Do not put the term on
  its own line or in a grey label.
- Collate a glossary only when the book needs a lookup list; it is an authored
  table with a caption, not a transform of every definition. A glossary in
  `source-faithful` mode exists only when the source supplies it.
- Make clear claims, including the limits of a claim.
- Work through at least one concrete example or case where the material carries
  one.
- Give a short check that uses the chapter's own vocabulary.
- Close with what the reader can now do; do not repeat the chapter.

The book is not a transcript, a summary of slides, or an annotated bibliography.
The agent's own pedagogical framing is allowed in teachable mode; it must be
honest about being framing, and it may not smuggle in facts.

## Before and after

These examples are the required contrast. “Weak” is input narration: the prose
reports on the source instead of teaching. “Better” states the idea directly and
keeps provenance where it belongs.

### Definition

Weak — input narration:

> The materials provided suggest that a definition matters. The slides explain that a definition fixes a term. Based on the provided content, we can see that examples are useful.

Better — direct coursebook prose:

> A definition fixes the meaning of a term so later claims can be tested against it. An example then turns that abstract distinction into something a reader can inspect. [source note or reference]

### Uncertainty

Weak — input narration:

> The course says the label cannot be read. The provided materials leave this unclear.

Better — direct coursebook prose:

> One label cannot be read. The book marks the gap as unresolved rather than guessing a value. [uncertainty note]

### Explanation

Weak — input narration:

> The provided materials suggest that the two categories differ. The slides
> explain the difference in a later section.

Better — direct coursebook prose:

> The two categories differ in what they count. A count records occurrences; a
> rate records occurrences per unit. The distinction matters because a count can
> rise while the rate falls. [source note]

### Summary

Weak — input narration:

> Based on the provided content, this chapter has explained several things.

Better — direct coursebook prose:

> You can now distinguish a count from a rate, and say why an apparently rising
> number can hide a declining trend. [source note]

## Semantic paraphrase review

Exact banned-phrase checks are regression aids only: they catch a few known
constructions and nothing else. The real review is semantic and happens on the
rendered prose.

For every chapter or page of a teachable book, read the prose and ask:

1. Does this teach the concept directly, or does it report what the input says?
2. Does every factual claim have a legitimate anchor or citation?
3. Are attribution, quotations, uncertainty and enrichment citations still
   visible and accurate?
4. Does the chapter keep repeating “the source/material/course/slides/provided
   content” instead of making its own argument?
5. Has any inferred or unreadable value been upgraded into a verified claim?
6. Is the chapter's own pedagogical framing visible where it could be mistaken
   for a source fact?

Record the finding per chapter/page: direct, needs revision, or blocked, with
the reason. Revise paraphrases, not only exact strings. A paraphrase of “the
provided materials suggest” fails even when the words differ. This review is not
automated; it is an agent read with recorded findings, and it is not human
sign-off.

Regression aids (use only as a sweep, not the whole gate):

- the provided materials suggest / the provided content shows;
- the course says / the slides explain / the source describes;
- “based on …” openings that frame the chapter as a report.

If a sweep finds one of these, fix it. If the sweep finds nothing, the semantic
read still decides.

## Keeping provenance without narrating the input

Citations, attribution and uncertainty are not obstacles to voice; they are part
of a trustworthy coursebook.

- Put citations in notes/endnotes, a reference list, captions, credits, a source
  index or the authoring record. Do not delete attribution to make the prose
  sound more confident.
- Quote directly where the exact words matter; name the source when naming it is
  the point.
- Keep an uncertainty note next to the uncertain claim, not buried in a cache.
- Label enrichment where it appears and record permission and citation in the
  authoring record.
- Never upgrade inferred or unreadable evidence into a verified claim, and never
  imply that an unsourced statement is source-verified.
- Never hide uncertainty to improve the voice. A confident sentence resting on an
  unresolved label is a defect, not a style improvement.

The correct exception to “do not name the input” is when attribution, a direct
quotation, an uncertainty note or an enrichment citation is itself the point.

## Chapter architecture

`source-faithful`:

- Follow source order and coverage. Improve headings, standfirsts, transitions,
  captions and typography.
- Do not add objectives, exercises, glossaries, examples or “further reading”
  unless the source supplies them; retained source exercises count as source
  content.
- A strict chapter's job is faithful, readable presentation, not a new argument.

`teachable`:

- Choose the smallest architecture that carries the material: one chapter for a
  short source, a sequence of chapters for a longer one.
- Give each chapter one job the reader can state.
- Sequence by dependency: define before using, show before asking the reader to
  apply.
- Move, merge or split source units when understanding improves; record every
  reorder, merge, split and omission with a reason.
- Keep source anchors on factual blocks even after reordering.

## Teaching apparatus that earns its place

- **Objectives** state what the reader will be able to do, not what the chapter
  covers.
- **Definitions** are short, used immediately, and consistent with the source's
  own terms.
- **Examples** are concrete and labelled if illustrative. A worked example should
  expose the reasoning, not just the answer.
- **Checks** ask the reader to use the chapter's vocabulary; they are not trivia.
- **Summaries** compress the argument, not the table of contents.
- **Glossaries** are a reference aid; do not use one to avoid explaining terms in
  place.

Do not add apparatus to fill space. An apparatus block that adds no understanding
is noise, and in strict mode it is a contract violation.

## Exercise and practice workspace design (human error-recovery rule)

Whenever a book includes exercises, practice problems, self-checks, or workbook
drills (`assessment` blocks or fill-in-the-blank tables), design every answer
area for **real human practice on paper or tablet**. Humans do not write final
answers in one clean pass: they make arithmetic or sign slips, cross out false
starts, erase, write larger than printed type, and revise intermediate steps.
Never size an answer zone to the tight footprint of a printed solution — build
in **+30–50 % error-recovery slack** adapted to the exact exercise format:

1. **Short-answer and paragraph questions:** Use `responseSpace: {kind: lines}`
   with full-measure dotted or ruled write-in lines at handwriting pitch
   (`24 pt`, never print body leading). Always add extra lines beyond the ideal
   answer length (minimum 3–4 full lines even for a 1–2 sentence prompt; 6–10+
   lines for a paragraph explanation) so a crossed-out sentence still leaves
   room to finish cleanly.
2. **Multi-step mathematics, derivations, and proofs:** Never put tight ruled
   single lines under equations or proofs — fractions, integrals, summations,
   matrices, and cancelled terms collide with horizontal rules. Use
   `responseSpace: {kind: grid}` (subtle dot-grid scratchpad) or `{kind: blank}`
   sized for the expected derivation **plus at least one false start**
   (`heightPt: 120–160` for short calculations; `180–260` for multi-step proofs).
3. **Fill-in-the-blank tables, truth tables, matrices, and ledgers:** Set
   `fillSpace: true` and `extraRows: 2` (or more) on the `table` block so every
   writable cell has generous vertical padding (2×–3× print height, letting a
   learner strike through a wrong value and write the correction inside the same
   cell) **plus** extra blank overflow rows at the bottom for re-attempts.
4. **Inline cloze / fill-in-the-blank sentences and equation blanks:** Make
   every inline blank at least **2× the printed width** of the expected term
   (or break to a full-width dotted line when a phrase is expected) so a
   handwritten correction never collides with adjacent printed words.
5. **Graphing, curve sketching, and geometric constructions:** Use
   `responseSpace: {kind: coordinate}` with generous outer axis margin so
   learners can rescale axes or correct mislabelled tick marks without writing
   over the problem statement.
6. **Diagram labelling and annotation:** Keep label callout boxes and leader
   lines wide and tall enough for handwritten terminology plus a crossed-out
   retry; never crowd label lines against the figure edge.
7. **Multiple-choice, true–false, and matching with justification:** Use
   `responseSpace: {kind: choices}` with generous vertical spacing between
   options (so changing a marked box stays readable) and 2–3 dotted
   *"Reasoning / revision space"* lines underneath.
8. **Code tracing, dry-run state tables, and algorithm walkthroughs:** Use
   `responseSpace: {kind: trace}` with explicit overflow rows (learners often
   miscount loop bounds or off-by-one steps) and a dedicated `"Scratch"` column
   for intermediate values.
9. **Worked-example → "Your turn" drills and multi-part `(a)/(b)/(c)` problems:**
   Place a dedicated response space immediately after **each** sub-part rather
   than stacking `(a)`, `(b)`, `(c)` back-to-back above one ambiguous blank box.
10. **Keep-together & readability honesty:** Never strand a problem prompt at
    the bottom of a page while its write-in area jumps to the next page (the
    engine keeps compact exercises unbreakable and anchors longer stems to
    their workspace). Never shrink practice whitespace merely to chase a higher
    words-per-page metric; record deliberate exercise pages in review notes if
    a thin-page warning fires.

## No fake facts, no upgraded evidence

- Every number, name, date, category, citation and quotation must come from the
  source or from a permitted, cited external source.
- An illustrative example or invented scenario is allowed only when labelled
  illustrative; never present one as a real observation or measurement.
- A reconstruction is a reconstruction, not documentary evidence.
- Do not resolve an unreadable label by plausibility. Use `unresolved`, `null`
  with a note, or an explicit uncertainty statement.
- Do not convert “about 40” into “40”, or an inferred relationship into a stated
  fact.
- Do not fabricate a citation to make a claim look grounded. A claim without a
  legitimate citation is unsupported and must be removed, qualified or recorded
  as unresolved.

## Review worksheet

For each chapter:

- [ ] One sentence stating what the chapter teaches.
- [ ] The opening teaches, rather than announces the source.
- [ ] Terms are defined before use.
- [ ] One concrete example or case, labelled if illustrative.
- [ ] One check that uses the chapter's vocabulary.
- [ ] Every factual claim has an anchor or an approved citation.
- [ ] Attribution, quotations, uncertainty and enrichment labels are visible.
- [ ] No recurring input narration, including paraphrases.
- [ ] No invented or upgraded fact.
- [ ] Finding recorded: direct / revised / blocked, with the reason.
