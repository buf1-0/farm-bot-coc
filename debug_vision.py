import cv2
import numpy as np
import pyautogui
import pytesseract
import time
import os
from configuration import Configuration

# Inicializar configuración
cfg = Configuration()
pytesseract.pytesseract.tesseract_cmd = cfg.RUTA_TESSERACT


def debug_ocr_guardar(nombre, region):
    print(f"\n--- Analizando {nombre} ---")
    print(f"📍 Coordenadas usadas: {region}")

    try:
        # 1. Captura
        img = pyautogui.screenshot(region=region)
        img_np = np.array(img)

        # GUARDAR IMAGEN ORIGINAL
        nombre_original = f"debug_{nombre}_1_original.png"
        img.save(nombre_original)
        print(f"📸 Guardada original: {nombre_original}")

        # 2. Preprocesamiento (LÓGICA BLINDADA IGUAL QUE EN VISION.PY)
        # Convertir a HSV
        hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)

        # Definir rango ESTRICTO de blanco puro
        # Bajamos la saturación máxima a 15 para eliminar cualquier rastro de color (verde/amarillo)
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 15, 255])

        # Crear máscara
        mask = cv2.inRange(hsv, lower_white, upper_white)

        # LIMPIEZA DE RUIDO (Morphology)
        # Esto elimina puntitos blancos sueltos que no sean números
        kernel = np.ones((2, 2), np.uint8)
        mask_clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # Invertir (Tesseract prefiere letras negras sobre fondo blanco)
        mask_inv = cv2.bitwise_not(mask_clean)

        # Resize x3
        img_final = cv2.resize(mask_inv, None, fx=3, fy=3, interpolation=cv2.INTER_LINEAR)

        # Añadir borde blanco
        img_final = cv2.copyMakeBorder(img_final, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)

        # GUARDAR IMAGEN PROCESADA
        nombre_procesada = f"debug_{nombre}_2_procesada.png"
        cv2.imwrite(nombre_procesada, img_final)
        print(f"🧪 Guardada procesada: {nombre_procesada}")

        # 3. Lectura OCR
        config_ocr = '--psm 7 -c tessedit_char_whitelist=0123456789'
        texto = pytesseract.image_to_string(img_final, config=config_ocr)
        print(f"🔢 TEXTO LEÍDO: '{texto.strip()}'")

    except Exception as e:
        print(f"❌ ERROR CRÍTICO en {nombre}: {e}")


print("🚀 Iniciando diagnóstico HSV Estricto...")
print("⏳ Tienes 3 segundos para poner el juego en primer plano...")
time.sleep(3)

# Prueba Oro
debug_ocr_guardar("ORO", cfg.REGION_ORO)
# Prueba Elixir
debug_ocr_guardar("ELIXIR", cfg.REGION_ELIXIR)

print("\n✅ FIN. Revisa los archivos .png nuevos.")
input("Pulsa ENTER para cerrar esto...")