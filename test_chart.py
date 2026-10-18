"""
Miop - Gráficos de Prueba y Calibración Óptica
Generador de Cartel de Snellen y Esfera Horaria de Astigmatismo para autocalibración.
"""

import cv2
import numpy as np


class OptometryChartGenerator:
    @staticmethod
    def generate_astigmatism_dial(width: int = 600, height: int = 600) -> np.ndarray:
        """
        Genera la rueda / abanico horario de astigmatismo (Clock Dial).
        En ojos con astigmatismo, una de las líneas radiales se ve más nítida o gruesa que las demás.
        El usuario debe calibrar el eje y cilindro hasta que todas las líneas se perciban uniformes.
        """
        img = np.full((height, width, 3), 255, dtype=np.uint8)
        cx, cy = width // 2, height // 2
        radius = int(min(cx, cy) * 0.82)
        inner_r = int(radius * 0.28)

        # Círculo guía exterior e interior
        cv2.circle(img, (cx, cy), radius, (200, 200, 200), 1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), inner_r, (230, 230, 230), 1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), 5, (50, 50, 50), -1, cv2.LINE_AA)

        # Dibujar líneas cada 15 grados de 0 a 180 (simetría)
        for angle_deg in range(0, 180, 15):
            rad = np.deg2rad(angle_deg)
            cos_a = np.cos(rad)
            sin_a = np.sin(rad)

            # Líneas radiales dobles (paralelas finas para notar desenfoque cilíndrico)
            p1_x = int(cx + inner_r * cos_a)
            p1_y = int(cy - inner_r * sin_a)
            p2_x = int(cx + radius * cos_a)
            p2_y = int(cy - radius * sin_a)

            # Opuesto
            p3_x = int(cx - inner_r * cos_a)
            p3_y = int(cy + inner_r * sin_a)
            p4_x = int(cx - radius * cos_a)
            p4_y = int(cy + radius * sin_a)

            # Línea principal
            cv2.line(img, (p1_x, p1_y), (p2_x, p2_y), (15, 15, 15), 2, cv2.LINE_AA)
            cv2.line(img, (p3_x, p3_y), (p4_x, p4_y), (15, 15, 15), 2, cv2.LINE_AA)

            # Etiquetas de grados
            label_r = radius + 22
            lx = int(cx + label_r * cos_a) - 12
            ly = int(cy - label_r * sin_a) + 5
            cv2.putText(
                img,
                f"{angle_deg}°",
                (lx, ly),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.38,
                (80, 80, 80),
                1,
                cv2.LINE_AA
            )

        # Título
        cv2.putText(
            img,
            "TEST DE ASTIGMATISMO (Reloj de Prueba)",
            (cx - 170, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (20, 20, 20),
            1,
            cv2.LINE_AA
        )
        cv2.putText(
            img,
            "Ajusta 'Eje' y 'Cilindro' hasta que todas las lineas se vean con igual nitidez",
            (cx - 240, height - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (100, 100, 100),
            1,
            cv2.LINE_AA
        )

        return img

    @staticmethod
    def generate_snellen_text_chart(width: int = 600, height: int = 600) -> np.ndarray:
        """
        Genera una cartelera de prueba con caracteres tipográficos de diferentes escalas
        y código fuente para verificar la legibilidad de la miopía.
        """
        img = np.full((height, width, 3), 250, dtype=np.uint8)

        # Encabezado
        cv2.putText(img, "TEST DE AGUDEZA VISUAL & TEXTO", (25, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (30, 30, 30), 2, cv2.LINE_AA)
        cv2.line(img, (25, 48), (width - 25, 48), (200, 200, 200), 1)

        # Líneas estilo Snellen
        lines = [
            ("E", 1.8, 4, 100),
            ("F P", 1.4, 3, 145),
            ("T O Z", 1.0, 2, 185),
            ("L P E D", 0.75, 2, 220),
            ("P E C F D", 0.60, 1, 252),
            ("E D F C Z P", 0.48, 1, 280),
            ("F E L O P Z D", 0.38, 1, 305)
        ]

        for text, scale, thick, y_pos in lines:
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)[0]
            x_pos = (width - text_size[0]) // 2
            cv2.putText(img, text, (x_pos, y_pos), cv2.FONT_HERSHEY_SIMPLEX, scale, (15, 15, 15), thick, cv2.LINE_AA)

        # Bloque de código de ejemplo (simula trabajo real de programador)
        cv2.line(img, (25, 330), (width - 25, 330), (200, 200, 200), 1)
        cv2.putText(img, "Prueba de lectura de codigo (fuente regular de editor):", (25, 355), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 80, 80), 1, cv2.LINE_AA)

        # Simular caja de editor oscuro
        cv2.rectangle(img, (25, 370), (width - 25, height - 35), (28, 30, 34), -1)
        code_lines = [
            "def test_astigmatism_angle(degree: float) -> bool:",
            "    # Calibrando frecuencias de onda corneal",
            "    optical_power = calculate_diopters(radius=1.2)",
            "    for char in ['{', '(', '[', ';', ':', '.', '|']:",
            "        render_crisp_pixel(char, contrast=1.4)",
            "    return True"
        ]

        y_code = 400
        for cline in code_lines:
            cv2.putText(img, cline, (40, y_code), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 235, 240), 1, cv2.LINE_AA)
            y_code += 28

        cv2.putText(
            img,
            "Verifica como los simbolos finos () {} ; : se definen con 'Miopia' y 'Engrosar Letras'",
            (25, height - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.40,
            (100, 100, 100),
            1,
            cv2.LINE_AA
        )

        return img
