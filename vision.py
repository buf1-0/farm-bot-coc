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
        try:
            img = pyautogui.screenshot(region=self.cfg.REGION_PORCENTAJE)
            img_np = np.array(img)
            img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            _, img_thresh = cv2.threshold(img_gray, 180, 255, cv2.THRESH_BINARY)
            img_inv = cv2.bitwise_not(img_thresh)
            img_final = cv2.resize(img_inv, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
            texto = pytesseract.image_to_string(img_final, config='--psm 7 outputbase digits')
            texto_limpio = ''.join(filter(str.isdigit, texto))
            if texto_limpio:
                valor = int(texto_limpio)
                if valor > 100: return 0
                return valor
        except:
            pass
        return 0

    def detectar_boton_fin(self):
        archivo = os.path.join(self.cfg.RUTA_IMG, 'fin_batalla.png')
        try:
            if pyautogui.locateOnScreen(archivo, confidence=0.8, grayscale=True):
                return True
        except:
            pass
        return False

    def esperar_fin_nubes(self):
        archivo = os.path.join(self.cfg.RUTA_IMG, 'terminar_batalla.png')
        while True:
            try:
                if pyautogui.locateOnScreen(archivo, confidence=0.8, grayscale=True):
                    return True
            except:
                pass
            time.sleep(0.5)

    def leer_recursos(self):
        oro = self._ocr_recurso(self.cfg.REGION_ORO)
        elixir = self._ocr_recurso(self.cfg.REGION_ELIXIR)
        return oro, elixir

    def _ocr_recurso(self, region):
        # LÓGICA DE BLOQUES DE 3 (BUCLE INFINITO)
        # No saldrá de aquí hasta leer un número menor de 30M.
        # LIMITE_REALISTA = 30000000

        while True:
            # 1. HACEMOS 3 LECTURAS
            bloque_lecturas = []
            for _ in range(3):
                val = self._procesar_imagen_ocr(region)
                if val > 0:
                    bloque_lecturas.append(val)
                time.sleep(0.05)

                # Si no hemos leído nada válido (>0) en este bloque, repetimos
            if not bloque_lecturas:
                continue

            # 2. ELEGIMOS EL VALOR MÁS SEGURO (El mínimo)
            mejor_valor = min(bloque_lecturas)

            # 3. VERIFICAMOS SI ES MENOR QUE X
            if mejor_valor < self.cfg.LIMITE_REALISTA:
                # ¡Es válido! Devolvemos este valor y salimos.
                return mejor_valor
            else:
                # Si sigue siendo mayor que 30M (lectura errónea gigante),
                # el bucle 'while True' volverá a empezar.
                pass

    def _procesar_imagen_ocr(self, region):
        try:
            img = pyautogui.screenshot(region=region)
            img_np = np.array(img)

            hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)
            lower_white = np.array([0, 0, 180])
            upper_white = np.array([180, 15, 255])

            mask = cv2.inRange(hsv, lower_white, upper_white)
            kernel = np.ones((2, 2), np.uint8)
            mask_clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            mask_inv = cv2.bitwise_not(mask_clean)
            img_final = cv2.resize(mask_inv, None, fx=3, fy=3, interpolation=cv2.INTER_LINEAR)
            img_final = cv2.copyMakeBorder(img_final, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)

            config = '--psm 7 -c tessedit_char_whitelist=0123456789'
            texto = pytesseract.image_to_string(img_final, config=config)

            texto_limpio = ''.join(filter(str.isdigit, texto))
            if texto_limpio:
                return int(texto_limpio)
        except:
            pass
        return 0

    def buscar_imagen(self, nombre_imagen, confianza=0.7):
        archivo = os.path.join(self.cfg.RUTA_IMG, nombre_imagen)
        try:
            pos = pyautogui.locateCenterOnScreen(archivo, confidence=confianza, grayscale=True)
            return pos
        except:
            return None