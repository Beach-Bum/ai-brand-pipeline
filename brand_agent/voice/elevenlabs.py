"""ElevenLabs as the voice agent's ears and mouth.

Speech to text and text to speech over the ElevenLabs HTTP API. The key is read from the
ELEVENLABS_API_KEY environment variable (or from a .env file in the project root) and is never
logged. Both calls were run against the live service on 2026-11-11 (see tests/test_elevenlabs_live.py,
which is skipped when no key is set).
"""
from __future__ import annotations

import os
from pathlib import Path

import httpx

API = 'https://api.elevenlabs.io'
DEFAULT_TTS_MODEL = 'eleven_multilingual_v2'
DEFAULT_STT_MODEL = 'scribe_v1'


class VoiceError(RuntimeError):
    """ElevenLabs refused or failed. The message carries the status and the service's own reason."""


def api_key() -> str:
    """The key from the environment, else from .env beside pyproject.toml."""
    key = os.environ.get('ELEVENLABS_API_KEY', '')
    env_file = Path(__file__).resolve().parents[2] / '.env'
    if not key and env_file.is_file():
        for line in env_file.read_text(encoding='utf8').splitlines():
            if line.startswith('ELEVENLABS_API_KEY='):
                key = line.split('=', 1)[1].strip()
    if not key:
        raise VoiceError('ELEVENLABS_API_KEY is not set (environment or .env).')
    return key


def _check(response: httpx.Response) -> httpx.Response:
    if response.status_code >= 400:
        try:
            detail = response.json().get('detail')
            reason = detail.get('message') if isinstance(detail, dict) else str(detail)
        except ValueError:
            reason = response.text[:200]
        raise VoiceError(f'ElevenLabs answered {response.status_code}: {reason}')
    return response


def voices() -> list[dict]:
    """The voices this key can use: id, name and labels."""
    r = _check(httpx.get(f'{API}/v1/voices', headers={'xi-api-key': api_key()}, timeout=30))
    return [{'id': v['voice_id'], 'name': v['name'], 'labels': v.get('labels', {})} for v in r.json()['voices']]


class ElevenLabsSpeaker:
    """Text to speech. Returns MP3 bytes."""

    def __init__(self, voice_id: str | None = None, model: str = DEFAULT_TTS_MODEL):
        self.voice_id = voice_id or os.environ.get('ELEVENLABS_VOICE_ID') or voices()[0]['id']
        self.model = model

    def speak(self, text: str) -> bytes:
        r = _check(httpx.post(
            f'{API}/v1/text-to-speech/{self.voice_id}',
            params={'output_format': 'mp3_44100_128'},
            headers={'xi-api-key': api_key()},
            json={'text': text, 'model_id': self.model},
            timeout=60,
        ))
        return r.content


class ElevenLabsTranscriber:
    """Speech to text. Takes audio bytes (MP3, WAV and similar) and returns the words."""

    def __init__(self, model: str = DEFAULT_STT_MODEL):
        self.model = model

    def transcribe(self, audio: bytes) -> str:
        r = _check(httpx.post(
            f'{API}/v1/speech-to-text',
            headers={'xi-api-key': api_key()},
            data={'model_id': self.model},
            files={'file': ('audio.mp3', audio, 'audio/mpeg')},
            timeout=120,
        ))
        return r.json().get('text', '').strip()
