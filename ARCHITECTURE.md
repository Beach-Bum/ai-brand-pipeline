# Architecture: what goes where, and why

Each section is a decision this repository takes, with the reason. They are opinions; the code
follows them.

## Retrieve the brand; do not put it in the prompt

The brand is served by tools, not pasted into a system prompt. An agent asks for the palette when
it needs a colour and gets the current one. Three reasons:

- A prompt holding the whole brand is paid for on every call, including the calls about spacing
  that never look at the strategy.
- A model given 14 colours in a prompt still writes a fifteenth. A model that has to call
  `brand_palette` and then `lint_css` gets caught.
- The brand changes. A tool reads the pack on disk; a prompt is a copy that goes stale.

A bigger prompt wins only when the content is short, needed on every turn and never checked. The
voice agent's instructions are like that, so they are in its prompt.

## Tool, skill or subagent

| It is a | When | Here |
| --- | --- | --- |
| **Tool** | The answer is a fact or a computation, the same every time, with no judgement in it. | `brand_palette`, `check_contrast`, `lint_css` and the other six. |
| **Skill** | The agent has the tools but needs the routine: what to call, in what order, what to do with the result. No new capability, only procedure. | `skills/brand-check`: read the brand first, check after, fix before showing. |
| **Subagent** | The job needs a separate context: either it would flood the main one, or it must not be biased by it. | `agents/brand-reviewer`: a review by something that did not write the work. |

The test for a tool is whether code can do it without a model. If it can, it should, because a
check that is a function gives the same answer on Tuesday as on Monday and costs nothing to run
ten thousand times. `lint_css` is about 60 lines of regular expressions and not a model call for that
reason.

## The model is never the judge of its own output

`brand_agent/pipeline.py` is a loop: a model writes, code checks, the findings go back as plain
instructions, at most three rounds. The model does not decide that it passed. The loop has three
endings and reports which one happened: passed, gave up with errors left, or stuck because the model
returned the same draft twice. A pipeline that only ever reports success is hiding the other two.

## Deterministic where the guideline is exact, a model where it is not

A hex value, a spacing scale and a list of avoided words are exact, so they are checked by code. Whether a
paragraph sounds like the brand is not exact, so `lint_copy` does not pretend to check it: it
reports listed words only, and the reviewer subagent reads the voice principles and judges tone,
labelled as judgement in its report.

## The eval comes before the feature

`evals/cases.example.jsonl` holds stylesheets with the findings a careful reviewer would report.
`evals/run.py` prints recall and precision per rule and fails under a floor. It was written before
the check was trusted, and its first run found a real miss (negative margins). A new rule starts
as new cases.

## One list of tools, three ways in

`brand_agent/tools.py` is the only place a tool is defined. The MCP server registers the list, the
voice agent builds the model's tool descriptions from the same functions' signatures, and the video
plan calls them directly. A tool described in two places drifts; this cannot.

## One file or a repository

`demo.py` is one file with no key and no network: it is for showing the idea in a minute. The
package exists because the idea needs three entrances, an eval and a brand that can be swapped. The
order was demo-sized first, structure when a second entrance appeared.

## Logs you can read without an account

Every tool call and every pipeline round can be written to `agent-logs/` as one JSON object per
line. `python -m brand_agent.logs` turns them into the numbers that matter before and after a
change: error rate and latency per tool, and how many tasks pass and in how many rounds. LangSmith
is wired as a second sink for when traces need sharing; it is not required to see what happened.
