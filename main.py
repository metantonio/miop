"""
Miop - Suite de Visión Óptica & Campo de Luz 4D
Punto de entrada principal.
"""

from lightfield_gui import HardwareOpticalSuite


def main():
    app = HardwareOpticalSuite()
    app.mainloop()


if __name__ == "__main__":
    main()
