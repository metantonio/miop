"""
Miop - Núcleo de Procesamiento Óptico para Miopía y Astigmatismo
Algoritmos de compensación de frente de onda y realce adaptativo de contraste.
"""

import cv2
import numpy as np


class VisionCorrector:
    def __init__(self):
        # Cache de kernels para alto rendimiento
        self._last_kernel_params = None
        self._cached_kernel = None

    @staticmethod
    def create_anisotropic_kernel(size: int, sigma_par: float, sigma_perp: float, angle_deg: float) -> np.ndarray:
        """
        Crea un kernel Gaussiano elíptico orientado en el ángulo especificado (en grados).
        Se usa para simular la PSF del astigmatismo y aplicar deconvolución/unsharp direccional.
        """
        if size % 2 == 0:
            size += 1
        
        # Coordenadas centradas
        ax = np.arange(-(size // 2), size // 2 + 1)
        xx, yy = np.meshgrid(ax, ax)
        
        # Rotación según el eje del astigmatismo
        theta = np.deg2rad(angle_deg)
        x_rot = xx * np.cos(theta) + yy * np.sin(theta)
        y_rot = -xx * np.sin(theta) + yy * np.cos(theta)
        
        # Gaussiana elíptica
        kernel = np.exp(-0.5 * ((x_rot ** 2) / (sigma_par ** 2 + 1e-5) + (y_rot ** 2) / (sigma_perp ** 2 + 1e-5)))
        kernel /= np.sum(kernel)
        return kernel.astype(np.float32)

    def process_frame(
        self,
        img_bgr: np.ndarray,
        myopia_intensity: float = 1.0,     # 0.0 a 4.0 (intensidad de realce de nitidez)
        myopia_radius: float = 1.2,        # 0.5 a 3.0 (radio de frecuencias a compensar)
        astigmatism_cyl: float = 0.0,      # 0.0 a 3.0 (fuerza cilíndrica)
        astigmatism_axis: float = 0.0,     # 0 a 180 grados
        stroke_thickness: float = 0.0,     # 0.0 a 2.0 (engrosamiento de fuentes/trazos)
        clahe_strength: float = 0.0,       # 0.0 a 1.0 (contraste adaptativo local)
        blue_light_filter: float = 0.0,    # 0.0 a 1.0 (reducción de aberración cromática)
        zoom_factor: float = 1.0           # 1.0 a 3.0
    ) -> np.ndarray:
        """
        Aplica la cadena completa de corrección sobre la imagen BGR capturada.
        """
        if img_bgr is None or img_bgr.size == 0:
            return img_bgr

        h, w = img_bgr.shape[:2]
        processed = img_bgr.copy()

        # 1. Zoom digital centrado (si aplica)
        if zoom_factor > 1.02:
            new_w = int(w / zoom_factor)
            new_h = int(h / zoom_factor)
            x1 = max(0, (w - new_w) // 2)
            y1 = max(0, (h - new_h) // 2)
            crop = processed[y1 : y1 + new_h, x1 : x1 + new_w]
            processed = cv2.resize(crop, (w, h), interpolation=cv2.INTER_LANCZOS4)

        # 2. Compensación de Miopía (Multi-Scale Frequency Sharpening para Alta Graduación)
        if myopia_intensity > 0.05:
            # Para miopía alta (> 3.0 D hasta 5.5+ D), un único filtro paso-alto produce halos.
            # Implementamos realce multiescala (frecuencias finas + medias estructurales):
            k_fine = int(max(3, round(myopia_radius * 2.5) | 1))
            k_coarse = int(max(5, round(myopia_radius * 5.0) | 1))
            
            blur_fine = cv2.GaussianBlur(processed, (k_fine, k_fine), myopia_radius)
            blur_coarse = cv2.GaussianBlur(processed, (k_coarse, k_coarse), myopia_radius * 2.0)
            
            # Banda de alta frecuencia (bordes finos)
            high_band = cv2.subtract(processed, blur_fine)
            # Banda de media frecuencia (cuerpo de las letras y contraste estructural)
            mid_band = cv2.subtract(blur_fine, blur_coarse)
            
            # Ponderación adaptativa: a mayor graduación, mayor refuerzo de frecuencias medias
            alpha_high = myopia_intensity * 0.75
            alpha_mid = myopia_intensity * 0.45
            
            processed = cv2.addWeighted(processed, 1.0, high_band, alpha_high, 0)
            processed = cv2.addWeighted(processed, 1.0, mid_band, alpha_mid, 0)

        # 3. Compensación de Astigmatismo (Filtro Direccional Anisotrópico)
        if astigmatism_cyl > 0.05:
            # En astigmatismo, el desenfoque es asimétrico.
            # Se aplica un kernel orientado a lo largo del eje para potenciar
            # las altas frecuencias específicamente en el meridiano afectado.
            k_size = int(max(9, round(7 + astigmatism_cyl * 4) | 1))
            sigma_par = 0.8 + astigmatism_cyl * 1.8
            sigma_perp = 0.5  # estrecho perpendicularmente
            kernel = self.create_anisotropic_kernel(k_size, sigma_par, sigma_perp, astigmatism_axis)
            
            # Filtro direccional
            blurred_dir = cv2.filter2D(processed, -1, kernel)
            dir_diff = cv2.subtract(processed, blurred_dir)
            # Sumar diferencial direccional ponderado por la potencia del cilindro
            processed = cv2.addWeighted(processed, 1.0, dir_diff, float(astigmatism_cyl * 1.4), 0)

        # 4. Engrosamiento adaptativo de trazos finos (Texto delgado para Alta Miopía)
        if stroke_thickness > 0.05:
            # A 5.5 D, los trazos de 1 px desaparecen. Se requiere engrosar 2-3 px.
            iters = max(1, int(round(stroke_thickness)))
            k_morph = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            
            gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
            is_dark_bg = (np.mean(gray) < 128)
            
            if is_dark_bg:
                # Fondo oscuro: engrosar letras claras mediante dilatación
                thick = cv2.dilate(processed, k_morph, iterations=iters)
            else:
                # Fondo claro: engrosar letras oscuras mediante erosión
                thick = cv2.erode(processed, k_morph, iterations=iters)
                
            blend_weight = min(1.0, stroke_thickness / float(iters))
            processed = cv2.addWeighted(processed, 1.0 - blend_weight, thick, blend_weight, 0)

        # 5. Contraste Local Adaptativo (CLAHE)
        if clahe_strength > 0.05:
            # Aplicar únicamente al canal de luminancia (L en LAB) para no distorsionar colores
            lab = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clip_limit = 1.0 + clahe_strength * 3.5
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
            l_enhanced = clahe.apply(l)
            # Mezcla suave para evitar artefactos excesivos
            l_final = cv2.addWeighted(l, 1.0 - clahe_strength, l_enhanced, clahe_strength, 0)
            lab = cv2.merge((l_final, a, b))
            processed = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # 6. Filtro Anti-Aberración Cromática / Luz Azul
        if blue_light_filter > 0.05:
            # En ojos miopes, la luz azul sufre mucha más refracción y genera mayor halo.
            # Reducir ligeramente el canal azul y atenuar destellos agudos incrementa la nitidez subjetiva.
            b, g, r = cv2.split(processed)
            reduction = blue_light_filter * 0.28  # hasta 28% de reducción del canal azul
            b = np.clip(b.astype(np.float32) * (1.0 - reduction), 0, 255).astype(np.uint8)
            # Pequeño impulso a tonos cálidos/ámbar para contraste
            warmth = blue_light_filter * 0.08
            r = np.clip(r.astype(np.float32) * (1.0 + warmth), 0, 255).astype(np.uint8)
            processed = cv2.merge((b, g, r))

        return processed
