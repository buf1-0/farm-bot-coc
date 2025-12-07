from dataclasses import dataclass, field
from typing import List

@dataclass
class Configuration:
    # --- RUTAS ---
    RUTA_TESSERACT: str = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    RUTA_IMG: str = 'img/'

    # --- ZONA OCR ---
    REGION_PORCENTAJE: tuple = (1780, 825, 1890, 875)

    # --- Tiempos ---
    TIEMPO_BATALLA: int = 30        # 30s para rendirse ( si no llega antes al 50% )

    # --- Numeros ---
    NUM_TROPAS: int = 40            # NUMERO DE TROPAS EN TU EJERCITO ( ! UTILIZA UNA UNICA TROPA ¡ )
    NUM_HECHIZOS: int = 11          # NUMERO DE HECHIZOS EN TU EJERCITO ( ! UTILIZA UN UNICO HECHIZO ¡ )

    # --- Teclas ---
    KEY_ATACAR: str = '1'
    KEY_MODO_NORMAL: str = '2'
    KEY_BUSCAR: str = '3'

    KEY_RENDIRSE: str = '4'
    KEY_CONFIRMAR: str = '5'
    KEY_VOLVER: str = '6'

    KEY_UNZOOM: str = 'f3'          # Tecla para quitar zoom

    # --- Tropas ---
    KEY_VALQUIRIAS: str = 'a'
    KEY_HECHIZOS: str = 'h'
    KEYS_HEROES: List[str] = field(default_factory=lambda: ['s', 'd', 'f', 'g'])