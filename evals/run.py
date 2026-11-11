"""Measures the CSS check against cases a person has labelled.

Each line of cases.jsonl is one stylesheet and the findings a careful reviewer would report for it,
as [rule, value] pairs. The run prints, per rule, how many expected findings were reported (recall)
and how many reported findings were expected (precision), and lists every miss and every false
alarm. It exits with status 1 if either number is below the floor, so it can gate a change.

Usage: uv run python evals/run.py [--brand example] [--floor 0.95]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brand_agent import checks  # noqa: E402
from brand_agent.brand import load  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--brand', default='example')
    parser.add_argument('--floor', type=float, default=0.95)
    args = parser.parse_args()

    brand = load(args.brand)
    path = Path(__file__).parent / f'cases.{args.brand}.jsonl'
    cases = [json.loads(line) for line in path.read_text(encoding='utf8').splitlines() if line.strip()]
    hit, missed, extra = Counter(), [], []
    expected_total, reported_total = Counter(), Counter()

    for case in cases:
        expected = Counter((rule, value) for rule, value in case['expect'])
        reported = Counter((f['rule'], f['value']) for f in checks.lint_css(brand, case['css']))
        for key, n in expected.items():
            expected_total[key[0]] += n
            hit[key[0]] += min(n, reported[key])
            if reported[key] < n:
                missed.append((case['id'], *key))
        for key, n in reported.items():
            reported_total[key[0]] += n
            if expected[key] < n:
                extra.append((case['id'], *key))

    print(f'{brand["name"]}: {len(cases)} cases\n')
    print(f'{"rule":10} {"expected":>8} {"reported":>8} {"recall":>7} {"precision":>9}')
    worst = 1.0
    for rule in sorted(set(expected_total) | set(reported_total)):
        recall = hit[rule] / expected_total[rule] if expected_total[rule] else 1.0
        precision = hit[rule] / reported_total[rule] if reported_total[rule] else 1.0
        worst = min(worst, recall, precision)
        print(f'{rule:10} {expected_total[rule]:8} {reported_total[rule]:8} {recall:7.2f} {precision:9.2f}')
    for case_id, rule, value in missed:
        print(f'\nMISSED       {case_id}: {rule} {value}')
    for case_id, rule, value in extra:
        print(f'\nFALSE ALARM  {case_id}: {rule} {value}')
    print(f'\nlowest score {worst:.2f}, floor {args.floor:.2f}: {"pass" if worst >= args.floor else "FAIL"}')
    return 0 if worst >= args.floor else 1


if __name__ == '__main__':
    raise SystemExit(main())
