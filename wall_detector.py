import cv2
import numpy as np
import pyautogui
import json
import os
from typing import List, Tuple, Dict, Optional, Callable
from dataclasses import dataclass


@dataclass
class WallDetection:
    center: Tuple[int, int]   # (x, y) pantalla
    level: int                 # 12-19
    area: int                  # px² del blob

    def __lt__(self, other):
        return self.level < other.level


class WallDetector:
    """
    Detecta y prioriza muros de CoC por nivel usando triple validación:

      1. Segmentación HSV  — captura candidatos por color de nivel
      2. Filtro Geométrico — convex hull: solidity + aspect ratio
                             → elimina fragmentos de edificios (inter-class FP)
      3. Color Dominante   — mediana HSV intra-blob
                             → elimina confusión shadow/highlight entre niveles
                               adyacentes (intra-class FP)

    Por qué convex hull y no approxPolyDP
    ─────────────────────────────────────
    A 200-4000 px², después de MORPH_CLOSE + erode, el contorno ya no tiene
    4 vértices limpios. approxPolyDP produce resultados inestables según el
    epsilon. El convex hull en cambio recupera la forma convexa real del blob
    absorviendo el ruido morfológico, y solidity = area/hull_area es un
    discriminante estable: tile de muro ≥ 0.55, fragmento orgánico ≤ 0.45.

    Por qué mediana y no media HSV
    ───────────────────────────────
    Los píxeles limítrofes de un nivel solapan con el adyacente (sombras de
    L15 cuyos H caen en rango L16, etc.). La media se contamina con esos
    outliers. La mediana al 50% los ignora por construcción; si el 70% del
    blob es dorado L15, la mediana H estará en el rango dorado, sin importar
    cuánto tire la cola roja del 30% limítrofe.
    """

    # ---------------------------------------------------------------
    # Rangos de captura HSV (amplios, para no perder tiles)
    # ---------------------------------------------------------------
    DEFAULT_HSV_RANGES: Dict[int, List[List]] = {
        12: [  # Obsidian Black
            [[0,   0,  10], [180, 60,  75]]
        ],
        13: [  # Void Purple
            [[120, 40,  25], [155, 210, 115]]
        ],
        14: [  # Infernal Teal
            [[78,  55,  25], [105, 230, 125]]
        ],
        15: [  # Gold Crown
            [[10, 140, 140], [30,  255, 255]],
            [[10,  80,  80], [30,  255, 150]],
        ],
        16: [  # Lava Red (wrap en H)
            [[0,   140,  90], [12,  255, 255]],
            [[168, 140,  90], [180, 255, 255]],
        ],
        17: [  # Ice Blue
            [[95,  55, 140], [125, 210, 255]]
        ],
        18: [  # Crystal Indigo
            [[110, 55,  90], [145, 210, 210]]
        ],
        19: [  # Max — blanco/plateado
            [[0,   0,  200], [180,  40, 255]],
            [[10,  80, 190], [30,  255, 255]],
        ],
    }

    # ---------------------------------------------------------------
    # Filtros Geométricos
    # Validados a 1920×1080, zoom F3×3
    # ---------------------------------------------------------------
    TILE_AREA_MIN = 200    # px²
    TILE_AREA_MAX = 4000   # px²

    # Solidity = area_contorno / area_convex_hull
    # Tile de muro isométrico (rombo): ≥ 0.55
    # Fragmento de edificio orgánico:  ≤ 0.45
    SOLIDITY_MIN  = 0.52

    # Aspect ratio = W / H del bounding rect
    # Tile individual: ~1.8-2.2  |  Segmento largo: hasta ~5
    # Fragmento cuadrado (edificio): ~1.0  |  Borde vertical (torre): < 0.7
    ASPECT_MIN    = 0.75
    ASPECT_MAX    = 5.50

    # ---------------------------------------------------------------
    # Validadores de Color Dominante (mediana HSV)
    # Más estrictos que los rangos de captura intencionalmente.
    # Cada lambda recibe (med_H, med_S, med_V) → bool
    # ---------------------------------------------------------------
    _CORE_HSV: Dict[int, object] = {
        # L12: Muy oscuro. H irrelevante (baja S). V < 90 es el discriminante.
        12: lambda h, s, v: v < 90  and s < 75,

        # L13: Púrpura. H claramente en rango violeta, S moderada.
        13: lambda h, s, v: 115 <= h <= 158 and s > 32,

        # L14: Teal. H en verde-azulado, S alta.
        14: lambda h, s, v: 72  <= h <= 110 and s > 48,

        # L15: Dorado. H en amarillo-naranja, S alta (separa de L16 rojo).
        # La clave del bug: exigimos H ≥ 9 para rechazar blobs con mediana H≈5
        # que corresponden a sombras de L16, no a L15.
        15: lambda h, s, v: 9   <= h <= 34  and s > 72,

        # L16: Rojo. H en los extremos del círculo (wrap). S muy alta.
        # Complementario al de L15: H ≤ 13 con S alta es rojo, no dorado.
        16: lambda h, s, v: (h <= 13 or h >= 163) and s > 115,

        # L17: Azul frío. H en azul, V alta (brillante).
        17: lambda h, s, v: 90  <= h <= 130 and v > 120,

        # L18: Índigo. H en azul-índigo, S moderada.
        18: lambda h, s, v: 105 <= h <= 150 and s > 42,

        # L19: Blanco/plateado. S casi nula, V muy alta.
        19: lambda h, s, v: s < 50  and v > 178,
    }

    def __init__(self, config_path: str = 'wall_config.json'):
        self.config_path = config_path
        self.hsv_ranges  = self._load_config()

    # ---------------------------------------------------------------
    # Config
    # ---------------------------------------------------------------

    def _load_config(self) -> Dict:
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                data = json.load(f)
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
    # Core pipeline — pasos individuales
    # ---------------------------------------------------------------

    def _apply_level_mask(self, img_hsv: np.ndarray, level: int) -> np.ndarray:
        """OR de todos los rangos HSV definidos para ese nivel."""
        ranges = self.hsv_ranges.get(level, [])
        mask = np.zeros(img_hsv.shape[:2], dtype=np.uint8)
        for (lo, hi) in ranges:
            mask |= cv2.inRange(img_hsv,
                                np.array(lo, np.uint8),
                                np.array(hi, np.uint8))
        return mask

    def _validate_blob_color(
        self,
        img_hsv: np.ndarray,
        cnt:     np.ndarray,
        level:   int,
    ) -> bool:
        """
        Extrae la mediana H, S, V de los píxeles interiores del blob y
        la valida contra la regla de color dominante del nivel.

        La mediana es robusta a los píxeles limítrofes que se solapan con
        el nivel adyacente; la mean no lo sería.
        """
        validator = self._CORE_HSV.get(level)
        if validator is None:
            return True   # Nivel sin regla definida → pasa por defecto

        # Máscara rasterizada del contorno
        blob_mask = np.zeros(img_hsv.shape[:2], dtype=np.uint8)
        cv2.drawContours(blob_mask, [cnt], -1, 255, cv2.FILLED)

        # Extraer todos los píxeles interiores: shape (N, 3)
        pixels = img_hsv[blob_mask > 0]
        if len(pixels) < 5:
            return False

        med_h = float(np.median(pixels[:, 0]))
        med_s = float(np.median(pixels[:, 1]))
        med_v = float(np.median(pixels[:, 2]))

        return bool(validator(med_h, med_s, med_v))

    def _blobs_from_mask(
        self,
        mask:    np.ndarray,
        img_hsv: np.ndarray,
        level:   int,
    ) -> List[Tuple[Tuple[int, int], int]]:
        """
        Morfología → contornos → filtro de área → filtro geométrico
        → validación de color dominante.

        Solo los blobs que superan los tres filtros llegan al caller.

        Args:
            mask    : Máscara binaria del nivel (salida de _apply_level_mask).
            img_hsv : Imagen HSV completa (para validación de color).
            level   : Nivel de muro (12-19).

        Returns:
            [(centro_xy, area), ...]
        """
        # ------------------------------------------------------------------
        # 1. MORFOLOGÍA
        #    Close: une píxeles próximos del mismo tile (huecos por sombra).
        #    Erode: vuelve a separar tiles adyacentes del mismo nivel.
        # ------------------------------------------------------------------
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        closed       = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)

        kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        separated    = cv2.erode(closed, kernel_erode, iterations=1)

        contours, _ = cv2.findContours(
            separated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        blobs = []
        for cnt in contours:

            # ------------------------------------------------------------------
            # 2. FILTRO DE ÁREA (igual que antes)
            # ------------------------------------------------------------------
            area = int(cv2.contourArea(cnt))
            if not (self.TILE_AREA_MIN <= area <= self.TILE_AREA_MAX):
                continue

            # ------------------------------------------------------------------
            # 3. FILTRO GEOMÉTRICO — convex hull
            #
            # Por qué hull y no approxPolyDP:
            #   approxPolyDP a esta escala produce resultados inestables
            #   (3-8 vértices según epsilon). El hull en cambio siempre
            #   entrega la envolvente convexa real; solidity y aspect ratio
            #   son métricas robustas a esa escala.
            # ------------------------------------------------------------------
            hull      = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            if hull_area < 1:
                continue

            solidity = area / hull_area          # [0, 1]: muro ≥ 0.52
            if solidity < self.SOLIDITY_MIN:
                # Forma irregular → fragmento de Almacén/Mina/edificio
                continue

            _, _, bw, bh = cv2.boundingRect(cnt)
            aspect = bw / bh if bh > 0 else 0   # tile: 1.8-2.2; segmento: <5.5
            if not (self.ASPECT_MIN <= aspect <= self.ASPECT_MAX):
                # Cuadrado (edificio) o columna vertical (borde de torre)
                continue

            # ------------------------------------------------------------------
            # 4. VALIDACIÓN DE COLOR DOMINANTE — mediana HSV intra-blob
            #
            # Elimina la confusión intra-clase (shadow L15 ↔ highlight L16):
            # aunque algunos píxeles del blob solapan con el nivel vecino,
            # la mediana del blob completo cae del lado correcto.
            # ------------------------------------------------------------------
            if not self._validate_blob_color(img_hsv, cnt, level):
                continue

            # Centro por momentos
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
        levels:  Optional[List[int]]  = None,
    ) -> List[WallDetection]:
        """
        Pipeline completo: captura → máscara por nivel → triple filtro.

        Args:
            img_bgr : Imagen BGR. Si None, captura pantalla.
            levels  : Niveles a detectar. None = todos (12..19).

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
            # Pasamos img_hsv y level para los filtros internos
            blobs = self._blobs_from_mask(mask, img_hsv, level)
            for (center, area) in blobs:
                detections.append(WallDetection(center, level, area))

        detections.sort()
        return detections

    # ---------------------------------------------------------------
    # Helpers para bot.py — firma idéntica, sin cambios en el caller
    # ---------------------------------------------------------------

    def get_upgrade_targets(
        self,
        img_bgr:     Optional[np.ndarray] = None,
        max_targets: int                  = 10,
    ) -> List[Tuple[Tuple[int, int], int]]:
        """
        Shortcut para bot.py.
        Returns: [(centro_xy, nivel), ...] ordenado por nivel ascendente.
        """
        detections = self.detect(img_bgr)
        return [(d.center, d.level) for d in detections[:max_targets]]

    # ---------------------------------------------------------------
    # Debug — sin cambios
    # ---------------------------------------------------------------

    LEVEL_COLORS = {
        12: (80,  80,  80),   13: (180,  0, 180),  14: ( 0, 180, 140),
        15: ( 0, 200, 255),   16: ( 0,  60, 255),  17: (220, 180,  40),
        18: (200,  80, 220),  19: ( 40, 220, 180),
    }

    def debug_frame(
        self,
        img_bgr:    np.ndarray,
        detections: List[WallDetection],
    ) -> np.ndarray:
        """Dibuja detecciones con etiqueta de nivel, número de prioridad,
        y ahora también el reason de cada filtro en modo verbose."""
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

    def debug_masks(
        self,
        img_bgr:    np.ndarray,
        output_dir: str = 'debug/',
    ) -> None:
        """Guarda una imagen por nivel mostrando qué píxeles captura la máscara."""
        os.makedirs(output_dir, exist_ok=True)
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        for level in range(12, 20):
            mask = self._apply_level_mask(img_hsv, level)
            if mask.any():
                preview = img_bgr.copy()
                preview[mask == 0] = 0
                cv2.imwrite(f"{output_dir}mask_L{level}.jpg", preview)
        print(f"📁 Máscaras guardadas en '{output_dir}'")

    def debug_blob_stats(
        self,
        img_bgr: Optional[np.ndarray] = None,
        level:   Optional[int]        = None,
    ) -> None:
        """
        Modo diagnóstico: imprime las métricas de cada blob candidato
        (antes de los filtros) para afinar SOLIDITY_MIN, ASPECT_MIN/MAX
        y los CORE_HSV en tu entorno específico.

        Uso:
            detector.debug_blob_stats(level=15)
        """
        if img_bgr is None:
            img_bgr = cv2.cvtColor(
                np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR
            )
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        target_levels = [level] if level else list(range(12, 20))

        for lvl in target_levels:
            mask  = self._apply_level_mask(img_hsv, lvl)
            kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)
            kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            separated = cv2.erode(closed, kernel_erode, iterations=1)
            contours, _ = cv2.findContours(
                separated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            print(f"\n─── L{lvl} ({len(contours)} contornos) ───")
            for i, cnt in enumerate(contours):
                area = int(cv2.contourArea(cnt))
                if area < 50:
                    continue
                hull      = cv2.convexHull(cnt)
                hull_area = cv2.contourArea(hull)
                solidity  = area / hull_area if hull_area > 0 else 0
                _, _, bw, bh = cv2.boundingRect(cnt)
                aspect    = bw / bh if bh > 0 else 0

                blob_mask = np.zeros(img_hsv.shape[:2], dtype=np.uint8)
                cv2.drawContours(blob_mask, [cnt], -1, 255, cv2.FILLED)
                pixels = img_hsv[blob_mask > 0]
                med_h  = float(np.median(pixels[:, 0])) if len(pixels) > 0 else -1
                med_s  = float(np.median(pixels[:, 1])) if len(pixels) > 0 else -1
                med_v  = float(np.median(pixels[:, 2])) if len(pixels) > 0 else -1

                geo_ok   = (self.TILE_AREA_MIN <= area <= self.TILE_AREA_MAX
                            and solidity >= self.SOLIDITY_MIN
                            and self.ASPECT_MIN <= aspect <= self.ASPECT_MAX)
                color_ok = self._validate_blob_color(img_hsv, cnt, lvl)

                status = "✅ PASS" if (geo_ok and color_ok) else (
                    "❌ GEO"   if not geo_ok   else
                    "❌ COLOR"
                )
                print(f"  #{i+1:02d} area={area:4d}  sol={solidity:.2f}  "
                      f"asp={aspect:.2f}  H={med_h:5.1f} S={med_s:5.1f} "
                      f"V={med_v:5.1f}  {status}")