"""
debug/debug_hybrid.py — Diagnóstico del Hybrid Wall Detector

Muestra tres vistas en paralelo:
  1. Candidatos Stage-1 (solo HSV) — lo que entraría al pipeline viejo
  2. Detecciones finales (Stage-1 + Template Matching) — lo que pasa al bot
  3. Score por candidato en consola, para ajustar TEMPLATE_THRESHOLD

Uso:
    cd <raiz_proyecto>
    python debug/debug_hybrid.py [--level 15] [--save]

Opciones:
    --level N   Solo analiza el nivel N (12-19); sin flag = todos
    --save      Guarda las imágenes de debug en debug/
    --threshold F   Override de TEMPLATE_THRESHOLD para esta sesión (ej: 0.45)
"""

import sys
import os
import argparse
import time

import cv2
import numpy as np
import pyautogui

# Asegurarse de que el script encuentra los módulos del proyecto raíz
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from configuration import Configuration
from wall_detector import WallDetector


# ════════════════════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(description="Debug Hybrid Wall Detector")
    p.add_argument('--level',     type=int, default=None,
                   help="Analizar solo este nivel (12-19)")
    p.add_argument('--save',      action='store_true',
                   help="Guardar imágenes de debug en debug/")
    p.add_argument('--threshold', type=float, default=None,
                   help="Override de TEMPLATE_THRESHOLD (ej: 0.45)")
    return p.parse_args()


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

def overlay_candidates(img_bgr, detector, level_filter=None):
    """
    Dibuja los candidatos de Stage-1 (ANTES del template matching).
    Rectángulos finos = blobs HSV que pasaron el filtro geométrico.
    """
    img_bgr_masked = detector._mask_roi(img_bgr)
    img_hsv = cv2.cvtColor(img_bgr_masked, cv2.COLOR_BGR2HSV)
    out = img_bgr.copy()

    levels = [level_filter] if level_filter else list(range(12, 20))
    total = 0
    for lvl in levels:
        color = detector.LEVEL_COLORS.get(lvl, (200, 200, 200))
        candidates = detector._get_candidates(img_hsv, lvl)
        total += len(candidates)
        for (cx, cy), (x, y, bw, bh) in candidates:
            # Thin rectangle = raw HSV candidate
            cv2.rectangle(out, (x, y), (x + bw, y + bh), color, 1)
            cv2.circle(out, (cx, cy), 3, color, -1)
            cv2.putText(out, f"L{lvl}?",
                        (x, y - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)

    print(f"Stage-1 (HSV) candidatos totales: {total}")
    return out, total


def overlay_detections(img_bgr, detector, level_filter=None):
    """
    Dibuja las detecciones FINALES (Stage-1 + template matching).
    Círculos gruesos = confirmados por el matcher.
    """
    levels = [level_filter] if level_filter else None
    detections = detector.detect(img_bgr.copy(), levels=levels)
    out = detector.debug_frame(img_bgr.copy(), detections)
    print(f"Detecciones finales validadas: {len(detections)}")
    for d in detections:
        path = "template" if d.score > 0 else "fallback"
        print(f"   L{d.level} @ {d.center}  score={d.score:.3f}  [{path}]")
    return out, detections


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    args = parse_args()
    cfg  = Configuration()

    print("=" * 58)
    print("  DEBUG HYBRID WALL DETECTOR")
    print("=" * 58)
    print("Capturando pantalla en 5 segundos (cambia a la ventana del juego)...")
    time.sleep(5)

    # Captura
    screenshot = pyautogui.screenshot()
    img_bgr    = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    print(f"✅ Captura: {img_bgr.shape[1]}×{img_bgr.shape[0]}px\n")

    # Inicializar detector
    detector = WallDetector(game_roi=cfg.GAME_ROI)
    if args.threshold is not None:
        detector.TEMPLATE_THRESHOLD = args.threshold
        print(f"⚙️  TEMPLATE_THRESHOLD override → {args.threshold}\n")

    os.makedirs('debug', exist_ok=True)

    # ── Vista 1: candidatos HSV (Stage-1) ────────────────────────────────
    print("─── Stage-1: Candidatos HSV (sin validación) ───")
    stage1_img, n_candidates = overlay_candidates(img_bgr, detector, args.level)

    # ── Vista 2: detecciones finales ─────────────────────────────────────
    print("\n─── Stage-2: Detecciones validadas por template ───")
    stage2_img, detections = overlay_detections(img_bgr, detector, args.level)

    # ── Score detallado ──────────────────────────────────────────────────
    print("\n─── Scores detallados (todos los candidatos HSV) ───")
    detector.debug_template_scores(img_bgr.copy(), level=args.level)

    # ── Mostrar / guardar ─────────────────────────────────────────────────
    # Combinar las dos vistas horizontalmente para comparar
    h1, w1 = stage1_img.shape[:2]
    h2, w2 = stage2_img.shape[:2]
    target_h = max(h1, h2)
    if h1 != target_h:
        stage1_img = cv2.copyMakeBorder(
            stage1_img, 0, target_h - h1, 0, 0, cv2.BORDER_CONSTANT)
    if h2 != target_h:
        stage2_img = cv2.copyMakeBorder(
            stage2_img, 0, target_h - h2, 0, 0, cv2.BORDER_CONSTANT)

    # Label banners
    for img, label in [(stage1_img, "STAGE-1: HSV candidates"),
                       (stage2_img, "STAGE-2: Template validated")]:
        cv2.rectangle(img, (0, 0), (340, 28), (20, 20, 20), -1)
        cv2.putText(img, label, (6, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 255), 1)

    combined = np.hstack([stage1_img, stage2_img])

    if args.save:
        out_path = 'debug/debug_hybrid_combined.jpg'
        cv2.imwrite(out_path, combined)
        cv2.imwrite('debug/debug_hybrid_stage1.jpg', stage1_img)
        cv2.imwrite('debug/debug_hybrid_stage2.jpg', stage2_img)
        print(f"\n📸 Imágenes guardadas en debug/")

    print(f"\n📊 Resumen: {n_candidates} candidatos HSV → "
          f"{len(detections)} detecciones validadas")
    reduction = (1 - len(detections) / n_candidates) * 100 if n_candidates else 0
    print(f"   Tasa de rechazo Stage-2: {reduction:.0f}%")
    print("\nMostrando resultado (cualquier tecla para cerrar)...")

    cv2.namedWindow("Hybrid Debug — izquierda=HSV | derecha=Template validated",
                    cv2.WINDOW_NORMAL)
    cv2.imshow(
        "Hybrid Debug — izquierda=HSV | derecha=Template validated",
        combined
    )
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()