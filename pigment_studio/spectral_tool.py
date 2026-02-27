import numpy as np
import colour
import json
import base64
import io
import os
from PIL import Image
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFileDialog, QSlider, QGroupBox, QFrame, QComboBox, QCheckBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from crop_dialog import CropDialog

WAVE_MIN, WAVE_MAX = 380, 780
WAVE_SAMPLES = np.arange(WAVE_MIN, WAVE_MAX + 1, 1)

class SpectralData:
    def __init__(self):
        self.points = {380: 50.0, 780: 50.0}
        self.bg_layers = [] # List of dicts: {"base64": str, "extent": [l, r, b, t], "visible": bool, "name": str}
        self.target_lab = None  # Store as [L, a, b] list or None
        
    def get_interpolated(self):
        sorted_keys = sorted(self.points.keys())
        sorted_vals = [self.points[k] for k in sorted_keys]
        return np.interp(WAVE_SAMPLES, sorted_keys, sorted_vals)

    def to_dict(self):
        return {
            "spectral_points": {str(k): v for k, v in self.points.items()},
            "background_layers": self.bg_layers,
            "target_lab": self.target_lab
        }

    def from_dict(self, data):
        raw_points = data.get("spectral_points", {})
        self.points = {float(k): v for k, v in raw_points.items()}
        self.bg_layers = data.get("background_layers", [])
        self.target_lab = data.get("target_lab", None)

class SpectralAnalysisWidget(QWidget):
    log_signal = Signal(str)

    def __init__(self, shared_data):
        super().__init__()
        self.data = shared_data
        self.dragging_key = None
        self.pick_radius = 10
        self.bg_artists = [] 

        # --- Main Layout (Horizontal) ---
        self.main_h_layout = QHBoxLayout(self)
        self.main_h_layout.setContentsMargins(0, 0, 0, 0)
        self.main_h_layout.setSpacing(0)

        # --- LEFT: Control Sidebar (Fixed Width) ---
        self.controls_sidebar = QFrame()
        self.controls_sidebar.setFixedWidth(240)
        self.controls_sidebar.setStyleSheet("background-color: #3d3d3b; border-right: 1px solid #2b2b2a;")
        self.sidebar_layout = QVBoxLayout(self.controls_sidebar)
        self.sidebar_layout.setContentsMargins(10, 10, 10, 10)
        self.sidebar_layout.setSpacing(15)

        self.setup_sidebar_ui()

        # --- RIGHT: Canvas Area ---
        self.canvas_container = QWidget()
        self.canvas_layout = QVBoxLayout(self.canvas_container)
        self.canvas_layout.setContentsMargins(5, 5, 5, 5)

        # Matplotlib Setup
        self.fig = Figure(figsize=(8, 4), facecolor='#4a4a48')
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.message = lambda x: "" 
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#2b2b2a')
        self.ax.format_coord = lambda x, y: ""

        # Floating Tooltip
        self.tooltip = self.ax.annotate("", xy=(0, 0), xytext=(15, 15), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="#3d3d3b", ec="#d4af37", alpha=0.9),
            color="#e0e0e0", fontsize=9, fontweight='bold', zorder=10)
        self.tooltip.set_visible(False)

        self.line, = self.ax.plot([], [], color='#d4af37', lw=2, zorder=5)
        self.dots = self.ax.scatter([], [], color='white', s=50, zorder=6, edgecolors='black')
        
        gradient = np.linspace(WAVE_MIN, WAVE_MAX, 256)
        self.ax.imshow([gradient], extent=[WAVE_MIN, WAVE_MAX, -5, 0], aspect='auto', cmap='turbo', zorder=0)
        self.ax.grid(True, which='both', linestyle=':', color='#5a5a58', alpha=0.6)
        self.ax.set_axisbelow(True) # Ensures grid stays behind the curve
        self.ax.set_ylim(-5, 105)
        self.ax.set_xlim(WAVE_MIN - 5, WAVE_MAX + 5)
        
        self.canvas_layout.addWidget(self.toolbar)
        self.canvas_layout.addWidget(self.canvas)

        # Color Preview (Now inside the canvas area for visibility)
        self.color_preview = QLabel("Color Preview")
        self.color_preview.setFixedHeight(40)
        self.color_preview.setAlignment(Qt.AlignCenter)
        self.canvas_layout.addWidget(self.color_preview)

        # Final assembly
        self.main_h_layout.addWidget(self.controls_sidebar)
        self.main_h_layout.addWidget(self.canvas_container)

        # Matplotlib Events
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_move)

        # Colour Science Init (Standard checks)
        try:
            self.cmfs = colour.MSDS_CMFS['CIE 1931 2 Degree Standard Observer'].copy().align(colour.SpectralShape(WAVE_MIN, WAVE_MAX, 1))
            self.illuminant = colour.SDS_ILLUMINANTS['D65'].copy().align(self.cmfs.shape)
        except:
            self.cmfs = colour.multi_spectral_distributions['CIE 1931 2 Degree Standard Observer'].copy().align(colour.SpectralShape(WAVE_MIN, WAVE_MAX, 1))
            self.illuminant = colour.spectral_distributions_illuminants['D65'].copy().align(self.cmfs.shape)
        
        self.update_view()

    def setup_sidebar_ui(self):
        # Section 1: General Actions
        lbl_gen = QLabel("SPECTRUM TOOLS")
        lbl_gen.setStyleSheet("font-weight: bold; color: #d4af37;")
        self.sidebar_layout.addWidget(lbl_gen)

        self.btn_reset = QPushButton("Reset Spectrum")
        self.btn_reset.clicked.connect(self.reset)
        self.sidebar_layout.addWidget(self.btn_reset)

        self.sidebar_layout.addSpacing(10)

        # Section 2: Background Layers
        lbl_bg = QLabel("IMAGE LAYERS")
        lbl_bg.setStyleSheet("font-weight: bold; color: #d4af37;")
        self.sidebar_layout.addWidget(lbl_bg)

        self.btn_add_bg = QPushButton("Add Layer")
        self.btn_remove_last = QPushButton("Remove Last Layer")
        self.btn_clear_bg = QPushButton("Clear All")
        
        self.btn_add_bg.clicked.connect(self.add_image_layer)
        self.btn_remove_last.clicked.connect(self.remove_last_layer)
        self.btn_clear_bg.clicked.connect(self.clear_all_bg)

        self.sidebar_layout.addWidget(self.btn_add_bg)
        self.sidebar_layout.addWidget(self.btn_remove_last)
        self.sidebar_layout.addWidget(self.btn_clear_bg)

        self.is_loading_layer = False  # Guard to prevent slider feedback loops

        self.combo_active_bg = QComboBox()
        self.combo_active_bg.currentIndexChanged.connect(self.on_active_layer_changed)
        
        self.check_bg_visible = QCheckBox("Show Layer")
        self.check_bg_visible.setChecked(True)
        self.check_bg_visible.toggled.connect(self.toggle_layer_visibility)

        self.sidebar_layout.addWidget(QLabel("Select Active Layer:"))
        self.sidebar_layout.addWidget(self.combo_active_bg)
        self.sidebar_layout.addWidget(self.check_bg_visible)

        # Section 3: Alignment (Sliders)
        bg_geo_group = QGroupBox("Active Layer Alignment")
        # Added 'padding-top: 20px' to the stylesheet to push content below the title
        bg_geo_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                margin-top: 10px; 
                padding-top: 20px; 
                color: #d4af37;
            }
        """)
        geo_layout = QVBoxLayout(bg_geo_group)
        
        # Also set contents margins to ensure no clipping on the sides/bottom
        geo_layout.setContentsMargins(10, 25, 10, 10) 
        geo_layout.setSpacing(5)

        self.slider_x = self.create_compact_slider(geo_layout, "X Pos", WAVE_MIN-100, WAVE_MAX)
        self.slider_y = self.create_compact_slider(geo_layout, "Y Pos", -50, 100)
        self.slider_w = self.create_compact_slider(geo_layout, "Width", 10, 1000, WAVE_MAX-WAVE_MIN)
        self.slider_h = self.create_compact_slider(geo_layout, "Height", 10, 300, 100)

        self.sidebar_layout.addWidget(bg_geo_group)
        self.sidebar_layout.addStretch()
        
        # --- NEW: TARGET MATCHING SECTION ---
        match_group = QGroupBox("Target Matching")
        match_group.setStyleSheet("QGroupBox { font-weight: bold; color: #d4af37; padding-top: 20px; }")
        match_layout = QVBoxLayout(match_group)
        
        self.btn_load_target = QPushButton("Load & Crop Blob")
        self.btn_load_target.clicked.connect(self.handle_load_target)
        
        self.target_preview = QLabel("No Target Loaded")
        self.target_preview.setFixedHeight(30)
        self.target_preview.setAlignment(Qt.AlignCenter)
        self.target_preview.setStyleSheet("background: #2b2b2a; border: 1px solid #5a5a58;")
        
        self.label_delta_e = QLabel("ΔE: ---")
        self.label_delta_e.setStyleSheet("font-size: 16px; font-weight: bold; color: #8fbc8f;")
        self.label_delta_e.setAlignment(Qt.AlignCenter)

        match_layout.addWidget(self.btn_load_target)
        match_layout.addWidget(self.target_preview)
        match_layout.addWidget(self.label_delta_e)
        
        self.sidebar_layout.addWidget(match_group)
        self.sidebar_layout.addStretch()

    def create_compact_slider(self, layout, label, min_v, max_v, default=0):
        lbl = QLabel(f"{label}:")
        s = QSlider(Qt.Horizontal)
        s.setRange(min_v, max_v)
        s.setValue(default)
        s.valueChanged.connect(self.update_image_geometry)
        layout.addWidget(lbl)
        layout.addWidget(s)
        return s

    def remove_last_layer(self):
        idx = self.combo_active_bg.currentIndex()
        if idx >= 0:
            # Remove from Matplotlib
            artist = self.bg_artists.pop(idx)
            artist.remove()
            # Remove from Data
            self.data.bg_layers.pop(idx)
            # Remove from UI
            self.combo_active_bg.removeItem(idx)
            
            self.canvas.draw_idle()
            self.log_signal.emit("Removed selected background layer.")

    # --- Existing logic remains the same below ---
    def add_image_layer(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg)")
        if not path: return
        
        with open(path, "rb") as f:
            b64_str = base64.b64encode(f.read()).decode('utf-8')
        
        name = os.path.basename(path)
        extent = [WAVE_MIN, WAVE_MAX, 0, 100] # Default
        
        self.data.bg_layers.append({
            "base64": b64_str, "extent": extent, "visible": True, "name": name
        })
        
        self.combo_active_bg.addItem(name)
        self.combo_active_bg.setCurrentIndex(self.combo_active_bg.count() - 1)
        self.refresh_bg_artists()

    def on_active_layer_changed(self, index):
        """Updates sliders to match the selected layer's geometry."""
        if index < 0 and index >= len(self.data.bg_layers):
            return
            
        layer = self.data.bg_layers[index]
        ext = layer["extent"] # [left, right, bottom, top]

        # 1. Block the 'valueChanged' signal so we don't accidentally move the image
        self.is_loading_layer = True
        
        self.slider_x.setValue(ext[0])
        self.slider_w.setValue(ext[1] - ext[0])
        self.slider_y.setValue(-ext[2])
        self.slider_h.setValue(ext[3] - ext[2])
        
        self.check_bg_visible.setChecked(layer.get("visible", True))
        
        # 4. Unblock signals
        self.is_loading_layer = False

    def toggle_layer_visibility(self, is_visible):
        idx = self.combo_active_bg.currentIndex()
        if idx >= 0:
            self.data.bg_layers[idx]["visible"] = is_visible
            if idx < len(self.bg_artists):
                self.bg_artists[idx].set_visible(is_visible)
                self.canvas.draw_idle()

    def refresh_bg_artists(self):
        """Rebuilds artists and syncs visibility from data."""
        # Clear existing
        for a in self.bg_artists: a.remove()
        self.bg_artists = []
        
        # Redraw all
        for layer in self.data.bg_layers:
            img_data = base64.b64decode(layer["base64"])
            img = Image.open(io.BytesIO(img_data))
            artist = self.ax.imshow(img, aspect='auto', extent=layer["extent"], 
                                   alpha=0.5, zorder=0.1, visible=layer["visible"])
            self.bg_artists.append(artist)
        self.canvas.draw_idle()


    def update_image_geometry(self):
        """Updates the specific layer selected in the ComboBox."""
        # If we are currently loading a layer's values into sliders, do nothing
        if self.is_loading_layer:
            return
            
        idx = self.combo_active_bg.currentIndex()
        if idx >= 0 and idx < len(self.bg_artists):
            # Calculate extent from current slider states
            l = self.slider_x.value()
            r = l + self.slider_w.value()
            b = -self.slider_y.value()
            t = b + self.slider_h.value()
            
            new_extent = [l, r, b, t]
            
            # Update the Matplotlib Artist
            self.bg_artists[idx].set_extent(new_extent)
            # Update the Data Model for JSON saving
            self.data.bg_layers[idx]["extent"] = new_extent
            
            self.canvas.draw_idle()

    def clear_all_bg(self):
        self.data.bg_layers = []
        self.refresh_bg_artists()
        self.log_signal.emit("Cleared all background layers.")

    def handle_load_target(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg)")
        if not path: return
        
        dialog = CropDialog(path, self)
        if dialog.exec():
            qimg = dialog.get_cropped_image()
            self.process_target_blob(qimg)

    def process_target_blob(self, qimage):
        # 1. Force the image into a standard 32-bit RGB format and swap BGR to RGB
        qimage = qimage.convertToFormat(QImage.Format_RGB32).rgbSwapped()
    
        # 1. Convert QImage to Numpy RGB
        width, height = qimage.width(), qimage.height()
        ptr = qimage.bits()
         
        # 2. Extract 4 channels (RGBA), then slice to get only RGB [:, :, :3]
        arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))[:, :, :3] / 255.0
        pixels = arr.reshape(-1, 3)

        # 2. CV Heuristic: Chroma = max(RGB) - min(RGB)
        chroma = np.max(pixels, axis=1) - np.min(pixels, axis=1)
        
        # 3. Filter top 10% most saturated
        threshold = np.percentile(chroma, 90)
        vibrant_pixels = pixels[chroma >= threshold]
        
        # 4. Median of vibrant pixels
        target_rgb = np.median(vibrant_pixels, axis=0)
        
        # 5. Convert to Lab for goal storage
        target_xyz = colour.sRGB_to_XYZ(target_rgb)
        lab_array = colour.XYZ_to_Lab(target_xyz)
        
        # Store as a list to ensure JSON serializability
        self.data.target_lab = lab_array.tolist()
        
        # Update UI Preview
        hex_c = '#%02x%02x%02x' % tuple((target_rgb * 255).astype(int))
        self.target_preview.setStyleSheet(f"background-color: {hex_c}; border-radius: 3px; border: 1px solid #d4af37;")
        self.target_preview.setText(f"Target Lab: {np.round(lab_array, 1)}")
        
        self.update_view() # Trigger Delta-E recalc
        self.log_signal.emit("New target color extracted from crop.")

    def update_view(self):
        full_y = self.data.get_interpolated()
        self.line.set_data(WAVE_SAMPLES, full_y)
        self.dots.set_offsets(np.c_[list(self.data.points.keys()), list(self.data.points.values())])
        
        sd = colour.SpectralDistribution(dict(zip(WAVE_SAMPLES, full_y / 100.0)))
        XYZ = colour.sd_to_XYZ(sd, self.cmfs, self.illuminant) / 100.0
        Lab = colour.XYZ_to_Lab(XYZ)
        rgb = np.clip(colour.XYZ_to_sRGB(XYZ), 0, 1)
        hex_c = '#%02x%02x%02x' % tuple((rgb * 255).astype(int))
        
        # --- NEW: Delta-E Calculation ---
        if self.data.target_lab is not None:
            # 1. Convert Lab back to RGB for the UI Swatch
            # We assume D65/2deg as used elsewhere in your app
            t_xyz = colour.Lab_to_XYZ(self.data.target_lab)
            t_rgb = np.clip(colour.XYZ_to_sRGB(t_xyz), 0, 1)
            t_hex = '#%02x%02x%02x' % tuple((t_rgb * 255).astype(int))
            
            # 2. Update the Sidebar Target Label
            self.target_preview.setStyleSheet(
                f"background-color: {t_hex}; border-radius: 3px; border: 1px solid #d4af37;"
            )
            # Round for clean professional display
            rounded_lab = np.round(self.data.target_lab, 1)
            self.target_preview.setText(f"Target Lab: {rounded_lab}")
        
            # Using CIEDE2000 for professional accuracy
            de = colour.delta_E(self.data.target_lab, Lab, method='CIE 2000')
            
            # Color coding the result
            if de < 0.2: color = "#ffd700" # Gold (Perfect)
            elif de < 1.0: color = "#90ee90" # Light Green (Excellent)
            elif de < 2.0: color = "#8fbc8f" # Pale Green (Good)
            else: color = "#e0e0e0" # Gray (Keep trying)
            
            self.label_delta_e.setText(f"ΔE00: {de:.3f}")
            self.label_delta_e.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        else:
            self.label_delta_e.setText("ΔE: ---")
        
        text_col = 'white' if Lab[0] < 50 else 'black'
        self.color_preview.setStyleSheet(f"background-color:{hex_c}; color:{text_col}; border-radius:4px; font-weight:bold; border: 1px solid #3d3d3b;")
        self.color_preview.setText(f"RGB: {np.round(rgb, 2)} | CIE L*a*b*: {np.round(Lab, 2)}")
        self.canvas.draw_idle()

    def on_click(self, event):
        if self.toolbar.mode != "" or event.inaxes != self.ax: return
        keys = list(self.data.points.keys())
        if keys:
            display_pts = self.ax.transData.transform(np.c_[keys, [self.data.points[k] for k in keys]])
            dists = np.linalg.norm(display_pts - np.array([event.x, event.y]), axis=1)
            idx = np.argmin(dists)
            if dists[idx] < self.pick_radius:
                if event.button == 3:
                    if len(self.data.points) > 2: del self.data.points[keys[idx]]; self.update_view()
                    return
                self.dragging_key = keys[idx]; return
        if event.button == 1:
            self.data.points[event.xdata] = np.clip(event.ydata, 0.5, 99.5)
            self.dragging_key = event.xdata
            self.update_view()

    def on_move(self, event):
        # 1. Update the Floating Tooltip
        if event.inaxes == self.ax and self.toolbar.mode == "":
            self.tooltip.set_visible(True)
            self.tooltip.xy = (event.xdata, event.ydata)
            self.tooltip.set_text(f"λ: {event.xdata:.1f} nm\nR: {event.ydata:.1f}%")
        else: 
            self.tooltip.set_visible(False)

        # 2. Handle Point Dragging with Safety Check
        if self.dragging_key is not None and self.toolbar.mode == "" and event.inaxes == self.ax:
            # --- ADD THIS CHECK ---
            if self.dragging_key not in self.data.points:
                return 
            # ----------------------

            new_x, new_y = np.clip(event.xdata, WAVE_MIN, WAVE_MAX), np.clip(event.ydata, 0.5, 99.5)
            
            # --- PREVENT OVERWRITE (The "Anti-Eating" Check) ---
            if new_x in self.data.points and new_x != self.dragging_key:
                new_x += 1e-9 # Add a microscopic offset so the ID is unique
            # ---------------------------------------------------
            
            # Perform the update
            self.data.points.pop(self.dragging_key)
            self.data.points[new_x] = new_y
            self.dragging_key = new_x
            
            self.update_view()
        else: 
            self.canvas.draw_idle()


    def on_release(self, event): self.dragging_key = None; self.update_view()
    def reset(self): self.data.points = {380: 50.0, 780: 50.0}; self.update_view(); self.log_signal.emit("Reset curve.")
