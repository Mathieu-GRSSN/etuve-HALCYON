import time
from hardware.capteur import Capteur
from hardware.relais import Relais
from control.state_machine import StateMachine
from control.event_manager import EventManager

import threading
import tkinter as tk
from ihm.app import HalcyonIHM

from utils.logger import setup_logger

# Définition des logs 
logger = setup_logger()

# Gestion de la concurrence avec un lock pour protéger l'accès à la variable data
lock = threading.RLock()

# Défininition des relais avec leur borne GPIO
RELAIS_ID = {
    "RELAY1_VENTILATION": 14,
    "RELAY2_R15kW": 15,
    "RELAY3_R7.5kW": 18,
    "RELAY4_PUMP": 23,
}

# Initialisation des data communicantes entre les scripts
data = {
    "temp1": 0,
    "temp2": 0,
    "temp3": 0,
    "temp4": 0,
    "temp5": 0,
    "temp6": 0,
    "temp7": 0,
    "press_vide": 0,
    "_all_mesures": {},
    "TEMP_CIBLE": 40,
    "TIME_HOLD": 10,
    "PUMP_ACTIVATION": False,
    "TEMP_STOP_PUMP": 35,
    "time_start_hold": None,
    "state": "IDLE",
    "previous_state": None,
    "sensor_activated": False,
    "min_interval_sensor": None,
    "ventilation_activated": False,
    "P1_activated": False,
    "P2_activated": False,
    "pump_activated": False,
    "cycle_validated_flag": False,
    "end_init_flag": False,
    "force_stop_flag": False,
    "cycle_finished_flag": False,
    "error_sensor_flag": False,
}

# Initialisation de composants
capteurs = Capteur(data, logger, lock)
relais = Relais(RELAIS_ID, logger)
window = tk.Tk()
ihm = HalcyonIHM(window, data, lock)
sm = StateMachine(relais, capteurs,ihm, data, logger, lock)
em = EventManager(logger)



def control_loop():
    while True:
            
        # Générer évenement
        with lock:
            event, update_em = em.generate_events(data)
            data.update(update_em) # Applique les modif de data

        # Appliquer transitions
        updates_sm = sm.transition(event, data)
        with lock :
            data.update(updates_sm) # Applique les modif de data


        # Attendre un peu avant la prochaine itération
        wait_time = 0.1
        time.sleep(wait_time)  

try :
    # Lancer le thread de controle en arrière-plan
    t = threading.Thread(target=control_loop, daemon=True)
    t.start()

    # Lancer l'IHM dans le thread principal (obligatoire pour Tkinter)
    logger.info("Ouverture IHM")
    ihm.run()
    logger.info("Fermeture IHM")
except Exception as e:
    print(e)
    logger.error(f"Erreur dans le main")
finally:
    relais.cleanup()