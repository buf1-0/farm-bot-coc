import cv2
import numpy as np
import pyautogui
import json
import os
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class WallDetection:
    center: Tuple[int, int]   # (x, y) pantalla
    level: int                 # 12-19
    area: int                  # px² del blob

    def __lt__(self, other):
        # Nivel más bajo = mayor prioridad de mejora
        return self.level < other.level


class WallDetector:
    """
    Detecta y prioriza muros de CoC por nivel usando segmentación HSV.

    Cada nivel tiene una paleta de color distinta. Al trabajar en espacio
    HSV aplicamos máscaras independientes del fondo (césped, nieve, volcán).

    AJUSTE INICIAL:
        Los rangos DEFAULT funcionan como punto de partida.
        Usa calibrate_walls.py para afinarlos a tu emulador/resolución.
    """

    # ---------------------------------------------------------------
    # Rangos HSV por nivel: [lower_HSV, upper_HSV]
    # OpenCV: H ∈ [0,180]  S ∈ [0,255]  V ∈ [0,255]
    #
    # Si un nivel tiene varios rangos, se hace OR de todos (útil para
    # colores que tienen parte brillante y parte en sombra).
    # ---------------------------------------------------------------
    DEFAULT_HSV_RANGES: Dict[int, List[List]] = {
        12: [  # Obsidian Black — muy oscuro, baja saturación
            [[0,   0,  10], [180, 60,  75]]
        ],
        13: [  # Void Purple — púrpura oscuro
            [[120, 40,  25], [155, 210, 115]]
        ],
        14: [  # Infernal Teal — teal/verde oscuro
            [[78,  55,  25], [105, 230, 125]]
        ],
        15: [  # Gold Crown — dorado brillante
            [[10, 140, 140], [30,  255, 255]],
            [[10,  80,  80], [30,  255, 150]]   # zonas en sombra
        ],
        16: [  # Lava Red — rojo (con wrap en H)
            [[0,   140,  90], [12,  255, 255]],
            [[168, 140,  90], [180, 255, 255]]
        ],
        17: [  # Ice Blue — azul frío brillante
            [[95,  55, 140], [125, 210, 255]]
        ],
        18: [  # Crystal Indigo — azul-índigo
            [[110, 55,  90], [145, 210, 210]]
        ],
        19: [  # Max — blanco/plateado muy brillante
            [[0,   0,  200], [180,  40, 255]],
            [[10,  80, 190], [30,  255, 255]]   # reflejos dorados
        ],
    }

    # Rango de área en px² para un tile de muro isométrico.
    # Validado para 1920x1080 con zoom alejado (3x F3 según tu bot).
    # Ajustar si cambias de resolución o nivel de zoom.
    TILE_AREA_MIN = 200
    TILE_AREA_MAX = 4000

    def __init__(self, config_path: str = 'wall_config.json'):
        self.config_path = config_path
        self.hsv_ranges = self._load_config()

    # ---------------------------------------------------------------
    # Config
    # ---------------------------------------------------------------

    def _load_config(self) -> Dict:
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            # JSON guarda claves como str; normalizamos a int
            result = {int(k): v for k, v in data.items()}
            print(f"✅ Rangos HSV personalizados: {sorted(result.keys())}")
            return result
        print("ℹ️  Usando rangos HSV por defecto. "
              "Ejecuta calibrate_walls.py para afinarlos.")
        return dict(self.DEFAULT_HSV_RANGES)

    def save_config(self):
        serializable = {str(k): v for k, v in self.hsv_ranges.items()}
        with open(self.config_path, 'w') as f:
            json.dump(serializable, f, indent=2)
        print(f"💾 Configuración guardada en '{self.config_path}'")

    # ---------------------------------------------------------------
    # Core pipeline
    # ---------------------------------------------------------------

    def _apply_level_mask(self, img_hsv: np.ndarray, level: int) -> np.ndarray:
        """OR de todos los rangos HSV definidos para ese nivel."""
        ranges = self.hsv_ranges.get(level, [])
        mask = np.zeros(img_hsv.shape[:2], dtype=np.uint8)
        for (lo, hi) in ranges:
            mask |= cv2.inRange(img_hsv, np.array(lo, np.uint8),
                                np.array(hi, np.uint8))
        return mask

    def _blobs_from_mask(
        self, mask: np.ndarray
    ) -> List[Tuple[Tuple[int, int], int]]:
        """
        Operaciones morfológicas + contornos para obtener blobs
        del tamaño de un tile de muro.

        Returns: [(centro_xy, area), ...]
        """
        # Cierre morfológico: une píxeles próximos (tiles adyacentes
        # del mismo nivel forman una línea continua de color)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Erosión ligera para separar tiles pegados
        kernel_sep = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        separated = cv2.erode(closed, kernel_sep, iterations=1)

        contours, _ = cv2.findContours(
            separated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        blobs = []
        for cnt in contours:
            area = int(cv2.contourArea(cnt))
            if not (self.TILE_AREA_MIN <= area <= self.TILE_AREA_MAX):
                continue
            M = cv2.moments(cnt)
            if M["m00"] == 0:
                continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            blobs.append(((cx, cy), area))
        return blobs

    def detect(
        self,
        img_bgr: Optional[np.ndarray] = None,
        levels: Optional[List[int]] = None,
    ) -> List[WallDetection]:
        """
        Ejecuta el pipeline completo de detección.

        Args:
            img_bgr : Imagen BGR. Si None, captura pantalla.
            levels  : Lista de niveles a detectar. None = todos (12..19).

        Returns:
            Lista de WallDetection ordenada por nivel ascendente.
            detections[0] es el muro de menor nivel → prioridad máxima.
        """
        if img_bgr is None:
            img_bgr = cv2.cvtColor(
                np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR
            )

        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        target_levels = levels if levels else list(range(12, 20))

        detections: List[WallDetection] = []
        for level in target_levels:
            mask  = self._apply_level_mask(img_hsv, level)
            blobs = self._blobs_from_mask(mask)
            for (center, area) in blobs:
                detections.append(WallDetection(center, level, area))

        detections.sort()
        return detections

    # ---------------------------------------------------------------
    # Helpers para bot.py
    # ---------------------------------------------------------------

    def get_upgrade_targets(
        self,
        img_bgr: Optional[np.ndarray] = None,
        max_targets: int = 10,
    ) -> List[Tuple[Tuple[int, int], int]]:
        """
        Shortcut para bot.py.

        Returns: [(centro_xy, nivel), ...] ordenado por nivel ascendente.
        """
        detections = self.detect(img_bgr)
        return [(d.center, d.level) for d in detections[:max_targets]]

    # ---------------------------------------------------------------
    # Debug
    # ---------------------------------------------------------------

    LEVEL_COLORS = {
        12: (80,  80,  80),   13: (180,  0, 180),  14: ( 0, 180, 140),
        15: ( 0, 200, 255),   16: ( 0,  60, 255),  17: (220, 180,  40),
        18: (200,  80, 220),  19: ( 40, 220, 180),
    }

    def debug_frame(
        self,
        img_bgr: np.ndarray,
        detections: List[WallDetection],
    ) -> np.ndarray:
        """Dibuja las detecciones con etiqueta de nivel y número de prioridad."""
        out = img_bgr.copy()
        for i, det in enumerate(detections):
            color = self.LEVEL_COLORS.get(det.level, (255, 255, 255))
            cx, cy = det.center
            cv2.circle(out, (cx, cy), 10, color, 2)
            cv2.putText(
                out, f"L{det.level} #{i+1}",
                (cx - 18, cy - 13),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1,
            )
        return out

    def debug_masks(self, img_bgr: np.ndarray, output_dir: str = 'debug/') -> None:
        """Guarda una imagen por nivel mostrando qué píxeles detecta cada máscara."""
        os.makedirs(output_dir, exist_ok=True)
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        for level in range(12, 20):
            mask = self._apply_level_mask(img_hsv, level)
            if mask.any():
                preview = img_bgr.copy()
                preview[mask == 0] = 0
                cv2.imwrite(f"{output_dir}mask_L{level}.jpg", preview)
        print(f"📁 Máscaras guardadas en '{output_dir}'")