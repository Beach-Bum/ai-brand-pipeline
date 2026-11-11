"""The generate-check-repair loop and the log summary, with a scripted generator."""
import json

from brand_agent import logs, pipeline, tools


class Scripted:
    """Returns the given drafts in order and records what it was asked."""
    def __init__(self, *drafts):
        self.drafts = list(drafts)
        self.asked = []

    def generate(self, task, kind, brand, previous, findings):
        self.asked.append((previous, [f['rule'] for f in findings]))
        return self.drafts[min(len(self.asked) - 1, len(self.drafts) - 1)]


BAD = '.btn { color: #1a73e8; font-family: Roboto; }'
BETTER = '.btn { color: #e8501f; font-family: Roboto; }'
GOOD = '.btn { color: #e8501f; font-family: "Inter", sans-serif; }'


def test_a_clean_first_draft_passes_in_one_round():
    result = pipeline.run('a button', 'css', Scripted(GOOD))
    assert (result.status, len(result.rounds), result.output) == ('passed', 1, GOOD)


def test_findings_go_back_to_the_generator_until_it_passes():
    generator = Scripted(BAD, BETTER, GOOD)
    result = pipeline.run('a button', 'css', generator)
    assert result.status == 'passed' and [r.errors for r in result.rounds] == [2, 1, 0]
    assert generator.asked == [(None, []), (BAD, ['colour', 'font']), (BETTER, ['font'])]


def test_warnings_do_not_block_a_pass_but_are_returned():
    result = pipeline.run('a card', 'css', Scripted('.card { padding: 10px; color: #1c2420; }'))
    assert result.status == 'passed' and [f['rule'] for f in result.findings] == ['spacing']


def test_it_gives_up_when_the_rounds_run_out_and_says_so():
    result = pipeline.run('a button', 'css', Scripted(BAD, BETTER, BAD + ' ', BETTER + ' '), max_rounds=2)
    assert result.status == 'gave_up' and result.output == BETTER and result.rounds[-1].errors == 1


def test_it_stops_when_the_generator_repeats_itself():
    generator = Scripted(BAD, BAD)
    result = pipeline.run('a button', 'css', generator, max_rounds=5)
    assert result.status == 'stuck' and len(generator.asked) == 2


def test_copy_goes_through_the_same_loop():
    result = pipeline.run('a tagline', 'copy', Scripted('A seamless notebook.', 'A notebook that survives rain.'))
    assert result.status == 'passed' and len(result.rounds) == 2


def test_repair_instructions_put_errors_first_and_name_the_fix():
    text = pipeline.repair_instructions(pipeline.check('css', pipeline.load(), '.a { padding: 10px; }\n.b { color: #1a73e8; }'))
    first, second = text.splitlines()
    assert first.startswith('- line 2:') and 'Use #' in first and second.startswith('- line 1:') and 'Use 8px.' in second


def test_logs_summarise_tool_calls_and_pipeline_outcomes(tmp_path, monkeypatch):
    monkeypatch.setenv('BRAND_AGENT_LOG', str(tmp_path / 'agent-logs' / 'calls.jsonl'))
    tools.check_contrast('#000000', '#ffffff')
    tools.check_contrast('#1c2420', '#f4f1e8')
    try:
        tools.nearest_brand_colour('nope')
    except ValueError:
        pass
    pipeline.run('task one', 'css', Scripted(BAD, GOOD))
    pipeline.run('task two', 'css', Scripted(BAD, BAD))
    pipeline.run('task three', 'css', Scripted(BAD, BETTER), max_rounds=2)

    summary = logs.summarise(logs.read(tmp_path / 'agent-logs'))
    assert summary['tools']['check_contrast'] == {**summary['tools']['check_contrast'], 'calls': 2, 'errors': 0, 'error_rate': 0.0}
    assert summary['tools']['nearest_brand_colour']['error_rate'] == 1.0
    assert summary['pipeline'] == {'tasks': 3, 'passed': 1, 'gave_up': 1, 'stuck': 1, 'mean_rounds_to_pass': 2}


def test_logs_skip_lines_that_are_not_json(tmp_path):
    (tmp_path / 'x.jsonl').write_text('not json\n' + json.dumps({'tool': 'lint_css', 'ms': 1.5}) + '\n', encoding='utf8')
    assert logs.summarise(logs.read(tmp_path))['tools']['lint_css']['calls'] == 1
