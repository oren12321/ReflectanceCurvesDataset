# Spectral Paint Engine (SPE) - Technical Documentation

This project builds a professional-grade digital paint mixing and glazing engine. Unlike standard RGB software, this engine operates in **Spectral Space**, simulating the physical behavior of light interacting with matter.

---

## Stage 0: Data Ingestion (The Digital "Source of Truth")
**Concept:** Digitization of Laboratory Measurements into Structured Data.

The foundation of the engine begins with raw sensor data provided by high-precision spectrometers (e.g., the CHSOS Gorgias system). In their native state, these files are unstructured text documents with inconsistent naming conventions and varied data resolutions.

*   **File Parsing and Sanitization:** 
    Original filenames are renamed to a standardized database format: `<PigmentCode>_<CommonName>`. For example, `PBk9_Ivory_Black.txt`. This allows the engine to perform "Fuzzy Searches" for human-readable names while maintaining a link to the **Color Index (CI)**, which identifies the pigment's chemical identity.
*   **Data Structure (Flattened Arrays):** 
    Raw data usually exists as coordinate pairs (Wavelength, Reflectance %). To optimize for the **NumPy** math required in later stages, we "unzip" these pairs into two separate, parallel arrays: `wavelengths` and `reflectance`. This allows for **Vectorized Operations**, meaning the engine can calculate math for hundreds of wavelengths simultaneously rather than looping through them.
*   **Result:** `stage0_raw_data.json`. This acts as a permanent, immutable record of the sensor's "raw vision" before any mathematical smoothing or normalization is applied.

---

## Stage 1: Standardization & Spline Interpolation
**Concept:** Physical Continuity and Wavelength Alignment.

Raw sensor data is often "jagged" and "offset." One sensor might take a reading at 380.4nm while another takes it at 381.1nm. To mix two pigments, they must exist on the exact same "Map of Light."

*   **Decimal Normalization (The Reflectance Ratio):** 
    Sensors record light as a percentage (0-100%). In physics and the **Kubelka-Munk** model, we treat light as a ratio of energy. We convert all values to decimals (0.0 to 1.0). A value of `1.0` represents a "Perfect Diffuse Reflector"—a theoretical material that reflects 100% of the energy hitting it.
*   **Cubic Spline Interpolation (Simulating Nature):** 
    Light in the physical world is continuous; it doesn't jump in "steps." If a sensor only takes a reading every 5nm, a "linear" (straight line) connection between those dots creates "sharp corners" in the data. We use **Cubic Splines**—a mathematical method using third-degree polynomials—to draw an elegant, smooth curve through the sensor points. This ensures that when the user moves a mixing slider, the colors shift with the fluid, organic feel of real paint rather than "digital stepping."
*   **5nm Resampling (The Spectral Data Cube):** 
    Every pigment in the library is forced onto a standardized **89-point grid** (360nm to 800nm, in 5nm intervals). This creates a "Data Cube" where the index `n` always refers to exactly the same wavelength across every pigment. This alignment is the prerequisite for all future subtractive mixing and glazing calculations.
*   **Result:** `stage1_standardized_data.json`. This is your "Digital Palette"—a library of smooth, high-fidelity spectral curves ready for the physics of the paint binder.

---

## Stage 2: The Studio Calibration (Normalization)
**Concept:** Dynamic Range & White Point Anchoring.

A common issue in laboratory-grade spectral data is that measurements often appear "pale" or "underexposed" relative to an artist's expectations. For instance, a physical swatch of **Titanium White** might only record a reflectance of **~79%** due to the specific lighting conditions of the spectrometer or the thinness of the test application. In a professional digital painting app, artists require "White" paint to be the brightest anchor of the canvas's dynamic range.

*   **The Problem of Human Perception:** 
    The human eye does not perceive all wavelengths with equal intensity. Our retinas are extremely sensitive to **Green/Yellow (~550nm)** and nearly blind to **Deep Violet (400nm)** or **Far Red (700nm)**. Therefore, we cannot simply average the 89 data points to find "brightness." We must use a weighted calculation.
*   **The Science of Luminance (CIE XYZ):** 
    We utilize the **CIE 1931 Color Matching Functions (CMFs)**—a set of standardized spectral sensitivity curves that represent the average human observer. By integrating our 89 spectral points with these curves, we calculate the **Luminance (Y)**, which is the scientific measurement of "perceived brightness."
*   **The Master Scale Factor:** 
    1.  The engine identifies the **Titanium White (PW6)** entry as the "Reference Standard."
    2.  If its calculated Luminance is $Y=79.48$, the engine calculates a **Global Scalar** ($95.0 / 79.48 \approx 1.20$).
    3.  Every pigment in the library is then multiplied by this **1.20 factor**. 
*   **Result:** `stage2_calibrated_data.json`. This stage "turns on the studio lights." It ensures that Titanium White hits a professional target of **Y = 95** (leaving 5% "headroom" for highlights), while all other colors shift proportionally to maintain their correct physical relationship to the white point.

## Stage 3: The Physics of "Binder & Ground" Removal
**Concept:** Subtractive De-convolution & The "Infinite Thickness" Masstone.

At this stage, our data represents **"Pigment + Acrylic Binder + White Card."** This explains why the colors still appear "pale" or "chalky" compared to professional oil paint catalogs. In the physical laboratory, the pigment was applied as a thin, translucent film. To achieve the deep, saturated look of **Winsor & Newton** artist colors, we must mathematically remove the optical interference of the binder and the white background.

*   **The Problem of the Substrate (The White Card):** 
    Because the paint layer is thin, light passes through the pigment, hits the white card underneath, and bounces back to the sensor. This "backlight" artificially inflates the reflectance values. We must isolate the **Absorption (K)** of the pigment particles alone.
*   **The Science of Kubelka-Munk (K-M) Theory:** 
    We move from **Reflectance (R)**—which is a surface measurement—to the **K/S Ratio**, which describes the internal physics of the material.
    *   **K (Absorption):** The pigment's ability to "eat" specific wavelengths of light.
    *   **S (Scattering):** The pigment's ability to "bounce" light (opacity).
    By using the **Acrylic Binder** as a "Baseline Reference," we can subtract its specific absorption from the total measurement, effectively "cleaning" the pigment DNA.
*   **The "Infinite Thickness" Simulation:** 
    Once we have the "Clean K/S DNA," we simulate a **Masstone**. In physics, if you make a paint layer thick enough, no light ever reaches the white card. This is called "Infinite Thickness." 
*   **The Result:** `stage3_physics_data.json`. This stage transforms "pale lab swatches" into "deep tube colors." By mathematically "sinking" the pigment into a simulated binder and removing the white card's interference, we finally achieve the rich, saturated appearance found in professional artist catalogs.
