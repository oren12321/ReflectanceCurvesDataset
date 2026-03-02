import numpy as np
import colour
from core.data import WAVE_MIN, WAVE_MAX, WAVE_SAMPLES


class ColorEngine:
    """
    Encapsulates colour-science operations.
    No UI or Qt here.
    """

    def __init__(self):
        self.cmfs = self._load_cmfs()
        self.illuminants_cache = {}

    def _load_cmfs(self):
        try:
            return (
                colour.MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]
                .copy()
                .align(colour.SpectralShape(WAVE_MIN, WAVE_MAX, 1))
            )
        except Exception:
            return (
                colour.multi_spectral_distributions[
                    "CIE 1931 2 Degree Standard Observer"
                ]
                .copy()
                .align(colour.SpectralShape(WAVE_MIN, WAVE_MAX, 1))
            )

    def get_illuminant(self, key: str):
        if key in self.illuminants_cache:
            return self.illuminants_cache[key]
        try:
            ill = colour.SDS_ILLUMINANTS[key].copy().align(self.cmfs.shape)
        except Exception:
            ill = (
                colour.spectral_distributions_illuminants[key]
                .copy()
                .align(self.cmfs.shape)
            )
        self.illuminants_cache[key] = ill
        return ill

    def spectral_to_lab_and_rgb(self, reflectance, illuminant_key: str):
        """
        Convert a reflectance curve (0-100) to Lab and sRGB under given illuminant.
        """
        sd = colour.SpectralDistribution(
            dict(zip(WAVE_SAMPLES, reflectance / 100.0))
        )
        ill = self.get_illuminant(illuminant_key)
        XYZ = colour.sd_to_XYZ(sd, self.cmfs, ill) / 100.0
        Lab = colour.XYZ_to_Lab(XYZ)
        rgb = np.clip(colour.XYZ_to_sRGB(XYZ), 0, 1)
        return Lab, rgb

    def lab_to_rgb_hex(self, lab):
        xyz = colour.Lab_to_XYZ(lab)
        rgb = np.clip(colour.XYZ_to_sRGB(xyz), 0, 1)
        return rgb, "#%02x%02x%02x" % tuple((rgb * 255).astype(int))

    def rgb_to_lab(self, rgb):
        xyz = colour.sRGB_to_XYZ(rgb)
        lab = colour.XYZ_to_Lab(xyz)
        return lab

    def delta_e(self, lab1, lab2):
        return colour.delta_E(lab1, lab2, method="CIE 2000")
