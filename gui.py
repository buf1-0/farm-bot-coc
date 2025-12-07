import tkinter as tk
from tkinter import ttk
import threading
from configuration import Configuration
from controller import EmulatorController
from vision import VisionEngine
from bot import FarmingBot


class BotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Clash Bot Launcher 🚜")
        self.root.geometry("350x450")

        # --- CONFIGURACIÓN DE COLORES (MODO OSCURO) ---
        bg_color = "#2b2b2b"
        fg_color = "#ffffff"
        accent_color = "#4CAF50"  # Verde bonito
        warning_color = "#FF5722"  # Naranja alerta

        self.root.configure(bg=bg_color)

        # Configurar Estilos (Usamos el tema 'clam' para tener control de colores)
        style = ttk.Style()
        style.theme_use('clam')

        # Estilo Genérico
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#4db6ac")
        style.configure("Warning.TLabel", font=("Segoe UI", 9, "bold"), foreground=warning_color)
        style.configure("Small.TLabel", font=("Segoe UI", 8), foreground="#aaaaaa")

        # Estilo Botones
        style.configure("TButton",
                        font=("Segoe UI", 10, "bold"),
                        background="#404040",
                        foreground="white",
                        borderwidth=1,
                        focuscolor="none")
        style.map("TButton", background=[('active', '#505050')])  # Efecto Hover

        # Estilo Checkbutton
        style.configure("TCheckbutton", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        style.map("TCheckbutton", background=[('active', bg_color)])

        # --- VARIABLE DE CONTROL ---
        self.bot_instance = None

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
        self.btn_start = ttk.Button(main_frame, text="🔥 INICIAR BOT 🔥", command=self.start_bot)
        self.btn_start.pack(pady=20, fill="x", ipady=5)

        # 5. Estado
        self.lbl_status = ttk.Label(main_frame, text="Estado: Esperando...", foreground="#aaaaaa")
        self.lbl_status.pack(pady=5)

        # Separador
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=15)

        # 6. INFO DE SEGURIDAD (FAILSAFE)
        lbl_failsafe = ttk.Label(main_frame,
                                 text="🚨 PARADA DE EMERGENCIA 🚨\nMueve el ratón bruscamente a una\nesquina de la pantalla para parar.",
                                 style="Warning.TLabel",
                                 justify="center")
        lbl_failsafe.pack(pady=5)

        # Nota final
        lbl_note = ttk.Label(main_frame, text="Cierra esta ventana para salir totalmente.", style="Small.TLabel")
        lbl_note.pack(side="bottom", pady=(10, 0))

    def start_bot(self):
        # Bloquear UI
        self.btn_start.config(state="disabled")
        self.combo_heroes.config(state="disabled")
        self.chk_siege.config(state="disabled")

        self.lbl_status.config(text="Estado: 🚀 EJECUTANDO...", foreground="#4CAF50")  # Verde

        # Recoger datos
        try:
            num_heroes = int(self.combo_heroes.get())
        except ValueError:
            num_heroes = 4

        usar_asedio = self.siege_var.get()

        # Inyectar Configuración
        config = Configuration()
        config.NUM_HEROES = num_heroes
        config.X_SIEGE_MACHINE = usar_asedio
        config.__post_init__()

        # Iniciar Bot en Hilo
        try:
            controller = EmulatorController()
            vision = VisionEngine(config)
            self.bot_instance = FarmingBot(config, controller, vision)

            t = threading.Thread(target=self.run_bot_logic)
            t.daemon = True
            t.start()
        except Exception as e:
            self.lbl_status.config(text=f"Error: {e}", foreground="red")
            self.btn_start.config(state="normal")

    def run_bot_logic(self):
        try:
            self.bot_instance.ejecutar_ciclo()
        except Exception as e:
            print(f"Bot detenido: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    # Centrar ventana
    w, h = 350, 480
    ws = root.winfo_screenwidth()
    hs = root.winfo_screenheight()
    x = (ws / 2) - (w / 2)
    y = (hs / 2) - (h / 2)
    root.geometry('%dx%d+%d+%d' % (w, h, x, y))

    app = BotGUI(root)
    root.mainloop()