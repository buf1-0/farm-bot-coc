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

    LIMITE_ORO: int = 20000000
    LIMITE_ELIXIR: int = 20000000

    # --- RUTAS ---
    RUTA_TESSERACT: str = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    RUTA_IMG: str = 'img/'

    # --- ZONA OCR ---
    REGION_PORCENTAJE: tuple = (1780, 825, 1890, 875)
    REGION_ORO: tuple = (1780, 825, 1890, 875)
    REGION_ELIXIR: tuple = (1780, 825, 1890, 875)

    # --- LISTA DE MUROS (Ordenados por prioridad de mejora) ---
    # El bot buscará primero el 13, si no hay, busca el 14, etc.
    LISTA_MUROS: List[str] = field(default_factory=lambda: [
        'muro_13.png',
        'muro_14.png',
        'muro_15.png',
        'muro_16.png',
        'muro_17.png',
        'muro_18.png'
    ])

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
    KEY_SIEGE_MACHINE: str = field(init=False)
    KEY_HECHIZOS: str = field(init=False)
    KEYS_HEROES: List[str] = field(init=False)

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
        #print(f"⚙️ Configuración dinámica:")
        #print(f"   - Tropa: {self.KEY_TROPAS}")
        #print(f"   - Máquina de Asedio: {self.KEY_SIEGE_MACHINE}")
        #print(f"   - Héroes: {self.KEYS_HEROES}")
        #print(f"   - Hechizos: {self.KEY_HECHIZOS}")