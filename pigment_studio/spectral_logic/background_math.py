from typing import List, Dict
from core.data import WAVE_MIN, WAVE_MAX


def default_extent():
    return [WAVE_MIN, WAVE_MAX, 0, 100]


def update_extent_from_sliders(x, y, w, h):
    """
    Convert slider values to extent [left, right, bottom, top].
    """
    l = x
    r = x + w
    b = -y
    t = b + h
    return [l, r, b, t]


def sync_sliders_from_extent(extent):
    """
    Convert extent [l, r, b, t] to slider values (x, y, w, h).
    """
    l, r, b, t = extent
    x = l
    w = r - l
    y = -b
    h = t - b
    return x, y, w, h


def remove_layer(layers: List[Dict], index: int):
    if 0 <= index < len(layers):
        return layers.pop(index)
    return None
