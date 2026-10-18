"""
Miop Magnifier - Motor de Ampliación de Alta Fidelidad
Especializado en magnificación limpia, sin artefactos de distorsión, para lectura sin gafas a -5.5 D.
"""

import cv2
import numpy as np


class CleanMagnifier:
    def __init__(self):
        pass

    def process(
        self,
        img_bgr: np.ndarray,
        zoom_factor: float = 2.0,
        high_contrast: bool = False,
        invert_colors: bool = False,
        crisp_text: bool = True
    ) -> np.ndarray:
        """
        Amplía y optimiza la imagen capturada con alta nitidez geométrica y fidelidad de color.
        """
        if img_bgr is None or img_bgr.size == 0:
            return img_bgr

        h, w = img_bgr.shape[:2]

        # 1. Recorte centrado para zoom
        if zoom_factor > 1.01:
            crop_w = max(10, int(w / zoom_factor))
            crop_h = max(10, int(h / zoom_factor))
            x1 = max(0, (w - crop_w) // 2)
            y1 = max(0, (h - crop_h) // 2)
            crop = img_bgr[y1 : y1 + crop_h, x1 : x1 + crop_w]
            # Interpolación Lanczos4 para preservar bordes tipográficos sin pixelación
            result = cv2.resize(crop, (w, h), interpolation=cv2.INTER_LANCZOS4)
        else:
            result = img_bgr.copy()

        # 2. Realce de nitidez sutil en bordes de texto (sin halos molestos)
        if crisp_text:
            # Unsharp sutil y controlado que hace resaltar la tipografía
            blur = cv2.GaussianBlur(result, (3, 3), 0.8)
            diff = cv2.subtract(result, blur)
            result = cv2.addWeighted(result, 1.0, diff, 0.45, 0)

        # 3. Alto Contraste para texto (opcional)
        if high_contrast:
            # Convierte a LAB y expande el rango dinámico de la luminancia
            lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
            l = clahe.apply(l)
            lab = cv2.merge((l, a, b))
            result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # 4. Inversión de Colores / Modo Oscuro (opcional para fatiga visual)
        if invert_colors:
            result = cv2.bitwise_not(result)

        return result
