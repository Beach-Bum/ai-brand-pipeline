"""The agent pipeline: generate, check, repair, until the work passes or the rounds run out.

    task --Generator--> draft --checks--> findings
                          ^                  |
                          +---- repair ------+      (at most `max_rounds` times)

The generator is a model (behind an interface; a stub until a provider is chosen). The checks are
the deterministic ones in checks.py. The point of the loop is that the model is never the judge of
its own output: it writes, code checks, and the findings go back to it as plain instructions.

A run ends in one of three states, and the caller is told which:
- passed: no errors left (warnings may remain and are returned);
- gave_up: the rounds ran out with errors left. The last draft is returned, marked as failing;
- stuck: the generator returned the same draft twice. Repeating would spend calls for nothing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from . import checks
from .brand import load
from .tracing import log_event

Kind = Literal['css', 'copy']


class Generator(Protocol):
    def generate(self, task: str, kind: Kind, brand: dict, previous: str | None, findings: list[dict]) -> str:
        """Writes a first draft (previous is None) or repairs `previous` given the findings."""


@dataclass
class Round:
    number: int
    draft: str
    findings: list[dict]

    @property
    def errors(self) -> int:
        return sum(f['severity'] == 'error' for f in self.findings)


@dataclass
class Result:
    status: Literal['passed', 'gave_up', 'stuck']
    output: str
    rounds: list[Round] = field(default_factory=list)

    @property
    def findings(self) -> list[dict]:
        return self.rounds[-1].findings if self.rounds else []


def check(kind: Kind, brand: dict, draft: str) -> list[dict]:
    return checks.lint_css(brand, draft) if kind == 'css' else checks.lint_copy(brand, draft)


def repair_instructions(findings: list[dict]) -> str:
    """The findings as instructions a model can act on: one line each, errors first."""
    ordered = sorted(findings, key=lambda f: (f['severity'] != 'error', f['line']))
    return '\n'.join(
        f"- line {f['line']}: {f['message']}" + (
            '' if f['rule'] == 'font'  # the font message already names the typefaces to use
            else f" Use {f['suggestion']}." if f.get('suggestion') else ' Remove or reword it.')
        for f in ordered
    )


def run(task: str, kind: Kind, generator: Generator, max_rounds: int = 3) -> Result:
    """Runs the loop for one task and returns the result with every round kept for inspection."""
    brand = load()
    rounds: list[Round] = []
    draft: str | None = None
    findings: list[dict] = []
    for number in range(1, max_rounds + 1):
        new = generator.generate(task, kind, brand, draft, findings)
        if draft is not None and new == draft:
            log_event('pipeline_round', task=task, kind=kind, round=number, status='stuck')
            return Result('stuck', draft, rounds)
        draft = new
        findings = check(kind, brand, draft)
        rounds.append(Round(number, draft, findings))
        errors = rounds[-1].errors
        log_event('pipeline_round', task=task, kind=kind, round=number, errors=errors,
                  warnings=len(findings) - errors, status='passed' if not errors else 'failing')
        if not errors:
            return Result('passed', draft, rounds)
    return Result('gave_up', draft or '', rounds)
