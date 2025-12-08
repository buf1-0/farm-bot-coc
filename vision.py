import pyautogui
import pytesseract
import cv2
import numpy as np
import os
import time
from configuration import Configuration


class VisionEngine:
    def __init__(self, config: Configuration):
        pytesseract.pytesseract.tesseract_cmd = config.RUTA_TESSERACT
        self.cfg = config

    def leer_porcentaje(self):
        """Captura la región, preprocesa con CV2 y lee el porcentaje."""
        try:
            img = pyautogui.screenshot(region=self.cfg.REGION_PORCENTAJE)
            img_np = np.array(img)

            # 1. Convertir a Gris
            img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

            # 2. Binarización (Umbral) para estabilizar el OCR
            _, img_thresh = cv2.threshold(img_gray, 180, 255, cv2.THRESH_BINARY)

            # 3. Aumentar escala
            img_final = cv2.resize(img_thresh, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)

            # 4. Leer con Tesseract
            texto = pytesseract.image_to_string(img_final, config='--psm 7 outputbase digits')

            texto_limpio = ''.join(filter(str.isdigit, texto))
            if texto_limpio:
                valor = int(texto_limpio)
                if valor > 100: return 0
                return valor
        except Exception as e:
            # print(f"Error OCR: {e}")
            pass
        return 0

    def detectar_boton_fin(self):
        # Busca la imagen del botón de fin de batalla en pantalla.
        archivo = os.path.join(self.cfg.RUTA_IMG, 'fin_batalla.png')
        try:
            # Si se encuentra el botón de fin/volver, devuelve True
            if pyautogui.locateOnScreen(archivo, confidence=0.8, grayscale=True):
                return True
        except:
            pass
        return False

    def esperar_fin_nubes(self):
        archivo = os.path.join(self.cfg.RUTA_IMG, 'terminar_batalla.png')

        # print("☁️ Esperando aldea (Modo Infinito)...")

        while True:
            try:
                # Si lo encuentra, rompe el bucle y devuelve True inmediatamente
                if pyautogui.locateOnScreen(archivo, confidence=0.8, grayscale=True):
                    return True
            except:
                pass

            time.sleep(0.5)  # Comprueba cada 0.5 segundos para no freír la CPU

    # --- NUEVO: LEER RECURSOS ---
    def leer_recursos(self):
        # Devuelve una tupla (oro, elixir).
        oro = self._ocr_recurso(self.cfg.REGION_ORO)
        elixir = self._ocr_recurso(self.cfg.REGION_ELIXIR)
        return oro, elixir

    def _ocr_recurso(self, region):
        try:
            img = pyautogui.screenshot(region=region)
            img_np = np.array(img)
            img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

            # Filtro agresivo para números blancos brillantes
            _, img_thresh = cv2.threshold(img_gray, 200, 255, cv2.THRESH_BINARY)

            # Invertir colores
            img_inv = cv2.bitwise_not(img_thresh)

            # Zoom al x3
            img_final = cv2.resize(img_inv, None, fx=3, fy=3, interpolation=cv2.INTER_LINEAR)

            # Configuración solo dígitos
            config = '--psm 7 -c tessedit_char_whitelist=0123456789'
            texto = pytesseract.image_to_string(img_final, config=config)

            texto_limpio = ''.join(filter(str.isdigit, texto))
            if texto_limpio:
                return int(texto_limpio)
        except:
            pass
        return 0

    # --- NUEVO: BUSCAR CUALQUIER COSA ---
    def buscar_imagen(self, nombre_imagen, confianza=0.7):
        # Busca una imagen en pantalla y devuelve su centro (x, y) o None.
        archivo = os.path.join(self.cfg.RUTA_IMG, nombre_imagen)
        try:
            pos = pyautogui.locateCenterOnScreen(archivo, confidence=confianza, grayscale=True)
            return pos # Devuelve (x, y)
        except:
            return None