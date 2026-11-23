"""FX catalog package; effect and transition modules load on import."""
import importlib

from .core import Context, effect, transition, EFFECTS, TRANSITIONS, evaluate

_CATALOG_MODULES = (
    '.effects.flash_white',
    '.effects.grade',
    '.effects.halation',
    '.effects.beat_bounce',
    '.effects.zoom_punch',
    '.effects.cutout_card',
    '.effects.accents',
    '.effects.styles',
    '.effects.typography',
    '.effects.parallax',
    '.effects.camera',
    '.transitions.crossfade',
    '.transitions.whip_pan',
    '.transitions.hex_shutter',
    '.transitions.flash_cut',
    '.transitions.extended',
    '.transitions.gl_ports',
)


def load_catalog():
    """Import catalog modules so @effect / @transition registration runs."""
    return [importlib.import_module(name, __package__) for name in _CATALOG_MODULES]


load_catalog()
