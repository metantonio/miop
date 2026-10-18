"""
Miop - Módulo de Captura de Pantalla en Tiempo Real
Optimizado con mss para alto rendimiento y baja latencia.
"""

import mss
import numpy as np
import cv2


class ScreenCapturer:
    def __init__(self):
        self._sct = mss.mss()
        self.monitors = self._sct.monitors
        # Monitor primario o todos los monitores
        self.primary_monitor = self.monitors[1] if len(self.monitors) > 1 else self.monitors[0]

    def capture_region(self, x: int, y: int, width: int, height: int) -> np.ndarray:
        """
        Captura una región rectangular de la pantalla con límites seguros.
        Retorna la imagen en formato BGR (compatible con OpenCV).
        """
        # Asegurar límites dentro de la resolución de pantalla
        max_w = self.monitors[0]["width"]
        max_h = self.monitors[0]["height"]

        x1 = max(0, min(x, max_w - 50))
        y1 = max(0, min(y, max_h - 50))
        w = max(50, min(width, max_w - x1))
        h = max(50, min(height, max_h - y1))

        bbox = {"left": int(x1), "top": int(y1), "width": int(w), "height": int(h)}
        
        try:
            shot = self._sct.grab(bbox)
            # mss retorna BGRA, convertimos a BGR
            img_bgra = np.array(shot, dtype=np.uint8)
            img_bgr = cv2.cvtColor(img_bgra, cv2.COLOR_BGRA2BGR)
            return img_bgr
        except Exception as e:
            # Fallback en caso de minimización o error
            return np.zeros((height, width, 3), dtype=np.uint8)

    def close(self):
        try:
            self._sct.close()
        except Exception:
            pass
