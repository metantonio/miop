"""
Miop - Ventana Lupa Flotante HUD (Lente de Corrección Visual)
Superpone la vista procesada sobre cualquier aplicación con exclusión de captura nativa.
"""

import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk
import cv2
import numpy as np
from PIL import Image, ImageTk

from vision_core import VisionCorrector
from screen_capture import ScreenCapturer


class FloatingLensWindow(tk.Toplevel):
    def __init__(self, parent, corrector: VisionCorrector, capturer: ScreenCapturer, get_params_cb):
        super().__init__(parent)
        self.corrector = corrector
        self.capturer = capturer
        self.get_params = get_params_cb

        # Configuración de ventana
        self.title("Miop - Lente HUD")
        self.geometry("480x360+200+200")
        self.minsize(280, 200)
        self.attributes("-topmost", True)

        # Variables de control
        self.is_frozen = False
        self.frozen_frame = None
        self.split_mode = False  # Mitad izquierda original, mitad derecha procesada
        self.follow_mouse = False
        self.running = True
        self._photo_image = None

        # Excluir esta ventana de la captura de pantalla en Windows 10/11
        # 0x00000011 = WDA_EXCLUDEFROMCAPTURE
        self._apply_display_affinity()

        # Construir UI
        self._build_ui()

        # Eventos de teclado y arrastre
        self.bind("<space>", lambda e: self.toggle_freeze())
        self.bind("<Control-s>", lambda e: self.toggle_split())
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Iniciar bucle de refresco continuo
        self.after(50, self._render_loop)

    def _apply_display_affinity(self):
        """Aplica la API de Windows para que la lupa sea invisible a la captura de pantalla."""
        try:
            self.update_idletasks()
            hwnd = self.winfo_id()
            WDA_EXCLUDEFROMCAPTURE = 0x00000011
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass

    def _build_ui(self):
        # Barra superior de control compacta y estilizada
        self.toolbar = tk.Frame(self, bg="#1e2024", height=34)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        # Indicador de estado
        self.lbl_status = tk.Label(
            self.toolbar,
            text="● EN VIVO",
            fg="#4ade80",
            bg="#1e2024",
            font=("Segoe UI", 9, "bold")
        )
        self.lbl_status.pack(side=tk.LEFT, padx=10)

        # Botón Congelar
        self.btn_freeze = tk.Button(
            self.toolbar,
            text="⏸ Congelar (Espacio)",
            bg="#2c3038",
            fg="#e0e0e0",
            activebackground="#3b4252",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 8),
            command=self.toggle_freeze,
            padx=6
        )
        self.btn_freeze.pack(side=tk.LEFT, padx=4)

        # Botón Split (Antes / Después)
        self.btn_split = tk.Button(
            self.toolbar,
            text="⚖ Split (Antes/Desp)",
            bg="#2c3038",
            fg="#e0e0e0",
            activebackground="#3b4252",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 8),
            command=self.toggle_split,
            padx=6
        )
        self.btn_split.pack(side=tk.LEFT, padx=4)

        # Botón Seguir Ratón
        self.btn_follow = tk.Button(
            self.toolbar,
            text="🖱 Seguir Cursor: OFF",
            bg="#2c3038",
            fg="#e0e0e0",
            activebackground="#3b4252",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 8),
            command=self.toggle_follow_mouse,
            padx=6
        )
        self.btn_follow.pack(side=tk.LEFT, padx=4)

        # Canvas principal para renderizado
        self.canvas = tk.Canvas(self, bg="#0d0e11", highlightthickness=0)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Soporte para arrastrar ventana pulsando sobre el canvas o la barra
        self.toolbar.bind("<ButtonPress-1>", self._start_drag)
        self.toolbar.bind("<B1-Motion>", self._do_drag)

    def _start_drag(self, event):
        self._drag_start_x = event.x_root - self.winfo_x()
        self._drag_start_y = event.y_root - self.winfo_y()

    def _do_drag(self, event):
        if not self.follow_mouse:
            x = event.x_root - self._drag_start_x
            y = event.y_root - self._drag_start_y
            self.geometry(f"+{x}+{y}")

    def toggle_freeze(self):
        self.is_frozen = not self.is_frozen
        if self.is_frozen:
            self.lbl_status.config(text="❚❚ CONGELADO", fg="#fbbf24")
            self.btn_freeze.config(text="▶ Reanudar", bg="#b45309")
        else:
            self.lbl_status.config(text="● EN VIVO", fg="#4ade80")
            self.btn_freeze.config(text="⏸ Congelar (Espacio)", bg="#2c3038")

    def toggle_split(self):
        self.split_mode = not self.split_mode
        if self.split_mode:
            self.btn_split.config(bg="#3b82f6", fg="#ffffff")
        else:
            self.btn_split.config(bg="#2c3038", fg="#e0e0e0")

    def toggle_follow_mouse(self):
        self.follow_mouse = not self.follow_mouse
        if self.follow_mouse:
            self.btn_follow.config(text="🖱 Seguir Cursor: ON", bg="#10b981", fg="#ffffff")
        else:
            self.btn_follow.config(text="🖱 Seguir Cursor: OFF", bg="#2c3038", fg="#e0e0e0")

    def _render_loop(self):
        if not self.running:
            return

        try:
            # Obtener parámetros ópticos actuales desde la UI principal
            params = self.get_params()
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()

            if cw > 20 and ch > 20:
                if not self.is_frozen or self.frozen_frame is None:
                    # Determinar posición de captura
                    if self.follow_mouse:
                        pt = wintypes.POINT()
                        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                        # Centrar captura en el cursor
                        cap_x = pt.x - (cw // 2)
                        cap_y = pt.y - (ch // 2)
                    else:
                        # Captura exactamente lo que hay detrás de esta ventana
                        cap_x = self.winfo_rootx()
                        cap_y = self.winfo_rooty() + self.toolbar.winfo_height()

                    raw_img = self.capturer.capture_region(cap_x, cap_y, cw, ch)

                    # Si el tamaño capturado difiere ligeramente, ajustar
                    if raw_img.shape[0] != ch or raw_img.shape[1] != cw:
                        raw_img = cv2.resize(raw_img, (cw, ch), interpolation=cv2.INTER_NEAREST)

                    if self.is_frozen:
                        self.frozen_frame = raw_img.copy()
                else:
                    raw_img = self.frozen_frame.copy()

                # Procesar con el motor óptico
                corrected_img = self.corrector.process_frame(
                    raw_img,
                    myopia_intensity=params.get("myopia_intensity", 1.0),
                    myopia_radius=params.get("myopia_radius", 1.2),
                    astigmatism_cyl=params.get("astigmatism_cyl", 0.0),
                    astigmatism_axis=params.get("astigmatism_axis", 0.0),
                    stroke_thickness=params.get("stroke_thickness", 0.0),
                    clahe_strength=params.get("clahe_strength", 0.0),
                    blue_light_filter=params.get("blue_light_filter", 0.0),
                    zoom_factor=params.get("zoom_factor", 1.0)
                )

                # Si el modo split está activo, fusionar mitad original y mitad corregida
                if self.split_mode:
                    mid = cw // 2
                    final_view = np.hstack([raw_img[:, :mid], corrected_img[:, mid:]])
                    # Línea divisoria
                    cv2.line(final_view, (mid, 0), (mid, ch), (0, 255, 255), 2)
                    # Etiquetas
                    cv2.putText(final_view, "ORIGINAL", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)
                    cv2.putText(final_view, "CORREGIDO", (mid + 15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
                else:
                    final_view = corrected_img

                # Convertir BGR a RGB para Tkinter PhotoImage
                rgb_img = cv2.cvtColor(final_view, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img)
                self._photo_image = ImageTk.PhotoImage(image=pil_img)

                self.canvas.delete("all")
                self.canvas.create_image(0, 0, image=self._photo_image, anchor=tk.NW)

        except Exception as e:
            pass

        # Próximo frame a ~33 FPS (30 ms)
        if self.running:
            self.after(30, self._render_loop)

    def on_close(self):
        self.running = False
        self.destroy()
