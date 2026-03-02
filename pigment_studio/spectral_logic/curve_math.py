import numpy as np
from core.data import WAVE_MIN, WAVE_MAX, WAVE_SAMPLES


def find_peak_and_trough(reflectance):
    """
    Return (peak_wave, peak_val, trough_wave, trough_val).
    """
    peak_idx = np.argmax(reflectance)
    trough_idx = np.argmin(reflectance)
    p_wave = WAVE_MIN + peak_idx
    t_wave = WAVE_MIN + trough_idx
    return p_wave, reflectance[peak_idx], t_wave, reflectance[trough_idx]
