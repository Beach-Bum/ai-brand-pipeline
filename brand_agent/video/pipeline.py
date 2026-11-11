"""A generative video pipeline that answers to the brand: a brief goes in, a set of clips comes out.

    Brief --plan()--> shots, each with a prompt built from the brand pack
          --render()--> one clip per shot, from a video model (behind an interface)
          --review()--> each clip checked before it is accepted

What is built: the brief, the plan and the prompt for each shot (pure functions, tested), and the
render loop with its review step. What is NOT built: the video model and the frame check. The model
needs an account and is a stub in providers.py; the frame check needs sampled frames from a real
clip and is described in review() below.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..brand import load

FORMATS = {'16:9': (1920, 1080), '9:16': (1080, 1920), '1:1': (1080, 1080)}


@dataclass(frozen=True)
class Brief:
    """What a person asks for. `lens` is an art-direction lens id from the brand pack."""
    subject: str
    lens: str
    shots: int = 3
    seconds_per_shot: int = 4
    format: str = '16:9'


@dataclass(frozen=True)
class Shot:
    number: int
    prompt: str
    negative_prompt: str
    seconds: int
    width: int
    height: int
    palette: tuple[str, ...]


@dataclass
class Clip:
    shot: Shot
    path: str
    accepted: bool = False
    notes: list[str] = field(default_factory=list)


class VideoModel(Protocol):
    def generate(self, shot: Shot) -> str:
        """Renders one shot and returns the path of the clip."""


class BriefError(ValueError):
    """The brief asks for something the brand pack or the pipeline does not have."""


# The same subject seen three ways, so a set of clips cuts together.
FRAMINGS = ('Wide establishing shot.', 'Medium shot, the subject in its surroundings.', 'Close detail shot.')


def plan(brief: Brief) -> list[Shot]:
    """Turns a brief into shots. Every shot's prompt carries the lens description and the lens
    colours from the brand pack, so the brand is in the request and not left to the model."""
    brand = load()
    lenses = {x['id']: x for x in brand['art_direction']}
    if brief.lens not in lenses:
        raise BriefError(f'"{brief.lens}" is not an art-direction lens of {brand["name"]}. Lenses: {", ".join(lenses)}.')
    if brief.format not in FORMATS:
        raise BriefError(f'"{brief.format}" is not a supported format. Formats: {", ".join(FORMATS)}.')
    if not 1 <= brief.shots <= 12:
        raise BriefError('A brief has between 1 and 12 shots.')
    if not brief.subject.strip():
        raise BriefError('The brief has no subject.')

    lens = lenses[brief.lens]
    palette = tuple(lens.get('swatches') or [c['hex'] for c in brand['palette'] if c['group'] == 'primary'])
    width, height = FORMATS[brief.format]
    avoid = brand.get('voice', {}).get('avoid', [])
    negative = 'text, captions, logos, watermarks, lens flare, oversaturated colour' + (', ' + ', '.join(avoid) if avoid else '')
    shots = []
    for i in range(brief.shots):
        prompt = ' '.join([
            FRAMINGS[i % len(FRAMINGS)],
            brief.subject.strip().rstrip('.') + '.',
            lens['intro'],
            f'Colour palette limited to {", ".join(palette)}.',
        ])
        shots.append(Shot(number=i + 1, prompt=prompt, negative_prompt=negative, seconds=brief.seconds_per_shot,
                          width=width, height=height, palette=palette))
    return shots


def review(clip: Clip) -> Clip:
    """Decides whether a clip is accepted. NOT BUILT: it accepts nothing and says why.

    To do, once there are real clips: sample frames, take each frame's dominant colours, and
    measure how far they sit from the shot's palette with checks.nearest_brand_colour (the delta E
    it returns is the measure). Accept under a threshold; the threshold is set from an eval of
    clips a person has marked on-brand and off-brand, not guessed.
    """
    clip.accepted = False
    clip.notes.append('Not reviewed: the frame check is not built yet.')
    return clip


def render(brief: Brief, model: VideoModel) -> list[Clip]:
    """Plans the brief, renders each shot and reviews each clip."""
    return [review(Clip(shot=shot, path=model.generate(shot))) for shot in plan(brief)]
