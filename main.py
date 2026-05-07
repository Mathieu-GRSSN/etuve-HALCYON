import time
from hardware.capteur import Capteur
from hardware.relais import Relais
from control.state_machine import StateMachine
from control.event_manager import EventManager

import threading
import tkinter as tk
from ihm.app_test import HalcyonIHM

from utils.logger import setup_logger

# Définition des logs 
logger = setup_logger()

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
    "_all_mesures": None,
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
}

# Initialisation de composants
capteurs = Capteur(data)
relais = Relais(RELAIS_ID)
window = tk.Tk()
ihm = HalcyonIHM(window, data)
sm = StateMachine(relais, capteurs,ihm, data, logger)
em = EventManager(logger)

def control_loop():
    while True:
            
        # Générer évenement
        event = em.generate_events(data)
        print(f'[main] event : {event}')
        if event != "no_transition":
            print(f'[main] event généré : {event}')

        # Appliquer transitions
        updates_sm = sm.transition(event, data)

        # Appliquer les modifications de data
        if "state" in updates_sm.keys():
            print(f'[main] updates : state {updates_sm.get("state", "None")}; previous state : {updates_sm.get("previous_state", "None")}')
        data.update(updates_sm)

        print(f'[main] data state : {data.get("state")}')

        if not data.get("min_interval_sensor"):
            wait_time = 0.1
        else :
            wait_time=data.get("min_interval_sensor")/1000
        time.sleep(wait_time)  # Attendre un peu avant la prochaine itération

# Lancer le thread de controle en arrière-plan
t = threading.Thread(target=control_loop, daemon=True)
t.start()

# Lancer l'IHM dans le thread principal (obligatoire pour Tkinter)
ihm.run()

relais.cleanup()