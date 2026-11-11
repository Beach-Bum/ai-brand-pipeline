"""The brand pack loader and the checks, tested against the made-up example brand."""
import copy
import json

import pytest

from brand_agent import brand as brand_module
from brand_agent import checks
from brand_agent.brand import BrandPackError, load, validate


@pytest.fixture
def pack():
    return load('example')


# ------------------------------------------------------------------ brand pack

def test_example_pack_is_valid(pack):
    assert validate(pack) == []
    assert pack['name'] == 'Fieldnote' and pack['fictional'] is True


def test_unknown_brand_names_what_exists():
    with pytest.raises(BrandPackError, match='Available: example'):
        load('no-such-brand')


@pytest.mark.parametrize('damage, expected', [
    (lambda p: p.pop('palette'), '"palette" is missing.'),
    (lambda p: p['palette'][0].update(hex='#FFF'), 'should look like #1c2420'),
    (lambda p: p['palette'].append(dict(p['palette'][0])), 'is used twice'),
    (lambda p: p['tokens'].pop('spacing'), 'tokens.spacing is missing or empty'),
    (lambda p: p['tokens']['duration'].update({'--dur-x': '200ms'}), 'should be a number'),
    (lambda p: p['art_direction'][0].pop('intro'), 'art_direction[0] has no "intro"'),
])
def test_validate_says_what_is_wrong(pack, damage, expected):
    broken = copy.deepcopy(pack)
    damage(broken)
    assert any(expected in problem for problem in validate(broken)), validate(broken)


def test_a_broken_pack_on_disk_is_refused(tmp_path, monkeypatch, pack):
    broken = copy.deepcopy(pack)
    broken['palette'] = []
    (tmp_path / 'bad').mkdir()
    (tmp_path / 'bad' / 'brand.json').write_text(json.dumps(broken), encoding='utf8')
    monkeypatch.setattr(brand_module, 'BRANDS_DIR', tmp_path)
    load.cache_clear()
    with pytest.raises(BrandPackError, match='The palette is empty'):
        load('bad')
    load.cache_clear()


# ------------------------------------------------------------------ colour

@pytest.mark.parametrize('given, expected', [('#ABC', '#aabbcc'), ('1c2420', '#1c2420'), ('#E8501F', '#e8501f'), ('#1c242080', '#1c2420')])
def test_normalise_hex(given, expected):
    assert checks.normalise_hex(given) == expected


@pytest.mark.parametrize('bad', ['', '#12', 'red', '#12345g'])
def test_normalise_hex_rejects(bad):
    with pytest.raises(ValueError):
        checks.normalise_hex(bad)


def test_brand_colour_is_recognised(pack):
    r = checks.nearest_brand_colour(pack, '#E8501F')
    assert r['in_brand'] and r['delta_e'] == 0 and 'Signal' in r['defined_as']


def test_near_miss_gets_the_brand_colour(pack):
    r = checks.nearest_brand_colour(pack, '#e85a2a')  # an orange, but not the brand's
    assert not r['in_brand'] and r['nearest'] == '#e8501f' and 0 < r['delta_e'] < 10


def test_contrast_known_values():
    assert checks.contrast('#000000', '#ffffff')['ratio'] == 21.0
    assert checks.contrast('#ffffff', '#ffffff')['ratio'] == 1.0
    assert checks.contrast('#ffffff', '#000000') == {**checks.contrast('#000000', '#ffffff'), 'foreground': '#ffffff', 'background': '#000000'}
    ink_on_paper = checks.contrast('#1c2420', '#f4f1e8')
    assert ink_on_paper['passes_body_text'] and ink_on_paper['ratio'] > 13
    stone_on_paper = checks.contrast('#b9b5a7', '#f4f1e8')
    assert not stone_on_paper['passes_large_text']


# ------------------------------------------------------------------ CSS

def rules(pack, css):
    return [(f['rule'], f['value']) for f in checks.lint_css(pack, css)]


def test_clean_css_has_no_findings(pack):
    css = """
    .card { color: #1c2420; background: #F4F1E8; padding: 24px 16px; margin: 0; gap: 8px; }
    .card h2 { font-family: "Inter", system-ui, sans-serif; transition: opacity 120ms; }
    .card code { font-family: var(--font-data); border: 1px solid #fff; }
    """
    assert rules(pack, css) == []


def test_each_rule_fires(pack):
    css = """
    .a { color: #1a73e8; }
    .b { font-family: Roboto, sans-serif; }
    .c { padding: 10px 16px; }
    .d { transition: all 0.3s ease; }
    """
    assert rules(pack, css) == [('colour', '#1a73e8'), ('font', 'Roboto'), ('spacing', '10px'), ('duration', '0.3s')]


def test_findings_carry_line_severity_and_suggestion(pack):
    f = checks.lint_css(pack, 'a {}\n.x { margin-top: 20px; }')[0]
    assert (f['line'], f['severity'], f['suggestion']) == (2, 'warning', '16px')
    assert checks.lint_css(pack, '.x { color: #ff0000 }')[0]['severity'] == 'error'


def test_comments_are_ignored(pack):
    assert rules(pack, '/* was #ff0000 and Comic Sans */ .x { color: #1c2420; }') == []


def test_font_shorthand_is_read(pack):
    assert rules(pack, '.x { font: 600 16px/1.4 Helvetica, sans-serif; }') == [('font', 'Helvetica')]
    assert rules(pack, '.x { font: 16px "Inter", sans-serif; }') == []


def test_sizes_that_are_not_spacing_are_left_alone(pack):
    assert rules(pack, '.x { font-size: 13px; width: 250px; border-radius: 6px; line-height: 20px; }') == []


# ------------------------------------------------------------------ copy

def test_lint_copy_finds_avoided_words_with_lines(pack):
    found = checks.lint_copy(pack, 'A notebook.\nA Revolutionary, seamless notebook.')
    assert [(f['line'], f['value']) for f in found] == [(2, 'Revolutionary'), (2, 'seamless')]


def test_lint_copy_matches_whole_words_only(pack):
    assert checks.lint_copy(pack, 'The seamlessly bound spine.') == []
