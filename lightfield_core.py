"""
Miop - Motor de Campo de Luz 4D y Adaptador para Modos Físicos
Soporta:
 1. Máscara de Micro-agujeros (Parallax Barrier)
 2. Lámina Lenticular (Lenticular Array)
 3. Gafas Estenopeicas (Pinhole Glasses Mode)
"""

import math
import cv2
import numpy as np


class OpticalHardwareSynthesizer:
    def __init__(self):
        pass

    # -------------------------------------------------------------------------
    # MODO 1: MÁSCARA DE PARALAJE / MICRO-AGUJEROS EN PANTALLA
    # -------------------------------------------------------------------------
    def process_pinhole_barrier(
        self,
        img_bgr: np.ndarray,
        diopters: float = -5.5,
        astig_cyl: float = 0.0,
        astig_axis_deg: float = 0.0,
        eye_distance_cm: float = 50.0,
        spacer_mm: float = 2.0,
        pitch_pixels: float = 4.0
    ) -> np.ndarray:
        """
        Sintetiza el campo de luz 4D para una máscara de micro-agujeros colocada sobre la pantalla.
        Calcula el desplazamiento angular inverso necesario para que los rayos converjan en la retina.
        """
        if img_bgr is None or img_bgr.size == 0:
            return img_bgr

        h, w = img_bgr.shape[:2]
        d_eye = eye_distance_cm * 10.0  # en mm
        s = max(0.5, spacer_mm)          # separación pantalla-lámina en mm

        # Desplazamiento corneal debido a la miopía:
        # A -5.5 D, los rayos deben emitirse con un ángulo de pre-divergencia
        # Delta = factor proporcional a dioptrías y relación s / d_eye
        k_myopia = (diopters / -5.5) * (s / 2.0) * (500.0 / d_eye) * 1.6
        
        # Astigmatismo direccional
        theta = np.deg2rad(astig_axis_deg)
        k_cyl_x = astig_cyl * 0.4 * np.cos(theta)
        k_cyl_y = astig_cyl * 0.4 * np.sin(theta)

        # Crear mallas de coordenadas de píxeles
        y_indices, x_indices = np.indices((h, w), dtype=np.float32)

        # Fase angular respecto al micro-agujero más cercano
        # Los píxeles a la izquierda/derecha del agujero emiten en ángulos distintos
        phase_x = (x_indices % pitch_pixels) - (pitch_pixels / 2.0)
        phase_y = (y_indices % pitch_pixels) - (pitch_pixels / 2.0)

        # Mapeo de rayos inversos (Ray-field remap)
        map_x = x_indices + phase_x * (k_myopia + k_cyl_x)
        map_y = y_indices + phase_y * (k_myopia + k_cyl_y)

        # Remapeo bilineal acelerado por OpenCV
        map_x = np.clip(map_x, 0, w - 1).astype(np.float32)
        map_y = np.clip(map_y, 0, h - 1).astype(np.float32)
        synthesized = cv2.remap(img_bgr, map_x, map_y, interpolation=cv2.INTER_LINEAR)

        # Realce de luminancia para compensar la atenuación de la máscara
        synthesized = cv2.convertScaleAbs(synthesized, alpha=1.35, beta=15)
        return synthesized

    # -------------------------------------------------------------------------
    # MODO 2: LÁMINA LENTICULAR (MICRO-LENTES CILÍNDRICAS)
    # -------------------------------------------------------------------------
    def process_lenticular(
        self,
        img_bgr: np.ndarray,
        diopters: float = -5.5,
        lpi: float = 60.0,              # Líneas por pulgada de la lámina (40, 60, 100)
        screen_dpi: float = 140.0,       # DPI del monitor
        slant_deg: float = 0.0           # Ángulo de inclinación (típicamente 0° o 9.46°)
    ) -> np.ndarray:
        """
        Sintetiza la multiplexación de subpíxeles angulares para láminas lenticulares.
        """
        if img_bgr is None or img_bgr.size == 0:
            return img_bgr

        h, w = img_bgr.shape[:2]
        # Píxeles por lente cilíndrica
        pixels_per_lens = max(2.0, screen_dpi / max(1.0, lpi))
        
        # Desplazamiento según dioptrías
        shift_strength = (diopters / -5.5) * 1.5

        y_indices, x_indices = np.indices((h, w), dtype=np.float32)
        slant_rad = np.deg2rad(slant_deg)

        # Eje de la lente cilíndrica
        lens_axis = (x_indices * np.cos(slant_rad) + y_indices * np.sin(slant_rad)) % pixels_per_lens
        phase = (lens_axis - (pixels_per_lens / 2.0)) / (pixels_per_lens / 2.0)

        # Mapeo horizontal anisotrópico
        map_x = x_indices + phase * shift_strength * (pixels_per_lens * 0.5)
        map_y = y_indices

        map_x = np.clip(map_x, 0, w - 1).astype(np.float32)
        map_y = np.clip(map_y, 0, h - 1).astype(np.float32)
        return cv2.remap(img_bgr, map_x, map_y, interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------
    # MODO 3: GAFAS ESTENOPEICAS (PINHOLE GLASSES OPTIMIZER)
    # -------------------------------------------------------------------------
    def process_pinhole_glasses(
        self,
        img_bgr: np.ndarray,
        boost_luminance: float = 1.6,
        anti_screen_door: bool = True,
        high_contrast_polarize: bool = True
    ) -> np.ndarray:
        """
        Optimización especial para usuarios que usan GAFAS ESTENOPEICAS delante de los ojos.
        Las gafas estenopeicas ya crean profundidad de foco infinita sin lentes graduadas,
        pero reducen drásticamente el brillo y sufren de efecto rejilla (moiré).
        Este modo maximiza la transmisión lumínica, amplifica el contraste y engrosa
        las fuentes para lectura perfecta a través de los agujeros de las gafas.
        """
        if img_bgr is None or img_bgr.size == 0:
            return img_bgr

        result = img_bgr.copy()

        # 1. Anti-Screen-Door: engrosamiento de caracteres finos para que no caigan en los puntos ciegos
        if anti_screen_door:
            k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
            is_dark = (np.mean(gray) < 128)
            if is_dark:
                thick = cv2.dilate(result, k, iterations=1)
            else:
                thick = cv2.erode(result, k, iterations=1)
            result = cv2.addWeighted(result, 0.35, thick, 0.65, 0)

        # 2. Alto contraste polarizado (elimina halos de difracción en los agujeritos)
        if high_contrast_polarize:
            lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(6, 6))
            l = clahe.apply(l)
            lab = cv2.merge((l, a, b))
            result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # 3. Impulso masivo de luminancia (las gafas estenopeicas recortan el 80% de fotones)
        if boost_luminance > 1.05:
            # Curva gamma ajustada para elevar tonos oscuros y medios sin quemar blancos
            gamma = 1.0 / max(1.1, boost_luminance * 0.8)
            inv_gamma = 1.0 / gamma
            table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
            result = cv2.LUT(result, table)
            # Escala adicional lineal
            result = cv2.convertScaleAbs(result, alpha=min(1.4, boost_luminance * 0.85), beta=10)

        return result
