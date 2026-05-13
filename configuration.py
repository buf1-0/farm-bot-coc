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
    REGION_ORO: tuple = (1585, 45, 230, 35)
    REGION_ELIXIR: tuple = (1590, 145, 230, 35)

    # ROI del terreno de juego, en fracción de (ancho, alto) de pantalla.
    # Ajusta estos valores mirando tu emulador con una regla visual:
    #   x_min excluye el chat/botones izquierdos
    #   y_min excluye la barra superior de recursos
    #   x_max excluye la columna derecha (Tienda, Clan Castle, etc.)
    #   y_max excluye la barra inferior de tropas
    GAME_ROI: tuple = (0.02, 0.06, 0.83, 0.87)

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

    AUTO_UPGRADE_WALLS: bool = True  # Necesitas constructor libre

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