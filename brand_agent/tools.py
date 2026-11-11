"""The brand tools, as plain functions with one description each.

There is one list of tools and three ways in: the MCP server registers them, the voice agent hands
them to its model, and the video pipeline calls them directly. Adding a tool here adds it everywhere.
"""
from __future__ import annotations

from typing import Literal

from . import checks
from .brand import load
from .tracing import traced


@traced
def brand_strategy() -> dict:
    """What the brand is for and how it should come across: the mission line, the strategy points
    and the voice principles from the guidelines. Read this before writing copy or briefing imagery."""
    b = load()
    return {'brand': b['name'], 'mission': b['mission'], 'points': b['strategy'], 'voice': b['voice'], 'source': b.get('source', {})}


@traced
def brand_palette(group: str = 'all') -> list[dict]:
    """The brand colours with their values and which text colour goes on each. `group` narrows it
    to one group (for example primary or secondary); 'all' returns every colour."""
    return [c for c in load()['palette'] if group in ('all', c['group'])]


@traced
def brand_typography() -> dict:
    """The brand typefaces with their roles and styles, the CSS font stacks, and the type sizes and
    line heights."""
    b = load()
    t = b['tokens']
    return {'typefaces': b['typefaces'], 'css_font_stacks': t['font'], 'sizes': t['font_size'], 'line_heights': t['line_height']}


@traced
def brand_art_direction(lens: str = 'all') -> list[dict]:
    """The art-direction lenses for imagery: what each shows, what it is used to say, and its colour
    swatches. Use it to brief photography, illustration, generated images or video. `lens` is a lens
    id, or 'all'."""
    return [x for x in load()['art_direction'] if lens in ('all', x['id'])]


@traced
def brand_tokens(category: Literal['color', 'font', 'font_size', 'line_height', 'spacing', 'duration', 'easing']) -> dict:
    """The design tokens of one category, as CSS custom property names and values."""
    return load()['tokens'][category]


@traced
def nearest_brand_colour(hex_colour: str) -> dict:
    """Whether a hex colour is a brand colour and, if it is not, the closest one that is, with the
    perceptual distance between them (delta E: under 2 is hard to see, over 10 is a different colour)."""
    return checks.nearest_brand_colour(load(), hex_colour)


@traced
def check_contrast(foreground: str, background: str) -> dict:
    """The WCAG contrast ratio of a text colour on a background colour, and whether it is enough
    for body text (4.5) and for large text (3.0)."""
    return checks.contrast(foreground, background)


def _report(findings: list[dict]) -> dict:
    return {
        'ok': not any(f['severity'] == 'error' for f in findings),
        'errors': sum(f['severity'] == 'error' for f in findings),
        'warnings': sum(f['severity'] == 'warning' for f in findings),
        'findings': findings,
    }


@traced
def lint_css(css: str) -> dict:
    """Checks a stylesheet against the brand system. Reports hex colours the brand does not define,
    typefaces that are not the brand's, spacing that is off the scale and animation times that are
    not brand durations. Each finding has the line, the value, and the nearest correct value."""
    return _report(checks.lint_css(load(), css))


@traced
def lint_copy(text: str) -> dict:
    """Checks copy against the brand's avoid list and reports each word or phrase found, with its
    line. It does not judge tone: for that, read the voice principles from brand_strategy."""
    return _report(checks.lint_copy(load(), text))


# The order here is the order an agent sees them in: facts first, checks after.
ALL = [brand_strategy, brand_palette, brand_typography, brand_art_direction, brand_tokens,
       nearest_brand_colour, check_contrast, lint_css, lint_copy]
BY_NAME = {f.__name__: f for f in ALL}
