"""Checks a piece of work against a brand pack. Pure functions: no model, no network.

Everything a check compares against comes from the brand pack passed in. A check never decides what
the brand is; it reports where the work differs from it, with the nearest correct value.
"""
from __future__ import annotations

import re

# Values that are not a design decision, so they are never reported.
NEUTRAL_COLOURS = {'#ffffff', '#000000'}
GENERIC_FAMILIES = {'serif', 'sans-serif', 'monospace', 'system-ui', 'inherit', 'initial', 'unset',
                    'ui-monospace', 'ui-sans-serif', 'ui-serif', '-apple-system'}


# ------------------------------------------------------------------ colour

def normalise_hex(value: str) -> str:
    """'#ABC' or 'abcdef' -> '#aabbcc'. Raises ValueError for anything that is not a hex colour."""
    v = value.strip().lstrip('#').lower()
    if len(v) in (3, 4):
        v = ''.join(c * 2 for c in v)
    if len(v) == 8:  # with alpha: the colour is what is checked
        v = v[:6]
    if not re.fullmatch(r'[0-9a-f]{6}', v):
        raise ValueError(f'not a hex colour: {value!r}')
    return '#' + v


def _linear(channel: float) -> float:
    channel /= 255
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def _rgb(hex_colour: str) -> tuple[int, int, int]:
    h = normalise_hex(hex_colour)
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def _lab(hex_colour: str) -> tuple[float, float, float]:
    """sRGB -> CIE L*a*b* (D65), so that 'nearest' means nearest to the eye and not nearest in RGB."""
    r, g, b = (_linear(c) for c in _rgb(hex_colour))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def brand_colours(brand: dict) -> dict[str, str]:
    """Every colour the brand defines: hex -> where it is defined (palette name or token)."""
    out = {c['hex']: f"palette: {c['name']} ({c['group']})" for c in brand['palette']}
    for token, value in brand['tokens']['color'].items():
        out.setdefault(value, f'token: {token}')
    return out


def nearest_brand_colour(brand: dict, hex_colour: str) -> dict:
    """The brand colour closest to the given one, and how far apart they are (delta E, CIE76).
    Under about 2 the two are hard to tell apart; over 10 they are clearly different colours."""
    colours = brand_colours(brand)
    target = _lab(hex_colour)

    def distance(other: str) -> float:
        return sum((a - b) ** 2 for a, b in zip(target, _lab(other))) ** 0.5

    best = min(colours, key=distance)
    return {'given': normalise_hex(hex_colour), 'nearest': best, 'defined_as': colours[best],
            'delta_e': round(distance(best), 1), 'in_brand': normalise_hex(hex_colour) in colours}


def contrast(foreground: str, background: str) -> dict:
    """WCAG 2 contrast ratio of two colours, and which text sizes it is enough for."""
    def luminance(h: str) -> float:
        r, g, b = (_linear(c) for c in _rgb(h))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    lighter, darker = sorted((luminance(foreground), luminance(background)), reverse=True)
    ratio = (lighter + 0.05) / (darker + 0.05)
    return {'foreground': normalise_hex(foreground), 'background': normalise_hex(background), 'ratio': round(ratio, 2),
            'passes_body_text': ratio >= 4.5, 'passes_large_text': ratio >= 3.0}


# ------------------------------------------------------------------ CSS

def _nearest(value: float, allowed: list) -> float:
    return min(allowed, key=lambda a: abs(a - value))


def lint_css(brand: dict, css: str) -> list[dict]:
    """Reports every place a stylesheet steps outside the brand system.

    Rules: `colour` (a hex colour the brand does not define), `font` (a typeface that is not one of
    the brand's), `spacing` (a margin, padding or gap in px that is not on the spacing scale) and
    `duration` (a transition or animation time that is not a brand duration).
    Colour and font findings are errors; spacing and duration findings are warnings.
    """
    colours = brand_colours(brand)
    families = {f.lower() for fs in brand['tokens']['font'].values() for f in fs} | {t['name'].lower() for t in brand['typefaces']}
    face_names = ', '.join(t['name'] for t in brand['typefaces'])
    scale = sorted(brand['tokens']['spacing'].values())
    durations = sorted(brand['tokens']['duration'].values())
    findings: list[dict] = []

    for number, line in enumerate(css.splitlines(), 1):
        code = re.sub(r'/\*.*?\*/', '', line)

        for raw in re.findall(r'#[0-9a-fA-F]{3,8}\b', code):
            try:
                colour = normalise_hex(raw)
            except ValueError:
                continue
            if colour in colours or colour in NEUTRAL_COLOURS:
                continue
            near = nearest_brand_colour(brand, colour)
            findings.append({'rule': 'colour', 'severity': 'error', 'line': number, 'value': raw,
                             'message': f"{raw} is not a {brand['name']} colour. Nearest: {near['nearest']} ({near['defined_as']}), delta E {near['delta_e']}.",
                             'suggestion': near['nearest']})

        m = re.search(r'\bfont(-family)?\s*:\s*([^;}]+)', code)
        if m and 'var(' not in m.group(2):
            declared = m.group(2)
            if not m.group(1):  # the `font:` shorthand: the family follows the size
                # drop everything up to and including the size (and the line height after a slash)
                declared = re.sub(r'^.*?\d[\d.]*(?:px|rem|em|pt|%)(?:\s*/\s*[\w.%]+)?\s+', '', declared, count=1)
            for family in (f.strip().strip('"\'') for f in declared.split(',')):
                if family and family.lower() not in families and family.lower() not in GENERIC_FAMILIES:
                    findings.append({'rule': 'font', 'severity': 'error', 'line': number, 'value': family,
                                     'message': f"'{family}' is not a {brand['name']} typeface. Use {face_names}.",
                                     'suggestion': face_names})

        m = re.search(r'\b(?:margin|padding|gap|row-gap|column-gap)(?:-[a-z]+)*\s*:\s*([^;}]+)', code)
        if m and scale:
            for px in re.findall(r'(?<![\w.])-?(\d+)px', m.group(1)):  # a negative margin is still a step on the scale
                if int(px) and int(px) not in scale:
                    near = _nearest(int(px), scale)
                    findings.append({'rule': 'spacing', 'severity': 'warning', 'line': number, 'value': f'{px}px',
                                     'message': f'{px}px is not on the spacing scale ({", ".join(map(str, scale))}). Nearest: {near}px.',
                                     'suggestion': f'{near}px'})

        m = re.search(r'\b(?:transition|animation)(?:-duration)?\s*:\s*([^;}]+)', code)
        if m and durations:
            for amount, unit in re.findall(r'(?<![\w.-])(\d*\.?\d+)(ms|s)\b', m.group(1)):
                ms = round(float(amount) * (1000 if unit == 's' else 1))
                if ms and ms not in durations:
                    near = _nearest(ms, durations)
                    findings.append({'rule': 'duration', 'severity': 'warning', 'line': number, 'value': f'{amount}{unit}',
                                     'message': f'{amount}{unit} is not a brand duration ({", ".join(f"{d}ms" for d in durations)}). Nearest: {near}ms.',
                                     'suggestion': f'{near}ms'})
    return findings


# ------------------------------------------------------------------ copy

def lint_copy(brand: dict, text: str) -> list[dict]:
    """Reports words and phrases the brand pack lists under voice.avoid. It checks only what the
    pack states exactly; whether copy sounds like the brand is a judgement left to the model, which
    gets the voice principles from the pack and not from this function."""
    findings = []
    for phrase in brand.get('voice', {}).get('avoid', []):
        for m in re.finditer(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', text, flags=re.I):
            line = text.count('\n', 0, m.start()) + 1
            findings.append({'rule': 'avoid', 'severity': 'error', 'line': line, 'value': m.group(0),
                             'message': f'"{m.group(0)}" is on the {brand["name"]} avoid list.', 'suggestion': None})
    return sorted(findings, key=lambda f: f['line'])
