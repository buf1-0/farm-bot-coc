"""
WallDetector — Hybrid HSV + Canny Template Matching

Architecture (two-stage pipeline):
───────────────────────────────────
  STAGE 1 · HSV Pre-filter (fast, permissive)
    - Generates candidate bounding boxes using existing HSV ranges.
    - Geometric coarse-filter (area + solidity) eliminates the obvious junk.
    - Intentionally PERMISSIVE: false positives are fine here; stage 2 kills them.

  STAGE 2 · Template Matching on Canny edges (precise, structural)
    - For each candidate bbox we extract a padded search window from the image.
    - Convert both window and stored templates to Canny edge maps.
    - Run cv2.matchTemplate(TM_CCOEFF_NORMED) on the edge maps.
    - Only detections above TEMPLATE_THRESHOLD survive.

Why Canny edges instead of raw pixels
────────────────────────────────────────
  Raw color matching fails because tile shadows, highlights and lighting vary.
  Canny extracts only structural edges (the isometric diamond outline of the
  tile). That topology is fixed regardless of lighting, shadow or color cast.
  A UI button, a gold mine flash or a patch of grass all have completely
  different edge geometry → score < 0.35 even when their HSV range overlaps.

Fallback (no templates loaded for a level)
────────────────────────────────────────────
  The original triple-filter (solidity + aspect + median HSV) is preserved
  verbatim and activates automatically for any level lacking template files.
  This means the bot degrades gracefully rather than silently missing walls.

Template directory layout
──────────────────────────
  wall_templates/
    L15/
      template_01.png   ← 56×36px crop of a real L15 tile at F3×3 zoom
      template_02.png   ← another variant (different neighbour tiles)
    L16/
      template_01.png
    ...

  Produce these with calibrate_templates.py (interactive click tool).
"""

import cv2
import numpy as np
import pyautogui
import json
import os
import glob
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class WallDetection:
    center: Tuple[int, int]   # (x, y) screen coordinates
    level: int                 # 12-19
    area: int                  # blob area in px² (or 0 when template path)
    score: float = 0.0         # TM_CCOEFF_NORMED score; 0.0 = fallback path

    def __lt__(self, other):
        # Primary sort: level ascending (cheapest wall first)
        # Secondary: score descending (most confident first within same level)
        if self.level != other.level:
            return self.level < other.level
        return self.score > other.score


# ─────────────────────────────────────────────────────────────────────────────
# Detector
# ─────────────────────────────────────────────────────────────────────────────

class WallDetector:

    # ── Template matching ──────────────────────────────────────────────────
    TEMPLATE_DIR = 'wall_templates'

    # Minimum TM_CCOEFF_NORMED score on Canny edge maps to accept a match.
    # 0.55 is deliberately conservative: a real wall tile at identical zoom
    # scores 0.70-0.90; UI elements and grass never exceed 0.45.
    TEMPLATE_THRESHOLD = 0.55

    # How many times larger than the template the search window is.
    # 2.5 gives ±0.75× tile wiggle-room while staying fast.
    SEARCH_WINDOW_FACTOR = 2.5

    # Canny thresholds — tuned for CoC at 1080p, F3×3 zoom.
    CANNY_LOW  = 40
    CANNY_HIGH = 120

    # ── HSV pre-filter (STAGE 1) — coarser than before intentionally ──────
    DEFAULT_HSV_RANGES: Dict = {}

    # Coarser than original because template stage absorbs the FP workload.
    TILE_AREA_MIN = 100
    TILE_AREA_MAX = 8_000
    SOLIDITY_MIN  = 0.40
    ASPECT_MIN    = 0.50
    ASPECT_MAX    = 7.00

    # ── Fallback validators (STAGE 1 only, when no templates) ─────────────
    _CORE_HSV: Dict = {
        12: lambda h, s, v: v < 90  and s < 75,
        13: lambda h, s, v: 115 <= h <= 158 and s > 32,
        14: lambda h, s, v: 72  <= h <= 110 and s > 48,
        15: lambda h, s, v: 9   <= h <= 34  and s > 72,
        16: lambda h, s, v: (h <= 13 or h >= 163) and s > 115,
        17: lambda h, s, v: 90  <= h <= 130 and v > 120,
        18: lambda h, s, v: 105 <= h <= 150 and s > 42,
        19: lambda h, s, v: s < 50  and v > 178,
    }

    # Debug colors (BGR)
    LEVEL_COLORS = {
        12: (80,  80,  80),   13: (180,  0, 180),  14: ( 0, 180, 140),
        15: ( 0, 200, 255),   16: ( 0,  60, 255),  17: (220, 180,  40),
        18: (200,  80, 220),  19: ( 40, 220, 180),
    }

    # ─────────────────────────────────────────────────────────────────────
    def __init__(
        self,
        config_path: str  = 'wall_config.json',
        game_roi:    tuple = None,
        templates_dir: str = None,
    ):
        self.config_path   = config_path
        self.game_roi      = game_roi
        self.templates_dir = templates_dir or self.TEMPLATE_DIR

        self.hsv_ranges = self._load_config()
        self.templates  = self._load_templates()

        n_templates = sum(len(v) for v in self.templates.values())
        levels_with_templates = sorted(self.templates.keys())
        levels_fallback = sorted(
            lvl for lvl in self.hsv_ranges
            if lvl not in self.templates
        )
        print(f"✅ Templates cargados: {n_templates} imágenes "
              f"para niveles {levels_with_templates}")
        if levels_fallback:
            print(f"⚠️  Sin templates para niveles {levels_fallback} → "
              f"modo fallback (HSV+Solidity+Mediana)")

    # ═════════════════════════════════════════════════════════════════════
    # TEMPLATE LOADING
    # ═════════════════════════════════════════════════════════════════════

    def _load_templates(self) -> Dict[int, list]:
        """
        Loads all wall_templates/L{level}/*.png files.

        For each image stores a tuple:
            (gray_img, canny_edges, (template_h, template_w))

        The canny edge map is pre-computed once at load time so the hot
        path (detect loop) never recomputes it.
        """
        result: Dict[int, list] = {}
        if not os.path.isdir(self.templates_dir):
            return result

        for level in range(12, 20):
            level_dir = os.path.join(self.templates_dir, f'L{level}')
            if not os.path.isdir(level_dir):
                continue
            pngs = sorted(glob.glob(os.path.join(level_dir, '*.png')))
            loaded = []
            for path in pngs:
                img = cv2.imread(path)
                if img is None:
                    print(f"⚠️  No se pudo cargar template: {path}")
                    continue
                gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray, self.CANNY_LOW, self.CANNY_HIGH)
                loaded.append((gray, edges, gray.shape[:2]))  # (th, tw)
            if loaded:
                result[level] = loaded
        return result

    def reload_templates(self):
        """Hot-reload templates without restarting the bot."""
        self.templates = self._load_templates()
        print(f"🔄 Templates recargados: "
              f"{sum(len(v) for v in self.templates.values())} imágenes")

    # ═════════════════════════════════════════════════════════════════════
    # STAGE 1 — HSV CANDIDATE EXTRACTION
    # ═════════════════════════════════════════════════════════════════════

    def _get_candidates(
        self,
        img_hsv: np.ndarray,
        level: int,
    ) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Returns [(hsv_center_xy, blob_bbox_xywh), ...] for blobs that pass
        the coarse geometric filter.

        This stage is intentionally loose:
          - SOLIDITY_MIN = 0.40  (original was 0.52)
          - TILE_AREA_MAX = 8000 (original was 4000)
        The template stage in Stage 2 provides the precise rejection.
        """
        mask = self._apply_level_mask(img_hsv, level)

        # Morphology: close gaps within a tile, then re-separate adjacent tiles
        k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        closed  = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k_close)
        k_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        separated = cv2.erode(closed, k_erode, iterations=1)

        contours, _ = cv2.findContours(
            separated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        candidates = []
        for cnt in contours:
            area = int(cv2.contourArea(cnt))
            if not (self.TILE_AREA_MIN <= area <= self.TILE_AREA_MAX):
                continue

            hull      = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            if hull_area < 1:
                continue
            if area / hull_area < self.SOLIDITY_MIN:
                continue

            _, _, bw, bh = cv2.boundingRect(cnt)
            aspect = bw / bh if bh > 0 else 0
            if not (self.ASPECT_MIN <= aspect <= self.ASPECT_MAX):
                continue

            M = cv2.moments(cnt)
            if M['m00'] == 0:
                continue
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
            candidates.append(((cx, cy), cv2.boundingRect(cnt)))

        return candidates

    # ═════════════════════════════════════════════════════════════════════
    # STAGE 2 — CANNY TEMPLATE MATCHING
    # ═════════════════════════════════════════════════════════════════════

    def _match_template(
        self,
        img_gray: np.ndarray,
        hsv_center: Tuple[int, int],
        level: int,
    ) -> Optional[Tuple[Tuple[int, int], float]]:
        """
        For each template of `level`, slide it over a search window centred
        on the HSV candidate.  Uses Canny edge maps + TM_CCOEFF_NORMED.

        Returns (refined_center_xy, best_score) if any template exceeds
        TEMPLATE_THRESHOLD, else None.

        ──────────────────────────────────────────────────────────────────
        Design rationale
        ──────────────────────────────────────────────────────────────────
        1. SEARCH WINDOW size = template_size × SEARCH_WINDOW_FACTOR
           Centred on the HSV candidate centre, clamped to image borders.
           This keeps the window small (fast) while giving ±37% wiggle
           room for the HSV centre being slightly off-tile.

        2. CANNY on the window at runtime (not pre-computed) because the
           window changes every call. Pre-computed template edges are reused.

        3. TM_CCOEFF_NORMED is chosen over TM_CCORR_NORMED because it
           subtracts the mean → invariant to global brightness offset
           between different parts of the base (snow/grass/lava).

        4. The template edge map is compared against the window edge map.
           A UI popup or grass pixel cluster produces random edges that
           never correlate with the clean isometric diamond edges of a tile.
        ──────────────────────────────────────────────────────────────────
        """
        tmpls = self.templates.get(level, [])
        if not tmpls:
            return None

        cx, cy = hsv_center
        h_img, w_img = img_gray.shape[:2]

        best_score = -1.0
        best_pt: Optional[Tuple[int, int]] = None

        for (_, tmpl_edges, (th, tw)) in tmpls:
            # Search window: factor × template size, centred on HSV hit
            sw_hw = max(int(tw * self.SEARCH_WINDOW_FACTOR // 2), tw)
            sw_hh = max(int(th * self.SEARCH_WINDOW_FACTOR // 2), th)

            x1 = max(0, cx - sw_hw);  x2 = min(w_img, cx + sw_hw)
            y1 = max(0, cy - sw_hh);  y2 = min(h_img, cy + sw_hh)

            window      = img_gray[y1:y2, x1:x2]
            win_edges   = cv2.Canny(window, self.CANNY_LOW, self.CANNY_HIGH)
            wh, ww      = win_edges.shape

            # Skip if window is smaller than template (we're at image edge)
            if th > wh or tw > ww:
                continue

            result = cv2.matchTemplate(win_edges, tmpl_edges,
                                       cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > best_score:
                best_score = max_val
                # Convert match top-left to absolute screen centre
                match_cx = x1 + max_loc[0] + tw // 2
                match_cy = y1 + max_loc[1] + th // 2
                best_pt  = (match_cx, match_cy)

        if best_score >= self.TEMPLATE_THRESHOLD and best_pt is not None:
            return (best_pt, best_score)
        return None

    # ═════════════════════════════════════════════════════════════════════
    # DEDUPLICATION
    # ═════════════════════════════════════════════════════════════════════

    @staticmethod
    def _deduplicate(
        detections: List[WallDetection],
        grid_size: int = 20,
    ) -> List[WallDetection]:
        """
        When multiple HSV candidates for the same level produce template
        matches that land on the same tile, keep only the highest-score one.

        Uses a coarse grid (grid_size px) for O(n) deduplication.
        """
        seen: Dict[Tuple[int, int, int], WallDetection] = {}
        for det in detections:
            key = (det.level,
                   det.center[0] // grid_size,
                   det.center[1] // grid_size)
            if key not in seen or det.score > seen[key].score:
                seen[key] = det
        return list(seen.values())

    # ═════════════════════════════════════════════════════════════════════
    # FALLBACK — original triple-filter pipeline (verbatim from v1)
    # ═════════════════════════════════════════════════════════════════════

    def _validate_blob_color(self, img_hsv, cnt, level) -> bool:
        validator = self._CORE_HSV.get(level)
        if validator is None:
            return True
        blob_mask = np.zeros(img_hsv.shape[:2], dtype=np.uint8)
        cv2.drawContours(blob_mask, [cnt], -1, 255, cv2.FILLED)
        pixels = img_hsv[blob_mask > 0]
        if len(pixels) < 5:
            return False
        return bool(validator(
            float(np.median(pixels[:, 0])),
            float(np.median(pixels[:, 1])),
            float(np.median(pixels[:, 2])),
        ))

    def _blobs_fallback(
        self, mask: np.ndarray, img_hsv: np.ndarray, level: int
    ) -> List[Tuple[Tuple[int, int], int]]:
        """Original pipeline — used when no templates are loaded for a level."""
        k_c = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        k_e = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        sep = cv2.erode(
            cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k_c), k_e, iterations=1
        )
        contours, _ = cv2.findContours(
            sep, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        blobs = []
        for cnt in contours:
            area = int(cv2.contourArea(cnt))
            if not (200 <= area <= 4000):
                continue
            hull_area = cv2.contourArea(cv2.convexHull(cnt))
            if hull_area < 1 or area / hull_area < 0.52:
                continue
            _, _, bw, bh = cv2.boundingRect(cnt)
            if bh == 0 or not (0.75 <= bw / bh <= 5.50):
                continue
            if not self._validate_blob_color(img_hsv, cnt, level):
                continue
            M = cv2.moments(cnt)
            if M['m00'] == 0:
                continue
            blobs.append((
                (int(M['m10'] / M['m00']), int(M['m01'] / M['m00'])),
                area,
            ))
        return blobs

    # ═════════════════════════════════════════════════════════════════════
    # CONFIG / ROI HELPERS
    # ═════════════════════════════════════════════════════════════════════

    def _mask_roi(self, img_bgr: np.ndarray) -> np.ndarray:
        if self.game_roi is None:
            return img_bgr
        h, w  = img_bgr.shape[:2]
        x0, y0, x1, y1 = self.game_roi
        masked = img_bgr.copy()
        py0, py1 = int(y0 * h), int(y1 * h)
        px0, px1 = int(x0 * w), int(x1 * w)
        masked[:py0, :] = 0
        masked[py1:, :] = 0
        masked[:, :px0] = 0
        masked[:, px1:] = 0
        return masked

    def _load_config(self) -> Dict:
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            result = {int(k): v for k, v in data.items()}
            print(f"✅ Rangos HSV cargados: niveles {sorted(result.keys())}")
            return result
        print("ℹ️  Sin wall_config.json. Ejecuta calibrate_walls.py.")
        return dict(self.DEFAULT_HSV_RANGES)

    def save_config(self):
        with open(self.config_path, 'w') as f:
            json.dump({str(k): v for k, v in self.hsv_ranges.items()}, f, indent=2)
        print(f"💾 Config guardada en '{self.config_path}'")

    def _apply_level_mask(self, img_hsv: np.ndarray, level: int) -> np.ndarray:
        mask = np.zeros(img_hsv.shape[:2], dtype=np.uint8)
        for (lo, hi) in self.hsv_ranges.get(level, []):
            mask |= cv2.inRange(img_hsv,
                                np.array(lo, np.uint8),
                                np.array(hi, np.uint8))
        return mask

    # ═════════════════════════════════════════════════════════════════════
    # PUBLIC API — detect()
    # ═════════════════════════════════════════════════════════════════════

    def detect(
        self,
        img_bgr: Optional[np.ndarray] = None,
        levels:  Optional[List[int]]  = None,
    ) -> List[WallDetection]:
        """
        Full two-stage pipeline.

        For levels WITH templates:
            Stage 1 (HSV) → candidate centers
            Stage 2 (Canny TM) → confirmed detections with sub-tile precision

        For levels WITHOUT templates:
            Original HSV + Solidity + Median-HSV fallback (degraded but working).

        Returns list sorted by level ascending, score descending within level.
        """
        if img_bgr is None:
            img_bgr = cv2.cvtColor(
                np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR
            )

        img_bgr  = self._mask_roi(img_bgr)
        img_hsv  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        target   = levels if levels else list(range(12, 20))

        raw_detections: List[WallDetection] = []

        for level in target:
            has_templates = bool(self.templates.get(level))

            if has_templates:
                # ── HYBRID PATH ──────────────────────────────────────────
                candidates = self._get_candidates(img_hsv, level)
                for (hsv_center, _bbox) in candidates:
                    result = self._match_template(img_gray, hsv_center, level)
                    if result is None:
                        continue
                    center, score = result
                    raw_detections.append(
                        WallDetection(center, level, 0, score)
                    )
            else:
                # ── FALLBACK PATH ─────────────────────────────────────────
                mask  = self._apply_level_mask(img_hsv, level)
                blobs = self._blobs_fallback(mask, img_hsv, level)
                for (center, area) in blobs:
                    raw_detections.append(
                        WallDetection(center, level, area, 0.0)
                    )

        detections = self._deduplicate(raw_detections)
        detections.sort()
        return detections

    # ═════════════════════════════════════════════════════════════════════
    # PUBLIC HELPER — interface for bot.py (unchanged signature)
    # ═════════════════════════════════════════════════════════════════════

    def get_upgrade_targets(
        self,
        img_bgr:     Optional[np.ndarray] = None,
        max_targets: int                  = 10,
    ) -> List[Tuple[Tuple[int, int], int]]:
        detections = self.detect(img_bgr)
        return [(d.center, d.level) for d in detections[:max_targets]]

    # ═════════════════════════════════════════════════════════════════════
    # DEBUG HELPERS
    # ═════════════════════════════════════════════════════════════════════

    def debug_frame(
        self,
        img_bgr: np.ndarray,
        detections: List[WallDetection],
    ) -> np.ndarray:
        """Annotates detections with level, rank, score and pipeline path."""
        out = img_bgr.copy()
        for i, det in enumerate(detections):
            color = self.LEVEL_COLORS.get(det.level, (255, 255, 255))
            cx, cy = det.center
            cv2.circle(out, (cx, cy), 12, color, 2)
            label = (f"L{det.level} #{i+1} [{det.score:.2f}]"
                     if det.score > 0 else
                     f"L{det.level} #{i+1} [fallback]")
            cv2.putText(out, label, (cx - 22, cy - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)
        return out

    def debug_stage1_candidates(
        self,
        img_bgr: Optional[np.ndarray] = None,
        level: int = 15,
    ) -> np.ndarray:
        """
        Visualises Stage-1 HSV candidates (before template validation).
        Useful to verify the HSV ranges catch the tile before Stage 2 runs.
        """
        if img_bgr is None:
            img_bgr = cv2.cvtColor(
                np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR
            )
        img_bgr = self._mask_roi(img_bgr)
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        out = img_bgr.copy()
        candidates = self._get_candidates(img_hsv, level)
        color = self.LEVEL_COLORS.get(level, (255, 255, 0))
        for (cx, cy), (x, y, bw, bh) in candidates:
            cv2.rectangle(out, (x, y), (x + bw, y + bh), color, 1)
            cv2.circle(out, (cx, cy), 5, color, -1)
        print(f"Stage-1 candidatos L{level}: {len(candidates)}")
        return out

    def debug_masks(
        self,
        img_bgr: np.ndarray,
        output_dir: str = 'debug/',
    ) -> None:
        os.makedirs(output_dir, exist_ok=True)
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        for level in range(12, 20):
            mask = self._apply_level_mask(img_hsv, level)
            if mask.any():
                preview = img_bgr.copy()
                preview[mask == 0] = 0
                cv2.imwrite(f"{output_dir}mask_L{level}.jpg", preview)
        print(f"📁 Máscaras guardadas en '{output_dir}'")

    def debug_template_scores(
        self,
        img_bgr: Optional[np.ndarray] = None,
        level: Optional[int] = None,
    ) -> None:
        """
        Prints the raw template match score for every Stage-1 candidate.
        Run this to tune TEMPLATE_THRESHOLD for your resolution/zoom.

        Example output:
            L15  candidate @ (842, 610)  best_score=0.71 ✅  → (848, 614)
            L15  candidate @ (312, 490)  best_score=0.31 ❌  (grass FP rejected)
        """
        if img_bgr is None:
            img_bgr = cv2.cvtColor(
                np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR
            )
        img_bgr  = self._mask_roi(img_bgr)
        img_hsv  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        target   = [level] if level else list(range(12, 20))

        for lvl in target:
            if not self.templates.get(lvl):
                print(f"L{lvl}: sin templates (fallback activo)")
                continue
            candidates = self._get_candidates(img_hsv, lvl)
            print(f"\n─── L{lvl} — {len(candidates)} candidatos HSV ───")
            for (cx, cy), _ in candidates:
                result = self._match_template(img_gray, (cx, cy), lvl)
                if result:
                    refined, score = result
                    status = "✅" if score >= self.TEMPLATE_THRESHOLD else "❌"
                    print(f"   HSV@({cx:4d},{cy:4d})  "
                          f"score={score:.3f} {status}  "
                          f"→ refined@{refined}")
                else:
                    print(f"   HSV@({cx:4d},{cy:4d})  score<threshold ❌")