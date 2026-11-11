"""The video model. STUB: not implemented.

It needs an account with a hosted video model, and the choice of model is still open
(docs/briefs/0001, "Open"). Implement generate(): send the shot's prompt, negative prompt, size and
length, wait for the job, save the clip, return its path.
"""
from __future__ import annotations

from .pipeline import Shot


class NotConfigured(RuntimeError):
    """Raised by the stub. The message says what has to be chosen and supplied."""


class HostedVideoModel:
    def generate(self, shot: Shot) -> str:
        raise NotConfigured('No video model provider is set up yet.')
