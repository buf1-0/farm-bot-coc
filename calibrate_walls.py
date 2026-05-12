"""
Flujo de calibración:
  1. Pon el juego en tu aldea con los muros visibles
  2. Ejecuta este script
  3. Haz clic en el centro de un tile de muro
  4. El script muestra el HSV mediano y propone el rango automáticamente
  5. Escribe el nivel en la consola (12-19)
  6. Repite para distintos niveles y distintos fondos de aldea
  7. Pulsa Q para salir y guardar

CONSEJO: Calibra el mismo nivel sobre 3-4 fondos distintos (césped/nieve/
         volcán) para que los rangos sean robustos.
"""

import cv2
import numpy as np
import pyautogui
import time
import json
import os

from wall_detector import WallDetector

SAMPLE_RADIUS = 7     # px alrededor del clic para muestrear
MARGIN_H      = 10    # tolerancia canal Hue
MARGIN_S      = 45    # tolerancia canal Saturation
MARGIN_V      = 55    # tolerancia canal Value

detector    = WallDetector()
img_bgr     = None
img_hsv     = None
win_main    = "Calibración (clic en muro) | Q = guardar y salir"
win_preview = "Preview — píxeles detectados por el rango actual"


def compute_range(img_hsv_local, x, y):
    """Calcula rango HSV con margen alrededor del píxel clickado."""
    h, w = img_hsv_local.shape[:2]
    x1 = max(0, x - SAMPLE_RADIUS);  x2 = min(w, x + SAMPLE_RADIUS)
    y1 = max(0, y - SAMPLE_RADIUS);  y2 = min(h, y + SAMPLE_RADIUS)
    patch = img_hsv_local[y1:y2, x1:x2]

    med_h = int(np.median(patch[:, :, 0]))
    med_s = int(np.median(patch[:, :, 1]))
    med_v = int(np.median(patch[:, :, 2]))

    lo = [max(0,   med_h - MARGIN_H),
          max(0,   med_s - MARGIN_S),
          max(0,   med_v - MARGIN_V)]
    hi = [min(180, med_h + MARGIN_H),
          min(255, med_s + MARGIN_S),
          min(255, med_v + MARGIN_V)]
    return lo, hi, (med_h, med_s, med_v)


def show_preview(level: int):
    """Muestra qué píxeles detecta el rango acumulado del nivel dado."""
    ranges = detector.hsv_ranges.get(level, [])
    combined = np.zeros(img_hsv.shape[:2], dtype=np.uint8)
    for (lo, hi) in ranges:
        combined |= cv2.inRange(img_hsv,
                                np.array(lo, np.uint8),
                                np.array(hi, np.uint8))
    preview = img_bgr.copy()
    preview[combined == 0] = 0
    cv2.imshow(win_preview, preview)


def on_click(event, x, y, flags, param):
    if event != cv2.EVENT_LBUTTONDOWN:
        return

    lo, hi, median = compute_range(img_hsv, x, y)

    print(f"\n📍 ({x}, {y})  →  HSV mediana: H={median[0]} S={median[1]} V={median[2]}")
    print(f"   Rango propuesto: lo={lo}  hi={hi}")

    try:
        level = int(input("   Nivel de este muro (12-19) | 0=cancelar: "))
    except (ValueError, EOFError):
        return

    if level == 0:
        print("   ↩ Cancelado.")
        return
    if not (12 <= level <= 19):
        print("   ⚠ Nivel fuera de rango 12-19.")
        return

    if level not in detector.hsv_ranges:
        detector.hsv_ranges[level] = []

    # Evitar duplicados exactos
    if [lo, hi] not in detector.hsv_ranges[level]:
        detector.hsv_ranges[level].append([lo, hi])

    n = len(detector.hsv_ranges[level])
    print(f"   ✅ Nivel {level}: {n} rango(s) acumulados.")

    # Preview inmediato
    show_preview(level)


def main():
    global img_bgr, img_hsv

    print("=" * 50)
    print("  CALIBRADOR DE RANGOS HSV — Clash of Clans")
    print("=" * 50)
    print("Pon el juego en tu aldea con muros visibles.")
    print("Capturando en 5 segundos...")
    time.sleep(5)

    screenshot = pyautogui.screenshot()
    img_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    cv2.namedWindow(win_main,    cv2.WINDOW_NORMAL)
    cv2.namedWindow(win_preview, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(win_main, on_click)
    cv2.imshow(win_main, img_bgr)
    cv2.imshow(win_preview, np.zeros_like(img_bgr))

    print("\n✅ Ventana abierta. Haz clic sobre muros individuales.")
    print("   Escribe el nivel en la consola cuando se pregunte.")
    print("   Q para guardar y salir.\n")

    while True:
        key = cv2.waitKey(100) & 0xFF
        if key == ord('q'):
            break

    cv2.destroyAllWindows()

    detector.save_config()
    print(f"\n📊 Resumen final:")
    for lvl in sorted(detector.hsv_ranges.keys()):
        n = len(detector.hsv_ranges[lvl])
        print(f"   Nivel {lvl}: {n} rango(s)")


if __name__ == "__main__":
    main()