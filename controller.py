import pyautogui
import time
import random
import pytesseract
import cv2
import numpy as np
import os

# Ajusta la ruta si es diferente en tu PC
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class EmulatorController:
    def __init__(self):
        # FASE 1: CÁMARA ABAJO IZQUIERDA
        self.cam_low_izq = (170, 270)
        self.cam_low_abajo = (950, 860)     # Aquí irán los héroes
        self.cam_low_der = (1780, 290)

        # FASE 2: CÁMARA ARRIBA IZQUIERDA
        self.cam_high_izq = (160, 680)
        self.cam_high_arriba = (960, 100)
        self.cam_high_der = (1690, 660)

        self.centro_pantalla_x = 960
        self.centro_pantalla_y = 540
        self.ruta_img = 'img/'

    def pulsar(self, tecla, espera=0.1):
        pyautogui.press(tecla)
        time.sleep(espera)

    def mover_camara_sur(self):
        print("🎥 Bajando cámara (Abajo-Izq)...")
        for _ in range(5):
            pyautogui.scroll(-1000)
            time.sleep(0.1)
        time.sleep(0.5)

    def mover_camara_norte(self):
        print("🎥 Subiendo cámara (Arriba-Izq)...")
        for _ in range(5):
            pyautogui.scroll(+1000)
            time.sleep(0.1)
        time.sleep(0.5)

    # --- NUEVO: Para tirar héroes en un punto fijo ---
    def clic_en_punto(self, punto):
        noise = 10
        x = int(punto[0] + random.randint(-noise, noise))
        y = int(punto[1] + random.randint(-noise, noise))
        pyautogui.click(x, y)
        time.sleep(random.uniform(0.02, 0.05))

    # --- DIBUJO DE LÍNEAS ---
    def clic_en_linea(self, p1, p2):
        t = random.uniform(0.02, 0.95)
        target_x = p1[0] + (p2[0] - p1[0]) * t
        target_y = p1[1] + (p2[1] - p1[1]) * t

        noise = 10
        x = int(target_x + random.randint(-noise, noise))
        y = int(target_y + random.randint(-noise, noise))

        pyautogui.click(x, y)
        time.sleep(random.uniform(0.02, 0.05))

    # --- ATAQUES FASE 1 (CÁMARA ABAJO) ---
    def lado_abajo_izq(self):
        self.clic_en_linea(self.cam_low_izq, self.cam_low_abajo)

    def lado_abajo_der(self):
        self.clic_en_linea(self.cam_low_abajo, self.cam_low_der)

    # --- ATAQUES FASE 2 (CÁMARA ARRIBA) ---
    def lado_arriba_izq(self):
        self.clic_en_linea(self.cam_high_izq, self.cam_high_arriba)

    def lado_arriba_der(self):
        self.clic_en_linea(self.cam_high_arriba, self.cam_high_der)

    # --- EXTRAS ---
    def clic_camino_al_centro(self):
        x = int(960 + random.randint(-150, 150))
        y = int(540 + random.randint(-150, 150))
        pyautogui.click(x, y)
        time.sleep(0.08)

    def leer_porcentaje(self, region):
        try:
            img = pyautogui.screenshot(region=region)
            img_np = np.array(img)

            img_gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

            _, img_thresh = cv2.threshold(img_gray, 180, 255, cv2.THRESH_BINARY)

            img_final = cv2.resize(img_thresh, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)

            texto = pytesseract.image_to_string(img_final, config='--psm 7 outputbase digits')

            texto_limpio = ''.join(filter(str.isdigit, texto))
            if texto_limpio:
                valor = int(texto_limpio)
                if valor > 100: return 0, texto_limpio
                return valor, texto_limpio
        except Exception as e:
            # print(f"Error OCR: {e}") # debug
            pass
        return 0, ""

    def detectar_boton_fin(self):
        archivo = os.path.join(self.ruta_img, 'fin_batalla.png')
        try:
            if pyautogui.locateOnScreen(archivo, confidence=0.8, grayscale=True): return True
        except:
            pass
        return False