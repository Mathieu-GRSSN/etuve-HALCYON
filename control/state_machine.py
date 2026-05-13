from datetime import datetime
import copy
import utils.save as us
import utils.mail_sender as ms
import threading

class StateMachine:
    def __init__(self, relais, capteurs, ihm, data, logger, lock):
        self.data_initial = copy.deepcopy(data) # sauvegarde des valeurs initiles
        self.relais = relais
        self.capteurs = capteurs
        self.ihm = ihm
        self.states_fonc = {
            "IDLE": self.idle_state,
            "START": self.start_state,
            "HEATING": self.heating_state,
            "HOLD": self.hold_state,
            "COOLING": self.cooling_state,
            "STOP": self.stop_state,
            "ERROR_SENSOR": self.end_error,
            "ERROR_TEMP": self.end_error,
            "WARNING_PUMP": self.end_warning,
        }
        self.list_transition = ['cycle_validated','end_init', 'temperature_reached', 'time_reached','temperature_low', 'cycle_end', 'end_error', 'end_warning']
        self.list_transition_error = []
        self.logger = logger
        self.lock = lock
        self.previous_state_warning = None
        
    # -------
    # TRANSITION : vérifie la condition de transition d'état, renvoie les modifications de data
    # -------
    def transition(self, event, data_transition):
        self.data = data_transition
        update = {}

        if event == 'force_stop':

            self.logger.warning(f'Arrêt forcé')
            update["state"] = "STOP"
            self.on_enter("STOP")
            return update
            
        if event == 'stop_heat':

            self.logger.warning(f'Température maximale atteinte (200°C)')
            update = self.stop_heat() 
            return update
            
        if event == 'error_sensor':

            self.logger.error("ERROR SENSOR")
            update = self.on_enter("ERROR_SENSOR")
            update["state"] = "ERROR_SENSOR"
            return update
        
        if event == 'warning_pump':
            self.previous_state_warning = self.data["state"]
            self.logger.warning(f'Pression supérieure à -0.5 bar')
            self.on_enter("WARNING_PUMP")
            update["state"] = "WARNING_PUMP"
            return update

        if event in self.list_transition:
            new_state = self.states_fonc[self.data["state"]](event)

            if new_state != self.data["state"]:
                update = self.on_enter(new_state)
                update["state"] = new_state
                self.logger.info(f'Transition: {update["previous_state"]} -> {update["state"]}')
                return update
                    
                
        elif event == 'no_transition':
            update = self.in_state(self.data["state"])
            return update
                        
        else:
            print(f"Invalid event: {event}")
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
    
    def end_error(self, event):
        if event == "end_error":
            return "STOP"
        return self.data["state"]
    
    def end_warning(self, event):
        if event == "end_warning":
            return self.previous_state_warning
        return self.data["state"]

    # -------
    # ON ENTER : execute les actions en entrée d'état, renvoie les modifications de data
    # -------

    def on_enter(self, state):
        update={}
        update["previous_state"] = self.data["state"]
        update["state"] = self.data["state"]

        if state == "ERROR_SENSOR":
            if self.data["ventilation_activated"] or self.data["P1_activated"] or self.data["P2_activated"] or self.data["pump_activated"]:
                self.relais.all_relay_off()
                update["ventilation_activated"] = False
                update["P1_activated"] = False
                update["P2_activated"] = False
                update["pump_activated"] = False
            return update
        
        if state == "WARNING_PUMP":
            if self.data["P1_activated"] or self.data["P2_activated"]:
                self.relais.heating_Pmax_off()
                update["P1_activated"] = False
                update["P2_activated"] = False
            return update

        if state == "IDLE":
            previous_state = self.data["state"]
            update = copy.deepcopy(self.data_initial)
            update["previous_state"] = previous_state
            self.ihm.window.after(0, self.ihm._reset_ihm)
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

            # Récupère les données 
            all_mesures = self.capteurs.get_all_mesures()
            pressure = self.data["PUMP_ACTIVATION"]
            receiver = self.data["RECEIVER_MAIL"]

            # Lance le thread d'enregistrement et d'envoie mail (pour éviter de bloquer l'interface)
            threading.Thread(target=self._save_and_send,args=(all_mesures, pressure, receiver),daemon=True).start()

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
            
            mesure = self.capteurs.lire_instantane(self.data["PUMP_ACTIVATION"])
            update = mesure
            update["previous_state"] = self.data["state"]
            return update

        elif state == "HEATING":
            mesure = self.capteurs.lire_instantane(self.data["PUMP_ACTIVATION"])
            update = mesure
            update["previous_state"] = self.data["state"]

            # Si les chauffages sont arrétés (ex: 200°c dépassé) rallume
            if (not self.data["P1_activated"]) and (not self.data["P2_activated"]) :
                self.relais.heating_Pmax_on()
                update["P1_activated"] = True
                update["P2_activated"] = True

            return update

        elif state == "HOLD":
            mesure = self.capteurs.lire_instantane(self.data["PUMP_ACTIVATION"])
            update = mesure

            temp_min_tool = min(self.data["temp1"], self.data["temp2"])

            if temp_min_tool < self.data.get("TEMP_CIBLE") - 2 and not self.data["P1_activated"]:
                self.relais.heating_P1_on()
                update["P1_activated"] = True
                
            elif temp_min_tool > self.data.get("TEMP_CIBLE") + 2 and self.data["P1_activated"]:
                self.relais.heating_P1_off()
                update["P1_activated"] = False

            update["previous_state"] = self.data["state"]
            return update

        elif state == "COOLING":
            mesure = self.capteurs.lire_instantane(self.data["PUMP_ACTIVATION"])
            update = mesure

            temp_max_tool = max(self.data["temp1"], self.data["temp2"])

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
        mesure = self.capteurs.lire_instantane(self.data["PUMP_ACTIVATION"])
        update.update(mesure)
        return update
    
    def _save_and_send(self, all_mesures, pressure, receiver):
            # Enregistre sous PNG les courbes
            save_graph, filepath_png = us.save_graph(all_mesures,pressure)
            if save_graph == 1:
                self.logger.info(f'Données sauvegarder en PNG')
            elif save_graph == 0:
                self.logger.error(f"Enregistrement des données en PNG échoué")

            # Enregistre sous CSV les données
            save_mesures, filepath_csv = us.save_all_mesures(all_mesures)
            if save_mesures == 1:
                self.logger.info(f'Données sauvegarder en CSV')
            elif save_mesures == 0:
                self.logger.error(f"Enregistrement des données en CSV échoué")

            # Envoie par mail
            subject = datetime.now().strftime("Données étuve %d-%m-%Y")
            body = """
Bonjour,

Voici en pièce jointe les données de l'étuve.

Les formats sont :
- CSV : données brutes ;
- PNG : graphes avec les données.

Gros bisous,
L'étuve
            """
            send_mail = ms.send_email(receiver,subject,body,filepath_csv, filepath_png)
            if send_mail == 1:
                self.logger.info(f'PNG et CSV envoyé par mail à {receiver}')
            elif send_mail == 0:
                self.logger.error(f"Envoie PNG et CVS échoué")
