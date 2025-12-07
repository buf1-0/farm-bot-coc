import pyautogui
import time
import random

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