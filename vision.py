import os
import time

import cv2
import numpy as np
import pyautogui
import pytesseract

from configuration import Configuration
from wall_detector import WallDetector


class VisionEngine:
    def __init__(self, config: Configuration):
        pytesseract.pytesseract.tesseract_cmd = config.RUTA_TESSERACT
        self.cfg = config

        # Detector HSV
        print("🧱 Cargando WallDetector...")
        self.wall_detector = WallDetector(config_path='wall_config.json')

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
        MAX_INTENTOS = 5  # Seguro de vida antibloqueos

        for intento in range(MAX_INTENTOS):
            bloque_lecturas = []
            for _ in range(3):
                val = self._procesar_imagen_ocr(region)

                # Solo guardamos el valor si tiene sentido (mayor que 0 y menor que tu límite)
                if 0 < val < self.cfg.LIMITE_REALISTA:
                    bloque_lecturas.append(val)
                time.sleep(0.05)

            if not bloque_lecturas:
                continue

            # Nos quedamos con el valor máximo para evitar cuando el OCR se "come" algún número
            mejor_valor = max(bloque_lecturas)
            return mejor_valor

        # Si después de 5 intentos el OCR no ha sido capaz de leer nada lógico,
        # devolvemos 0. Así el bot se irá a atacar en vez de dar error.
        return 0

    def _procesar_imagen_ocr(self, region):
        try:
            # 1. Captura
            img = pyautogui.screenshot(region=region)
            img_np = np.array(img)

            # 2. LA CLAVE MÁGICA: Hacer la imagen gigante (x4) ANTES de cualquier filtro
            img_grande = cv2.resize(img_np, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)

            # 3. Filtro de Blanco (HSV)
            hsv = cv2.cvtColor(img_grande, cv2.COLOR_RGB2HSV)
            lower_white = np.array([0, 0, 180])
            upper_white = np.array([180, 15, 255])
            mask = cv2.inRange(hsv, lower_white, upper_white)

            # 4. Invertir y poner un buen borde (Sin filtros que rompan los números)
            mask_inv = cv2.bitwise_not(mask)
            img_final = cv2.copyMakeBorder(mask_inv, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)

            # 5. Lectura OCR
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

    def buscar_muros(
        self,
        img_bgr=None,
        max_targets: int = 10
    ):
        """
        Devuelve lista de (centro_xy, nivel) ordenada por nivel ascendente.
        Compatibilidad: si solo necesitas centros, llama a
            [t for t, _ in vision.buscar_muros()]
        """
        return self.wall_detector.get_upgrade_targets(img_bgr, max_targets)