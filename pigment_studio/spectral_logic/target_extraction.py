import numpy as np
from PySide6.QtGui import QImage
from spectral_logic.color_engine import ColorEngine


class TargetExtractor:
    """
    Extracts a representative target color from a cropped QImage.
    """

    def __init__(self, color_engine: ColorEngine):
        self.color_engine = color_engine

    def extract_lab_from_crop(self, qimage: QImage):
        """
        Convert crop to Lab:
          - Convert to RGB
          - Compute chroma
          - Take top 10% saturated pixels
          - Median RGB -> Lab
        """
        qimage = qimage.convertToFormat(QImage.Format_RGB32).rgbSwapped()
        width, height = qimage.width(), qimage.height()
        ptr = qimage.bits()
        arr = (
            np.frombuffer(ptr, np.uint8)
            .reshape((height, width, 4))[:, :, :3]
            / 255.0
        )
        pixels = arr.reshape(-1, 3)
        chroma = np.max(pixels, axis=1) - np.min(pixels, axis=1)
        threshold = np.percentile(chroma, 90)
        vibrant_pixels = pixels[chroma >= threshold]
        target_rgb = np.median(vibrant_pixels, axis=0)
        lab = self.color_engine.rgb_to_lab(target_rgb)
        return lab, target_rgb
