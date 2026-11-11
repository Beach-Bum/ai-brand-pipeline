# ai-brand-pipeline

Machinery that makes AI work answer to a real brand system. A brand's guidelines go in as one
folder (a *brand pack*); agents get tools that return the brand's facts and check work against them.

The brand is not chosen yet. The repository ships with a made-up one, Fieldnote, so every part can
be run and tested. Nothing in the code names a brand.

```bash
uv sync && uv run python demo.py     # one file, no key, no network: a draft, what is off-brand, the repaired result
```

What is in it:

- **An MCP server** with nine tools: five return the brand's facts, four check work against them.
- **An agent pipeline**: a model writes, code checks, findings go back, until it passes or says it could not.
- **A Claude Code plugin**: the server, a skill for the make-check-fix routine, and a reviewer subagent.
- **An eval** for the check, with a pass floor, and **logs** that report error rate, latency and pass rate.
- **The structure for a voice agent and a generative video pipeline**, tested with stand-ins; the provider calls are stubs.

Why each piece is a tool, a skill, a subagent or a prompt is in [ARCHITECTURE.md](ARCHITECTURE.md).

## Status

| Part | State | Needs |
| --- | --- | --- |
| Brand pack format, loader, validation | Built, tested | nothing |
| Checks: colour, contrast, CSS, copy avoid-list | Built, tested, eval set of 22 cases | nothing |
| MCP server (stdio and HTTP), 9 tools | Built, tested; run over both transports locally | nothing |
| Agent pipeline: generate, check, repair | Built, tested with a scripted generator | a model provider to run for real |
| Claude Code plugin: MCP config, skill, reviewer subagent | Written; passes `claude plugin validate`; **not yet installed and used in a session** | nothing |
| Logs in `agent-logs/` and their summary | Built, tested | nothing |
| Tracing to LangSmith | Written, **never run** | LangSmith account and key |
| Voice agent: loop, prompt, tool hand-off | Built, tested with fake providers | nothing |
| Voice agent: speech-to-text, model, text-to-speech | **Stubs** | three provider choices and keys |
| Video: brief, shot plan, prompts | Built, tested | nothing |
| Video: model call | **Stub** | a hosted video model account |
| Video: frame review | **Not built**; every clip is marked unreviewed | real clips to measure |
| Cloud Run deployment | Dockerfile and steps written, **never run** | Google Cloud project with billing |
| A real brand | **Not chosen** | a brand pack |

Licence: MIT.

## Run

```bash
uv sync
uv run pytest                              # 52 tests
uv run python evals/run.py                 # the CSS check against labelled cases
uv run python -m brand_agent.server        # MCP over stdio
PORT=8931 uv run python -m brand_agent.server --http   # MCP over HTTP at /mcp
```

`BRAND_ID` picks the brand pack (default `example`). `BRAND_AGENT_LOG=agent-logs/calls.jsonl` writes
one line per tool call and pipeline round; `uv run python -m brand_agent.logs` summarises them.

## Layout

```
brands/<id>/brand.json     a brand pack: the only place a brand lives (see brands/README.md)
brand_agent/brand.py       loads and validates a brand pack
brand_agent/checks.py      colour, contrast, CSS and copy checks; pure functions
brand_agent/tools.py       the tools, one list used by the server, the voice agent and the video plan
brand_agent/server.py      MCP server
brand_agent/pipeline.py    generate, check, repair loop
brand_agent/tracing.py     local log and LangSmith
brand_agent/logs.py        summary of agent-logs/
brand_agent/voice/         voice agent loop and provider stubs
brand_agent/video/         brief -> shots -> clips, and the model stub
evals/                     labelled cases and the runner
.claude-plugin/, .mcp.json, skills/, agents/   the Claude Code plugin
demo.py                    the idea in one file
deploy/                    container and Cloud Run steps
docs/                      brief and decisions
```

## Adding the real brand

1. Create `brands/<id>/brand.json` in the shape of `brands/example/brand.json`.
2. `BRAND_ID=<id> uv run python -c "from brand_agent.brand import load; load()"` reports anything missing.
3. Write `evals/cases.<id>.jsonl` (a person labels what a reviewer would flag) and run `evals/run.py --brand <id>`.
