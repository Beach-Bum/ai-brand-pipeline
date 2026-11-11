# Decision 0001: build brand-neutral, with a made-up brand for tests

Date: 2026-11-11. Decided by: Ned Karlovich.

## Decision

The structure is built without a brand; one is named later. A fictional brand, Fieldnote, lives
in `brands/example/` so the machinery can be tested.

## What changed because of it

- The first scaffold read one brand's guidelines directly. That reader and its data were removed.
- A brand pack format was added (`brands/<id>/brand.json`) with a loader that validates it and says
  in plain words what is missing.
- Checks, tools, the voice prompt and the video plan take the brand from the pack.

## Next legal step

Name the brand. Then: write its brand pack, label eval cases for it, and choose providers.
