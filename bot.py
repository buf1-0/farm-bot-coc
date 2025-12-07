import time
from configuration import Configuration
from controller import EmulatorController

class FarmingBot:
    def __init__(self, config: Configuration, controller: EmulatorController):
        self.cfg = config
        self.ctrl = controller
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
            self.ctrl.pulsar(self.cfg.KEY_UNZOOM, 0.1)

        # Mueve la camara hacia abajo
        self.ctrl.mover_camara_sur()

        print("⚔️ ESTRATEGIA: CUADRADO (Héroes Juntos Abajo)")

        tropa_total = self.cfg.NUM_TROPA
        tropa_lado = int(tropa_total / 4)

        # ==========================================
        # FASE 1: SUR (Cámara Abajo)
        # ==========================================
        print(f"⬇️ ATACANDO SUR...")

        # --- CAMBIO: TODOS LOS HÉROES JUNTOS EN LA ESQUINA ABAJO ---
        print("🤴 Tirando TODOS los Héroes abajo...")
        for heroe in self.cfg.KEYS_HEROES:
            self.ctrl.pulsar(heroe)
            # Usamos la coordenada exacta de la esquina de abajo
            self.ctrl.clic_en_punto(self.ctrl.cam_low_abajo)

        # 2. Valquirias Sur
        self.ctrl.pulsar(self.cfg.KEY_VALQUIRIAS)
        time.sleep(0.1)

        # Lado Izq-Abajo
        for _ in range(tropa_lado):
            self.ctrl.lado_abajo_izq()
            time.sleep(0.08)
        # Lado Abajo-Der
        for _ in range(tropa_lado):
            self.ctrl.lado_abajo_der()
            time.sleep(0.08)

        # ==========================================
        # FASE 2: MOVIMIENTO CÁMARA
        # ==========================================
        self.ctrl.mover_camara_norte()  # Sube a tope arriba-izquierda

        # ==========================================
        # FASE 3: NORTE (Cámara Arriba)
        # ==========================================
        print(f"⬆️ ATACANDO NORTE...")

        # Volver a pulsar la tecla de tropa tras mover cámara
        self.ctrl.pulsar(self.cfg.KEY_VALQUIRIAS)
        time.sleep(0.3)

        # Lado Izq-Arriba
        for _ in range(tropa_lado):
            self.ctrl.lado_arriba_izq()
            time.sleep(0.08)

        # Lado Arriba-Der (y el resto)
        resto = tropa_total - (tropa_lado * 3)
        for _ in range(resto):
            self.ctrl.lado_arriba_der()
            time.sleep(0.08)

        # ==========================================
        # FASE 4: REMATE
        # ==========================================
        print("✨ Hechizos...")
        self.ctrl.pulsar(self.cfg.KEY_HECHIZOS)
        time.sleep(0.1)
        for _ in range(self.cfg.NUM_HECHIZOS): self.ctrl.clic_camino_al_centro()

        print("⚡ Habilidades...")
        for k in self.cfg.KEYS_HEROES: self.ctrl.pulsar(k, espera=0.1)

    def terminar_y_volver(self):
        print(f"👀 VIGILANDO...")
        start = time.time()
        max_porcentaje = 0

        while True:

            if (time.time() - start) > self.cfg.TIEMPO_BATALLA:
                print("⏰ Tiempo.")
                self.rendirse()
                break

            lectura, _ = self.ctrl.leer_porcentaje(self.cfg.REGION_PORCENTAJE)
            if lectura > max_porcentaje:
                max_porcentaje = lectura
                print(f"   --> 📈 {max_porcentaje}%")

            if max_porcentaje >= 50:
                print(f"🏆 ¡{max_porcentaje}%! VICTORIA.")
                self.rendirse()
                break

            if self.ctrl.detectar_boton_fin():
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