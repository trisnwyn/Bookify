# Modes and playbooks

One authoring capability, exactly two modes. The command entry chooses the mode;
the mode decides what may be added to the source.

## Entry and authority

| Entry | Mode | Notes |
| --- | --- | --- |
| `/bookify` | `source-faithful` | Default alias. It is a third *entry*, not a third mode. |
| `/bookify-source-faithful` | `source-faithful` | Explicit strict entry. |
| `/bookify-teachable-textbook` | `teachable` | Explicit teachable entry. |

- The selected command establishes the mode. Do not ask which mode to use, and
  do not infer a mode from tone, vocabulary or the shape of the source.
- Direct skill load without a command is a fallback: use the documented
  `source-faithful` default only when the request names no mode; honour an
  explicitly named mode.
- A conflict between the entry and the arguments is not a mode interview. State
  it and ask for one brief resolution.

Examples:

| Request | Correct response |
| --- | --- |
| `/bookify` + “turn this into a teachable course with exercises” | “This entry is source-faithful. I can keep that contract, or you can use `/bookify-teachable-textbook` for the coursebook treatment. Which do you want?” |
| `/bookify-teachable-textbook` + “keep the original order exactly” | “Teachable reorganises and adds teaching apparatus. I can keep this exact order within the teachable contract, or switch to `/bookify-source-faithful` for a literal strict book. Which?” |
| `/bookify-source-faithful` + “add a chapter summary” | Ask once whether the summary is source content. If it is not, it is teaching apparatus and belongs in teachable mode. |
| “Make me a book from this PDF” (direct load) | `source-faithful`, because no explicit mode was named. Do not ask a mode question. |

A requested mode change starts a new authoring decision. Never transform an
existing revision silently in either direction.

## The strict playbook: `source-faithful`

1. Read the source in page order. Note its own sectioning, headings, figures,
   tables and exercises.
2. Build the content inventory: each source unit, its page anchor, and whether it
   is covered, merged with another unit, or excluded. A merge or exclusion needs
   a reason. Omitting a whole page without a recorded reason is a coverage
   failure.
3. Flatten content into manuscript blocks in source page order. Within a page,
   preserve the source's own order and review any merge.
4. Write presentation-only text: section titles, standfirsts, captions,
   transitions and cross-references. Test every sentence: does it assert a
   fact, number, name, date, category, causal claim or citation? If yes, it is
   content and needs an anchor. Presentation may improve the reading experience;
   it may not add knowledge.
5. Keep source-supplied citations and quotations as source content. Do not add
   outside material, reading lists, exercises, glossaries or “further reading”.
6. Mark unreadable values `unresolved` or `null` with a note. Mark redrawn
   figures as reconstructions and keep the source's approximate values
   approximate.
7. Record every omission, merge, redraw and unresolved item with a reason.
8. Render the PDF and compare it against the source's coverage. A strict book can
   be denser and better typeset; it cannot be a different argument.

Useful invariants:

- Anchors are monotonic with source order unless a deliberate merge is recorded.
- Every content block has at least one anchor.
- No derivation kind from the teaching set (`explain`, `example`, `assessment`,
  `glossary`) appears unless the source itself supplies that content and the
  block is retained as source content.
- No `external` derivation and no enrichment source.

## The teachable playbook: `teachable`

1. Read the whole source before deciding the chapter architecture. Ask what a
   reader should be able to do or explain after each chapter.
2. Group, reorder, merge or split source units where that serves understanding.
   Keep every original anchor. Record each reorder, merge, split and omission as
   a derivation with a decision.
3. Write a chapter that stands on its own:
   - open with the problem or question the chapter answers, not with “this
     chapter covers the source's section 3”;
   - define a term where the reader first needs it, not in a glossary dump;
   - make the central claim explicitly;
   - work through one concrete example or case where the material supports it;
   - add a short check or reflective question that uses the chapter's own
     vocabulary;
   - close with what the reader can now do, without repeating the whole chapter.
4. Keep facts source-grounded. Your own pedagogical framing, analogies and
   illustrative examples are allowed and must be labelled as framing or
   illustrative when they could be mistaken for observations. A fabricated
   statistic, quote, name or citation is never acceptable, and a plausible
   example is not a source fact.
5. Put citations and provenance where a reader expects them: a note, reference
   list, caption, credit, source index or the authoring record. Naming the source
   is correct when attribution is the point.
6. Record teaching derivations: `explain`, `example`, `assessment`, `glossary`,
   `condense`, `split`, `merge`, `reorder`, `heading`, `caption`. Record external
   material as `external` with a permission record and a citation.

### Voice

Teachable prose is natural standalone coursebook writing. State the teaching
point directly. The recurring “what the input says” frame is the failure mode.
See `editorial.md` for positive and weak examples and the semantic review that
replaces a banned-string checklist.

## Outside enrichment: permission, citations, records

Outside enrichment means any material not present in the supplied source:
another book, an article, a dataset, a website, a lecture, an image, or your own
external knowledge presented as fact.

Protocol:

1. Ask before using it, once per book. “May I bring in outside material for this
   book? If so, name or provide the sources you permit.”
2. Record the permission verbatim enough to be auditable, not just “user agreed”.
3. For each external source record a citation (author/title/publisher where
   available), an access date, and a stable locator or local content hash. A URL
   alone is weaker than a stored local copy with a hash.
4. Mark the derivation `external` and cite it at the point of use. The authoring
   record must name the block ids and anchors.
5. If permission is refused or absent, do not browse, do not “just check one
   fact”, and do not smuggle external knowledge into an example.
6. Permission to use a source is not permission to invent around it. Do not
   extend a permitted source into claims it does not support.

What is not permission:

- “Make it teachable” does not imply outside research.
- “Use your judgement” does not imply external sources.
- A citation supplied in the source does not authorise fetching it.
- A previous book's permission does not carry over to this book.

Strict mode has no enrichment branch. Source-supplied URLs or citations may be
quoted as source content, with their original anchor.

## Mode leakage: what must fail

| Leak | Contract violated |
| --- | --- |
| Strict book contains an external citation or a “further reading” list | No outside material. |
| Strict book adds objectives, exercises, a glossary or an explanatory analogy | No teaching apparatus. |
| Strict book reorders pages without a recorded merge | Source order. |
| Strict book drops a page with no exclusion reason | Coverage. |
| Teachable book cites an external source with no permission | Enrichment permission. |
| Teachable book cites an external source with no citation or stable locator | Enrichment evidence. |
| Teachable book presents an illustrative example as a real observation | Uncertainty. |
| Either mode invents a number, name, date or label | No invention. |

## Records and repeatability

Each skill-authored book records its mode and provenance in
`authoring/record.json`, beside the manuscript. Published record fields
(`schemaVersion: "1.0"`): `bookId`, `mode`, source `id`/`sha256`/`pages`/
`intakeManifest`, `enrichment` (`requested`, `permission`, `sources[]`),
`coverage[]` per source page, `derivations[]`, optional `uncertainty[]` and
`decisions[]`, `manuscriptSha256`, `manuscriptRevision`.

Mode guards worth knowing while authoring:

- `source-faithful` rejects `external`, rejects `reorder`, and rejects a
  teaching derivation unless it is marked `retained: true` because that content
  is actually present in the source. Manuscript teaching blocks (`definition`,
  `example`, `assessment`, `case`) must be named by a retained derivation of the
  matching kind.
- `teachable` allows reorder/merge/split; `external` needs `enrichment.requested`,
  a permission string, and a citation naming exactly one declared source. Every
  declared source must be used, and teaching derivations need source anchors.
- Both modes require every content block to have provenance and every
  unreadable/unresolved block to have an uncertainty entry.
- A violation is `INPUT_INVALID` with a locator such as
  `authoring/record.json:derivations[2].kind`.

The record is validated by the runtime track's contract check. If your installed
engine does not yet expose it, still write the record and keep the evidence
truthful rather than inventing a check result.

Repeatability means the same approved manuscript, assets and pins rebuild the
same layout and, where the engine proves it, the same PDF bytes. It never means
that two independent agent rewrites from the same source are byte-identical.
