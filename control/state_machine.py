from datetime import datetime
import pandas as pd
import copy

class StateMachine:
    def __init__(self, relais, capteurs, ihm, data, logger):
        self.data_initial = copy.deepcopy(data) # sauvegarde des valeurs initiles
        self.relais = relais
        self.capteurs = capteurs
        self.ihm = ihm
        self.states = {
            "IDLE": self.idle_state,
            "START": self.start_state,
            "HEATING": self.heating_state,
            "HOLD": self.hold_state,
            "COOLING": self.cooling_state,
            "STOP": self.stop_state,
        }
        self.logger = logger
        
    # -------
    # TRANSITION : vérifie la condition de transition d'état, renvoie les modifications de data
    # -------
    def transition(self, event, data):
        self.data = data
        update = {}

        if event == 'force_stop':

            self.logger.warning(f'Arret forcé')

            update["state"] = "STOP"
            self.on_enter("STOP")
            return update
        
        if event == 'stop_heat':

            self.logger.warning(f'Température maximale atteinte (200°C)')

            update = self.stop_heat() 
            return update
        
        if event == 'error_sensor':

            self.logger.error("ERROR SENSOR")

            update["state"] = "ERROR_SENSOR"
            self.on_enter("ERROR_SENSOR")
            return update

        
        if event in ['cycle_validated','end_init', 'temperature_reached', 'time_reached','temperature_low', 'cycle_end']:
            new_state = self.states[self.data["state"]](event)

            if new_state != self.data["state"]:
                update = self.on_enter(new_state)
                update["state"] = new_state
                self.logger.info(f'Transition: {update["previous_state"]} -> {update["state"]}')
                
            
        elif event == 'no_transition':
            update = self.in_state(self.data["state"])
                    
        else:
            print(f"Invalid event: {event}")
            # retourner error event dans update ou rappeler transition avec event error
        return update

    # -------
    # STATES : modifie l'état, renvoie la modifications de l'état
    # -------
    def idle_state(self, event):
        if event == "cycle_validated":
            return "START"
        return self.data["state"]
    
    def start_state(self,event):
        if event == 'end_init':
            return "HEATING"
        return self.data["state"]

    def heating_state(self, event):
        if event == "temperature_reached":
            return "HOLD"
        return self.data["state"]
    
    def hold_state(self,event):
        if event == "time_reached":
            return "COOLING"
        return self.data["state"]
    
    def cooling_state(self,event):
        if event == "temperature_low":
            return "STOP"
        return self.data["state"]
 
    def stop_state(self, event):
        if event == "cycle_end":
            return "IDLE"
        return self.data["state"]

    # -------
    # ON ENTER : execute les actions en entrée d'état, renvoie les modifications de data
    # -------

    def on_enter(self, state):
        update={}
        update["previous_state"] = self.data["state"]
        update["state"] = self.data["state"]

        if state == "ERROR_SENSOR":
            
            return update

        if state == "IDLE":
            previous_state = self.data["state"]
            update = copy.deepcopy(self.data_initial)
            update["previous_state"] = previous_state
            print(f'[state_machine] on_enter IDLE -> previous_state : {update["previous_state"]}')
            # print(f'[state_machine] data réinitialisé -> {update}')
            self.ihm._reset_ihm()
            self.capteurs.reset_mesures()
            return update

        if state == "START":
            update["sensor_activated"], update["min_interval_sensor"] = self.capteurs.configure_channels()

            if not update["sensor_activated"] and update["min_interval_sensor"] < 0 :
                return update
            
            else:
                self.relais.ventilation_on()
                update["ventilation_activated"] = True

                if self.data.get("PUMP_ACTIVATION"):
                    self.relais.pump_on()
                    update["pump_activated"] = True
                
                return update

        elif state == "HEATING":
            self.relais.heating_Pmax_on()
            update["P1_activated"] = True
            update["P2_activated"] = True
            return update

        elif state == "HOLD":
            self.relais.heating_Pmax_off()
            update["P1_activated"] = False
            update["P2_activated"] = False
            update["time_start_hold"] = datetime.now()
            return update

        elif state == "COOLING":
            self.relais.heating_Pmax_off()
            update["P1_activated"] = False
            update["P2_activated"] = False
            return update

        elif state == "STOP":
            # Coupe la ventilation
            self.relais.ventilation_off()
            update["ventilation_activated"] = False

            # Ferme le TC-08
            update["sensor_activated"] = self.capteurs.close_connection()

            # Enregistre sous PNG les courbes
            self.ihm._save_graph()

            # Enregistre sous CSV les données
            self.capteurs.save_all_mesures()

            return update

    # -------
    # IN STATE : Execute les actions qui ont lieux durant l'état
    # -------

    def in_state(self,state):
        update={}
        update["state"] = self.data["state"]

        if state == "IDLE":
            update["previous_state"] = self.data["state"]
            return update

        elif state == "START":
            
            mesure = self.capteurs.lire_instantane()
            update = mesure
            update["previous_state"] = self.data["state"]
            return update

        elif state == "HEATING":
            mesure = self.capteurs.lire_instantane()
            update = mesure
            update["previous_state"] = self.data["state"]

            print(f'[state_machine] heatin on transition, état P1 : {self.data["P1_activated"]}, P2 : {self.data["P2_activated"]}')

            # Si les chauffages sont arrétés (ex: 200°c dépassé) rallume
            if (not self.data["P1_activated"]) and (not self.data["P2_activated"]) :
                self.relais.heating_Pmax_on()
                update["P1_activated"] = True
                update["P2_activated"] = True

                print(f"[state_machine] rallume tout")

            return update

        elif state == "HOLD":
            mesure = self.capteurs.lire_instantane()
            update = mesure

            temp_min_tool = min(self.data["temp1"], self.data["temp2"])
            # print(f'[state_machine] temp_min_tool : {temp_min_tool} temp cible : {self.data.get("TEMP_CIBLE")}')

            if temp_min_tool < self.data.get("TEMP_CIBLE") - 2:
                self.relais.heating_P1_on()
                update["P1_activated"] = True
                
            elif temp_min_tool > self.data.get("TEMP_CIBLE") + 2:
                self.relais.heating_P1_off()
                update["P1_activated"] = False

            update["previous_state"] = self.data["state"]
            return update

        elif state == "COOLING":
            mesure = self.capteurs.lire_instantane()
            update = mesure

            temp_max_tool = min(self.data["temp1"], self.data["temp2"])

            if self.data.get("pump_activated") and temp_max_tool < self.data.get("TEMP_STOP_PUMP"):
                self.relais.pump_off()
                update["pump_activated"] = False

            update["previous_state"] = self.data["state"]
            return update
            
        elif state == "STOP":
            # Ferme tous les relais
            self.relais.all_relay_off()

            # Mets les relais sur False si c'est pas le cas
            if self.data["ventilation_activated"]:
                update["ventilation_activated"] = False
            if self.data["P1_activated"]:
                update["P1_activated"] = False
            if self.data["P2_activated"]:
                update["P2_activated"] = False
            if self.data["pump_activated"]:
                update["pump_activated"] = False

            update["previous_state"] = self.data["state"]
            return update
        
        else:
            return update
    # ─────────────────────────────────────────────
    # UTILITAIRES
    # ─────────────────────────────────────────────

    def stop_heat(self):
        # Si température élevée : reste dans le meme état mais coupe relais et remesure température
        update = {}
        self.relais.heating_Pmax_off()
        update["P1_activated"] = False
        update["P2_activated"] = False
        mesure = self.capteurs.lire_instantane()
        update.update(mesure)
        return update