"""Stable gl-transitions registry; modules load on first access."""
import importlib

PORT_NAMES = (
    'gl_clock_wipe',
    'gl_cross_warp',
    'gl_directional_warp',
    'gl_dreamy',
    'gl_dreamy_zoom',
    'gl_rotate_scale_fade',
    'gl_swirl',
    'gl_water_drop',
    'gl_burn_through',
    'gl_overexposure',
    'gl_fade_grayscale',
    'gl_color_distance',
    'gl_luminance_melt',
    'gl_pixelize',
    'gl_dither_dissolve',
    'gl_random_squares',
    'gl_window_slices',
    'gl_wind',
    'gl_pinwheel',
    'gl_polka_dots_curtain',
    'gl_crosshatch',
    'gl_perlin_dissolve',
    'gl_glitch_memories',
    'gl_scale_in',
    'gl_bounce',
    'gl_multiply_blend',
    'gl_color_phase',
    'gl_hexagonalize',
    'gl_squares_wipe',
    'gl_bow_tie_horizontal',
    'gl_curved_wipe',
    'gl_arrow_wipe',
)


def __getattr__(name):
    if name in PORT_NAMES:
        return importlib.import_module('.' + name, __package__)
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


def load_all():
    """Import every port so @transition registration still runs at package import."""
    return [importlib.import_module('.' + name, __package__) for name in PORT_NAMES]


load_all()
