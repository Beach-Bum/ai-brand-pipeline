"""The whole idea in one file: a stylesheet goes in, the places it leaves the brand come out, and a
repair loop fixes them. No model, no key, no network.

    uv run python demo.py

It uses the made-up Fieldnote brand in brands/example. The "generator" here applies each finding's
suggested value, which is what a model is asked to do in the real pipeline.
"""
from brand_agent import pipeline
from brand_agent.brand import load

DRAFT = """\
.card {
  color: #333333;
  background: #f4f1e8;
  font-family: Roboto, sans-serif;
  padding: 15px 24px;
  transition: opacity 0.3s ease;
}
.card a { color: #e85a2a; }
"""


class ApplySuggestions:
    """Stands in for the model: the first draft is the one above; each repair replaces every
    flagged value with the value the check suggested."""

    def generate(self, task, kind, brand, previous, findings):
        if previous is None:
            return DRAFT
        lines = previous.splitlines()
        for f in findings:
            fix = f['suggestion'].split(',')[1].strip() if f['rule'] == 'font' else f['suggestion']
            lines[f['line'] - 1] = lines[f['line'] - 1].replace(f['value'], f'"{fix}"' if f['rule'] == 'font' else fix)
        return '\n'.join(lines) + '\n'


def main() -> None:
    brand = load()
    print(f"Brand: {brand['name']} (made up, for the demo)\n")
    print('Draft:\n' + DRAFT)

    first = pipeline.check('css', brand, DRAFT)
    print(f'The check finds {len(first)} problems:')
    print(pipeline.repair_instructions(first), '\n')

    result = pipeline.run('a card', 'css', ApplySuggestions(), max_rounds=3)
    print(f'Repair loop: {result.status} after {len(result.rounds)} rounds '
          f'(errors per round: {[r.errors for r in result.rounds]}).\n')
    print('Result:\n' + result.output)


if __name__ == '__main__':
    main()
