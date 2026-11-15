---
description: Make a teachable textbook PDF from a source.
---

Make a Bookify book in `teachable` mode.

This command establishes `teachable`: reorganise and rewrite the supplied source
into a coherent, standalone authorial coursebook with explanations, examples,
checks, summaries and learning aids. Remain source-grounded. Use outside
enrichment only when the user explicitly requests it here and supplies a source
to cite. Do not ask which mode to use.

$ARGUMENTS

Treat the user's composer attachments as the supplied source. Preserve any
requested language, audience, length, citation style and output path. Do not
rely on `@path` expansion in this template. Never put `$ARGUMENTS`, a source
path or other untrusted text inside a `!` shell block.

Write natural coursebook prose. Do not narrate the input: phrases such as "the
provided materials suggest", "the course says", "the slides explain" or "based
on the provided content" put the reader behind the source instead of inside the
subject. State the teaching point directly, define terms where they are needed,
work through a concrete example, and make the chapter's own argument. Keep
required attribution, direct quotations, uncertainty and enrichment citations
visible in a note, reference, caption, source index or the authoring record;
naming the source is correct when that naming is the point. Never upgrade an
inferred or unreadable value into a verified claim.

If the arguments explicitly request source-faithful mode, state the conflict, do
not switch modes silently, and ask for one brief resolution: keep this teachable
entry, or switch to the `/bookify-source-faithful` entry. If outside enrichment
is requested without a source or permission, ask for both once. If no source is
attached or named, ask for it once.

Then load the Bookify skill and follow its teachable provenance, authoring,
inspection, build and verification contract. The user supplies a source and
wants a finished book; do not ask them to write YAML, run commands or manage
caches.
