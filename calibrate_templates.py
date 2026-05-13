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
  5. Vuelve a la CONSOLA y escribe el nivel (12-19) + ENTER para guardar.
     (Si pulsas solo ENTER sin número, cancela sin guardar.)
  6. Repite para 2-3 variantes por nivel (distintos vecinos/iluminaciones).
  7. Pulsa Q en la ventana principal para salir y ver el resumen.

Controles del teclado (en la ventana principal)
─────────────────────────────────────────────────
  +  /  =    Ampliar el recorte (semiancho ++)
  -          Reducir el recorte
  R          Recapturar pantalla
  Q          Salir

FIX v2 — por qué ya no crashea
────────────────────────────────
  El crash original era porque input() se llamaba dentro del callback del
  ratón de OpenCV, lo que bloqueaba el hilo principal de las ventanas. Ahora
  el callback solo marca un "crop pendiente" en el estado global. El bucle
  principal detecta esa bandera, refresca las ventanas y ENTONCES llama a
  input() de forma segura.

Directorio de salida
─────────────────────
  wall_templates/
    L{nivel}/
      template_01.png
      template_02.png
      ...
"""

import cv2
import numpy as np
import pyautogui
import time
import os
import sys
import traceback

# ── Defaults (F3×3 zoom a 1080p) ────────────────────────────────────────────
DEFAULT_HALF_W = 30   # semiancho horizontal del recorte en px
DEFAULT_HALF_H = 20   # semialto del recorte en px

TEMPLATE_DIR   = 'wall_templates'
WIN_MAIN       = "Calibrador Templates | Clic=seleccionar | +/-=tamaño | R=recapturar | Q=salir"
WIN_CANNY      = "Preview Canny (lo que ve el matcher)"
WIN_CROP       = "Preview Crop (recorte en color)"

CANNY_LOW  = 40
CANNY_HIGH = 120

# ── Estado global ─────────────────────────────────────────────────────────────
state = {
    'img_bgr':      None,   # Captura actual (BGR)
    'img_display':  None,   # Copia con anotaciones para WIN_MAIN
    'last_crop':    None,   # Último recorte válido
    'last_xy':      None,   # (x, y) del último clic válido
    'half_w':       DEFAULT_HALF_W,
    'half_h':       DEFAULT_HALF_H,
    'pending_save': False,  # ← El callback pone True; el bucle lee y borra
}


# ════════════════════════════════════════════════════════════════════════════
# HELPERS SEGUROS
# ════════════════════════════════════════════════════════════════════════════

def safe_imshow(window: str, img: np.ndarray) -> None:
    """cv2.imshow envuelto en try/except para nunca propagar excepciones."""
    try:
        if img is not None and img.size > 0:
            cv2.imshow(window, img)
    except Exception as exc:
        print(f"[WARN] imshow('{window}'): {exc}")


def capture_screen() -> bool:
    """Captura la pantalla y actualiza el estado. Devuelve True si tiene éxito."""
    print("📸 Capturando pantalla...")
    try:
        screenshot = pyautogui.screenshot()
        img_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        if img_bgr is None or img_bgr.size == 0:
            print("❌ La captura devolvió una imagen vacía.")
            return False
        state['img_bgr']    = img_bgr
        state['img_display'] = img_bgr.copy()
        safe_imshow(WIN_MAIN, state['img_display'])
        print(f"   ✅ Captura lista ({img_bgr.shape[1]}×{img_bgr.shape[0]}px)")
        return True
    except Exception as exc:
        print(f"❌ Error capturando pantalla: {exc}")
        traceback.print_exc()
        return False


def crop_around(x: int, y: int):
    """
    Recorta una región centrada en (x, y).
    Devuelve (crop_bgr, (x1, y1, x2, y2)) o (None, None) si falla.
    """
    try:
        img = state['img_bgr']
        if img is None:
            return None, None

        h, w   = img.shape[:2]
        hw, hh = state['half_w'], state['half_h']

        x1, y1 = max(0, x - hw), max(0, y - hh)
        x2, y2 = min(w, x + hw), min(h, y + hh)

        # Garantizar que el recorte tiene al menos 4×4 px
        if (x2 - x1) < 4 or (y2 - y1) < 4:
            print(f"[WARN] Recorte demasiado pequeño en ({x},{y}): "
                  f"{x2-x1}×{y2-y1}px. Haz clic dentro de la imagen.")
            return None, None

        return img[y1:y2, x1:x2].copy(), (x1, y1, x2, y2)

    except Exception as exc:
        print(f"[WARN] crop_around falló: {exc}")
        return None, None


def show_previews(crop_bgr: np.ndarray) -> None:
    """Muestra el recorte en color y su mapa Canny. Nunca lanza excepciones."""
    if crop_bgr is None or crop_bgr.size == 0:
        return
    try:
        max_dim = max(crop_bgr.shape[:2])
        if max_dim == 0:
            return
        scale = max(1, 200 // max_dim)

        # Recorte en color
        big = cv2.resize(
            crop_bgr,
            (crop_bgr.shape[1] * scale, crop_bgr.shape[0] * scale),
            interpolation=cv2.INTER_NEAREST,
        )
        safe_imshow(WIN_CROP, big)

        # Canny
        gray  = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, CANNY_LOW, CANNY_HIGH)
        big_e = cv2.resize(
            edges,
            (edges.shape[1] * scale, edges.shape[0] * scale),
            interpolation=cv2.INTER_NEAREST,
        )
        vis = cv2.cvtColor(big_e, cv2.COLOR_GRAY2BGR)
        safe_imshow(WIN_CANNY, vis)

    except Exception as exc:
        print(f"[WARN] show_previews falló: {exc}")


def redraw_selection(x: int, y: int, x1: int, y1: int, x2: int, y2: int) -> None:
    """Redibuja la imagen principal con el recuadro de selección."""
    try:
        if state['img_bgr'] is None:
            return
        disp = state['img_bgr'].copy()
        cv2.rectangle(disp, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.circle(disp, (x, y), 3, (0, 0, 255), -1)
        cv2.line(disp, (x - 14, y), (x + 14, y), (0, 200, 255), 1)
        cv2.line(disp, (x, y - 14), (x, y + 14), (0, 200, 255), 1)
        state['img_display'] = disp
        safe_imshow(WIN_MAIN, disp)
    except Exception as exc:
        print(f"[WARN] redraw_selection falló: {exc}")


def save_template(crop_bgr: np.ndarray, level: int) -> str | None:
    """Guarda el recorte como PNG en wall_templates/L{level}/. Devuelve la ruta o None."""
    try:
        if crop_bgr is None or crop_bgr.size == 0:
            print("   ❌ El recorte está vacío. No se guardó.")
            return None
        level_dir = os.path.join(TEMPLATE_DIR, f'L{level}')
        os.makedirs(level_dir, exist_ok=True)
        existing = [f for f in os.listdir(level_dir) if f.endswith('.png')]
        idx      = len(existing) + 1
        filename = os.path.join(level_dir, f'template_{idx:02d}.png')
        ok = cv2.imwrite(filename, crop_bgr)
        if not ok:
            print(f"   ❌ cv2.imwrite falló para '{filename}'.")
            return None
        print(f"   💾 Guardado: {filename}  "
              f"({crop_bgr.shape[1]}×{crop_bgr.shape[0]}px)")
        return filename
    except Exception as exc:
        print(f"   ❌ save_template falló: {exc}")
        return None


def ask_level_in_console() -> int | None:
    """
    Pide el nivel al usuario en la consola (LLAMAR SOLO DESDE EL BUCLE PRINCIPAL,
    nunca desde un callback de OpenCV).
    Devuelve el nivel entero (12-19) o None para cancelar.
    """
    try:
        raw = input("   Nivel del muro (12-19) | ENTER=cancelar: ").strip()
        if not raw:
            print("   ↩ Cancelado.")
            return None
        level = int(raw)
        if not (12 <= level <= 19):
            print("   ⚠ Nivel fuera de rango 12-19. Cancelado.")
            return None
        return level
    except (ValueError, EOFError):
        print("   ↩ Entrada inválida. Cancelado.")
        return None
    except KeyboardInterrupt:
        print("\n   ↩ Interrumpido.")
        return None


# ════════════════════════════════════════════════════════════════════════════
# MOUSE CALLBACK — NO bloquea, solo anota en el estado
# ════════════════════════════════════════════════════════════════════════════

def on_click(event, x, y, flags, param):
    """
    Única responsabilidad: actualizar estado con el nuevo crop.
    Nunca llama a input() ni hace nada que bloquee el hilo de OpenCV.
    """
    if event != cv2.EVENT_LBUTTONDOWN:
        return

    try:
        if state['img_bgr'] is None:
            print("[WARN] Imagen no cargada todavía. Usa R para recapturar.")
            return

        crop, coords = crop_around(x, y)
        if crop is None:
            return  # crop_around ya imprimió el aviso

        x1, y1, x2, y2 = coords
        state['last_crop']    = crop
        state['last_xy']      = (x, y)
        state['pending_save'] = True   # ← señal para el bucle principal

        redraw_selection(x, y, x1, y1, x2, y2)
        show_previews(crop)

        print(f"\n📍 Clic en ({x}, {y})  "
              f"recorte: {crop.shape[1]}×{crop.shape[0]}px")
        print("   ➡  Vuelve a la CONSOLA y escribe el nivel (12-19) + ENTER.")

    except Exception as exc:
        print(f"[ERROR] on_click falló inesperadamente: {exc}")
        traceback.print_exc()


# ════════════════════════════════════════════════════════════════════════════
# INICIALIZACIÓN DE VENTANAS
# ════════════════════════════════════════════════════════════════════════════

def init_windows() -> None:
    blank = np.zeros((120, 120, 3), dtype=np.uint8)
    cv2.namedWindow(WIN_MAIN,  cv2.WINDOW_NORMAL)
    cv2.namedWindow(WIN_CANNY, cv2.WINDOW_NORMAL)
    cv2.namedWindow(WIN_CROP,  cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WIN_MAIN, on_click)
    safe_imshow(WIN_CANNY, blank)
    safe_imshow(WIN_CROP,  blank)
    if state['img_display'] is not None:
        safe_imshow(WIN_MAIN, state['img_display'])


# ════════════════════════════════════════════════════════════════════════════
# BUCLE PRINCIPAL
# ════════════════════════════════════════════════════════════════════════════

def resize_crop_and_refresh() -> None:
    """Recalcula el recorte con el tamaño actual y refresca previews."""
    if state['last_xy'] is None:
        return
    x, y = state['last_xy']
    crop, coords = crop_around(x, y)
    if crop is None:
        return
    x1, y1, x2, y2 = coords
    state['last_crop'] = crop
    redraw_selection(x, y, x1, y1, x2, y2)
    show_previews(crop)
    print(f"   🔍 Tamaño recorte: "
          f"{state['half_w']*2}×{state['half_h']*2}px")


def main():
    print("=" * 60)
    print("  CALIBRADOR DE TEMPLATES — Hybrid Wall Detector  v2")
    print("=" * 60)
    print(f"Zoom target: F3×3  |  Semitamaño inicial: "
          f"{DEFAULT_HALF_W}×{DEFAULT_HALF_H}px")
    print("\nTienes 5 segundos para cambiar a la ventana del juego...")
    time.sleep(5)

    if not capture_screen():
        print("❌ No se pudo capturar la pantalla. Saliendo.")
        sys.exit(1)

    init_windows()

    print("\n✅ Listo. Instrucciones:")
    print("   1. Haz clic en el CENTRO de un tile de muro en la ventana principal.")
    print("   2. Revisa el Preview Canny: debe mostrar el contorno del rombo.")
    print("   3. Vuelve aquí a la consola y escribe el nivel (12-19) + ENTER.")
    print("   4. Usa +/- para ajustar el tamaño del recorte si es necesario.")
    print("   5. Pulsa Q en la ventana principal para salir.\n")

    while True:
        try:
            key = cv2.waitKey(50) & 0xFF  # 50 ms → 20 fps de polling
        except Exception:
            key = 0xFF

        # ── Gestión de teclas ──────────────────────────────────────────────
        if key == ord('q'):
            print("\n👋 Saliendo...")
            break

        elif key in (ord('+'), ord('=')):
            state['half_w'] = min(state['half_w'] + 4, 120)
            state['half_h'] = min(state['half_h'] + 3, 80)
            resize_crop_and_refresh()

        elif key == ord('-'):
            state['half_w'] = max(state['half_w'] - 4, 6)
            state['half_h'] = max(state['half_h'] - 3, 4)
            resize_crop_and_refresh()

        elif key == ord('r'):
            print("\n🔄 Recapturando pantalla en 3 segundos...")
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass
            time.sleep(3)
            capture_screen()
            init_windows()

        # ── Gestión del crop pendiente (pide el nivel en consola) ──────────
        #
        # IMPORTANTE: Esta sección se ejecuta en el bucle principal,
        # NUNCA en el callback del ratón. Así OpenCV puede seguir
        # procesando eventos mientras el usuario escribe.
        #
        if state['pending_save']:
            state['pending_save'] = False  # consumir la señal primero
            crop = state['last_crop']

            if crop is None or crop.size == 0:
                print("[WARN] El recorte estaba vacío, no se puede guardar.")
                continue

            level = ask_level_in_console()
            if level is None:
                continue

            path = save_template(crop, level)
            if path:
                level_dir = os.path.join(TEMPLATE_DIR, f'L{level}')
                n = len([f for f in os.listdir(level_dir) if f.endswith('.png')])
                print(f"   📊 L{level} ahora tiene {n} template(s).")
                if n < 2:
                    print(f"   💡 Recomendado: añade 1-2 templates más de L{level} "
                          f"con distintos vecinos/iluminaciones.")
                # Refresca la ventana principal tras guardar
                if state['img_display'] is not None:
                    safe_imshow(WIN_MAIN, state['img_display'])

    # ── Cierre y resumen ─────────────────────────────────────────────────
    try:
        cv2.destroyAllWindows()
    except Exception:
        pass

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
        if total:
            print(f"\n   ✅ Total: {total} templates en '{TEMPLATE_DIR}/'")
            print("   Reinicia el bot para que los cargue automáticamente.")
        else:
            print("   (No se guardó ningún template en esta sesión.)")
    else:
        print("   (No se creó la carpeta de templates.)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Interrumpido por el usuario.")
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
    except Exception as exc:
        print(f"\n💥 Error fatal no esperado: {exc}")
        traceback.print_exc()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        sys.exit(1)