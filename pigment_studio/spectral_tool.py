import sys
import numpy as np
import colour
import json
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFileDialog, QSlider, QFrame)
from PySide6.QtCore import Qt, Signal
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

WAVE_MIN, WAVE_MAX = 380, 780
WAVE_SAMPLES = np.arange(WAVE_MIN, WAVE_MAX + 1, 1)

class SpectralAnalysisWidget(QWidget):
    # Custom signal to send messages to your app's log area
    log_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.points = {380: 50.0, 780: 50.0}
        self.dragging_key = None
        self.pick_radius = 10
        self.bg_image_obj = None

        # --- Setup Matplotlib ---
        self.fig = Figure(figsize=(9, 4), facecolor='#4a4a48')
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#2b2b2a')
        
        # Initial Plot Elements
        self.line, = self.ax.plot([], [], color='#d4af37', lw=2)
        self.dots = self.ax.scatter([], [], color='white', s=50, zorder=4, edgecolors='black')
        
        # Turbo Gradient Background
        gradient = np.linspace(WAVE_MIN, WAVE_MAX, 256)
        self.ax.imshow([gradient], extent=[WAVE_MIN, WAVE_MAX, -5, 0], aspect='auto', cmap='turbo', zorder=0)
        self.ax.set_ylim(-5, 105)
        self.ax.set_xlim(WAVE_MIN - 5, WAVE_MAX + 5)
        
        # Connect Events
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_move)

        # --- UI Elements (Replacing ipywidgets) ---
        self.color_preview = QLabel("Color Preview")
        self.color_preview.setFixedHeight(40)
        self.color_preview.setAlignment(Qt.AlignCenter)
        self.color_preview.setStyleSheet("border-radius: 5px; font-weight: bold; border: 1px solid #3d3d3b;")

        self.btn_export = QPushButton("Export JSON")
        self.btn_import = QPushButton("Import JSON")
        self.btn_reset = QPushButton("Reset")
        
        # Signals
        self.btn_export.clicked.connect(self.handle_export)
        self.btn_import.clicked.connect(self.handle_import)
        self.btn_reset.clicked.connect(self.reset)

        # Layout
        layout = QVBoxLayout(self)
        layout.addWidget(NavigationToolbar(self.canvas, self))
        layout.addWidget(self.canvas)
        layout.addWidget(self.color_preview)
        
        controls = QHBoxLayout()
        controls.addWidget(self.btn_import)
        controls.addWidget(self.btn_export)
        controls.addWidget(self.btn_reset)
        layout.addLayout(controls)

        # Initialize Colour Science
        self.cmfs = colour.MSDS_CMFS['CIE 1931 2 Degree Standard Observer'].copy().align(
            colour.SpectralShape(WAVE_MIN, WAVE_MAX, 1))
        self.illuminant = colour.SDS_ILLUMINANTS['D65'].copy().align(self.cmfs.shape)
        
        self.update_calculations()

    def update_calculations(self, full_metrics=True):
        sorted_keys = sorted(self.points.keys())
        sorted_vals = [self.points[k] for k in sorted_keys]
        full_y = np.interp(WAVE_SAMPLES, sorted_keys, sorted_vals)
        
        # Update Plot
        self.line.set_data(WAVE_SAMPLES, full_y)
        self.dots.set_offsets(np.c_[sorted_keys, sorted_vals])
        
        # Colour Math
        sd = colour.SpectralDistribution(dict(zip(WAVE_SAMPLES, full_y / 100.0)))
        XYZ = colour.sd_to_XYZ(sd, self.cmfs, self.illuminant) / 100.0
        rgb = np.clip(colour.XYZ_to_sRGB(XYZ), 0, 1)
        hex_c = '#%02x%02x%02x' % tuple((rgb * 255).astype(int))
        
        # Update UI Preview
        self.color_preview.setStyleSheet(f"background-color: {hex_c}; color: {'white' if np.mean(rgb)<0.5 else 'black'}; border-radius: 5px;")
        self.color_preview.setText(f"HEX: {hex_c.upper()} | XYZ: {np.round(XYZ, 2)}")
        self.canvas.draw_idle()

    # --- Interaction Logic (Ported from your code) ---
    def on_click(self, event):
        if event.inaxes != self.ax: return
        
        # Find closest point
        keys = list(self.points.keys())
        if keys:
            display_pts = self.ax.transData.transform(np.c_[keys, [self.points[k] for k in keys]])
            dists = np.linalg.norm(display_pts - np.array([event.x, event.y]), axis=1)
            idx = np.argmin(dists)
            
            if dists[idx] < self.pick_radius:
                if event.button == 3: # Right Click Delete
                    if len(self.points) > 2:
                        del self.points[keys[idx]]
                        self.update_calculations()
                    return
                self.dragging_key = keys[idx]
                return

        # Add new point
        if event.button == 1:
            self.points[event.xdata] = np.clip(event.ydata, 0, 100)
            self.dragging_key = event.xdata
            self.update_calculations()

    def on_move(self, event):
        if self.dragging_key is None or event.inaxes != self.ax: return
        new_x = np.clip(event.xdata, WAVE_MIN, WAVE_MAX)
        new_y = np.clip(event.ydata, 0, 100)
        
        self.points.pop(self.dragging_key)
        self.points[new_x] = new_y
        self.dragging_key = new_x
        self.update_calculations(False)

    def on_release(self, event):
        self.dragging_key = None
        self.update_calculations(True)

    def handle_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Spectrum", "", "JSON Files (*.json)")
        if path:
            data = {"wavelengths": sorted(self.points.keys()), "reflectance": [self.points[k] for k in sorted(self.points.keys())]}
            with open(path, 'w') as f:
                json.dump(data, f)
            self.log_signal.emit(f"Exported to {path}")

    def handle_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Spectrum", "", "JSON Files (*.json)")
        if path:
            with open(path, 'r') as f:
                data = json.load(f)
            self.points = dict(zip(data['wavelengths'], data['reflectance']))
            self.update_calculations()
            self.log_signal.emit(f"Imported {path}")

    def reset(self):
        self.points = {380: 50.0, 780: 50.0}
        self.update_calculations()
        self.log_signal.emit("Tool Reset")
