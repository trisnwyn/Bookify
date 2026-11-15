---
description: Make a source-faithful Bookify PDF from a source.
---

Make a Bookify book in `source-faithful` mode.

This command establishes `source-faithful`: preserve the supplied source's
order, coverage and meaning; improve headings, transitions, captions and
typography only; add no teaching apparatus and no outside material. Do not ask
which mode to use.

$ARGUMENTS

Treat the user's composer attachments as the supplied source. Preserve any
requested language, audience, length, citation style and output path. Do not
rely on `@path` expansion in this template. Never put `$ARGUMENTS`, a source
path or other untrusted text inside a `!` shell block.

If the arguments explicitly request teachable mode or outside enrichment, state
the conflict, do not switch modes silently, and ask for one brief resolution:
keep this source-faithful entry, or switch to the
`/bookify-teachable-textbook` entry. If no source is attached or named, ask for
it once.

Then load the Bookify skill and follow its source-faithful provenance, authoring,
inspection, build and verification contract. The user supplies a source and
wants a finished book; do not ask them to write YAML, run commands or manage
caches.
