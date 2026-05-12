from dataclasses import dataclass, field
from typing import List

@dataclass
class Configuration:
    # --- RUTAS ---
    RUTA_TESSERACT: str = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    RUTA_IMG: str = 'img/'

    # --- ZONA OCR (Porcentaje Batalla) ---
    REGION_PORCENTAJE: tuple = (1780, 825, 110, 50)

    # --- ZONA OCR (Recursos en la Aldea) ---
    REGION_ORO: tuple = (1590, 45, 220, 30)
    REGION_ELIXIR: tuple = (1595, 145, 220, 35)

    # Cantidad mínima para empezar a gastar en muros
    LIMITE_ORO: int = 28000000
    LIMITE_ELIXIR: int = 28000000

    LIMITE_REALISTA: int = 29000000 #

    # --- Tiempos ---
    TIEMPO_BATALLA: int = 20

    # --- OPCIONES ---
    NUM_TROPAS: int = 42
    NUM_HECHIZOS: int = 11
    NUM_HEROES: int = 4
    X_SIEGE_MACHINE: bool = True

    AUTO_UPGRADE_WALLS: bool = False  # Necesitas constructor libre

    # --- Teclas Fijas ---
    KEY_ATACAR: str = '1'
    KEY_MODO_NORMAL: str = '2'
    KEY_BUSCAR: str = '3'
    KEY_RENDIRSE: str = '4'
    KEY_CONFIRMAR: str = '5'
    KEY_VOLVER: str = '6'

    KEY_UNZOOM: str = 'f3'
    KEY_TROPAS: str = 'a'

    # --- NUEVA TECLA PARA MUROS ---
    KEY_MEJORAR_ORO: str = '7'
    KEY_MEJORAR_ELIXIR: str = '8'

    # --- LISTA DE MUROS (Fotos tomadas con ZOOM ALEJADO) ---
    LISTA_MUROS: List[str] = field(default_factory=lambda: [
        'muro_13.png', 'muro_14.png', 'muro_15.png',
        'muro_16.png', 'muro_17.png'#, 'muro_18.png'
    ])

    # --- Teclas Variables ---
    KEY_SIEGE_MACHINE: str = field(init=False)
    KEY_HECHIZOS: str = field(init=False)
    KEYS_HEROES: List[str] = field(init=False)

    def __post_init__(self):
        fila_teclas = ['s', 'd', 'f', 'g', 'h', 'j']
        idx = 0
        if self.X_SIEGE_MACHINE:
            self.KEY_SIEGE_MACHINE = fila_teclas[idx]
            idx += 1
        else:
            self.KEY_SIEGE_MACHINE = None
        self.KEYS_HEROES = fila_teclas[idx : idx + self.NUM_HEROES]
        idx += self.NUM_HEROES
        self.KEY_HECHIZOS = fila_teclas[idx]