# 👓 Miop

**Miop** is an open-source optical computing suite and assistive vision tool designed for individuals with **high myopia (e.g. -5.5 D)** and **astigmatism**. It enables glasses-free reading on desktop monitors by combining **4D Light Field Ray Synthesis**, **physical optical barrier masks**, and **pinhole glasses optimization**.

---

## 🔬 The Optical Problem & Solution

### Why standard 2D monitors cannot correct high myopia via software alone
In an eye with high myopia (-5.5 Diopters), the cornea and crystalline lens refract incoming light excessively, focusing parallel rays at a focal plane just **18 cm** away from the eye:
$$\text{Focal Distance} = \frac{1}{5.5\text{ D}} \approx 0.18\text{ meters} = 18\text{ cm}$$

When seated at a standard desk distance of **50–60 cm**, every single pixel on a standard 2D flat panel emits light in a wide diffuse cone across the entire pupil, creating a retinal blur circle several millimeters wide. Because a standard pixel cannot emit different light rays in different directions, pure 2D image filtering cannot bend the physical photons to cancel out -5.5 D defocus.

### How Miop overcomes this limitation
Miop bridges optical physics and digital computing through four dedicated operating modes:

```
[Target Text / Code]
        ↓
[4D Ray-Field Synthesizer (Miop)]
        ↓
[Physical Optical Element: Pinhole Mask / Lenticular Array / Pinhole Glasses]
        ↓
[Eye's Refractive Media (Cornea & Lens: -5.5 D)]
        ↓
[Sharp, In-Focus Image Converges Directly on the Retina]
```

---

## 🚀 Operating Modes

### 1. Pinhole Parallax Barrier Mode (Screen Mask)
* **Hardware:** A high-precision micro-hole film (printed on clear acetate or photoplotter film at 2400+ DPI) separated by an acrylic spacer (1.5–2.5 mm) in front of the screen.
* **Algorithm:** Projects angular rays through the nearest pinholes calibrated to the user's exact diopters, astigmatism cylinder, axis, and eye-to-screen distance.
* **Vector Mask Generator:** Includes an automated generator to produce publication-grade SVG masks (`generate_pinhole_mask.py`).

### 2. Lenticular Array Mode (3D Autostereoscopic Sheet)
* **Hardware:** Commercial cylindrical micro-lens sheets (40, 60, or 100 LPI).
* **Algorithm:** Multiplexes angular subpixel slices across cylindrical lenses with adjustable slant angles, transmitting nearly 100% of the screen's native brightness.

### 3. Pinhole Glasses Mode (Physical Glasses on Eyes)
* **Hardware:** Commercial pinhole glasses (stenopeic glasses with perforated grid).
* **Algorithm:** While pinhole glasses provide infinite depth of field without prescription lenses, they cut ~85% of ambient light and suffer from "screen-door" grid artifacts. Miop applies:
  * **Adaptive Luminance Boost:** Tailored gamma curve expansion to restore brightness.
  * **Anti-Screen-Door Filter:** Stroke dilation preventing code symbols (`{}`, `()`, `;`) from vanishing into grid blind spots.
  * **Polarized Contrast:** Eliminates edge diffraction halos around the pinholes.

### 4. Pure High-Fidelity Magnifier Mode
* High-resolution, artifact-free Lanczos4 magnification (1.25x to 4.5x) with freeze-frame capability for quick reading without any physical attachments.

---

## 🛠 Project Structure

* **`main.py`**: Application entrypoint launching the Hardware Optical Suite.
* **`lightfield_gui.py`**: Modern dark-themed dashboard and real-time floating HUD lens.
* **`lightfield_core.py`**: 4D Light Field Ray Synthesizer, ray remapping, and stenopeic vision pipeline.
* **`generate_pinhole_mask.py`**: Parametric vector generator creating SVG printing masks.
* **`magnifier_core.py`**: Clean, high-fidelity digital zoom and contrast processor.
* **`screen_capture.py`**: Low-latency screen grabber powered by `mss` and Windows GDI APIs.
* **`run.bat`**: One-click launcher for Windows.

---

## 💻 Installation & Quick Start

### Requirements
* Windows 10 / 11
* Python 3.10+ (tested up to Python 3.14)

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/miop.git
   cd miop
   ```
2. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install mss opencv-python scipy pillow numpy pywin32
   ```
4. Run Miop:
   ```powershell
   python main.py
   ```
   *(Or simply double-click `run.bat`)*

---

## 📐 Generating a Physical Pinhole Mask for Printing

To generate a custom hexagonal micro-hole barrier for your screen:

```powershell
python generate_pinhole_mask.py
```

This creates `mascara_estenopeica_pantalla.svg` configured with:
* Hole diameter: **85 µm**
* Hole pitch: **0.45 mm** (hexagonal packing)
* Format: Scalable Vector Graphics (ready for photoplotter or high-resolution acetate printing).

---

## 🎛 Keyboard & Mouse Shortcuts (Floating HUD Lens)

| Shortcut | Action |
| :--- | :--- |
| **`Space`** or **`Right Click`** | Freeze / Resume live capture |
| **`Mouse Wheel`** | Smooth Zoom In / Out |
| **`+` / `-`** | Adjust Zoom level |
| **`F`** | Toggle Follow Mouse / Pinned Window |
| **`C`** | Toggle High-Contrast Boost |

---

## 🛡 License

This project is licensed under a **Modified MIT License** with Attribution and Commercial Royalty terms:
* **Attribution:** Anyone is free to use, modify, and distribute the code, provided that clear credit and attribution to **Antonio Martínez** is retained.
* **Commercial Royalty:** Free for non-commercial, academic, research, and commercial usage up to **$100,000 USD** in gross revenue. Any commercial exploitation generating revenues above $100,000 USD is subject to a **2% royalty** payable to Antonio Martínez.

See the [LICENSE](LICENSE) file for the full legal text.
