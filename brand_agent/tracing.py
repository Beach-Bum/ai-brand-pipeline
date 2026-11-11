"""Tracing: records each tool call so a run can be inspected afterwards.

Two sinks, both optional and both off unless asked for:
- a local JSON-lines file, when BRAND_AGENT_LOG is set to a path, by convention
  agent-logs/calls.jsonl (no account needed; `python -m brand_agent.logs` summarises it);
- LangSmith, when LANGSMITH_TRACING=true and the `langsmith` package is installed and a
  LANGSMITH_API_KEY is set. NOT YET EXERCISED: written against the documented `traceable`
  decorator, to be verified the first time an account is connected (see docs/briefs/0001).

With neither set, `traced` returns the function unchanged.
"""
from __future__ import annotations

import functools
import json
import os
import time
from typing import Any, Callable


def _langsmith_traceable() -> Callable | None:
    if os.environ.get('LANGSMITH_TRACING', '').lower() != 'true':
        return None
    try:
        from langsmith import traceable  # type: ignore[import-not-found]
    except ImportError:
        return None
    return traceable


def _short(value: Any, limit: int = 400) -> Any:
    text = json.dumps(value, default=str, ensure_ascii=False)
    return value if len(text) <= limit else text[:limit] + '…'


def _append(path: str, record: dict) -> None:
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'a', encoding='utf8') as log:
        log.write(json.dumps(record, default=str, ensure_ascii=False) + '\n')


def log_event(event: str, **fields: Any) -> None:
    """Writes one line to the local log, if one is set. Used for things that are not a tool call,
    such as each round of the generate-check-repair pipeline."""
    path = os.environ.get('BRAND_AGENT_LOG')
    if path:
        _append(path, {'at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'event': event, **fields})


def traced(fn: Callable) -> Callable:
    """Wraps a tool so that each call is recorded: name, arguments, time taken, and the result or
    the error. The wrapped function keeps its name, signature and description."""
    traceable = _langsmith_traceable()
    inner = traceable(run_type='tool', name=fn.__name__)(fn) if traceable else fn

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        path = os.environ.get('BRAND_AGENT_LOG')
        if not path:
            return inner(*args, **kwargs)
        started = time.perf_counter()
        record: dict[str, Any] = {'at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'tool': fn.__name__, 'args': _short({'args': args, **kwargs})}
        try:
            result = inner(*args, **kwargs)
            record['result'] = _short(result)
            return result
        except Exception as error:
            record['error'] = f'{type(error).__name__}: {error}'
            raise
        finally:
            record['ms'] = round((time.perf_counter() - started) * 1000, 2)
            _append(path, record)

    return wrapper
