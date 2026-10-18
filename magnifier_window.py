"""
Miop Magnifier - Ventana Principal de Lectura Fluida para -5.5 D
Ampliación limpia a 30-40 FPS con exclusión de captura y control por rueda de ratón.
"""

import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk
import cv2
import numpy as np
from PIL import Image, ImageTk

from screen_capture import ScreenCapturer
from magnifier_core import CleanMagnifier


class MagnifierWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Miop - Lupa de Lectura Nítida (Sin Gafas)")
        self.geometry("640x480+180+140")
        self.minsize(320, 220)
        self.configure(bg="#121316")
        self.attributes("-topmost", True)

        # Motores
        self.capturer = ScreenCapturer()
        self.core = CleanMagnifier()

        # Parámetros de magnificación
        self.zoom_level = 2.5
        self.follow_mouse = False
        self.is_frozen = False
        self.frozen_frame = None
        self.high_contrast = False
        self.invert_colors = False
        self.running = True
        self._photo = None

        # Excluir de la captura nativa de Windows (WDA_EXCLUDEFROMCAPTURE)
        self._apply_display_affinity()

        # Construir Interfaz
        self._build_ui()

        # Atajos de teclado y ratón
        self.bind("<space>", lambda e: self.toggle_freeze())
        self.bind("<plus>", lambda e: self.adjust_zoom(0.25))
        self.bind("<minus>", lambda e: self.adjust_zoom(-0.25))
        self.bind("<KP_Add>", lambda e: self.adjust_zoom(0.25))
        self.bind("<KP_Subtract>", lambda e: self.adjust_zoom(-0.25))
        self.bind("f", lambda e: self.toggle_follow_mouse())
        self.bind("F", lambda e: self.toggle_follow_mouse())
        self.bind("c", lambda e: self.toggle_high_contrast())
        self.bind("C", lambda e: self.toggle_high_contrast())
        self.bind("i", lambda e: self.toggle_invert())
        self.bind("I", lambda e: self.toggle_invert())
        self.bind("<MouseWheel>", self._on_mouse_wheel)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Iniciar bucle de refresco continuo
        self.after(40, self._render_loop)

    def _apply_display_affinity(self):
        try:
            self.update_idletasks()
            hwnd = self.winfo_id()
            WDA_EXCLUDEFROMCAPTURE = 0x00000011
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        except Exception:
            pass

    def _build_ui(self):
        # Barra superior con controles intuitivos
        self.toolbar = tk.Frame(self, bg="#1a1d24", height=38)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        # Indicador de Zoom actual
        self.lbl_zoom = tk.Label(
            self.toolbar,
            text=f"🔍 {self.zoom_level:.1f}x",
            fg="#60a5fa",
            bg="#1a1d24",
            font=("Segoe UI", 11, "bold")
        )
        self.lbl_zoom.pack(side=tk.LEFT, padx=(12, 6))

        # Botones de ajuste de zoom rápido
        btn_zoom_out = tk.Button(
            self.toolbar,
            text="➖",
            bg="#262a33",
            fg="#e2e8f0",
            activebackground="#333844",
            relief=tk.FLAT,
            font=("Segoe UI", 9),
            padx=4,
            command=lambda: self.adjust_zoom(-0.25)
        )
        btn_zoom_out.pack(side=tk.LEFT, padx=2)

        btn_zoom_in = tk.Button(
            self.toolbar,
            text="➕",
            bg="#262a33",
            fg="#e2e8f0",
            activebackground="#333844",
            relief=tk.FLAT,
            font=("Segoe UI", 9),
            padx=4,
            command=lambda: self.adjust_zoom(0.25)
        )
        btn_zoom_in.pack(side=tk.LEFT, padx=(2, 10))

        # Presets rápidos de 2x y 3x
        for z in [2.0, 2.5, 3.0, 3.5]:
            b = tk.Button(
                self.toolbar,
                text=f"{z}x",
                bg="#262a33",
                fg="#94a3b8",
                activebackground="#2563eb",
                activeforeground="#ffffff",
                relief=tk.FLAT,
                font=("Segoe UI", 8, "bold"),
                padx=5,
                command=lambda val=z: self.set_zoom(val)
            )
            b.pack(side=tk.LEFT, padx=2)

        # Botón Congelar
        self.btn_freeze = tk.Button(
            self.toolbar,
            text="❚❚ Pausar (Espacio)",
            bg="#262a33",
            fg="#e2e8f0",
            activebackground="#b45309",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 8),
            padx=8,
            command=self.toggle_freeze
        )
        self.btn_freeze.pack(side=tk.LEFT, padx=(10, 4))

        # Botón Seguir Ratón
        self.btn_follow = tk.Button(
            self.toolbar,
            text="🖱 Seguir: OFF",
            bg="#262a33",
            fg="#e2e8f0",
            activebackground="#059669",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 8),
            padx=8,
            command=self.toggle_follow_mouse
        )
        self.btn_follow.pack(side=tk.LEFT, padx=4)

        # Botón Alto Contraste
        self.btn_contrast = tk.Button(
            self.toolbar,
            text="◐ Contraste",
            bg="#262a33",
            fg="#e2e8f0",
            activebackground="#4f46e5",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 8),
            padx=8,
            command=self.toggle_high_contrast
        )
        self.btn_contrast.pack(side=tk.LEFT, padx=4)

        # Estado en vivo a la derecha
        self.lbl_status = tk.Label(
            self.toolbar,
            text="● EN VIVO",
            fg="#10b981",
            bg="#1a1d24",
            font=("Segoe UI", 8, "bold")
        )
        self.lbl_status.pack(side=tk.RIGHT, padx=12)

        # Canvas para el contenido ampliado
        self.canvas = tk.Canvas(self, bg="#0d0e11", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Permitir arrastrar la ventana fácilmente
        self.toolbar.bind("<ButtonPress-1>", self._start_drag)
        self.toolbar.bind("<B1-Motion>", self._do_drag)
        self.canvas.bind("<ButtonPress-3>", lambda e: self.toggle_freeze())  # Clic derecho = pausar

    def _start_drag(self, event):
        self._drag_start_x = event.x_root - self.winfo_x()
        self._drag_start_y = event.y_root - self.winfo_y()

    def _do_drag(self, event):
        if not self.follow_mouse:
            x = event.x_root - self._drag_start_x
            y = event.y_root - self._drag_start_y
            self.geometry(f"+{x}+{y}")

    def _on_mouse_wheel(self, event):
        # Girar rueda hacia arriba = más zoom; hacia abajo = menos zoom
        if event.delta > 0:
            self.adjust_zoom(0.25)
        else:
            self.adjust_zoom(-0.25)

    def set_zoom(self, value: float):
        self.zoom_level = max(1.25, min(4.5, round(value, 2)))
        self.lbl_zoom.config(text=f"🔍 {self.zoom_level:.1f}x")

    def adjust_zoom(self, delta: float):
        self.set_zoom(self.zoom_level + delta)

    def toggle_freeze(self):
        self.is_frozen = not self.is_frozen
        if self.is_frozen:
            self.lbl_status.config(text="❚❚ PAUSADO", fg="#f59e0b")
            self.btn_freeze.config(text="▶ Reanudar", bg="#b45309", fg="#ffffff")
        else:
            self.lbl_status.config(text="● EN VIVO", fg="#10b981")
            self.btn_freeze.config(text="❚❚ Pausar (Espacio)", bg="#262a33", fg="#e2e8f0")

    def toggle_follow_mouse(self):
        self.follow_mouse = not self.follow_mouse
        if self.follow_mouse:
            self.btn_follow.config(text="🖱 Seguir: ON", bg="#10b981", fg="#ffffff")
        else:
            self.btn_follow.config(text="🖱 Seguir: OFF", bg="#262a33", fg="#e2e8f0")

    def toggle_high_contrast(self):
        self.high_contrast = not self.high_contrast
        if self.high_contrast:
            self.btn_contrast.config(bg="#4f46e5", fg="#ffffff")
        else:
            self.btn_contrast.config(bg="#262a33", fg="#e2e8f0")

    def toggle_invert(self):
        self.invert_colors = not self.invert_colors

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
                        cap_y = self.winfo_rooty() + self.toolbar.winfo_height()

                    raw_img = self.capturer.capture_region(cap_x, cap_y, cw, ch)
                    if raw_img.shape[0] != ch or raw_img.shape[1] != cw:
                        raw_img = cv2.resize(raw_img, (cw, ch), interpolation=cv2.INTER_NEAREST)

                    if self.is_frozen:
                        self.frozen_frame = raw_img.copy()
                else:
                    raw_img = self.frozen_frame.copy()

                # Procesar ampliación limpia y nítida
                magnified = self.core.process(
                    raw_img,
                    zoom_factor=self.zoom_level,
                    high_contrast=self.high_contrast,
                    invert_colors=self.invert_colors,
                    crisp_text=True
                )

                # Renderizar en Tkinter
                rgb = cv2.cvtColor(magnified, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb)
                self._photo = ImageTk.PhotoImage(image=pil_img)

                self.canvas.delete("all")
                self.canvas.create_image(0, 0, image=self._photo, anchor=tk.NW)

        except Exception:
            pass

        if self.running:
            self.after(30, self._render_loop)

    def on_close(self):
        self.running = False
        try:
            self.capturer.close()
        except Exception:
            pass
        self.destroy()


def main():
    app = MagnifierWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
