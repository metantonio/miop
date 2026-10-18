"""
Miop - Panel de Control Principal y Calibrador Visual
Dashboard con interfaz oscura moderna, dial interactivo de astigmatismo y tests de agudeza.
"""

import math
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk

from vision_core import VisionCorrector
from screen_capture import ScreenCapturer
from test_chart import OptometryChartGenerator
from config_manager import ConfigManager, DEFAULT_PRESETS
from lens_window import FloatingLensWindow


class MiopApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Miop - Asistente de Visión para Miopía & Astigmatismo")
        self.root.geometry("860x720")
        self.root.minsize(780, 640)
        self.root.configure(bg="#0f1115")

        # Motores
        self.corrector = VisionCorrector()
        self.capturer = ScreenCapturer()
        self.config_data = ConfigManager.load_config()
        self.lens_win = None

        # Variables reactivas para los sliders (Calibrados por defecto para 5.5 D)
        current_cfg = self.config_data.get("current", {})
        self.var_myopia_int = tk.DoubleVar(value=current_cfg.get("myopia_intensity", 3.8))
        self.var_myopia_rad = tk.DoubleVar(value=current_cfg.get("myopia_radius", 2.4))
        self.var_astig_cyl = tk.DoubleVar(value=current_cfg.get("astigmatism_cyl", 1.2))
        self.var_astig_axis = tk.DoubleVar(value=current_cfg.get("astigmatism_axis", 90.0))
        self.var_stroke = tk.DoubleVar(value=current_cfg.get("stroke_thickness", 1.8))
        self.var_clahe = tk.DoubleVar(value=current_cfg.get("clahe_strength", 0.55))
        self.var_blue_light = tk.DoubleVar(value=current_cfg.get("blue_light_filter", 0.35))
        self.var_zoom = tk.DoubleVar(value=current_cfg.get("zoom_factor", 1.55))

        # Test chart activo
        self.current_test_type = "snellen"  # 'snellen' o 'dial'
        self.test_img_raw = None
        self._test_photo = None

        # Construir Interfaz
        self._setup_styles()
        self._build_header()
        self._build_notebook()
        self._build_footer()

        # Generar primer test
        self._switch_test_chart("snellen")

        # Escuchar cambios para actualizar el dial de astigmatismo y el preview
        self.var_astig_axis.trace_add("write", lambda *args: self._on_param_change())
        self.var_astig_cyl.trace_add("write", lambda *args: self._on_param_change())
        self.var_myopia_int.trace_add("write", lambda *args: self._on_param_change())
        self.var_myopia_rad.trace_add("write", lambda *args: self._on_param_change())
        self.var_stroke.trace_add("write", lambda *args: self._on_param_change())
        self.var_clahe.trace_add("write", lambda *args: self._on_param_change())
        self.var_blue_light.trace_add("write", lambda *args: self._on_param_change())
        self.var_zoom.trace_add("write", lambda *args: self._on_param_change())

        # Dibujar aguja inicial
        self.root.after(100, self._draw_astigmatism_dial)

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        # Estilos generales para Notebook y pestañas
        style.configure("TNotebook", background="#0f1115", borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background="#1c1f26",
            foreground="#9ca3af",
            padding=[14, 8],
            font=("Segoe UI", 9, "bold"),
            borderwidth=0
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#2563eb"), ("active", "#1e293b")],
            foreground=[("selected", "#ffffff"), ("active", "#e2e8f0")]
        )

        style.configure("TFrame", background="#0f1115")
        style.configure("Card.TFrame", background="#181b21", relief="flat")

    def _build_header(self):
        header_frame = tk.Frame(self.root, bg="#13161c", height=70)
        header_frame.pack(side=tk.TOP, fill=tk.X)

        title_box = tk.Frame(header_frame, bg="#13161c")
        title_box.pack(side=tk.LEFT, padx=20, pady=12)

        lbl_app = tk.Label(
            title_box,
            text="👓 Miop",
            fg="#60a5fa",
            bg="#13161c",
            font=("Segoe UI", 16, "bold")
        )
        lbl_app.pack(anchor="w")

        lbl_sub = tk.Label(
            title_box,
            text="Compensador Óptico Digital para Miopía & Astigmatismo",
            fg="#94a3b8",
            bg="#13161c",
            font=("Segoe UI", 9)
        )
        lbl_sub.pack(anchor="w")

        # Botón para abrir Lupa HUD
        self.btn_open_lens = tk.Button(
            header_frame,
            text="🔍 ABRIR LUPA FLOTANTE (HUD)",
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
            command=self.toggle_lens_window
        )
        self.btn_open_lens.pack(side=tk.RIGHT, padx=20, pady=14)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Tab 1: Calibrador y Controles
        self.tab_controls = tk.Frame(self.notebook, bg="#0f1115")
        self.notebook.add(self.tab_controls, text=" 🎛 Calibración & Controles ")
        self._build_controls_tab(self.tab_controls)

        # Tab 2: Test de Agudeza Visual & Snellen
        self.tab_test = tk.Frame(self.notebook, bg="#0f1115")
        self.notebook.add(self.tab_test, text=" 👁 Test de Calibración en Vivo ")
        self._build_test_tab(self.tab_test)

        # Tab 3: Guía Médica y Ajuste
        self.tab_guide = tk.Frame(self.notebook, bg="#0f1115")
        self.notebook.add(self.tab_guide, text=" 📖 Guía de Graduación ")
        self._build_guide_tab(self.tab_guide)

    def _build_controls_tab(self, parent):
        # Dividir en dos columnas: Izquierda (Sliders) y Derecha (Dial Astigmatismo + Presets)
        container = tk.Frame(parent, bg="#0f1115")
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        col_left = tk.Frame(container, bg="#181b21", bd=1, relief=tk.SOLID)
        col_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8), pady=0)

        col_right = tk.Frame(container, bg="#181b21", width=280, bd=1, relief=tk.SOLID)
        col_right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(8, 0), pady=0)

        # --- COLUMNA IZQUIERDA: SLIDERS ---
        scroll_canvas = tk.Canvas(col_left, bg="#181b21", highlightthickness=0)
        scrollbar = ttk.Scrollbar(col_left, orient="vertical", command=scroll_canvas.yview)
        scroll_content = tk.Frame(scroll_canvas, bg="#181b21")

        scroll_content.bind(
            "<Configure>",
            lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        )
        scroll_canvas.create_window((0, 0), window=scroll_content, anchor="nw", width=470)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Grupo 1: Miopía
        self._create_section_label(scroll_content, "🔍 1. COMPENSACIÓN DE MIOPÍA (Apto para 5.5 D)")
        self._create_slider(
            scroll_content,
            label="Intensidad de Enfoque (Defocus):",
            var=self.var_myopia_int,
            from_=0.0, to=5.0, resolution=0.1,
            unit="x"
        )
        self._create_slider(
            scroll_content,
            label="Radio de Frecuencia (Dioptrías estimadas):",
            var=self.var_myopia_rad,
            from_=0.5, to=4.5, resolution=0.1,
            unit=" px"
        )

        # Grupo 2: Astigmatismo
        self._create_section_label(scroll_content, "📐 2. COMPENSACIÓN DE ASTIGMATISMO")
        self._create_slider(
            scroll_content,
            label="Cilindro (Potencia / Fuerza):",
            var=self.var_astig_cyl,
            from_=0.0, to=3.0, resolution=0.1,
            unit=" D"
        )
        self._create_slider(
            scroll_content,
            label="Eje del Astigmatismo (Ángulo):",
            var=self.var_astig_axis,
            from_=0.0, to=180.0, resolution=1.0,
            unit="°"
        )

        # Grupo 3: Legibilidad de Texto & Contraste
        self._create_section_label(scroll_content, "✍ 3. LEGIBILIDAD DE CÓDIGO Y TEXTO (Alta Graduación)")
        self._create_slider(
            scroll_content,
            label="Engrosar Trazos / Letras Finas (Anti-Desvanecimiento):",
            var=self.var_stroke,
            from_=0.0, to=2.5, resolution=0.1,
            unit=""
        )
        self._create_slider(
            scroll_content,
            label="Micro-Contraste Adaptativo (CLAHE):",
            var=self.var_clahe,
            from_=0.0, to=1.0, resolution=0.05,
            unit=""
        )
        self._create_slider(
            scroll_content,
            label="Filtro Anti-Aberración (Luz Cálida):",
            var=self.var_blue_light,
            from_=0.0, to=1.0, resolution=0.05,
            unit=""
        )
        self._create_slider(
            scroll_content,
            label="Zoom Digital de Lupa:",
            var=self.var_zoom,
            from_=1.0, to=3.0, resolution=0.05,
            unit="x"
        )

        # --- COLUMNA DERECHA: DIAL + PRESETS ---
        # Mini reloj de astigmatismo interactivo
        tk.Label(
            col_right,
            text="ORIENTACIÓN DEL EJE",
            fg="#60a5fa",
            bg="#181b21",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="center", pady=(14, 4))

        self.dial_canvas = tk.Canvas(col_right, width=150, height=150, bg="#121418", highlightthickness=1, highlightbackground="#272b34")
        self.dial_canvas.pack(anchor="center", pady=4)

        self.lbl_axis_readout = tk.Label(
            col_right,
            text="Eje: 90° (Vertical)",
            fg="#cbd5e1",
            bg="#181b21",
            font=("Segoe UI", 9, "bold")
        )
        self.lbl_axis_readout.pack(anchor="center", pady=2)

        # Separador
        tk.Frame(col_right, bg="#2d3340", height=1).pack(fill=tk.X, padx=12, pady=10)

        # Presets rápidos
        tk.Label(
            col_right,
            text="PERFILES RÁPIDOS",
            fg="#94a3b8",
            bg="#181b21",
            font=("Segoe UI", 8, "bold")
        ).pack(anchor="w", padx=14, pady=2)

        for preset_name in DEFAULT_PRESETS.keys():
            btn = tk.Button(
                col_right,
                text=preset_name,
                bg="#232730",
                fg="#e2e8f0",
                activebackground="#334155",
                activeforeground="#ffffff",
                relief=tk.FLAT,
                font=("Segoe UI", 8),
                anchor="w",
                padx=8,
                pady=4,
                command=lambda name=preset_name: self.apply_preset(name)
            )
            btn.pack(fill=tk.X, padx=12, pady=2)

        # Botón Guardar Perfil
        btn_save = tk.Button(
            col_right,
            text="💾 Guardar como Mi Perfil",
            bg="#059669",
            fg="#ffffff",
            activebackground="#047857",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=10,
            pady=6,
            command=self.save_current_profile
        )
        btn_save.pack(fill=tk.X, padx=12, pady=(15, 10))

    def _create_section_label(self, parent, text):
        lbl = tk.Label(
            parent,
            text=text,
            fg="#38bdf8",
            bg="#181b21",
            font=("Segoe UI", 9, "bold")
        )
        lbl.pack(anchor="w", padx=12, pady=(12, 4))

    def _create_slider(self, parent, label, var, from_, to, resolution, unit=""):
        frame = tk.Frame(parent, bg="#181b21")
        frame.pack(fill=tk.X, padx=14, pady=4)

        top_line = tk.Frame(frame, bg="#181b21")
        top_line.pack(fill=tk.X)

        lbl = tk.Label(top_line, text=label, fg="#cbd5e1", bg="#181b21", font=("Segoe UI", 8))
        lbl.pack(side=tk.LEFT)

        val_lbl = tk.Label(top_line, text=f"{var.get():.1f}{unit}", fg="#38bdf8", bg="#181b21", font=("Segoe UI", 8, "bold"))
        val_lbl.pack(side=tk.RIGHT)

        def on_slider(val):
            v = float(val)
            val_lbl.config(text=f"{v:.1f}{unit}")

        scale = tk.Scale(
            frame,
            from_=from_,
            to=to,
            resolution=resolution,
            orient=tk.HORIZONTAL,
            variable=var,
            showvalue=0,
            bg="#181b21",
            fg="#38bdf8",
            troughcolor="#0d0e11",
            activebackground="#60a5fa",
            highlightthickness=0,
            bd=0,
            command=on_slider
        )
        scale.pack(fill=tk.X, pady=(2, 4))

    def _draw_astigmatism_dial(self):
        """Dibuja el compás / dial visual con la aguja indicadora del eje en grados."""
        self.dial_canvas.delete("all")
        cx, cy, r = 75, 75, 60
        # Círculo base
        self.dial_canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#334155", width=1)
        self.dial_canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill="#38bdf8", outline="")

        # Marcas cada 45 grados
        for deg in [0, 45, 90, 135]:
            rad = math.radians(deg)
            x1 = cx + (r - 8) * math.cos(rad)
            y1 = cy - (r - 8) * math.sin(rad)
            x2 = cx - (r - 8) * math.cos(rad)
            y2 = cy + (r - 8) * math.sin(rad)
            self.dial_canvas.create_line(x1, y1, x2, y2, fill="#1e293b", width=1)

        # Aguja del ángulo actual
        angle = self.var_astig_axis.get()
        rad = math.radians(angle)
        needle_x1 = cx + (r - 6) * math.cos(rad)
        needle_y1 = cy - (r - 6) * math.sin(rad)
        needle_x2 = cx - (r - 6) * math.cos(rad)
        needle_y2 = cy + (r - 6) * math.sin(rad)
        self.dial_canvas.create_line(needle_x1, needle_y1, needle_x2, needle_y2, fill="#f59e0b", width=3)

        # Actualizar texto explicativo
        desc = "Horizontal" if (angle <= 15 or angle >= 165) else ("Vertical" if (75 <= angle <= 105) else "Oblicuo")
        self.lbl_axis_readout.config(text=f"Eje: {int(angle)}° ({desc})")

    def _build_test_tab(self, parent):
        top_bar = tk.Frame(parent, bg="#0f1115")
        top_bar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=8)

        tk.Label(
            top_bar,
            text="Elige el gráfico de prueba para autocalibrar tus ojos:",
            fg="#94a3b8",
            bg="#0f1115",
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=5)

        btn_snellen = tk.Button(
            top_bar,
            text="📄 Cartel de Snellen & Código",
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            font=("Segoe UI", 8, "bold"),
            relief=tk.FLAT,
            padx=10,
            pady=4,
            command=lambda: self._switch_test_chart("snellen")
        )
        btn_snellen.pack(side=tk.LEFT, padx=6)

        btn_dial = tk.Button(
            top_bar,
            text="🎯 Reloj de Astigmatismo (Líneas Radiales)",
            bg="#334155",
            fg="#ffffff",
            activebackground="#1e293b",
            font=("Segoe UI", 8, "bold"),
            relief=tk.FLAT,
            padx=10,
            pady=4,
            command=lambda: self._switch_test_chart("dial")
        )
        btn_dial.pack(side=tk.LEFT, padx=6)

        # Botón Split Preview
        self.btn_preview_split = tk.Button(
            top_bar,
            text="⚖ Modo Dividido (Mitad Original / Mitad Corregido)",
            bg="#10b981",
            fg="#ffffff",
            activebackground="#059669",
            font=("Segoe UI", 8, "bold"),
            relief=tk.FLAT,
            padx=10,
            pady=4,
            command=self._toggle_test_split
        )
        self.btn_preview_split.pack(side=tk.RIGHT, padx=6)
        self.test_split_active = True

        # Canvas para mostrar el test procesado
        self.test_canvas = tk.Canvas(parent, bg="#181b21", highlightthickness=0)
        self.test_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def _switch_test_chart(self, chart_type):
        self.current_test_type = chart_type
        if chart_type == "snellen":
            self.test_img_raw = OptometryChartGenerator.generate_snellen_text_chart(800, 520)
        else:
            self.test_img_raw = OptometryChartGenerator.generate_astigmatism_dial(800, 520)
        self._refresh_test_preview()

    def _toggle_test_split(self):
        self.test_split_active = not self.test_split_active
        self._refresh_test_preview()

    def _refresh_test_preview(self):
        if self.test_img_raw is None:
            return

        params = self.get_current_params()
        # Aplicar corrección al test
        processed = self.corrector.process_frame(
            self.test_img_raw,
            myopia_intensity=params["myopia_intensity"],
            myopia_radius=params["myopia_radius"],
            astigmatism_cyl=params["astigmatism_cyl"],
            astigmatism_axis=params["astigmatism_axis"],
            stroke_thickness=params["stroke_thickness"],
            clahe_strength=params["clahe_strength"],
            blue_light_filter=params["blue_light_filter"],
            zoom_factor=1.0  # en el test no forzamos zoom para evaluar tamaño real
        )

        h, w = self.test_img_raw.shape[:2]
        if self.test_split_active:
            mid = w // 2
            display_img = np.hstack([self.test_img_raw[:, :mid], processed[:, mid:]])
            cv2.line(display_img, (mid, 0), (mid, h), (0, 0, 255), 2)
            cv2.putText(display_img, "ORIGINAL (Sin procesar)", (20, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 200), 2, cv2.LINE_AA)
            cv2.putText(display_img, "CON CORRECCION OPTICA", (mid + 20, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 150, 0), 2, cv2.LINE_AA)
        else:
            display_img = processed

        # Renderizar en canvas
        rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        self._test_photo = ImageTk.PhotoImage(image=pil_img)
        self.test_canvas.delete("all")
        self.test_canvas.create_image(10, 10, image=self._test_photo, anchor=tk.NW)

    def _build_guide_tab(self, parent):
        box = tk.Frame(parent, bg="#181b21", bd=1, relief=tk.SOLID)
        box.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        guide_text = """
👓 GUÍA DE CALIBRACIÓN ÓPTICA PERSONALIZADA

Si tienes tu receta de optometría / oftalmología a mano, puedes usarla como guía:

1. ESFERA (SPH) -> Miopía:
   • Los números negativos (ej. -1.50, -2.75) corresponden a la miopía.
   • En Miop, a mayor miopía, aumenta la 'Intensidad de Enfoque' y el 'Radio de Frecuencia'.
   • Si sientes que las letras pequeñas en tu editor o navegador se desvanecen, activa 'Engrosar Trazos / Letras Finas'.

2. CILINDRO (CYL) -> Astigmatismo:
   • Si tu receta dice Cilindro -0.75 o -1.50, ajusta el slider de 'Cilindro'.
   • El astigmatismo hace que las letras se vean dobles o estiradas en una dirección (ej. ver la letra 'o' como óvalo).

3. EJE (AXIS) -> Grados de 0° a 180°:
   • Si tu receta dice Eje 90°, coloca el slider de 'Eje' en 90° (Vertical).
   • Si dice 180°, colócalo en 0° / 180° (Horizontal).
   • Para autocalibrar sin receta: ve a la pestaña 'Test de Calibración en Vivo', selecciona el 'Reloj de Astigmatismo' y rota el eje hasta que todas las líneas radiales se vean con la misma intensidad y nitidez.

4. ¿CÓMO USAR LA LUPA FLOTANTE (HUD) CON OTRAS APPS?
   • Pulsa el botón azul 'ABRIR LUPA FLOTANTE (HUD)'.
   • Aparecerá una ventana que puedes colocar encima de VS Code, Chrome, PDFs o cualquier juego/app.
   • La lupa capturará y procesará en tiempo real exactamente lo que hay detrás con tus ajustes ópticos.
   • Puedes presionar la tecla ESPACIO en cualquier momento para congelar la imagen y leer sin esfuerzo.
"""
        lbl = tk.Label(
            box,
            text=guide_text,
            fg="#e2e8f0",
            bg="#181b21",
            justify=tk.LEFT,
            font=("Segoe UI", 9),
            padx=20,
            pady=15
        )
        lbl.pack(anchor="nw", fill=tk.BOTH, expand=True)

    def _build_footer(self):
        footer = tk.Frame(self.root, bg="#13161c", height=32)
        footer.pack(side=tk.BOTTOM, fill=tk.X)

        lbl = tk.Label(
            footer,
            text="Miop Engine v1.0 • Acelerado por OpenCV & NumPy • Diseñado para Accesibilidad Visual",
            fg="#64748b",
            bg="#13161c",
            font=("Segoe UI", 8)
        )
        lbl.pack(side=tk.LEFT, padx=15, pady=6)

    def _on_param_change(self):
        self._draw_astigmatism_dial()
        if self.notebook.index(self.notebook.select()) == 1:
            self._refresh_test_preview()

    def get_current_params(self):
        return {
            "myopia_intensity": float(self.var_myopia_int.get()),
            "myopia_radius": float(self.var_myopia_rad.get()),
            "astigmatism_cyl": float(self.var_astig_cyl.get()),
            "astigmatism_axis": float(self.var_astig_axis.get()),
            "stroke_thickness": float(self.var_stroke.get()),
            "clahe_strength": float(self.var_clahe.get()),
            "blue_light_filter": float(self.var_blue_light.get()),
            "zoom_factor": float(self.var_zoom.get())
        }

    def apply_preset(self, name):
        preset = DEFAULT_PRESETS.get(name)
        if not preset:
            return
        self.var_myopia_int.set(preset.get("myopia_intensity", 1.0))
        self.var_myopia_rad.set(preset.get("myopia_radius", 1.2))
        self.var_astig_cyl.set(preset.get("astigmatism_cyl", 0.0))
        self.var_astig_axis.set(preset.get("astigmatism_axis", 90.0))
        self.var_stroke.set(preset.get("stroke_thickness", 0.5))
        self.var_clahe.set(preset.get("clahe_strength", 0.3))
        self.var_blue_light.set(preset.get("blue_light_filter", 0.2))
        self.var_zoom.set(preset.get("zoom_factor", 1.0))
        self._refresh_test_preview()

    def save_current_profile(self):
        params = self.get_current_params()
        self.config_data["current"] = params
        if ConfigManager.save_config(self.config_data):
            messagebox.showinfo("Perfil Guardado", "Tu calibración visual ha sido guardada exitosamente y se cargará automáticamente al iniciar.")
        else:
            messagebox.showerror("Error", "No se pudo guardar la configuración.")

    def toggle_lens_window(self):
        if self.lens_win is None or not self.lens_win.winfo_exists():
            self.lens_win = FloatingLensWindow(
                self.root,
                self.corrector,
                self.capturer,
                self.get_current_params
            )
            self.btn_open_lens.config(text="🔍 LUPA HUD ACTIVA (Cerrar)", bg="#dc2626")
        else:
            self.lens_win.on_close()
            self.lens_win = None
            self.btn_open_lens.config(text="🔍 ABRIR LUPA FLOTANTE (HUD)", bg="#2563eb")


def main():
    root = tk.Tk()
    app = MiopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
