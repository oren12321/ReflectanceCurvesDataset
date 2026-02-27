import numpy as np
import colour
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFileDialog)
from PySide6.QtCore import Qt, Signal
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

# --- GLOBAL CONSTANTS ---
WAVE_MIN, WAVE_MAX = 380, 780
WAVE_SAMPLES = np.arange(WAVE_MIN, WAVE_MAX + 1, 1)

class SpectralData:
    """A shared data model for pigments across different tabs."""
    def __init__(self):
        self.points = {380: 50.0, 780: 50.0}
        
    def get_interpolated(self):
        sorted_keys = sorted(self.points.keys())
        sorted_vals = [self.points[k] for k in sorted_keys]
        return np.interp(WAVE_SAMPLES, sorted_keys, sorted_vals)

class SpectralAnalysisWidget(QWidget):
    log_signal = Signal(str)

    def __init__(self, shared_data: SpectralData):
        super().__init__()
        self.data = shared_data  # Reference to shared data
        self.dragging_key = None
        self.pick_radius = 10

        # --- Setup Matplotlib ---
        self.fig = Figure(figsize=(9, 4), facecolor='#4a4a48')
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # REMOVE DEFAULT (x,y) LABEL:
        # We set an empty string to the message to hide the top-right text
        self.toolbar.message = "" 
        
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#2b2b2a')
        
        # CUSTOM COORDINATE FORMATTING
        # This replaces the top-right label with a custom string
        self.ax.format_coord = lambda x, y: f"λ: {x:.1f} nm | R: {y:.1f}%"

        self.line, = self.ax.plot([], [], color='#d4af37', lw=2)
        self.dots = self.ax.scatter([], [], color='white', s=50, zorder=4, edgecolors='black')
        
        gradient = np.linspace(WAVE_MIN, WAVE_MAX, 256)
        self.ax.imshow([gradient], extent=[WAVE_MIN, WAVE_MAX, -5, 0], aspect='auto', cmap='turbo', zorder=0)
        self.ax.set_ylim(-5, 105)
        self.ax.set_xlim(WAVE_MIN - 5, WAVE_MAX + 5)
        
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_move)

        # --- UI Elements ---
        self.color_preview = QLabel("Color Preview")
        self.color_preview.setFixedHeight(30)
        self.color_preview.setAlignment(Qt.AlignCenter)
        
        self.btn_export = QPushButton("Export")
        self.btn_import = QPushButton("Import")
        self.btn_reset = QPushButton("Reset")
        
        self.btn_export.clicked.connect(self.handle_export)
        self.btn_import.clicked.connect(self.handle_import)
        self.btn_reset.clicked.connect(self.reset)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.addWidget(self.color_preview)
        
        controls = QHBoxLayout()
        controls.addWidget(self.btn_import)
        controls.addWidget(self.btn_export)
        controls.addWidget(self.btn_reset)
        layout.addLayout(controls)

        # Setup Colour Science
        self.cmfs = colour.MSDS_CMFS['CIE 1931 2 Degree Standard Observer'].copy().align(
            colour.SpectralShape(WAVE_MIN, WAVE_MAX, 1))
        self.illuminant = colour.SDS_ILLUMINANTS['D65'].copy().align(self.cmfs.shape)
        
        self.update_view()

    def update_view(self):
        full_y = self.data.get_interpolated()
        sorted_keys = sorted(self.data.points.keys())
        sorted_vals = [self.data.points[k] for k in sorted_keys]
        
        self.line.set_data(WAVE_SAMPLES, full_y)
        self.dots.set_offsets(np.c_[sorted_keys, sorted_vals])
        
        sd = colour.SpectralDistribution(dict(zip(WAVE_SAMPLES, full_y / 100.0)))
        XYZ = colour.sd_to_XYZ(sd, self.cmfs, self.illuminant) / 100.0
        rgb = np.clip(colour.XYZ_to_sRGB(XYZ), 0, 1)
        hex_c = '#%02x%02x%02x' % tuple((rgb * 255).astype(int))
        
        self.color_preview.setStyleSheet(f"background-color: {hex_c}; color: {'white' if np.mean(rgb)<0.5 else 'black'}; border-radius: 3px; font-weight: bold;")
        self.color_preview.setText(f"HEX: {hex_c.upper()} | XYZ: {np.round(XYZ, 2)}")
        self.canvas.draw_idle()

    def on_click(self, event):
        if self.toolbar.mode != "" or event.inaxes != self.ax: return
        
        keys = list(self.data.points.keys())
        if keys:
            display_pts = self.ax.transData.transform(np.c_[keys, [self.data.points[k] for k in keys]])
            dists = np.linalg.norm(display_pts - np.array([event.x, event.y]), axis=1)
            idx = np.argmin(dists)
            
            if dists[idx] < self.pick_radius:
                if event.button == 3: # Right Click
                    if len(self.data.points) > 2:
                        del self.data.points[keys[idx]]
                        self.update_view()
                    return
                self.dragging_key = keys[idx]
                return

        if event.button == 1:
            self.data.points[event.xdata] = np.clip(event.ydata, 0, 100)
            self.dragging_key = event.xdata
            self.update_view()

    def on_move(self, event):
        if self.dragging_key is None or self.toolbar.mode != "" or event.inaxes != self.ax: 
            return
        
        new_x = np.clip(event.xdata, WAVE_MIN, WAVE_MAX)
        new_y = np.clip(event.ydata, 0, 100)
        
        self.data.points.pop(self.dragging_key)
        self.data.points[new_x] = new_y
        self.dragging_key = new_x
        self.update_view()

    def on_release(self, event):
        self.dragging_key = None
        self.update_view()

    def handle_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export", "", "JSON (*.json)")
        if path:
            data = {"wavelengths": sorted(self.data.points.keys()), 
                    "reflectance": [self.data.points[k] for k in sorted(self.data.points.keys())]}
            with open(path, 'w') as f: json.dump(data, f)
            self.log_signal.emit(f"Exported: {path}")

    def handle_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import", "", "JSON (*.json)")
        if path:
            with open(path, 'r') as f: data = json.load(f)
            self.data.points = dict(zip(data['wavelengths'], data['reflectance']))
            self.update_view()
            self.log_signal.emit(f"Imported: {path}")

    def reset(self):
        self.data.points = {380: 50.0, 780: 50.0}
        self.update_view()
