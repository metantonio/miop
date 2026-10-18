"""
Miop - Gestor de Configuración y Perfiles de Visión
Permite guardar, cargar y restaurar presets personalizados de graduación.
"""

import json
import os
from typing import Dict, Any

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_PRESETS: Dict[str, Dict[str, Any]] = {
    "⭐ Miopia 5.5 D (Alta Graduacion)": {
        "myopia_intensity": 3.8,
        "myopia_radius": 2.4,
        "astigmatism_cyl": 1.2,
        "astigmatism_axis": 90.0,
        "stroke_thickness": 1.8,
        "clahe_strength": 0.55,
        "blue_light_filter": 0.35,
        "zoom_factor": 1.55
    },
    "Programacion (Letras Nitidas)": {
        "myopia_intensity": 1.6,
        "myopia_radius": 1.2,
        "astigmatism_cyl": 0.8,
        "astigmatism_axis": 90.0,
        "stroke_thickness": 0.6,
        "clahe_strength": 0.35,
        "blue_light_filter": 0.25,
        "zoom_factor": 1.25
    },
    "Lectura Web / Documentos": {
        "myopia_intensity": 1.3,
        "myopia_radius": 1.0,
        "astigmatism_cyl": 0.5,
        "astigmatism_axis": 0.0,
        "stroke_thickness": 0.4,
        "clahe_strength": 0.45,
        "blue_light_filter": 0.35,
        "zoom_factor": 1.20
    },
    "Astigmatismo Pronunciado": {
        "myopia_intensity": 1.2,
        "myopia_radius": 1.0,
        "astigmatism_cyl": 1.8,
        "astigmatism_axis": 45.0,
        "stroke_thickness": 0.5,
        "clahe_strength": 0.3,
        "blue_light_filter": 0.2,
        "zoom_factor": 1.15
    },
    "Maximo Enfoque & Contraste": {
        "myopia_intensity": 2.2,
        "myopia_radius": 1.4,
        "astigmatism_cyl": 1.2,
        "astigmatism_axis": 90.0,
        "stroke_thickness": 0.8,
        "clahe_strength": 0.60,
        "blue_light_filter": 0.40,
        "zoom_factor": 1.40
    },
    "Neutral (Sin Correccion)": {
        "myopia_intensity": 0.0,
        "myopia_radius": 1.0,
        "astigmatism_cyl": 0.0,
        "astigmatism_axis": 0.0,
        "stroke_thickness": 0.0,
        "clahe_strength": 0.0,
        "blue_light_filter": 0.0,
        "zoom_factor": 1.0
    }
}


class ConfigManager:
    @staticmethod
    def load_config() -> Dict[str, Any]:
        """Carga la configuración del usuario o los valores iniciales recomendados."""
        base_config = {
            "current": dict(DEFAULT_PRESETS["⭐ Miopia 5.5 D (Alta Graduacion)"]),
            "presets": dict(DEFAULT_PRESETS),
            "lens_width": 460,
            "lens_height": 340,
            "follow_mouse": False,
            "split_comparison": False
        }

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    base_config.update(data)
            except Exception:
                pass
        return base_config

    @staticmethod
    def save_config(config: Dict[str, Any]) -> bool:
        """Guarda la configuración actual en config.json."""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False
