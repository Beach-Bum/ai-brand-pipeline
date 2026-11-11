"""The three ways into the tools: the MCP server, the voice loop and the video plan."""
import asyncio
import json

import pytest

from brand_agent import tools
from brand_agent.server import build
from brand_agent.video.pipeline import Brief, BriefError, Shot, plan, render
from brand_agent.video.providers import HostedVideoModel
from brand_agent.video.providers import NotConfigured as VideoNotConfigured
from brand_agent.voice.agent import Reply, ToolCall, VoiceSession, run_tool, system_prompt, tool_specs
from brand_agent.voice.providers import ModelResponder, NotConfigured, SpeechToText, TextToSpeech


# ------------------------------------------------------------------ MCP server

def call(name, arguments):
    """Calls a tool through the server. A list comes back as one text item per element."""
    async def go():
        result = await build().call_tool(name, arguments)
        items = [json.loads(c.text) for c in result.content]
        return items[0] if len(items) == 1 else items
    return asyncio.run(go())


def test_server_lists_every_tool_with_a_description():
    listed = asyncio.run(build().list_tools())
    assert [t.name for t in listed] == [f.__name__ for f in tools.ALL]
    assert all(t.description and len(t.description) > 40 for t in listed)


def test_server_answers_from_the_brand_pack():
    assert call('brand_strategy', {})['mission'] == 'Fieldnote makes notebooks for people who work outdoors.'
    assert [c['name'] for c in call('brand_palette', {'group': 'primary'})] == ['Ink', 'Paper', 'Signal']
    assert call('brand_art_direction', {'lens': 'material'})['title'] == 'Material'


def test_server_lint_reports_errors_and_warnings():
    report = call('lint_css', {'css': '.a { color: #1a73e8; padding: 10px; }'})
    assert (report['ok'], report['errors'], report['warnings']) == (False, 1, 1)


def test_tracing_writes_one_line_per_call(tmp_path, monkeypatch):
    log = tmp_path / 'calls.jsonl'
    monkeypatch.setenv('BRAND_AGENT_LOG', str(log))
    tools.check_contrast('#000000', '#ffffff')
    with pytest.raises(ValueError):
        tools.nearest_brand_colour('not-a-colour')
    first, second = (json.loads(line) for line in log.read_text(encoding='utf8').splitlines())
    assert first['tool'] == 'check_contrast' and first['result']['ratio'] == 21.0 and 'ms' in first
    assert second['tool'] == 'nearest_brand_colour' and second['error'].startswith('ValueError')


# ------------------------------------------------------------------ voice

class FakeEars:
    def transcribe(self, audio):
        return audio.decode()


class FakeMouth:
    def speak(self, text):
        return text.encode()


class ScriptedModel:
    """Asks for the palette on its first call, then answers from what the tool returned."""
    def __init__(self):
        self.seen = []

    def respond(self, system, messages, specs):
        self.seen.append((system, [m['role'] for m in messages], [s['name'] for s in specs]))
        if messages[-1]['role'] == 'user':
            return Reply(tool_calls=[ToolCall('brand_palette', {'group': 'primary'}, id='c1')])
        names = [c['name'] for c in json.loads(messages[-1]['content'])]
        return Reply(text='The primary colours are ' + ', '.join(names) + '.')


def test_tool_specs_match_the_tools():
    specs = {s['name']: s for s in tool_specs()}
    assert list(specs) == [f.__name__ for f in tools.ALL]
    assert specs['check_contrast']['input_schema']['required'] == ['foreground', 'background']
    assert specs['brand_palette']['input_schema']['required'] == []
    assert 'spacing' in specs['brand_tokens']['input_schema']['properties']['category']['enum']


def test_a_spoken_turn_goes_through_a_tool_and_comes_back_as_audio():
    model = ScriptedModel()
    session = VoiceSession(FakeEars(), model, FakeMouth())
    assert session.turn(b'What are the main colours?') == b'The primary colours are Ink, Paper, Signal.'
    assert [m['role'] for m in session.messages] == ['user', 'assistant', 'tool', 'assistant']
    assert model.seen[0][0] == system_prompt() and 'Fieldnote' in system_prompt()


def test_a_wrong_tool_call_is_an_error_the_model_can_read():
    assert 'There is no tool named nope' in run_tool(ToolCall('nope', {}))
    assert 'error' in json.loads(run_tool(ToolCall('check_contrast', {'foreground': '#000'})))


def test_a_model_that_never_stops_calling_tools_is_cut_off():
    class Looping:
        def respond(self, system, messages, specs):
            return Reply(tool_calls=[ToolCall('brand_strategy', {})])
    session = VoiceSession(FakeEars(), Looping(), FakeMouth(), max_tool_rounds=2)
    assert session.answer('hello').startswith('I could not finish')


def test_provider_stubs_say_they_are_not_set_up():
    for stub, use in [(SpeechToText(), lambda s: s.transcribe(b'')), (ModelResponder(), lambda s: s.respond('', [], [])),
                      (TextToSpeech(), lambda s: s.speak(''))]:
        with pytest.raises(NotConfigured):
            use(stub)
    with pytest.raises(VideoNotConfigured):
        HostedVideoModel().generate(plan(Brief('x', 'in-use', shots=1))[0])


# ------------------------------------------------------------------ video

def test_plan_puts_the_brand_in_every_prompt():
    shots = plan(Brief('A notebook on a fence post in rain', 'in-use', shots=4, format='9:16'))
    assert [s.number for s in shots] == [1, 2, 3, 4]
    assert all('Daylight only.' in s.prompt and '#5c6f52' in s.prompt for s in shots)
    assert shots[0].prompt.startswith('Wide establishing shot.') and shots[3].prompt.startswith('Wide establishing shot.')
    assert (shots[0].width, shots[0].height) == (1080, 1920)
    assert 'seamless' in shots[0].negative_prompt


@pytest.mark.parametrize('brief, message', [
    (Brief('x', 'no-such-lens'), 'is not an art-direction lens of Fieldnote'),
    (Brief('x', 'in-use', format='4:3'), 'is not a supported format'),
    (Brief('x', 'in-use', shots=0), 'between 1 and 12 shots'),
    (Brief('  ', 'in-use'), 'has no subject'),
])
def test_plan_refuses_a_brief_it_cannot_meet(brief, message):
    with pytest.raises(BriefError, match=message):
        plan(brief)


def test_render_marks_clips_unreviewed_until_the_frame_check_exists():
    class FakeModel:
        def generate(self, shot: Shot) -> str:
            return f'clip-{shot.number}.mp4'
    clips = render(Brief('A notebook', 'material', shots=2), FakeModel())
    assert [c.path for c in clips] == ['clip-1.mp4', 'clip-2.mp4']
    assert not any(c.accepted for c in clips) and 'not built' in clips[0].notes[0]
