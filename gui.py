import tkinter as tk
from tkinter import ttk
import threading
import pyautogui  # Necesario para detectar la excepción de Failsafe
from configuration import Configuration
from controller import EmulatorController
from vision import VisionEngine
from bot import FarmingBot


class BotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Farm Bot Launcher")
        self.root.geometry("350x480")

        try:
            root.iconbitmap("icono.ico")  # Debe estar junto al exe
        except:
            pass

        # --- CONFIGURACIÓN DE COLORES (MODO OSCURO) ---
        self.bg_color = "#2b2b2b"
        self.fg_color = "#ffffff"
        self.warning_color = "#FF5722"

        self.root.configure(bg=self.bg_color)

        # Configurar Estilos
        style = ttk.Style()
        style.theme_use('clam')

        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#4db6ac")
        style.configure("Warning.TLabel", font=("Segoe UI", 9, "bold"), foreground=self.warning_color)
        style.configure("Small.TLabel", font=("Segoe UI", 8), foreground="#aaaaaa")

        # Botones
        style.configure("TButton",
                        font=("Segoe UI", 10, "bold"),
                        background="#404040",
                        foreground="white",
                        borderwidth=1,
                        focuscolor="none")
        style.map("TButton", background=[('active', '#505050'), ('disabled', '#2b2b2b')])

        # Checkbutton
        style.configure("TCheckbutton", background=self.bg_color, foreground=self.fg_color, font=("Segoe UI", 10))
        style.map("TCheckbutton", background=[('active', self.bg_color)])

        self.bot_instance = None
        self.is_running = False

        # --- INTERFAZ ---
        main_frame = ttk.Frame(root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 1. Título
        lbl_title = ttk.Label(main_frame, text="CONFIGURACIÓN ATAQUE", style="Header.TLabel")
        lbl_title.pack(pady=(0, 20))

        # 2. Selección de Héroes
        frame_heroes = ttk.Frame(main_frame)
        frame_heroes.pack(pady=5, fill="x")

        lbl_heroes = ttk.Label(frame_heroes, text="Número de Héroes:")
        lbl_heroes.pack(side="left")

        self.combo_heroes = ttk.Combobox(frame_heroes, state="readonly", values=[0, 1, 2, 3, 4], width=5)
        self.combo_heroes.set(4)
        self.combo_heroes.pack(side="right")

        # 3. Máquina de Asedio
        self.siege_var = tk.BooleanVar(value=False)
        self.chk_siege = ttk.Checkbutton(main_frame, text="Usar Máquina de Asedio", variable=self.siege_var)
        self.chk_siege.pack(pady=15, anchor="w")

        # 4. Botón de Inicio
        self.btn_start = ttk.Button(main_frame, text="INICIAR BOT", command=self.start_bot)
        self.btn_start.pack(pady=20, fill="x", ipady=5)

        # 5. Estado
        self.lbl_status = ttk.Label(main_frame, text="Estado: Esperando...", foreground="#aaaaaa")
        self.lbl_status.pack(pady=5)

        # Separador
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=15)

        # 6. INFO DE SEGURIDAD
        lbl_failsafe = ttk.Label(main_frame,
                                 text="PARADA DE EMERGENCIA\nMueve el ratón bruscamente a una\nesquina de la pantalla para parar.",
                                 style="Warning.TLabel",
                                 justify="center")
        lbl_failsafe.pack(pady=5)

        lbl_note = ttk.Label(main_frame, text="Si el bot se para, podrás reiniciar aquí.", style="Small.TLabel")
        lbl_note.pack(side="bottom", pady=(10, 0))

    def start_bot(self):
        if self.is_running:
            return

        # 1. Bloquear UI
        self.toggle_inputs(enable=False)
        self.lbl_status.config(text="Estado: 🚀 EJECUTANDO...", foreground="#4CAF50")  # Verde
        self.is_running = True

        # 2. Recoger datos
        try:
            num_heroes = int(self.combo_heroes.get())
        except ValueError:
            num_heroes = 4

        usar_asedio = self.siege_var.get()

        # 3. Configuración
        config = Configuration()
        config.NUM_HEROES = num_heroes
        config.X_SIEGE_MACHINE = usar_asedio
        config.__post_init__()

        # 4. Iniciar Hilo
        try:
            controller = EmulatorController()
            vision = VisionEngine(config)
            self.bot_instance = FarmingBot(config, controller, vision)

            t = threading.Thread(target=self.run_bot_logic)
            t.daemon = True
            t.start()
        except Exception as e:
            self.update_status(f"Error inic: {e}", is_error=True)
            self.toggle_inputs(enable=True)

    def run_bot_logic(self):
        # Esta función corre en un hilo secundario.
        try:
            self.bot_instance.ejecutar_ciclo()
        except pyautogui.FailSafeException:
            # Detectamos la parada de emergencia
            self.root.after(0, lambda: self.update_status("🛑 DETENIDO POR EMERGENCIA", is_error=True))
        except Exception as e:
            # Detectamos cualquier otro error
            self.root.after(0, lambda: self.update_status(f"❌ Error: {e}", is_error=True))
        finally:
            # Siempre reactivamos los botones al final
            self.root.after(0, lambda: self.toggle_inputs(enable=True))
            self.is_running = False

    def update_status(self, text, is_error=False):
        # Actualiza el texto de estado de forma segura.
        color = self.warning_color if is_error else "#aaaaaa"
        self.lbl_status.config(text=f"Estado: {text}", foreground=color)

    def toggle_inputs(self, enable):
        # Habilita o deshabilita los controles.
        state = "normal" if enable else "disabled"
        # Combobox usa "readonly" para habilitado, "disabled" para deshabilitado
        combo_state = "readonly" if enable else "disabled"

        self.btn_start.config(state=state)
        self.chk_siege.config(state=state)
        self.combo_heroes.config(state=combo_state)

        if enable:
            self.btn_start.config(text="INICIAR BOT")
        else:
            self.btn_start.config(text="⏳ BOT CORRIENDO...")


if __name__ == "__main__":
    root = tk.Tk()
    w, h = 350, 480
    ws = root.winfo_screenwidth()
    hs = root.winfo_screenheight()
    x = (ws / 2) - (w / 2)
    y = (hs / 2) - (h / 2)
    root.geometry('%dx%d+%d+%d' % (w, h, x, y))

    app = BotGUI(root)
    root.mainloop()