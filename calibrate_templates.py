"""
calibrate_templates.py — Generador de Templates para el Hybrid Wall Detector
═══════════════════════════════════════════════════════════════════════════════

Flujo de trabajo
────────────────
  1. Pon el juego en tu aldea con los muros visibles (zoom F3 × 3).
  2. Ejecuta este script. Tienes 5 segundos para cambiar de ventana.
  3. Ventana principal: haz clic en el CENTRO de un tile de muro.
  4. La ventana "Preview Canny" te muestra los bordes que el matcher usará.
     — Si los bordes son el contorno limpio del rombo isométrico → perfecto.
     — Si los bordes son un borrón o están vacíos → elige otro tile más iluminado.
  5. Escribe el nivel en la consola (12-19) y pulsa ENTER para guardar.
  6. Repite para 2-3 variantes por nivel (distintos vecinos/iluminaciones).
  7. Pulsa Q para salir.

Controles del teclado (en la ventana principal)
─────────────────────────────────────────────────
  +  /  =    Ampliar el recorte (mitad del ancho ++)
  -          Reducir el recorte
  R          Recapturar pantalla
  Q          Salir

Directorio de salida
─────────────────────
  wall_templates/
    L{nivel}/
      template_01.png
      template_02.png
      ...

CONSEJO: Un tile limpio sin edificios encima y sin tiles del mismo nivel
pegados es el mejor candidato. No necesitas más de 3-4 templates por nivel.
"""

import cv2
import numpy as np
import pyautogui
import time
import os
import sys

# ── Defaults (F3×3 zoom a 1080p) ────────────────────────────────────────────
# Tamaño del recorte cuadrado en píxeles (desde el centro del clic).
# La tile isométrica de CoC mide ~56×36px a F3×3; usamos 30 de semi-ancho
# para capturar también el interior sin cortar los bordes.
DEFAULT_HALF_W = 30   # píxeles desde el centro hacia cada lado (horizontal)
DEFAULT_HALF_H = 20   # píxeles desde el centro hacia arriba/abajo

TEMPLATE_DIR   = 'wall_templates'
WIN_MAIN       = "Calibrador Templates | Clic=capturar | +/-=tamaño | R=recapturar | Q=salir"
WIN_CANNY      = "Preview Canny (así ve el matcher el template)"
WIN_CROP       = "Preview Crop (recorte original)"

# ── Estado global (OpenCV callback no acepta clases fácilmente) ──────────────
state = {
    'img_bgr':    None,
    'img_display': None,
    'last_crop':  None,
    'half_w':     DEFAULT_HALF_W,
    'half_h':     DEFAULT_HALF_H,
    'last_xy':    None,
}


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

def capture_screen():
    print("📸 Capturando pantalla...")
    screenshot = pyautogui.screenshot()
    img_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    state['img_bgr']    = img_bgr
    state['img_display'] = img_bgr.copy()
    cv2.imshow(WIN_MAIN, state['img_display'])
    print(f"   ✅ Captura lista ({img_bgr.shape[1]}×{img_bgr.shape[0]}px)")


def crop_around(x, y):
    img    = state['img_bgr']
    h, w   = img.shape[:2]
    hw, hh = state['half_w'], state['half_h']
    x1, y1 = max(0, x - hw), max(0, y - hh)
    x2, y2 = min(w, x + hw), min(h, y + hh)
    return img[y1:y2, x1:x2].copy(), (x1, y1, x2, y2)


def show_previews(crop_bgr):
    # Raw crop
    scale = max(1, 200 // max(crop_bgr.shape[:2]))
    big   = cv2.resize(crop_bgr, None, fx=scale, fy=scale,
                       interpolation=cv2.INTER_NEAREST)
    cv2.imshow(WIN_CROP, big)

    # Canny preview
    gray  = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 40, 120)
    big_e = cv2.resize(edges, None, fx=scale, fy=scale,
                       interpolation=cv2.INTER_NEAREST)
    # Colorize: white edges on dark bg for readability
    vis   = cv2.cvtColor(big_e, cv2.COLOR_GRAY2BGR)
    cv2.imshow(WIN_CANNY, vis)


def save_template(crop_bgr, level):
    level_dir = os.path.join(TEMPLATE_DIR, f'L{level}')
    os.makedirs(level_dir, exist_ok=True)
    existing = [f for f in os.listdir(level_dir) if f.endswith('.png')]
    idx      = len(existing) + 1
    filename = os.path.join(level_dir, f'template_{idx:02d}.png')
    cv2.imwrite(filename, crop_bgr)
    print(f"   💾 Guardado: {filename}  "
          f"({crop_bgr.shape[1]}×{crop_bgr.shape[0]}px)")
    return filename


def redraw_selection(x, y, x1, y1, x2, y2):
    disp = state['img_bgr'].copy()
    cv2.rectangle(disp, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.circle(disp, (x, y), 3, (0, 0, 255), -1)
    # Crosshair
    cv2.line(disp, (x - 12, y), (x + 12, y), (0, 200, 255), 1)
    cv2.line(disp, (x, y - 12), (x, y + 12), (0, 200, 255), 1)
    state['img_display'] = disp
    cv2.imshow(WIN_MAIN, disp)


# ════════════════════════════════════════════════════════════════════════════
# MOUSE CALLBACK
# ════════════════════════════════════════════════════════════════════════════

def on_click(event, x, y, flags, param):
    if event != cv2.EVENT_LBUTTONDOWN:
        return

    crop, (x1, y1, x2, y2) = crop_around(x, y)
    state['last_crop'] = crop
    state['last_xy']   = (x, y)

    redraw_selection(x, y, x1, y1, x2, y2)
    show_previews(crop)

    print(f"\n📍 Clic en ({x}, {y})  "
          f"recorte: {crop.shape[1]}×{crop.shape[0]}px")
    print(f"   ¿Los bordes del rombo isométrico son claros en el preview Canny?")

    # Ask level via stdin (blocks briefly but fine for a calibration tool)
    try:
        raw = input("   Nivel del muro (12-19) | ENTER=cancelar: ").strip()
        if not raw:
            print("   ↩ Cancelado.")
            return
        level = int(raw)
    except (ValueError, EOFError):
        print("   ↩ Entrada inválida.")
        return

    if not (12 <= level <= 19):
        print("   ⚠ Nivel fuera de rango 12-19.")
        return

    # Optional: re-confirm by showing a clean description
    print(f"   Guardando template para L{level}...")
    save_template(crop, level)

    # Count how many templates exist now for this level
    level_dir = os.path.join(TEMPLATE_DIR, f'L{level}')
    n = len([f for f in os.listdir(level_dir) if f.endswith('.png')])
    print(f"   📊 L{level} ahora tiene {n} template(s).")
    if n < 2:
        print(f"   💡 Recomendado: añade 1-2 templates más de L{level} "
              f"con distintos tiles vecinos.")


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  CALIBRADOR DE TEMPLATES — Hybrid Wall Detector")
    print("=" * 60)
    print(f"Zoom target: F3×3  |  Semi-tamaño inicial: "
          f"{DEFAULT_HALF_W}×{DEFAULT_HALF_H}px")
    print("Pon el juego en tu aldea. Capturando en 5 segundos...")
    time.sleep(5)

    capture_screen()

    cv2.namedWindow(WIN_MAIN,  cv2.WINDOW_NORMAL)
    cv2.namedWindow(WIN_CANNY, cv2.WINDOW_NORMAL)
    cv2.namedWindow(WIN_CROP,  cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WIN_MAIN, on_click)

    blank = np.zeros((120, 120, 3), dtype=np.uint8)
    cv2.imshow(WIN_CANNY, blank)
    cv2.imshow(WIN_CROP,  blank)

    print("\n✅ Listo. Haz clic en el CENTRO de un tile de muro.")
    print("   Controles: +/- tamaño recorte | R recapturar | Q salir\n")

    while True:
        key = cv2.waitKey(100) & 0xFF

        if key == ord('q'):
            break

        elif key in (ord('+'), ord('=')):
            state['half_w'] = min(state['half_w'] + 4, 120)
            state['half_h'] = min(state['half_h'] + 3, 80)
            print(f"   🔍 Tamaño: {state['half_w']*2}×{state['half_h']*2}px")
            if state['last_xy']:
                x, y = state['last_xy']
                crop, (x1, y1, x2, y2) = crop_around(x, y)
                state['last_crop'] = crop
                redraw_selection(x, y, x1, y1, x2, y2)
                show_previews(crop)

        elif key == ord('-'):
            state['half_w'] = max(state['half_w'] - 4, 10)
            state['half_h'] = max(state['half_h'] - 3, 7)
            print(f"   🔍 Tamaño: {state['half_w']*2}×{state['half_h']*2}px")
            if state['last_xy']:
                x, y = state['last_xy']
                crop, (x1, y1, x2, y2) = crop_around(x, y)
                state['last_crop'] = crop
                redraw_selection(x, y, x1, y1, x2, y2)
                show_previews(crop)

        elif key == ord('r'):
            print("\n🔄 Recapturando pantalla en 3 segundos...")
            cv2.destroyAllWindows()
            time.sleep(3)
            capture_screen()
            cv2.namedWindow(WIN_MAIN,  cv2.WINDOW_NORMAL)
            cv2.namedWindow(WIN_CANNY, cv2.WINDOW_NORMAL)
            cv2.namedWindow(WIN_CROP,  cv2.WINDOW_NORMAL)
            cv2.setMouseCallback(WIN_MAIN, on_click)
            cv2.imshow(WIN_CANNY, blank)
            cv2.imshow(WIN_CROP,  blank)

    cv2.destroyAllWindows()

    # Summary
    print("\n" + "=" * 60)
    print("  RESUMEN DE TEMPLATES GUARDADOS")
    print("=" * 60)
    if os.path.isdir(TEMPLATE_DIR):
        total = 0
        for level in range(12, 20):
            d = os.path.join(TEMPLATE_DIR, f'L{level}')
            if os.path.isdir(d):
                n = len([f for f in os.listdir(d) if f.endswith('.png')])
                if n:
                    bar = "█" * n
                    print(f"   L{level}: {bar} ({n} template{'s' if n>1 else ''})")
                    total += n
        print(f"\n   Total: {total} templates en '{TEMPLATE_DIR}/'")
    else:
        print("   (No se guardó ningún template)")
    print("\n   Reinicia el bot para cargar los nuevos templates. ✅")


if __name__ == "__main__":
    main()