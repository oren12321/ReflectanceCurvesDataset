import numpy as np

WAVE_MIN, WAVE_MAX = 380, 780
WAVE_SAMPLES = np.arange(WAVE_MIN, WAVE_MAX + 1, 1)


class SpectralData:
    """
    Pure data model for spectral information.
    No UI or algorithmic logic here.
    """

    def __init__(self):
        self.reset_all()

    def reset_all(self):
        """Reset all spectral-related data to a clean state."""
        self.points = {float(WAVE_MIN): 50.0, float(WAVE_MAX): 50.0}
        self.bg_layers = []  # list of dicts: {"base64", "extent", "visible", "name"}
        self.target_lab = None  # [L, a, b] or None
        self.illuminant_key = "D65"  # 'D65', 'A', 'FL2'

    def get_interpolated(self):
        """Return interpolated reflectance curve over WAVE_SAMPLES."""
        sorted_keys = sorted(self.points.keys())
        sorted_vals = [self.points[k] for k in sorted_keys]
        return np.interp(WAVE_SAMPLES, sorted_keys, sorted_vals)

    def to_dict(self):
        """Serialize to JSON-friendly dict."""
        return {
            "spectral_points": {str(k): v for k, v in self.points.items()},
            "background_layers": self.bg_layers,
            "target_lab": self.target_lab,
            "illuminant_key": self.illuminant_key,
        }

    def from_dict(self, data: dict):
        """Load from JSON-friendly dict."""
        raw_points = data.get("spectral_points", {})
        self.points = {float(k): v for k, v in raw_points.items()}
        self.bg_layers = data.get("background_layers", [])
        self.target_lab = data.get("target_lab", None)
        self.illuminant_key = data.get("illuminant_key", "D65")
