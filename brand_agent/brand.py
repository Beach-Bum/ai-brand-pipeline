"""Loads a brand pack: one folder under brands/ holding brand.json.

A brand pack is the only place a brand lives. The server, the checks, the voice agent and the video
pipeline all read it and none of them hard-codes a colour, a typeface or a sentence about the brand.
Swapping the brand means swapping the folder (or setting BRAND_ID).
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path

BRANDS_DIR = Path(os.environ.get('BRANDS_DIR', Path(__file__).resolve().parent.parent / 'brands'))
DEFAULT_BRAND = 'example'

REQUIRED = {
    'id': str, 'name': str, 'mission': str, 'strategy': list, 'palette': list, 'typefaces': list,
    'art_direction': list, 'tokens': dict,
}
TOKEN_CATEGORIES = ('color', 'font', 'font_size', 'line_height', 'spacing', 'duration', 'easing')
HEX = re.compile(r'#[0-9a-f]{6}')


class BrandPackError(ValueError):
    """The brand pack is missing something the machinery needs. The message says what and where."""


def validate(pack: dict) -> list[str]:
    """Every problem in a brand pack, as plain sentences. An empty list means it can be used."""
    problems: list[str] = []
    for key, kind in REQUIRED.items():
        if key not in pack:
            problems.append(f'"{key}" is missing.')
        elif not isinstance(pack[key], kind):
            problems.append(f'"{key}" should be a {kind.__name__}.')
    if problems:
        return problems

    names = set()
    for i, c in enumerate(pack['palette']):
        where = f'palette[{i}]'
        if not isinstance(c.get('name'), str) or not c.get('name'):
            problems.append(f'{where} has no name.')
        elif c['name'] in names:
            problems.append(f'{where}: the name "{c["name"]}" is used twice.')
        names.add(c.get('name'))
        if not HEX.fullmatch(str(c.get('hex', ''))):
            problems.append(f'{where} ({c.get("name")}): "hex" should look like #1c2420, lower case, six digits.')
        if not c.get('group'):
            problems.append(f'{where} ({c.get("name")}) has no group (for example primary or secondary).')
    if not pack['palette']:
        problems.append('The palette is empty.')

    for i, t in enumerate(pack['typefaces']):
        if not t.get('name'):
            problems.append(f'typefaces[{i}] has no name.')
    for i, lens in enumerate(pack['art_direction']):
        for key in ('id', 'title', 'intro'):
            if not lens.get(key):
                problems.append(f'art_direction[{i}] has no "{key}".')

    tokens = pack['tokens']
    for category in ('color', 'font', 'spacing', 'duration'):
        if not isinstance(tokens.get(category), dict) or not tokens[category]:
            problems.append(f'tokens.{category} is missing or empty: the CSS check needs it.')
    for name, value in (tokens.get('color') or {}).items():
        if not HEX.fullmatch(str(value)):
            problems.append(f'tokens.color["{name}"] should look like #1c2420, lower case, six digits.')
    for category in ('spacing', 'duration'):
        for name, value in (tokens.get(category) or {}).items():
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                problems.append(f'tokens.{category}["{name}"] should be a number (px for spacing, ms for duration).')
    for name, value in (tokens.get('font') or {}).items():
        if not isinstance(value, list) or not value:
            problems.append(f'tokens.font["{name}"] should be a list of family names, the brand face first.')
    return problems


def available() -> list[str]:
    """The ids of the brand packs on disk."""
    return sorted(p.parent.name for p in BRANDS_DIR.glob('*/brand.json'))


@lru_cache
def load(brand_id: str | None = None) -> dict:
    """The brand pack named by `brand_id`, else by the BRAND_ID environment variable, else the example."""
    brand_id = brand_id or os.environ.get('BRAND_ID') or DEFAULT_BRAND
    path = BRANDS_DIR / brand_id / 'brand.json'
    if not path.is_file():
        raise BrandPackError(f'No brand pack "{brand_id}" in {BRANDS_DIR}. Available: {", ".join(available()) or "none"}.')
    pack = json.loads(path.read_text(encoding='utf8'))
    problems = validate(pack)
    if problems:
        raise BrandPackError(f'{path} cannot be used:\n- ' + '\n- '.join(problems))
    for category in TOKEN_CATEGORIES:
        pack['tokens'].setdefault(category, {})
    pack.setdefault('voice', {'principles': [], 'avoid': []})
    return pack
