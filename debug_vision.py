import cv2
import numpy as np
import pyautogui
import pytesseract
import time
from configuration import Configuration

cfg = Configuration()
pytesseract.pytesseract.tesseract_cmd = cfg.RUTA_TESSERACT


def debug_ocr_guardar(nombre, region):
    print(f"\n--- Analizando {nombre} ---")
    try:
        # 1. Captura
        img = pyautogui.screenshot(region=region)
        img_np = np.array(img)
        img.save(f"debug_{nombre}_1_original.png")

        # 2. LA CLAVE: Hacer la imagen GIGANTE (x4) ANTES de filtrarla
        # Así no se pierden los detalles finos de los números (el fallo de antes)
        img_grande = cv2.resize(img_np, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)

        # 3. Filtro de Blanco (HSV)
        hsv = cv2.cvtColor(img_grande, cv2.COLOR_RGB2HSV)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 15, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)

        # 4. Invertir y poner un buen borde (Sin filtros que rompan los números)
        mask_inv = cv2.bitwise_not(mask)
        img_final = cv2.copyMakeBorder(mask_inv, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)

        cv2.imwrite(f"debug_{nombre}_2_procesada.png", img_final)

        # 5. Lectura OCR
        config_ocr = '--psm 7 -c tessedit_char_whitelist=0123456789'
        texto = pytesseract.image_to_string(img_final, config=config_ocr)

        print(f"🔢 TEXTO LEÍDO: '{texto.strip()}'")

    except Exception as e:
        print(f"❌ ERROR: {e}")


print("🚀 Iniciando diagnóstico DEFINITIVO...")
print("⏳ Tienes 3 segundos para ir al juego...")
time.sleep(3)

debug_ocr_guardar("ORO", cfg.REGION_ORO)
debug_ocr_guardar("ELIXIR", cfg.REGION_ELIXIR)

input("\n✅ FIN. Pulsa ENTER...")