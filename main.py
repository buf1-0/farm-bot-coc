from configuration import Configuration
from controller import EmulatorController
from bot import FarmingBot

if __name__ == "__main__":
    configuracion = Configuration()
    controlador = EmulatorController()
    bot = FarmingBot(configuracion, controlador)

    # El bot tiene 10 segundos de espera dentro de ejecutar_ciclo
    bot.ejecutar_ciclo()