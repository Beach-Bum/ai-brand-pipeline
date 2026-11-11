"""A voice agent for the brand: a person asks out loud, it answers out loud, from the guidelines.

One turn is three steps, each behind an interface so a provider can be swapped without touching the
loop:

    audio in --Transcriber--> text --Responder (model + brand tools)--> text --Speaker--> audio out

What is built: the loop, the system prompt, the tool descriptions handed to the model, the code
that runs the tools the model asks for, and speech in and out on ElevenLabs (elevenlabs.py, run
against the live service). What is NOT built: the model call, a stub in providers.py. The loop is
tested with fakes in tests/test_server_voice_video.py and live in tests/test_elevenlabs_live.py.
"""
from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, get_args, get_origin

from .. import tools
from ..brand import load


class Transcriber(Protocol):
    def transcribe(self, audio: bytes) -> str:
        """Speech to text."""


class Speaker(Protocol):
    def speak(self, text: str) -> bytes:
        """Text to speech."""


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    id: str = ''


@dataclass
class Reply:
    """What the model returned: either words to say, or tools it wants run first."""
    text: str = ''
    tool_calls: list[ToolCall] = field(default_factory=list)


class Responder(Protocol):
    def respond(self, system: str, messages: list[dict], tool_specs: list[dict]) -> Reply:
        """One model call. `messages` is the conversation so far, including tool results."""


def system_prompt() -> str:
    """What the model is told about its job. Spoken answers are short, so the prompt asks for that."""
    b = load()
    return (
        f"You are the voice of the {b['name']} brand guidelines. People ask you questions out loud and "
        'hear your answer, so answer in one to three short sentences, with no lists and no markup. '
        'Every fact about the brand comes from a tool: call the tool before answering and never answer '
        'from memory. Say colour values as words a person can follow, then the hex code once. '
        'If the guidelines do not cover the question, say so.'
    )


_JSON_TYPES = {str: 'string', int: 'integer', float: 'number', bool: 'boolean', dict: 'object', list: 'array'}


def tool_specs() -> list[dict]:
    """The brand tools described for a model: name, description and a JSON schema of the arguments,
    read from each function's signature so the two cannot drift apart."""
    specs = []
    for fn in tools.ALL:
        properties, required = {}, []
        for name, param in inspect.signature(fn).parameters.items():
            annotation = inspect.get_annotations(inspect.unwrap(fn), eval_str=True).get(name, str)
            if get_origin(annotation) is Literal:
                schema = {'type': 'string', 'enum': list(get_args(annotation))}
            else:
                schema = {'type': _JSON_TYPES.get(annotation, 'string')}
            properties[name] = schema
            if param.default is inspect.Parameter.empty:
                required.append(name)
        specs.append({'name': fn.__name__, 'description': ' '.join((fn.__doc__ or '').split()),
                      'input_schema': {'type': 'object', 'properties': properties, 'required': required}})
    return specs


def run_tool(call: ToolCall) -> str:
    """Runs one tool the model asked for and returns the result as JSON text. A wrong name or wrong
    arguments come back as an error the model can read and correct, not as a crash."""
    fn = tools.BY_NAME.get(call.name)
    if fn is None:
        return json.dumps({'error': f'There is no tool named {call.name}. Tools: {", ".join(tools.BY_NAME)}.'})
    try:
        return json.dumps(fn(**call.arguments), ensure_ascii=False)
    except (TypeError, ValueError, KeyError) as error:
        return json.dumps({'error': f'{type(error).__name__}: {error}'})


@dataclass
class VoiceSession:
    """One conversation. Keeps the history so a follow-up question ("and the darker one?") works."""
    transcriber: Transcriber
    responder: Responder
    speaker: Speaker
    max_tool_rounds: int = 4
    messages: list[dict] = field(default_factory=list)

    def answer(self, question: str) -> str:
        """Text in, text out: the model call and its tool calls, without the audio at either end."""
        self.messages.append({'role': 'user', 'content': question})
        for _ in range(self.max_tool_rounds):
            reply = self.responder.respond(system_prompt(), self.messages, tool_specs())
            if not reply.tool_calls:
                self.messages.append({'role': 'assistant', 'content': reply.text})
                return reply.text
            self.messages.append({'role': 'assistant', 'content': reply.text, 'tool_calls': [vars(c) for c in reply.tool_calls]})
            for call in reply.tool_calls:
                self.messages.append({'role': 'tool', 'tool_call_id': call.id, 'name': call.name, 'content': run_tool(call)})
        text = 'I could not finish looking that up. Please ask again.'
        self.messages.append({'role': 'assistant', 'content': text})
        return text

    def turn(self, audio: bytes) -> bytes:
        """One spoken turn: audio in, audio out."""
        return self.speaker.speak(self.answer(self.transcriber.transcribe(audio)))
