# Brief 0001: ai-brand-pipeline

Date: 2026-11-11. Owner: Ned Karlovich. Status: structure built, brand not chosen.

## Why

Generated work drifts off-brand because the model recalls a brand loosely instead of reading it.
This project gives five kinds of AI machinery one job: make the output answer to a real brand
system. The five are an MCP server, a voice agent, a generative video pipeline, tracing of agent
runs, and a hosted deployment.

## What it is

A brand's guidelines become a *brand pack* (one JSON file). From it:

1. **MCP server.** Tools that return the brand's facts (strategy, palette, typefaces, art
   direction, tokens) and tools that check work (a colour, a colour pair, a stylesheet, copy).
2. **Voice agent.** Ask about the brand out loud; it answers from the tools, not from memory.
3. **Video pipeline.** A brief becomes shots whose prompts carry the brand's art direction and
   colours; each clip is reviewed before it is accepted.
4. **Tracing.** Every tool call is recorded, locally or in LangSmith.
5. **Deployment.** The MCP server on Cloud Run.

## Decided

- The brand is not chosen yet (2026-11-11). Until it is, a made-up brand (Fieldnote) stands in so
  everything can be tested. See decisions/0001.
- No brand value is written in code. A check reports differences from the pack and never decides
  what the brand is.
- Deterministic checks only where the guideline is exact (a hex value, a scale, a listed word).
  Whether copy *sounds* right is left to a model that has read the voice principles.
- The eval comes before the feature: the CSS check has labelled cases and a pass floor.

## Open

- Which brand, and where its guidelines live.
- Providers: speech-to-text, the model, text-to-speech, the video model.
- Accounts: LangSmith; a Google Cloud project with billing.
- A licence for the repository (public since 2026-11-11; none chosen yet).

## Not built yet

See the status table in README.md. In short: provider calls (voice, video), the frame review for
video, and anything that needs an account.

## Evidence so far

- 43 tests pass.
- CSS check eval, 22 cases on the example brand: recall and precision 1.00 for all four rules.
  The first run scored 0.80 on spacing (negative margins were missed); fixed and rerun.
- MCP server answered `initialize`, `tools/list` and `tools/call` over stdio and over HTTP on this
  machine. Not yet connected to a real agent client.
