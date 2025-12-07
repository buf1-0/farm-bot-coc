from dataclasses import dataclass, field
from typing import List

@dataclass
class Configuration:
    # --- OPCIONES ---
    NUM_TROPAS: int = 40
    NUM_HECHIZOS: int = 11
    NUM_HEROES: int = 4
    X_SIEGE_MACHINE: bool = True

    TIEMPO_BATALLA: int = 30  # 30s para rendirse ( si no llega antes al 50% )

    # --- RUTAS ---
    RUTA_TESSERACT: str = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    RUTA_IMG: str = 'img/'

    # --- ZONA OCR ---
    REGION_PORCENTAJE: tuple = (1780, 825, 1890, 875)   # OBLIGATORIO USAR PANTALLA COMPLETA

    # --- Teclas Fijas ---
    KEY_ATACAR: str = '1'
    KEY_MODO_NORMAL: str = '2'
    KEY_BUSCAR: str = '3'

    KEY_RENDIRSE: str = '4'
    KEY_CONFIRMAR: str = '5'
    KEY_VOLVER: str = '6'

    KEY_UNZOOM: str = 'f3'          # Tecla para quitar zoom

    KEY_TROPAS: str = 'a'

    # --- Teclas Variables ---
    KEY_SIEGE_MACHINE: str = field(init=False)  # ⚠ NO TOCAR ⚠
    KEY_HECHIZOS: str = field(init=False)       # ⚠ NO TOCAR ⚠
    KEYS_HEROES: List[str] = field(init=False)  # ⚠ NO TOCAR ⚠

    def __post_init__(self):
        # Fila de teclas disponibles después de la 'A'
        fila_teclas = ['s', 'd', 'f', 'g', 'h', 'j']
        idx = 0  # Índice actual en la fila de teclas

        #1. ¿Hay Máquina de Asedio?
        if self.X_SIEGE_MACHINE:
            self.KEY_SIEGE_MACHINE = fila_teclas[idx] # Se queda con 's'
            idx += 1 # Avanzamos el índice para lo siguiente
        else:
            self.KEY_SIEGE_MACHINE = None # No hay asedio

        # 2. Asignamos Héroes (cogen las siguientes teclas disponibles)
        # Cogemos desde idx hasta idx + num_heroes
        self.KEYS_HEROES = fila_teclas[idx : idx + self.NUM_HEROES]
        idx += self.NUM_HEROES # Avanzamos el índice

        # 3. Asignamos Hechizos (coge la siguiente tecla libre)
        self.KEY_HECHIZOS = fila_teclas[idx]

        # DEBUG
        print(f"⚙️ Configuración dinámica:")
        print(f"   - Tropa: {self.KEY_TROPAS}")
        print(f"   - Máquina de Asedio: {self.KEY_SIEGE_MACHINE}")
        print(f"   - Héroes: {self.KEYS_HEROES}")
        print(f"   - Hechizos: {self.KEY_HECHIZOS}")