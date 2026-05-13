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
        self.ctrl.pulsar(self.cfg.KEY_ATACAR, 1)
        self.ctrl.pulsar(self.cfg.KEY_MODO_NORMAL, 1)
        self.ctrl.pulsar(self.cfg.KEY_BUSCAR, 1)

        print("☁️ Esperando nubes (Dinámico)...")
        encontrado = self.vision.esperar_fin_nubes()

    def desplegar_ejercito(self):
        # ==========================================
        # FASE 0: PREPARACIÓN Y ZOOM OUT (NUEVO)
        # ==========================================
        print(f"🔬 Unzooming (F3 x5)...")
        for _ in range(3):
            self.ctrl.pulsar(self.cfg.KEY_UNZOOM)

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
                self.ctrl.pulsar(heroe)
                # Usamos la coordenada exacta de la esquina de abajo
                self.ctrl.clic_en_punto(self.ctrl.cam_low_abajo)
        else:
            print("🤴 Sin Héroes (Modo Farming puro)...")

        # 2. Valquirias Sur
        self.ctrl.pulsar(self.cfg.KEY_TROPAS)

        # Lado Izq-Abajo
        for _ in range(tropas_lado):
            self.ctrl.lado_abajo_izq()
        # Lado Abajo-Der
        for _ in range(tropas_lado):
            self.ctrl.lado_abajo_der()

        # ==========================================
        # FASE 2: NORTE (Cámara Arriba)
        # ==========================================
        self.ctrl.mover_camara_norte()  # Sube a tope arriba-izquierda
        print(f"⬆️ ATACANDO NORTE...")

        if self.cfg.X_SIEGE_MACHINE and self.cfg.KEY_SIEGE_MACHINE:
            print(f"🚜 Tirando Máquina de Asedio ({self.cfg.KEY_SIEGE_MACHINE})...")
            self.ctrl.pulsar(self.cfg.KEY_SIEGE_MACHINE)
            self.ctrl.clic_en_punto(self.ctrl.cam_high_arriba)

        # Volver a pulsar la tecla de tropa tras mover cámara
        self.ctrl.pulsar(self.cfg.KEY_TROPAS)

        # Lado Izq-Arriba
        for _ in range(tropas_lado):
            self.ctrl.lado_arriba_izq()

        # Lado Arriba-Der (y el resto)
        resto = tropas_total - (tropas_lado * 3)
        for _ in range(resto):
            self.ctrl.lado_arriba_der()

        # ==========================================
        # FASE 3: REMATE
        # ==========================================
        print("✨ Hechizos...")
        self.ctrl.pulsar(self.cfg.KEY_HECHIZOS)
        for _ in range(self.cfg.NUM_HECHIZOS): self.ctrl.clic_camino_al_centro()

        print("⚡ Habilidades...")
        for k in self.cfg.KEYS_HEROES: self.ctrl.pulsar(k)

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

    def rendirse(self):
        self.ctrl.pulsar(self.cfg.KEY_RENDIRSE, 1)
        self.ctrl.pulsar(self.cfg.KEY_CONFIRMAR, 1)
        self.volver_casa()

    def volver_casa(self):
        print("🏠 Casa...")
        self.ctrl.pulsar(self.cfg.KEY_VOLVER, 1.0)

    def volver_casa_directo(self):
        print("🏠 Casa (Directo)...")
        self.ctrl.pulsar(self.cfg.KEY_VOLVER, 1.0)

    def gestionar_muros(self):
        if not self.cfg.AUTO_UPGRADE_WALLS:
            return

        print("💰 Leyendo recursos y escaneando muros...")
        contador_muros = 0

        while True:
            oro, elixir = self.vision.leer_recursos()
            gastar_elixir = elixir >= self.cfg.LIMITE_ELIXIR
            gastar_oro = oro >= self.cfg.LIMITE_ORO

            if not gastar_elixir and not gastar_oro:
                print("   --> 📉 Recursos bajo límite. A atacar.")
                break

            # Alejamos cámara para que el detector tenga más tiles visibles
            print("   🔍 Alejando cámara...")
            for _ in range(3):
                self.ctrl.pulsar(self.cfg.KEY_UNZOOM)
            time.sleep(0.5)

            print("   🧱 Escaneando muros (HSV)...")
            # Lista de (centro, nivel) — ya viene ordenada: nivel 12 primero
            targets = self.vision.buscar_muros(max_targets=10)

            if not targets:
                print("   --> ✅ Sin muros detectables. Pasando a atacar.")
                break

            muro_target, nivel_detectado = targets[0]
            print(f"   --> 🎯 Muro L{nivel_detectado} en {muro_target} (prioridad máxima)")

            # Decidir recurso: Como los muros 12+ aceptan oro y elixir,
            # simplemente usamos el recurso que haya superado el límite.
            # Si sobran los dos, priorizamos gastar Elixir.

            usar_elixir = gastar_elixir
            usar_oro = gastar_oro and not usar_elixir

            if not usar_elixir and not usar_oro:
                print("   --> Recurso disponible no coincide con nivel. Saltando.")
                break

            print(f"   --> Mejorando con {'ELIXIR' if usar_elixir else 'ORO'}...")

            self.ctrl.clic_en_punto(muro_target)
            time.sleep(0.1)

            for _ in range(3): # Nº de muros a mejorar
                self.ctrl.pulsar(self.cfg.KEY_VOLVER, espera=0.08)

            if usar_elixir:
                self.ctrl.pulsar(self.cfg.KEY_MEJORAR_ELIXIR, espera=0.2)
            else:
                self.ctrl.pulsar(self.cfg.KEY_MEJORAR_ORO, espera=0.2)

            self.ctrl.pulsar(self.cfg.KEY_CONFIRMAR, espera=1)

            # Verificación
            nuevo_oro, nuevo_elixir = self.vision.leer_recursos()
            exito = (usar_elixir and nuevo_elixir < elixir - 1000) or \
                    (usar_oro and nuevo_oro < oro - 1000)

            if exito:
                print(f"   --> ✅ ¡Muro L{nivel_detectado} mejorado! (#{contador_muros + 1})")
                contador_muros += 1
                self.ctrl.clic_en_punto((1840, 500))
                time.sleep(0.5)
            else:
                print("   --> ❌ Verificación fallida. Parada de seguridad.")
                raise pyautogui.FailSafeException("Fallo verificación muros")

            time.sleep(0.08)

    def esperarmenu(self):
        time.sleep(3)

    def ejecutar_ciclo(self):
        print("🚀 BOT CUADRADO V2 INICIADO.")
        print("Maximiza MEmu. 10 segundos.")
        time.sleep(10)

        while True:
            try:
                self.ataques_totales += 1

                self.gestionar_muros()

                print(f"--- ATAQUE {self.ataques_totales} ---")
                self.buscar_batalla()
                time.sleep(0.5)
                self.desplegar_ejercito()
                self.terminar_y_volver()
                print("🔄 ...")
                self.esperarmenu()
            except pyautogui.FailSafeException:
                raise
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"⚠️ Error recuperable: {e}")
                self.volver_casa_directo()

if __name__ == "__main__":
    # Inicialización de Clases
    configuracion = Configuration()
    controlador = EmulatorController()
    vision = VisionEngine(configuracion)

    # El bot recibe las tres dependencias
    bot = FarmingBot(configuracion, controlador, vision)

    # Ejecución
    print("--- Iniciando bot ---")
    try:
        bot.ejecutar_ciclo()
    except pyautogui.FailSafeException:
        print("\n🛑 BOT DETENIDO: Parada de Emergencia (Ratón en esquina).")