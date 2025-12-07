import time

import pyautogui
pyautogui.FAILSAFE = True

from configuration import Configuration
from controller import EmulatorController
from vision import VisionEngine

class FarmingBot:
    def __init__(self, config: Configuration, controller: EmulatorController, vision_engine: VisionEngine):
        self.cfg = config
        self.ctrl = controller
        self.vision = vision_engine
        self.ataques_totales = 0

    def buscar_batalla(self):
        print("\n🔎 Buscando...")
        self.ctrl.pulsar(self.cfg.KEY_ATACAR, 0.5)
        self.ctrl.pulsar(self.cfg.KEY_MODO_NORMAL, 0.5)
        self.ctrl.pulsar(self.cfg.KEY_BUSCAR, 0.5)
        print("☁️ Esperando nubes (5s)...")
        time.sleep(5)

    def desplegar_ejercito(self):
        # ==========================================
        # FASE 0: PREPARACIÓN Y ZOOM OUT (NUEVO)
        # ==========================================
        print(f"🔬 Unzooming (F3 x5)...")
        for _ in range(5):
            self.ctrl.pulsar(self.cfg.KEY_UNZOOM, 0.08)

        # Mueve la camara hacia abajo
        self.ctrl.mover_camara_sur()

        print("⚔️ ESTRATEGIA: CUADRADO (Héroes Juntos Abajo)")

        tropas_total = self.cfg.NUM_TROPAS
        tropas_lado = int(tropas_total / 4)

        # Obtenemos la lista de héroes ya calculada en Configuración
        heroes_activos = self.cfg.KEYS_HEROES

        # ==========================================
        # FASE 1: SUR (Cámara Abajo)
        # ==========================================
        print(f"⬇️ ATACANDO SUR...")

        if heroes_activos:
            print(f"🤴 Tirando {len(heroes_activos)} Héroes abajo...")
            for heroe in self.cfg.KEYS_HEROES:
                self.ctrl.pulsar(heroe, 0.08)
                # Usamos la coordenada exacta de la esquina de abajo
                self.ctrl.clic_en_punto(self.ctrl.cam_low_abajo)
        else:
            print("🤴 Sin Héroes (Modo Farming puro)...")

        # 2. Valquirias Sur
        self.ctrl.pulsar(self.cfg.KEY_TROPAS)
        time.sleep(0.08)

        # Lado Izq-Abajo
        for _ in range(tropas_lado):
            self.ctrl.lado_abajo_izq()
            time.sleep(0.08)
        # Lado Abajo-Der
        for _ in range(tropas_lado):
            self.ctrl.lado_abajo_der()
            time.sleep(0.08)

        # ==========================================
        # FASE 2: NORTE (Cámara Arriba)
        # ==========================================
        self.ctrl.mover_camara_norte()  # Sube a tope arriba-izquierda
        print(f"⬆️ ATACANDO NORTE...")

        if self.cfg.X_SIEGE_MACHINE and self.cfg.KEY_SIEGE_MACHINE:
            print(f"🚜 Tirando Máquina de Asedio ({self.cfg.KEY_SIEGE_MACHINE})...")
            self.ctrl.pulsar(self.cfg.KEY_SIEGE_MACHINE)
            time.sleep(0.08)
            self.ctrl.clic_en_punto(self.ctrl.cam_high_arriba)

        # Volver a pulsar la tecla de tropa tras mover cámara
        self.ctrl.pulsar(self.cfg.KEY_TROPAS)
        time.sleep(0.08)

        # Lado Izq-Arriba
        for _ in range(tropas_lado):
            self.ctrl.lado_arriba_izq()
            time.sleep(0.08)

        # Lado Arriba-Der (y el resto)
        resto = tropas_total - (tropas_lado * 3)
        for _ in range(resto):
            self.ctrl.lado_arriba_der()
            time.sleep(0.08)

        # ==========================================
        # FASE 3: REMATE
        # ==========================================
        print("✨ Hechizos...")
        self.ctrl.pulsar(self.cfg.KEY_HECHIZOS)
        time.sleep(0.08)
        for _ in range(self.cfg.NUM_HECHIZOS): self.ctrl.clic_camino_al_centro()

        print("⚡ Habilidades...")
        for k in self.cfg.KEYS_HEROES: self.ctrl.pulsar(k, espera=0.08)

    def terminar_y_volver(self):
        print(f"👀 VIGILANDO...")
        start = time.time()
        max_porcentaje = 0

        while True:

            if (time.time() - start) > self.cfg.TIEMPO_BATALLA:
                print(f"⏰ Tiempo límite {self.cfg.TIEMPO_BATALLA} alcanzado. Rindiéndose")
                self.rendirse()
                break

            lectura = self.vision.leer_porcentaje()

            if lectura > max_porcentaje:
                max_porcentaje = lectura
                print(f"   --> 📈 {max_porcentaje}%")

            if max_porcentaje >= 50:
                print(f"🏆 ¡{max_porcentaje}%! VICTORIA.")
                self.rendirse()
                break

            if self.vision.detectar_boton_fin():
                print("💀 FIN.")
                self.volver_casa_directo()
                break

            time.sleep(0.5)

    def rendirse(self):
        self.ctrl.pulsar(self.cfg.KEY_RENDIRSE, 0.5)
        self.ctrl.pulsar(self.cfg.KEY_CONFIRMAR, 0.5)
        self.volver_casa()

    def volver_casa(self):
        print("🏠 Casa...")
        self.ctrl.pulsar(self.cfg.KEY_VOLVER, 1.0)

    def volver_casa_directo(self):
        print("🏠 Casa (Directo)...")
        self.ctrl.pulsar(self.cfg.KEY_VOLVER, 1.0)

    def ejecutar_ciclo(self):
        print("🚀 BOT CUADRADO V2 INICIADO.")
        print("Maximiza MEmu. 10 segundos.")
        time.sleep(10)

        while True:
            try:
                self.ataques_totales += 1
                print(f"--- ATAQUE {self.ataques_totales} ---")
                self.buscar_batalla()
                self.desplegar_ejercito()
                self.terminar_y_volver()
                print("🔄 ...")
                time.sleep(1)
            except KeyboardInterrupt:
                break

if __name__ == "__main__":
    # Inicialización de Clases
    configuracion = Configuration()
    controlador = EmulatorController()
    vision = VisionEngine(configuracion)

    # El bot recibe las tres dependencias
    bot = FarmingBot(configuracion, controlador, vision)

    # Ejecución
    print("--- Iniciando bot ---")
    bot.ejecutar_ciclo()