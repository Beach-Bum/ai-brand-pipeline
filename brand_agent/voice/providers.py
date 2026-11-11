"""Provider stubs. Speech in and out are implemented in elevenlabs.py; the model is not.

SpeechToText and TextToSpeech below are kept as the shape for another vendor.

Each one needs an account and a choice of vendor, which is still open (docs/briefs/0001, "Open").
They are here so the shape is fixed: implement the one method, pass the object to VoiceSession.
"""
from __future__ import annotations

from .agent import Reply


class NotConfigured(RuntimeError):
    """Raised by a provider stub. The message says what has to be chosen and supplied."""


class SpeechToText:
    """Transcriber. To do: pick a speech-to-text service, read its key from the environment, send
    the audio, return the transcript."""

    def transcribe(self, audio: bytes) -> str:
        raise NotConfigured('No speech-to-text provider is set up yet.')


class ModelResponder:
    """Responder. To do: call a model with the system prompt, the messages and the tool specs, and
    translate its answer into a Reply (text, or the tool calls it asked for). The message and tool
    formats in agent.py are neutral; convert them to the vendor's format here."""

    def respond(self, system: str, messages: list[dict], tool_specs: list[dict]) -> Reply:
        raise NotConfigured('No model provider is set up yet.')


class TextToSpeech:
    """Speaker. To do: pick a text-to-speech service and a voice, return the audio bytes."""

    def speak(self, text: str) -> bytes:
        raise NotConfigured('No text-to-speech provider is set up yet.')
