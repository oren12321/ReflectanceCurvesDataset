import base64
import io
import os

import numpy as np
from PIL import Image

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QSlider,
    QGroupBox,
    QFrame,
    QComboBox,
    QCheckBox,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from core.data import WAVE_MIN, WAVE_MAX, WAVE_SAMPLES
from plugins.spectral.crop_dialog import CropDialog
from spectral_controller.controller import SpectralController


class SpectralAnalysisWidget(QWidget):
    """
    UI-only spectral editor widget.
    All domain logic is delegated to SpectralController.
    """

    log_signal = Signal(str)

    def __init__(self, controller: SpectralController, parent=None):
        super().__init__(parent)
        self.controller = controller

        self.dragging_key = None
        self.pick_radius = 10
        self.bg_artists = []
        self.is_loading_layer = False

        self._build_layout()
        self._connect_canvas_events()
        self._connect_controller_signals()

        self.update_view()

    def _build_layout(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.controls_sidebar = QFrame()
        self.controls_sidebar.setFixedWidth(260)
        sidebar_outer_layout = QVBoxLayout(self.controls_sidebar)
        sidebar_outer_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.sidebar_content = QWidget()
        self.sidebar_layout = QVBoxLayout(self.sidebar_content)
        self.sidebar_layout.setContentsMargins(10, 10, 10, 10)
        self.sidebar_layout.setSpacing(12)

        self.scroll_area.setWidget(self.sidebar_content)
        sidebar_outer_layout.addWidget(self.scroll_area)

        self._build_sidebar_sections()

        self.canvas_container = QWidget()
        canvas_layout = QVBoxLayout(self.canvas_container)
        canvas_layout.setContentsMargins(6, 6, 6, 6)
        canvas_layout.setSpacing(6)

        self.fig = Figure(figsize=(8, 4), facecolor="#2b2b2a")
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.message = lambda x: ""

        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#1f1f1e")
        self.ax.format_coord = lambda x, y: ""

        self.tooltip = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(
                boxstyle="round,pad=0.5",
                fc="#3d3d3b",
                ec="#d4af37",
                alpha=0.9,
            ),
            color="#e0e0e0",
            fontsize=9,
            fontweight="bold",
            zorder=10,
        )
        self.tooltip.set_visible(False)

        self.line, = self.ax.plot([], [], color="#d4af37", lw=2, zorder=5)
        self.dots = self.ax.scatter(
            [], [], color="white", s=50, zorder=6, edgecolors="black"
        )

        gradient = np.linspace(WAVE_MIN, WAVE_MAX, 256)
        self.ax.imshow(
            [gradient],
            extent=[WAVE_MIN, WAVE_MAX, -5, 0],
            aspect="auto",
            cmap="turbo",
            zorder=0,
        )
        self.ax.grid(True, which="both", linestyle=":", color="#5a5a58", alpha=0.6)
        self.ax.set_axisbelow(True)
        self.ax.set_ylim(-5, 105)
        self.ax.set_xlim(WAVE_MIN - 5, WAVE_MAX + 5)
        self.extrema_annotes = []

        canvas_layout.addWidget(self.toolbar)
        canvas_layout.addWidget(self.canvas)

        self.color_preview = QLabel("Color Preview")
        self.color_preview.setFixedHeight(40)
        self.color_preview.setAlignment(Qt.AlignCenter)
        canvas_layout.addWidget(self.color_preview)

        main_layout.addWidget(self.controls_sidebar)
        main_layout.addWidget(self.canvas_container)

    def _build_sidebar_sections(self):
        spectrum_group = QGroupBox("Spectrum Tools")
        spec_layout = QVBoxLayout(spectrum_group)
        self.btn_reset = QPushButton("Reset Spectrum")
        self.btn_reset.clicked.connect(self._on_reset_clicked)
        spec_layout.addWidget(self.btn_reset)

        lbl_amp = QLabel("Global Amplitude (Scale %)")
        self.slider_amplitude = QSlider(Qt.Horizontal)
        self.slider_amplitude.setRange(50, 150)
        self.slider_amplitude.setValue(100)
        self.slider_amplitude.valueChanged.connect(self._on_amplitude_changed)
        spec_layout.addWidget(lbl_amp)
        spec_layout.addWidget(self.slider_amplitude)

        self.sidebar_layout.addWidget(spectrum_group)

        bg_group = QGroupBox("Image Layers")
        bg_layout = QVBoxLayout(bg_group)

        row1 = QHBoxLayout()
        self.btn_add_bg = QPushButton("Add Layer")
        self.btn_remove_last = QPushButton("Remove Selected")
        row1.addWidget(self.btn_add_bg)
        row1.addWidget(self.btn_remove_last)
        bg_layout.addLayout(row1)

        self.btn_clear_bg = QPushButton("Clear All Layers")
        bg_layout.addWidget(self.btn_clear_bg)

        self.btn_add_bg.clicked.connect(self._on_add_layer)
        self.btn_remove_last.clicked.connect(self._on_remove_layer)
        self.btn_clear_bg.clicked.connect(self._on_clear_layers)

        self.combo_active_bg = QComboBox()
        self.combo_active_bg.currentIndexChanged.connect(
            self._on_active_layer_changed
        )

        self.check_bg_visible = QCheckBox("Show Active Layer")
        self.check_bg_visible.setChecked(True)
        self.check_bg_visible.toggled.connect(self._on_toggle_layer_visibility)

        bg_layout.addWidget(QLabel("Active Layer:"))
        bg_layout.addWidget(self.combo_active_bg)
        bg_layout.addWidget(self.check_bg_visible)

        align_group = QGroupBox("Active Layer Alignment")
        align_layout = QVBoxLayout(align_group)
        align_layout.setContentsMargins(8, 18, 8, 8)
        align_layout.setSpacing(4)

        self.slider_x = self._create_slider(align_layout, "X Pos (nm)", WAVE_MIN - 100, WAVE_MAX)
        self.slider_y = self._create_slider(align_layout, "Y Pos (%)", -50, 100)
        self.slider_w = self._create_slider(align_layout, "Width (nm)", 10, 1000, WAVE_MAX - WAVE_MIN)
        self.slider_h = self._create_slider(align_layout, "Height (%)", 10, 300, 100)

        bg_layout.addWidget(align_group)
        self.sidebar_layout.addWidget(bg_group)

        match_group = QGroupBox("Target Matching")
        match_layout = QVBoxLayout(match_group)

        self.btn_load_target = QPushButton("Load & Crop Blob")
        self.btn_load_target.clicked.connect(self._on_load_target)
        match_layout.addWidget(self.btn_load_target)

        self.target_preview = QLabel("No Target Loaded")
        self.target_preview.setFixedHeight(30)
        self.target_preview.setAlignment(Qt.AlignCenter)
        self.target_preview.setStyleSheet(
            "background: #2b2b2a; border: 1px solid #5a5a58;"
        )
        match_layout.addWidget(self.target_preview)

        self.label_delta_e = QLabel("ΔE: ---")
        self.label_delta_e.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #8fbc8f;"
        )
        self.label_delta_e.setAlignment(Qt.AlignCenter)
        match_layout.addWidget(self.label_delta_e)

        lbl_light = QLabel("Illuminant (Environment)")
        self.combo_illuminant = QComboBox()
        self.combo_illuminant.addItems(
            ["D65 (Daylight)", "A (Incandescent)", "F2 (Fluorescent)"]
        )
        self.combo_illuminant.currentIndexChanged.connect(
            self._on_illuminant_changed
        )
        match_layout.addWidget(lbl_light)
        match_layout.addWidget(self.combo_illuminant)

        self.sidebar_layout.addWidget(match_group)

        smart_group = QGroupBox("Smart Tools")
        smart_layout = QVBoxLayout(smart_group)

        self.btn_smart_match = QPushButton("Auto-Optimize Curve")
        self.btn_stop_match = QPushButton("Stop Optimization")
        self.btn_stop_match.setStyleSheet(
            "background-color: #a0522d; color: white; font-weight: bold;"
        )
        self.btn_stop_match.setEnabled(False)

        self.btn_smart_match.clicked.connect(self._on_start_optimization)
        self.btn_stop_match.clicked.connect(self._on_stop_optimization)

        smart_layout.addWidget(self.btn_smart_match)
        smart_layout.addWidget(self.btn_stop_match)

        self.sidebar_layout.addWidget(smart_group)
        self.sidebar_layout.addStretch()

    def _create_slider(self, layout, label, min_v, max_v, default=0):
        lbl = QLabel(label)
        s = QSlider(Qt.Horizontal)
        s.setRange(min_v, max_v)
        s.setValue(default)
        s.valueChanged.connect(self._on_image_geometry_changed)
        layout.addWidget(lbl)
        layout.addWidget(s)
        return s

    def _connect_canvas_events(self):
        self.canvas.mpl_connect("button_press_event", self._on_click)
        self.canvas.mpl_connect("button_release_event", self._on_release)
        self.canvas.mpl_connect("motion_notify_event", self._on_move)

    def _connect_controller_signals(self):
        self.controller.optimization_started.connect(self._on_optimization_started)
        self.controller.optimization_finished.connect(self._on_optimization_finished)

    # ---------------------- UI event handlers ---------------------------

    def _on_reset_clicked(self):
        self.controller.reset_curve()
        self.update_view()
        self.log_signal.emit("Reset curve.")

    def _on_amplitude_changed(self, value: int):
        scale = value / 100.0
        self.controller.scale_amplitude(scale)
        self.slider_amplitude.blockSignals(True)
        self.slider_amplitude.setValue(100)
        self.slider_amplitude.blockSignals(False)
        self.update_view()

    def _on_add_layer(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if not path:
            return
        with open(path, "rb") as f:
            b64_str = base64.b64encode(f.read()).decode("utf-8")
        name = os.path.basename(path)
        self.controller.add_background_layer(b64_str, name)
        self.combo_active_bg.addItem(name)
        self.combo_active_bg.setCurrentIndex(self.combo_active_bg.count() - 1)
        self.refresh_bg_artists()
        self.log_signal.emit(f"Added background layer: {name}")

    def _on_remove_layer(self):
        idx = self.combo_active_bg.currentIndex()
        if idx >= 0:
            removed = self.controller.remove_layer(idx)
            if removed:
                artist = self.bg_artists.pop(idx)
                artist.remove()
                self.combo_active_bg.removeItem(idx)
                self.canvas.draw_idle()
                self.log_signal.emit(f"Removed background layer: {removed['name']}")

    def _on_clear_layers(self):
        self.controller.clear_layers()
        self.combo_active_bg.clear()
        self.refresh_bg_artists()
        self.log_signal.emit("Cleared all background layers.")

    def _on_active_layer_changed(self, index: int):
        if index < 0:
            return
        sliders = self.controller.get_layer_sliders_from_extent(index)
        if sliders is None:
            return
        x, y, w, h = sliders
        self.is_loading_layer = True
        self.slider_x.setValue(x)
        self.slider_y.setValue(y)
        self.slider_w.setValue(w)
        self.slider_h.setValue(h)
        layers = self.controller.get_background_layers()
        self.check_bg_visible.setChecked(layers[index].get("visible", True))
        self.is_loading_layer = False

    def _on_toggle_layer_visibility(self, visible: bool):
        idx = self.combo_active_bg.currentIndex()
        if idx >= 0:
            self.controller.set_layer_visibility(idx, visible)
            if idx < len(self.bg_artists):
                self.bg_artists[idx].set_visible(visible)
                self.canvas.draw_idle()

    def _on_image_geometry_changed(self):
        if self.is_loading_layer:
            return
        idx = self.combo_active_bg.currentIndex()
        if idx < 0:
            return
        x = self.slider_x.value()
        y = self.slider_y.value()
        w = self.slider_w.value()
        h = self.slider_h.value()
        self.controller.set_layer_extent_from_sliders(idx, x, y, w, h)
        layers = self.controller.get_background_layers()
        if idx < len(self.bg_artists):
            self.bg_artists[idx].set_extent(layers[idx]["extent"])
            self.canvas.draw_idle()

    def _on_load_target(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if not path:
            return
        dialog = CropDialog(path, self)
        if dialog.exec():
            qimg = dialog.get_cropped_image()
            lab, rgb = self.controller.extract_target_from_crop(qimg)
            hex_c = "#%02x%02x%02x" % tuple((rgb * 255).astype(int))
            self.target_preview.setStyleSheet(
                f"background-color: {hex_c}; border-radius: 3px; border: 1px solid #d4af37;"
            )
            self.target_preview.setText(f"Target Lab: {np.round(lab, 1)}")
            self.update_view()
            self.log_signal.emit("New target color extracted from crop.")

    def _on_illuminant_changed(self):
        choice = self.combo_illuminant.currentText()
        ill_key = "D65" if "D65" in choice else ("A" if "A" in choice else "FL2")
        self.controller.set_illuminant_key(ill_key)
        self.update_view()

    def _on_start_optimization(self):
        self.controller.start_optimization(self.log_signal.emit)

    def _on_stop_optimization(self):
        self.controller.stop_optimization()
        self.log_signal.emit("Stop requested...")

    def _on_optimization_started(self):
        self.btn_smart_match.setEnabled(False)
        self.btn_stop_match.setEnabled(True)

    def _on_optimization_finished(self, result: dict):
        self.btn_smart_match.setEnabled(True)
        self.btn_stop_match.setEnabled(False)
        if result.get("success"):
            self.update_view()
            self.log_signal.emit(
                f"Match Finalized. Approx. ΔE: {result.get('final_de', 0):.4f}"
            )
        else:
            self.log_signal.emit(
                f"Optimization failed or aborted: {result.get('message', '')}"
            )

    # ---------------------- Background artists --------------------------

    def refresh_bg_artists(self):
        for a in self.bg_artists:
            a.remove()
        self.bg_artists = []
        layers = self.controller.get_background_layers()
        for layer in layers:
            img_data = base64.b64decode(layer["base64"])
            img = Image.open(io.BytesIO(img_data))
            artist = self.ax.imshow(
                img,
                aspect="auto",
                extent=layer["extent"],
                alpha=0.5,
                zorder=0.1,
                visible=layer.get("visible", True),
            )
            self.bg_artists.append(artist)
        self.canvas.draw_idle()

    # ---------------------- View update --------------------------------

    def update_view(self):
        full_y = self.controller.get_interpolated()
        p_wave, p_val, t_wave, t_val = self.controller.get_peak_and_trough(full_y)

        for ann in getattr(self, "extrema_annotes", []):
            ann.remove()
        self.extrema_annotes = []

        self.extrema_annotes.append(
            self.ax.annotate(
                f"Peak: {p_wave}nm",
                xy=(p_wave, p_val),
                xytext=(0, 10),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color="#90ee90",
                fontweight="bold",
            )
        )
        self.extrema_annotes.append(
            self.ax.annotate(
                f"Dip: {t_wave}nm",
                xy=(t_wave, t_val),
                xytext=(0, -15),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color="#ff7f7f",
                fontweight="bold",
            )
        )

        self.line.set_data(WAVE_SAMPLES, full_y)
        points = self.controller.data.points
        self.dots.set_offsets(
            np.c_[
                list(points.keys()),
                list(points.values()),
            ]
        )

        Lab, rgb = self.controller.spectral_to_lab_rgb(full_y)
        hex_c = "#%02x%02x%02x" % tuple((rgb * 255).astype(int))

        if self.controller.data.target_lab is not None:
            t_lab = self.controller.data.target_lab
            t_rgb, t_hex = self.controller.lab_to_rgb_hex(t_lab)
            self.target_preview.setStyleSheet(
                f"background-color: {t_hex}; border-radius: 3px; border: 1px solid #d4af37;"
            )
            self.target_preview.setText(f"Target Lab: {np.round(t_lab, 1)}")
            de = self.controller.delta_e_to_target(Lab)
            if de is not None:
                if de < 0.2:
                    color = "#ffd700"
                elif de < 1.0:
                    color = "#90ee90"
                elif de < 2.0:
                    color = "#8fbc8f"
                else:
                    color = "#e0e0e0"
                self.label_delta_e.setText(f"ΔE00: {de:.3f}")
                self.label_delta_e.setStyleSheet(
                    f"color: {color}; font-size: 18px; font-weight: bold;"
                )
        else:
            self.target_preview.setStyleSheet(
                "background: #2b2b2a; border: 1px solid #5a5a58;"
            )
            self.target_preview.setText("No Target Loaded")
            self.label_delta_e.setText("ΔE: ---")
            self.label_delta_e.setStyleSheet(
                "color: #e0e0e0; font-size: 16px; font-weight: bold;"
            )

        text_col = "white" if Lab[0] < 50 else "black"
        self.color_preview.setStyleSheet(
            f"background-color:{hex_c}; color:{text_col}; "
            "border-radius:4px; font-weight:bold; border: 1px solid #3d3d3b;"
        )
        self.color_preview.setText(
            f"RGB: {np.round(rgb, 2)} | CIE L*a*b*: {np.round(Lab, 2)}"
        )

        self.canvas.draw_idle()

    # ---------------------- Mouse events -------------------------------

    def _on_click(self, event):
        if self.toolbar.mode != "" or event.inaxes != self.ax:
            return
        points = self.controller.data.points
        keys = list(points.keys())
        if keys:
            display_pts = self.ax.transData.transform(
                np.c_[keys, [points[k] for k in keys]]
            )
            dists = np.linalg.norm(
                display_pts - np.array([event.x, event.y]), axis=1
            )
            idx = np.argmin(dists)
            if dists[idx] < self.pick_radius:
                if event.button == 3:
                    self.controller.delete_point(keys[idx])
                    self.update_view()
                    return
                self.dragging_key = keys[idx]
                return
        if (
            event.button == 1
            and event.xdata is not None
            and event.ydata is not None
        ):
            x = float(np.clip(event.xdata, WAVE_MIN, WAVE_MAX))
            y = float(np.clip(event.ydata, 0.5, 99.5))
            self.controller.set_point(x, y)
            self.dragging_key = x
            self.update_view()

    def _on_move(self, event):
        if event.inaxes == self.ax and self.toolbar.mode == "":
            self.tooltip.set_visible(True)
            self.tooltip.xy = (event.xdata, event.ydata)
            if event.xdata is not None and event.ydata is not None:
                self.tooltip.set_text(
                    f"λ: {event.xdata:.1f} nm\nR: {event.ydata:.1f}%"
                )
        else:
            self.tooltip.set_visible(False)

        if (
            self.dragging_key is not None
            and self.toolbar.mode == ""
            and event.inaxes == self.ax
            and event.xdata is not None
            and event.ydata is not None
        ):
            new_x = float(np.clip(event.xdata, WAVE_MIN, WAVE_MAX))
            new_y = float(np.clip(event.ydata, 0.5, 99.5))
            self.dragging_key = self.controller.move_point(
                self.dragging_key, new_x, new_y
            )
            self.update_view()
        else:
            self.canvas.draw_idle()

    def _on_release(self, event):
        self.dragging_key = None
        self.update_view()
