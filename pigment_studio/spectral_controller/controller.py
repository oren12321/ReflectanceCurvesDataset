from typing import Callable
from PySide6.QtCore import QObject, Signal, QThread

from core.data import SpectralData
from spectral_logic.color_engine import ColorEngine
from spectral_logic.optimizer import SpectralOptimizer
from spectral_logic.target_extraction import TargetExtractor
from spectral_logic.background_math import (
    default_extent,
    update_extent_from_sliders,
    sync_sliders_from_extent,
)
from spectral_logic.curve_math import find_peak_and_trough


class OptimizationWorker(QThread):
    """
    Runs optimization in a separate thread for UI responsiveness.
    """

    finished_with_result = Signal(dict)

    def __init__(self, optimizer: SpectralOptimizer, data: SpectralData, stop_flag: Callable[[], bool], log: Callable[[str], None]):
        super().__init__()
        self.optimizer = optimizer
        self.data = data
        self._stop_flag = stop_flag
        self._log = log

    def run(self):
        result = self.optimizer.optimize(
            points=self.data.points,
            target_lab=self.data.target_lab,
            active_illuminant_key=self.data.illuminant_key,
            stop_flag=self._stop_flag,
            progress_callback=self._log,
        )
        self.finished_with_result.emit(result)


class SpectralController(QObject):
    """
    Controller that mediates between UI and spectral logic.
    """

    optimization_started = Signal()
    optimization_finished = Signal(dict)

    def __init__(self, data: SpectralData, parent=None):
        super().__init__(parent)
        self.data = data
        self.color_engine = ColorEngine()
        self.optimizer = SpectralOptimizer(self.color_engine)
        self.target_extractor = TargetExtractor(self.color_engine)
        self._stop_optimization = False
        self._worker: OptimizationWorker | None = None

    # ---------------------- Data access helpers -------------------------

    def reset_data(self):
        self.data.reset_all()

    def set_illuminant_key(self, key: str):
        self.data.illuminant_key = key

    def get_interpolated(self):
        return self.data.get_interpolated()

    def get_peak_and_trough(self, reflectance):
        return find_peak_and_trough(reflectance)

    def spectral_to_lab_rgb(self, reflectance):
        return self.color_engine.spectral_to_lab_and_rgb(
            reflectance, self.data.illuminant_key
        )

    def lab_to_rgb_hex(self, lab):
        return self.color_engine.lab_to_rgb_hex(lab)

    def delta_e_to_target(self, lab):
        if self.data.target_lab is None:
            return None
        return self.color_engine.delta_e(self.data.target_lab, lab)

    def extract_target_from_crop(self, qimage):
        lab, rgb = self.target_extractor.extract_lab_from_crop(qimage)
        self.data.target_lab = lab.tolist()
        return lab, rgb

    # ---------------------- Background layers ---------------------------

    def add_background_layer(self, b64_str: str, name: str):
        self.data.bg_layers.append(
            {"base64": b64_str, "extent": default_extent(), "visible": True, "name": name}
        )

    def get_background_layers(self):
        return self.data.bg_layers

    def set_layer_extent_from_sliders(self, index: int, x, y, w, h):
        if 0 <= index < len(self.data.bg_layers):
            self.data.bg_layers[index]["extent"] = update_extent_from_sliders(
                x, y, w, h
            )

    def get_layer_sliders_from_extent(self, index: int):
        if 0 <= index < len(self.data.bg_layers):
            return sync_sliders_from_extent(self.data.bg_layers[index]["extent"])
        return None

    def set_layer_visibility(self, index: int, visible: bool):
        if 0 <= index < len(self.data.bg_layers):
            self.data.bg_layers[index]["visible"] = visible

    def remove_layer(self, index: int):
        if 0 <= index < len(self.data.bg_layers):
            return self.data.bg_layers.pop(index)
        return None

    def clear_layers(self):
        self.data.bg_layers = []

    # ---------------------- Points / curve ------------------------------

    def reset_curve(self):
        self.data.points = {380.0: 50.0, 780.0: 50.0}

    def set_point(self, x: float, y: float):
        self.data.points[x] = y

    def delete_point(self, x: float):
        if x in self.data.points and len(self.data.points) > 2:
            del self.data.points[x]

    def move_point(self, old_x: float, new_x: float, new_y: float):
        if old_x in self.data.points:
            self.data.points.pop(old_x)
            if new_x in self.data.points and new_x != old_x:
                new_x += 1e-9
            self.data.points[new_x] = new_y
            return new_x
        return old_x

    def scale_amplitude(self, scale: float):
        for k in list(self.data.points.keys()):
            self.data.points[k] = float(
                max(0.5, min(99.5, self.data.points[k] * scale))
            )

    # ---------------------- Optimization -------------------------------

    def start_optimization(self, log_callback: Callable[[str], None]):
        if self.data.target_lab is None:
            log_callback("Error: No target color loaded.")
            return

        num_pts = len(self.data.points)
        if num_pts < 5:
            log_callback(
                f"Warning: Only {num_pts} points. Optimization may be too stiff."
            )
        elif num_pts > 25:
            log_callback(
                f"Notice: {num_pts} points. High density may cause jitter or slow performance."
            )

        self._stop_optimization = False
        self._worker = OptimizationWorker(
            optimizer=self.optimizer,
            data=self.data,
            stop_flag=lambda: self._stop_optimization,
            log=log_callback,
        )
        self._worker.finished_with_result.connect(self._on_optimization_finished)
        self.optimization_started.emit()
        self._worker.start()

    def stop_optimization(self):
        self._stop_optimization = True

    def _on_optimization_finished(self, result: dict):
        if result.get("success") and result.get("best_points") is not None:
            self.data.points = result["best_points"]
        self.optimization_finished.emit(result)
