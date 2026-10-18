"""
Miop - Generador de Máscara Física de Micro-Agujeros (Máscara de Paralaje)
Crea archivos vectoriales SVG y mapas de bits de alta resolución listos para imprimir en acetato/fotoplotter.
"""

import math
import os


def generate_pinhole_mask_svg(
    output_path: str = "pinhole_mask.svg",
    width_mm: float = 200.0,         # Ancho de la lámina en mm
    height_mm: float = 150.0,        # Alto de la lámina en mm
    hole_diameter_um: float = 90.0,  # Diámetro de cada orificio en micrómetros (70 a 120 um)
    pitch_x_mm: float = 0.50,        # Separación horizontal entre agujeros en mm
    pitch_y_mm: float = 0.50,        # Separación vertical entre agujeros en mm
    pattern: str = "hexagonal"       # 'hexagonal' (panal de abeja) o 'grid' (ortogonal)
):
    """
    Genera un archivo SVG vectorial ultra-preciso para enviar a imprenta/fotomecánica.
    La máscara es negra opaca con orificios transparentes circulares.
    """
    hole_radius_mm = (hole_diameter_um / 1000.0) / 2.0
    
    cols = int(width_mm / pitch_x_mm) + 1
    rows = int(height_mm / pitch_y_mm) + 1

    print(f"[+] Generando máscara {pattern}: {cols}x{rows} agujeros...")
    print(f"    Diámetro del agujero: {hole_diameter_um} um ({hole_diameter_um/1000:.3f} mm)")
    print(f"    Dimensiones físicas: {width_mm} mm x {height_mm} mm")

    svg_header = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="{width_mm}mm" height="{height_mm}mm" viewBox="0 0 {width_mm} {height_mm}"
     xmlns="http://www.w3.org/2000/svg">
  <!-- Fondo negro totalmente opaco -->
  <rect x="0" y="0" width="{width_mm}" height="{height_mm}" fill="black" />
  <!-- Micro-orificios transparentes/blancos -->
  <g fill="white">
"""
    circles = []
    total_holes = 0

    for r in range(rows):
        y = r * pitch_y_mm
        if y > height_mm:
            break

        # Si es hexagonal, desplazar filas alternas medio pitch
        offset_x = (pitch_x_mm * 0.5) if (pattern == "hexagonal" and (r % 2 == 1)) else 0.0

        for c in range(cols):
            x = c * pitch_x_mm + offset_x
            if x > width_mm:
                break
            circles.append(f'<circle cx="{x:.4f}" cy="{y:.4f}" r="{hole_radius_mm:.4f}" />')
            total_holes += 1

    svg_footer = """  </g>
</svg>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_header)
        f.write("\n".join(circles))
        f.write("\n" + svg_footer)

    print(f"[OK] Archivo SVG generado con exito: {os.path.abspath(output_path)}")
    print(f"    Total de micro-orificios: {total_holes:,}")
    return output_path


if __name__ == "__main__":
    generate_pinhole_mask_svg(
        output_path="mascara_estenopeica_pantalla.svg",
        width_mm=200.0,
        height_mm=130.0,
        hole_diameter_um=85.0,
        pitch_x_mm=0.45,
        pitch_y_mm=0.45,
        pattern="hexagonal"
    )
