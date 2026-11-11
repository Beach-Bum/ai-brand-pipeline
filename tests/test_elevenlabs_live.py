"""Calls the real ElevenLabs service. Skipped unless a key is set, so the normal run needs no account."""
import os

import pytest

from brand_agent.voice import elevenlabs as el
from brand_agent.voice.agent import Reply, VoiceSession

try:
    el.api_key()
    HAVE_KEY = True
except el.VoiceError:
    HAVE_KEY = False

pytestmark = pytest.mark.skipif(not HAVE_KEY or os.environ.get('SKIP_LIVE') == '1', reason='no ELEVENLABS_API_KEY, or SKIP_LIVE=1')


def words(text):
    return [w.strip('.,').lower().replace('colors', 'colours') for w in text.split()]


def test_speech_goes_out_and_comes_back_as_the_same_words():
    said = 'The primary colours are ink, paper and signal.'
    audio = el.ElevenLabsSpeaker().speak(said)
    assert len(audio) > 5000
    assert words(el.ElevenLabsTranscriber().transcribe(audio)) == words(said)


def test_a_full_spoken_turn_with_real_ears_and_mouth_and_a_scripted_model():
    class Scripted:
        def respond(self, system, messages, specs):
            return Reply(text='You asked: ' + messages[-1]['content'])

    session = VoiceSession(el.ElevenLabsTranscriber(), Scripted(), el.ElevenLabsSpeaker())
    question = el.ElevenLabsSpeaker().speak('Which typeface is used for headings?')
    answer_audio = session.turn(question)
    assert 'typeface' in session.messages[0]['content'].lower()
    assert 'typeface' in el.ElevenLabsTranscriber().transcribe(answer_audio).lower()


def test_a_bad_key_is_reported_with_the_services_reason(monkeypatch):
    monkeypatch.setenv('ELEVENLABS_API_KEY', 'sk_not_a_real_key')
    with pytest.raises(el.VoiceError, match='ElevenLabs answered 401'):
        el.voices()
