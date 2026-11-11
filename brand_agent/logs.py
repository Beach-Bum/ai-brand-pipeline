"""Reads the agent logs and says how the tools and the pipeline are doing.

Usage: uv run python -m brand_agent.logs [agent-logs]

For each tool: how often it was called, how often it failed, and the typical and slow call times.
For the pipeline: how many tasks passed, gave up or got stuck, and how many rounds a pass took.
These are the numbers to look at before changing a prompt or a check, and again after.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def read(folder: Path) -> list[dict]:
    """Every record in every .jsonl file of the folder. A line that is not JSON is skipped."""
    records = []
    for path in sorted(folder.glob('*.jsonl')):
        for line in path.read_text(encoding='utf8').splitlines():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def summarise(records: list[dict]) -> dict:
    tools: dict[str, dict] = defaultdict(lambda: {'calls': 0, 'errors': 0, 'ms': []})
    tasks: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        if 'tool' in r:
            t = tools[r['tool']]
            t['calls'] += 1
            t['errors'] += 'error' in r
            t['ms'].append(r.get('ms', 0))
        elif r.get('event') == 'pipeline_round':
            tasks[(r.get('task'), r.get('kind'))].append(r)

    tool_rows = {}
    for name, t in sorted(tools.items()):
        ms = sorted(t['ms'])
        tool_rows[name] = {'calls': t['calls'], 'errors': t['errors'], 'error_rate': round(t['errors'] / t['calls'], 3),
                           'ms_median': round(statistics.median(ms), 2), 'ms_p95': round(ms[min(len(ms) - 1, int(len(ms) * 0.95))], 2)}

    outcomes = {'passed': 0, 'gave_up': 0, 'stuck': 0}
    rounds_to_pass = []
    for rounds in tasks.values():
        last = rounds[-1]
        if last['status'] == 'passed':
            outcomes['passed'] += 1
            rounds_to_pass.append(last['round'])
        elif last['status'] == 'stuck':
            outcomes['stuck'] += 1
        else:
            outcomes['gave_up'] += 1
    pipeline = {'tasks': len(tasks), **outcomes,
                'mean_rounds_to_pass': round(statistics.mean(rounds_to_pass), 2) if rounds_to_pass else None}
    return {'tools': tool_rows, 'pipeline': pipeline}


def main() -> None:
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else 'agent-logs')
    if not folder.is_dir():
        raise SystemExit(f'No folder {folder}. Set BRAND_AGENT_LOG={folder}/calls.jsonl and run something first.')
    summary = summarise(read(folder))
    if not summary['tools'] and not summary['pipeline']['tasks']:
        raise SystemExit(f'{folder} has no records yet.')
    if summary['tools']:
        print(f'{"tool":24} {"calls":>6} {"errors":>6} {"rate":>6} {"median ms":>10} {"p95 ms":>8}')
    for name, t in summary['tools'].items():
        print(f'{name:24} {t["calls"]:6} {t["errors"]:6} {t["error_rate"]:6.1%} {t["ms_median"]:10} {t["ms_p95"]:8}')
    p = summary['pipeline']
    if p['tasks']:
        print(f'\npipeline: {p["tasks"]} tasks, {p["passed"]} passed, {p["gave_up"]} gave up, {p["stuck"]} stuck; '
              f'mean rounds to pass {p["mean_rounds_to_pass"]}')


if __name__ == '__main__':
    main()
