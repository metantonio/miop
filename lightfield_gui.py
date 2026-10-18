"""
Miop - Suite de Visión sin Gafas con Soporte de Hardware Óptico
Permite calibrar y renderizar para:
 1. Máscara de Micro-Agujeros (Impresa sobre pantalla)
 2. Lámina Lenticular
 3. Gafas Estenopeicas (Físicas frente a los ojos)
 4. Lupa de Lectura de Alta Resolución
"""

import os
import subprocess
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk

from screen_capture import ScreenCapturer
from lightfield_core import OpticalHardwareSynthesizer
from magnifier_core import CleanMagnifier
from generate_pinhole_mask import generate_pinhole_mask_svg


class HardwareOpticalSuite(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Miop - Suite Óptica de Campo de Luz & Gafas Estenopeicas")
        self.geometry("900x740+140+70")
        self.minsize(820, 650)
        self.configure(bg="#0f1115")

        # Motores
        self.capturer = ScreenCapturer()
        self.lf_synth = OpticalHardwareSynthesizer()
        self.clean_mag = CleanMagnifier()

        # Variables reactivas
        self.hardware_mode = tk.StringVar(value="pinhole_barrier")  # 'pinhole_barrier', 'lenticular', 'pinhole_glasses', 'pure_magnifier'
        
        # Parámetros Ópticos
        self.var_diopters = tk.DoubleVar(value=-5.5)
        self.var_astig_cyl = tk.DoubleVar(value=0.8)
        self.var_astig_axis = tk.DoubleVar(value=90.0)
        self.var_eye_dist = tk.DoubleVar(value=50.0)      # cm
        self.var_spacer = tk.DoubleVar(value=2.0)         # mm
        self.var_pitch = tk.DoubleVar(value=4.0)          # px

        # Parámetros Lenticulares
        self.var_lpi = tk.DoubleVar(value=60.0)
        self.var_slant = tk.DoubleVar(value=0.0)

        # Parámetros Gafas Estenopeicas
        self.var_glasses_boost = tk.DoubleVar(value=1.5)
        self.var_anti_screendoor = tk.BooleanVar(value=True)
        self.var_polarize = tk.BooleanVar(value=True)

        # Parámetros Lupa
        self.var_zoom = tk.DoubleVar(value=2.5)

        # Estado ventana HUD
        self.lens_window = None
        self._test_photo = None
        self.test_img = self._create_test_pattern()

        # UI
        self._setup_styles()
        self._build_header()
        self._build_mode_selector()
        self._build_dynamic_controls()
        self._build_preview_area()
        self._build_footer()

        # Refrescar preview inicial
        self.after(100, self._refresh_preview)

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#0f1115")
        style.configure("Card.TFrame", background="#181b21")

    def _create_test_pattern(self) -> np.ndarray:
        """Crea un patrón de prueba con texto fino de código y caracteres de oftalmología."""
        img = np.full((320, 720, 3), 24, dtype=np.uint8)
        # Título
        cv2.putText(img, "PATRON DE PRUEBA OPTICO (5.5 D & ASTIGMATISMO)", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (74, 222, 128), 2, cv2.LINE_AA)
        cv2.line(img, (20, 48), (700, 48), (60, 60, 60), 1)

        # Líneas de texto fino
        lines = [
            "E F P T O Z L P E D P E C F D",
            "const lightfield = synthesize_4d_rays(diopters=-5.5, cylinder=0.8);",
            "for (int i = 0; i < retina_cones; ++i) { focus_fovea(x[i], y[i]); }",
            "Simbolos finos: { } [ ] ( ) ; : . -> => | & ! @ # $ % ^ *",
            "Elige tu modo fisico arriba: Lamina de agujeros, Lenticular o Gafas Estenopeicas"
        ]
        y = 85
        scales = [0.8, 0.52, 0.48, 0.46, 0.42]
        colors = [(240, 240, 240), (96, 165, 250), (220, 220, 220), (251, 191, 36), (148, 163, 184)]

        for text, sc, col in zip(lines, scales, colors):
            cv2.putText(img, text, (25, y), cv2.FONT_HERSHEY_SIMPLEX, sc, col, 1, cv2.LINE_AA)
            y += 44

        return img

    def _build_header(self):
        top = tk.Frame(self, bg="#13161c", height=65)
        top.pack(side=tk.TOP, fill=tk.X)

        box = tk.Frame(top, bg="#13161c")
        box.pack(side=tk.LEFT, padx=20, pady=10)

        tk.Label(box, text="👓 Miop Optical Suite", fg="#60a5fa", bg="#13161c", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        tk.Label(box, text="Campo de Luz 4D, Láminas Ópticas & Optimizador de Gafas Estenopeicas", fg="#94a3b8", bg="#13161c", font=("Segoe UI", 8)).pack(anchor="w")

        # Botón para lanzar la Lupa HUD en vivo sobre cualquier app
        self.btn_hud = tk.Button(
            top,
            text="🔍 ABRIR LENTE FLOTANTE (HUD)",
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=14,
            pady=8,
            command=self.toggle_lens_hud
        )
        self.btn_hud.pack(side=tk.RIGHT, padx=20, pady=12)

    def _build_mode_selector(self):
        frame = tk.Frame(self, bg="#181b21", bd=1, relief=tk.SOLID)
        frame.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(12, 6))

        tk.Label(frame, text="SELECCIONA TU TIPO DE HARDWARE FISICO:", fg="#38bdf8", bg="#181b21", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(8, 4))

        modes_box = tk.Frame(frame, bg="#181b21")
        modes_box.pack(fill=tk.X, padx=10, pady=(0, 8))

        modes = [
            ("pinhole_barrier", "1. Lámina de Micro-Agujeros (Pantalla)", "#2563eb"),
            ("lenticular", "2. Lámina Lenticular (Pantalla 3D)", "#7c3aed"),
            ("pinhole_glasses", "3. Gafas Estenopeicas (Físicas)", "#059669"),
            ("pure_magnifier", "4. Lupa Digital Directa (Zoom)", "#d97706")
        ]

        for val, label, active_color in modes:
            rb = tk.Radiobutton(
                modes_box,
                text=label,
                value=val,
                variable=self.hardware_mode,
                fg="#e2e8f0",
                bg="#181b21",
                activebackground="#181b21",
                activeforeground="#60a5fa",
                selectcolor="#0f1115",
                font=("Segoe UI", 9, "bold"),
                command=self._on_mode_change
            )
            rb.pack(side=tk.LEFT, padx=10, pady=4)

    def _build_dynamic_controls(self):
        self.controls_container = tk.Frame(self, bg="#181b21", bd=1, relief=tk.SOLID)
        self.controls_container.pack(side=tk.TOP, fill=tk.X, padx=15, pady=6)
        self._render_current_mode_controls()

    def _on_mode_change(self):
        self._render_current_mode_controls()
        self._refresh_preview()

    def _render_current_mode_controls(self):
        # Limpiar contenedor de controles dinámicos
        for widget in self.controls_container.winfo_children():
            widget.destroy()

        mode = self.hardware_mode.get()

        if mode == "pinhole_barrier":
            self._build_pinhole_barrier_ui()
        elif mode == "lenticular":
            self._build_lenticular_ui()
        elif mode == "pinhole_glasses":
            self._build_pinhole_glasses_ui()
        else:
            self._build_magnifier_ui()

    def _build_pinhole_barrier_ui(self):
        header = tk.Frame(self.controls_container, bg="#181b21")
        header.pack(fill=tk.X, padx=12, pady=(8, 4))
        tk.Label(header, text="⚙ PARÁMETROS DEL CAMPO DE LUZ (LÁMINA CON MICRO-AGUJEROS)", fg="#60a5fa", bg="#181b21", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)

        btn_svg = tk.Button(
            header,
            text="📥 Generar Archivo SVG para Imprimir Lámina",
            bg="#0284c7",
            fg="#ffffff",
            activebackground="#0369a1",
            relief=tk.FLAT,
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=3,
            command=self._generate_and_open_svg
        )
        btn_svg.pack(side=tk.RIGHT)

        grid = tk.Frame(self.controls_container, bg="#181b21")
        grid.pack(fill=tk.X, padx=12, pady=(0, 10))

        # Fila 1: Dioptrías y Distancia ojo
        f1 = tk.Frame(grid, bg="#181b21")
        f1.pack(fill=tk.X, pady=2)
        self._add_slider(f1, "Miopía (Dioptrías):", self.var_diopters, -8.0, -1.0, 0.25, " D")
        self._add_slider(f1, "Distancia Ojo-Pantalla:", self.var_eye_dist, 30.0, 80.0, 5.0, " cm")

        # Fila 2: Separador acrílico y Pitch de la lámina
        f2 = tk.Frame(grid, bg="#181b21")
        f2.pack(fill=tk.X, pady=2)
        self._add_slider(f2, "Espaciador Acrílico (Spacer):", self.var_spacer, 0.5, 4.0, 0.1, " mm")
        self._add_slider(f2, "Separación Agujeros (Pitch):", self.var_pitch, 2.0, 8.0, 0.5, " px")

        # Fila 3: Astigmatismo
        f3 = tk.Frame(grid, bg="#181b21")
        f3.pack(fill=tk.X, pady=2)
        self._add_slider(f3, "Astigmatismo (Cilindro):", self.var_astig_cyl, 0.0, 3.0, 0.25, " D")
        self._add_slider(f3, "Eje del Astigmatismo:", self.var_astig_axis, 0.0, 180.0, 5.0, "°")

    def _build_lenticular_ui(self):
        tk.Label(self.controls_container, text="⚙ PARÁMETROS PARA LÁMINA LENTICULAR (MICRO-LENTES CILÍNDRICAS)", fg="#a78bfa", bg="#181b21", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(8, 4))
        grid = tk.Frame(self.controls_container, bg="#181b21")
        grid.pack(fill=tk.X, padx=12, pady=(0, 10))

        f1 = tk.Frame(grid, bg="#181b21")
        f1.pack(fill=tk.X, pady=2)
        self._add_slider(f1, "Líneas por Pulgada (LPI):", self.var_lpi, 40.0, 100.0, 10.0, " LPI")
        self._add_slider(f1, "Ángulo Inclinación (Slant):", self.var_slant, 0.0, 15.0, 0.5, "°")

        f2 = tk.Frame(grid, bg="#181b21")
        f2.pack(fill=tk.X, pady=2)
        self._add_slider(f2, "Miopía a Compensar:", self.var_diopters, -8.0, -1.0, 0.25, " D")

    def _build_pinhole_glasses_ui(self):
        tk.Label(self.controls_container, text="⚙ OPTIMIZADOR PARA GAFAS ESTENOPEICAS FÍSICAS (EN TUS OJOS)", fg="#34d399", bg="#181b21", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(8, 4))
        grid = tk.Frame(self.controls_container, bg="#181b21")
        grid.pack(fill=tk.X, padx=12, pady=(0, 10))

        f1 = tk.Frame(grid, bg="#181b21")
        f1.pack(fill=tk.X, pady=4)
        self._add_slider(f1, "Impulso de Luminancia (Compensa la pérdida de luz):", self.var_glasses_boost, 1.0, 2.2, 0.1, "x")

        f2 = tk.Frame(grid, bg="#181b21")
        f2.pack(fill=tk.X, pady=4)

        cb1 = tk.Checkbutton(
            f2,
            text="Filtro Anti-Rejilla (Anti-Screen-Door: engrosa trazos para no caer en agujeros ciegos)",
            variable=self.var_anti_screendoor,
            fg="#e2e8f0",
            bg="#181b21",
            selectcolor="#0f1115",
            font=("Segoe UI", 9),
            command=self._refresh_preview
        )
        cb1.pack(side=tk.LEFT, padx=10)

        cb2 = tk.Checkbutton(
            f2,
            text="Alto Contraste Polarizado (Elimina halos de difracción)",
            variable=self.var_polarize,
            fg="#e2e8f0",
            bg="#181b21",
            selectcolor="#0f1115",
            font=("Segoe UI", 9),
            command=self._refresh_preview
        )
        cb2.pack(side=tk.LEFT, padx=10)

    def _build_magnifier_ui(self):
        tk.Label(self.controls_container, text="⚙ PARÁMETROS DE LUPA DIGITAL DIRECTA (SIN HARDWARE)", fg="#fbbf24", bg="#181b21", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(8, 4))
        grid = tk.Frame(self.controls_container, bg="#181b21")
        grid.pack(fill=tk.X, padx=12, pady=(0, 10))

        f1 = tk.Frame(grid, bg="#181b21")
        f1.pack(fill=tk.X, pady=4)
        self._add_slider(f1, "Nivel de Zoom Óptico:", self.var_zoom, 1.25, 4.5, 0.25, "x")

    def _add_slider(self, parent, label, var, from_, to, res, unit):
        box = tk.Frame(parent, bg="#181b21")
        box.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

        lbl_line = tk.Frame(box, bg="#181b21")
        lbl_line.pack(fill=tk.X)
        tk.Label(lbl_line, text=label, fg="#cbd5e1", bg="#181b21", font=("Segoe UI", 8)).pack(side=tk.LEFT)
        val_lbl = tk.Label(lbl_line, text=f"{var.get():.2f}{unit}", fg="#38bdf8", bg="#181b21", font=("Segoe UI", 8, "bold"))
        val_lbl.pack(side=tk.RIGHT)

        def on_slide(val):
            val_lbl.config(text=f"{float(val):.2f}{unit}")
            self._refresh_preview()

        scale = tk.Scale(
            box,
            from_=from_,
            to=to,
            resolution=res,
            orient=tk.HORIZONTAL,
            variable=var,
            showvalue=0,
            bg="#181b21",
            troughcolor="#0d0e11",
            activebackground="#38bdf8",
            highlightthickness=0,
            bd=0,
            command=on_slide
        )
        scale.pack(fill=tk.X, pady=(1, 3))

    def _build_preview_area(self):
        container = tk.Frame(self, bg="#0f1115")
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=6)

        header = tk.Frame(container, bg="#0f1115")
        header.pack(fill=tk.X, pady=(0, 4))
        tk.Label(header, text="VISTA PREVIA DEL RENDERIZADOR:", fg="#94a3b8", bg="#0f1115", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)

        self.canvas_preview = tk.Canvas(container, bg="#121418", highlightthickness=1, highlightbackground="#272b34")
        self.canvas_preview.pack(fill=tk.BOTH, expand=True)

    def _build_footer(self):
        foot = tk.Frame(self, bg="#13161c", height=30)
        foot.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Label(
            foot,
            text="Miop Hardware Engine • Diseñado para -5.5 D & Astigmatismo • Presiona 'ABRIR LENTE FLOTANTE' para usar sobre cualquier app",
            fg="#64748b",
            bg="#13161c",
            font=("Segoe UI", 8)
        ).pack(side=tk.LEFT, padx=15, pady=6)

    def _refresh_preview(self):
        mode = self.hardware_mode.get()
        source = self.test_img.copy()

        if mode == "pinhole_barrier":
            processed = self.lf_synth.process_pinhole_barrier(
                source,
                diopters=self.var_diopters.get(),
                astig_cyl=self.var_astig_cyl.get(),
                astig_axis_deg=self.var_astig_axis.get(),
                eye_distance_cm=self.var_eye_dist.get(),
                spacer_mm=self.var_spacer.get(),
                pitch_pixels=self.var_pitch.get()
            )
        elif mode == "lenticular":
            processed = self.lf_synth.process_lenticular(
                source,
                diopters=self.var_diopters.get(),
                lpi=self.var_lpi.get(),
                screen_dpi=140.0,
                slant_deg=self.var_slant.get()
            )
        elif mode == "pinhole_glasses":
            processed = self.lf_synth.process_pinhole_glasses(
                source,
                boost_luminance=self.var_glasses_boost.get(),
                anti_screen_door=self.var_anti_screendoor.get(),
                high_contrast_polarize=self.var_polarize.get()
            )
        else:
            processed = self.clean_mag.process(
                source,
                zoom_factor=self.var_zoom.get(),
                high_contrast=True,
                crisp_text=True
            )

        # Ajustar a tamaño del canvas si es necesario
        cw = self.canvas_preview.winfo_width()
        ch = self.canvas_preview.winfo_height()
        if cw > 50 and ch > 50:
            pw = min(cw, processed.shape[1])
            ph = min(ch, processed.shape[0])
            display_img = processed[:ph, :pw]
        else:
            display_img = processed

        rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        self._test_photo = ImageTk.PhotoImage(image=pil_img)
        self.canvas_preview.delete("all")
        self.canvas_preview.create_image(10, 10, image=self._test_photo, anchor=tk.NW)

    def _generate_and_open_svg(self):
        svg_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mascara_estenopeica_pantalla.svg")
        generate_pinhole_mask_svg(
            output_path=svg_file,
            width_mm=210.0,
            height_mm=148.0,
            hole_diameter_um=85.0,
            pitch_x_mm=0.45,
            pitch_y_mm=0.45,
            pattern="hexagonal"
        )
        msg = f"Se ha generado la mascara física en formato SVG vectorial:\n\n{svg_file}\n\nPuedes abrirla en el navegador o enviarla a imprimir en acetato transparente a alta resolución (fotomecánica)."
        messagebox.showinfo("Máscara SVG Generada", msg)
        try:
            os.startfile(svg_file)
        except Exception:
            pass

    def toggle_lens_hud(self):
        if self.lens_window is None or not self.lens_window.winfo_exists():
            self.lens_window = FloatingOpticalHUD(self, self._process_current_frame)
            self.btn_hud.config(text="🔍 CERRAR LENTE FLOTANTE", bg="#dc2626")
        else:
            self.lens_window.on_close()
            self.lens_window = None
            self.btn_hud.config(text="🔍 ABRIR LENTE FLOTANTE (HUD)", bg="#2563eb")

    def _process_current_frame(self, frame_bgr: np.ndarray) -> np.ndarray:
        mode = self.hardware_mode.get()
        if mode == "pinhole_barrier":
            return self.lf_synth.process_pinhole_barrier(
                frame_bgr,
                diopters=self.var_diopters.get(),
                astig_cyl=self.var_astig_cyl.get(),
                astig_axis_deg=self.var_astig_axis.get(),
                eye_distance_cm=self.var_eye_dist.get(),
                spacer_mm=self.var_spacer.get(),
                pitch_pixels=self.var_pitch.get()
            )
        elif mode == "lenticular":
            return self.lf_synth.process_lenticular(
                frame_bgr,
                diopters=self.var_diopters.get(),
                lpi=self.var_lpi.get(),
                screen_dpi=140.0,
                slant_deg=self.var_slant.get()
            )
        elif mode == "pinhole_glasses":
            return self.lf_synth.process_pinhole_glasses(
                frame_bgr,
                boost_luminance=self.var_glasses_boost.get(),
                anti_screen_door=self.var_anti_screendoor.get(),
                high_contrast_polarize=self.var_polarize.get()
            )
        else:
            return self.clean_mag.process(
                frame_bgr,
                zoom_factor=self.var_zoom.get(),
                high_contrast=True,
                crisp_text=True
            )


class FloatingOpticalHUD(tk.Toplevel):
    def __init__(self, parent, process_cb):
        super().__init__(parent)
        self.process_frame_cb = process_cb
        self.capturer = ScreenCapturer()

        self.title("Miop - Lente HUD de Campo de Luz")
        self.geometry("560x420+240+180")
        self.attributes("-topmost", True)

        self.is_frozen = False
        self.frozen_frame = None
        self.follow_mouse = False
        self.running = True
        self._photo = None

        # Excluir de la captura en Windows
        try:
            self.update_idletasks()
            hwnd = self.winfo_id()
            WDA_EXCLUDEFROMCAPTURE = 0x00000011
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass

        # Toolbar
        bar = tk.Frame(self, bg="#1a1d24", height=34)
        bar.pack(side=tk.TOP, fill=tk.X)

        self.lbl_status = tk.Label(bar, text="● EN VIVO", fg="#10b981", bg="#1a1d24", font=("Segoe UI", 9, "bold"))
        self.lbl_status.pack(side=tk.LEFT, padx=10)

        self.btn_frz = tk.Button(bar, text="❚❚ Pausar (Espacio)", bg="#262a33", fg="#e2e8f0", relief=tk.FLAT, font=("Segoe UI", 8), command=self.toggle_freeze, padx=6)
        self.btn_frz.pack(side=tk.LEFT, padx=4)

        self.btn_flw = tk.Button(bar, text="🖱 Seguir Ratón: OFF", bg="#262a33", fg="#e2e8f0", relief=tk.FLAT, font=("Segoe UI", 8), command=self.toggle_follow, padx=6)
        self.btn_flw.pack(side=tk.LEFT, padx=4)

        self.canvas = tk.Canvas(self, bg="#0d0e11", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.bind("<space>", lambda e: self.toggle_freeze())
        bar.bind("<ButtonPress-1>", self._start_drag)
        bar.bind("<B1-Motion>", self._do_drag)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(35, self._render_loop)

    def _start_drag(self, event):
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _do_drag(self, event):
        if not self.follow_mouse:
            self.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def toggle_freeze(self):
        self.is_frozen = not self.is_frozen
        if self.is_frozen:
            self.lbl_status.config(text="❚❚ PAUSADO", fg="#f59e0b")
            self.btn_frz.config(text="▶ Reanudar", bg="#b45309")
        else:
            self.lbl_status.config(text="● EN VIVO", fg="#10b981")
            self.btn_frz.config(text="❚❚ Pausar (Espacio)", bg="#262a33")

    def toggle_follow(self):
        self.follow_mouse = not self.follow_mouse
        if self.follow_mouse:
            self.btn_flw.config(text="🖱 Seguir Ratón: ON", bg="#10b981", fg="#ffffff")
        else:
            self.btn_flw.config(text="🖱 Seguir Ratón: OFF", bg="#262a33", fg="#e2e8f0")

    def _render_loop(self):
        if not self.running:
            return

        try:
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()

            if cw > 30 and ch > 30:
                if not self.is_frozen or self.frozen_frame is None:
                    if self.follow_mouse:
                        pt = wintypes.POINT()
                        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                        cap_x = pt.x - (cw // 2)
                        cap_y = pt.y - (ch // 2)
                    else:
                        cap_x = self.winfo_rootx()
                        cap_y = self.winfo_rooty() + 34

                    raw = self.capturer.capture_region(cap_x, cap_y, cw, ch)
                    if raw.shape[0] != ch or raw.shape[1] != cw:
                        raw = cv2.resize(raw, (cw, ch), interpolation=cv2.INTER_NEAREST)

                    if self.is_frozen:
                        self.frozen_frame = raw.copy()
                else:
                    raw = self.frozen_frame.copy()

                processed = self.process_frame_cb(raw)
                rgb = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb)
                self._photo = ImageTk.PhotoImage(image=pil_img)

                self.canvas.delete("all")
                self.canvas.create_image(0, 0, image=self._photo, anchor=tk.NW)
        except Exception:
            pass

        if self.running:
            self.after(35, self._render_loop)

    def on_close(self):
        self.running = False
        try:
            self.capturer.close()
        except Exception:
            pass
        self.destroy()


def main():
    app = HardwareOpticalSuite()
    app.mainloop()


if __name__ == "__main__":
    main()
