from datetime import datetime

class EventManager:
    def __init__(self, logger):
        self.start_hold_time = None
        self.logger = logger

    def generate_events(self, data):
        event = None
        update = {}

        # =========================
        # CYCLE
        # =========================
        
        # liste des température de data
        temp_list = []
        for i in range(1,8):
                temp_list.append(data.get(f"temp{i}"))

        # Si le flag d'arret forcé détecté -> force_stop
        if data.get("force_stop_flag"):
            update["force_stop_flag"] = False
            event = 'force_stop'
            return event, update
        
        # Si la machine n'est pas en été d'error sensor, vérifie s'il n'y a pas de problème
        if data.get('error_sensor_flag') == False :
            # Si une des valeurs est None (pas captée) -> error_sensor
            if None in temp_list:
                update['error_sensor_flag'] = True
                event='error_sensor'
                return event, update
            
            # Si l'interval minimum du capteur est <0 -> error_sensor (vérifie d'abord que pas None car réglage de base)
            if data.get("min_interval_sensor") != None:
                if data.get("min_interval_sensor")<0:
                    update['error_sensor_flag'] = True
                    event='error_sensor'
                    return event, update
                
        # Si la température maximale atteinte (200°C) -> stop_heat (vérifie d'abord None pour éviter problème lors error_sensor)
        if not None in temp_list:
            if max(temp_list)>=200:
                event='stop_heat'
                return event, update
                
        # Si l'état est error sensor -> no_transition si flag toujours activé / end_error si flag desactivé
        if data.get("state") == "ERROR_SENSOR":
            if data.get("error_sensor_flag"):
                event = "no_transition"
            else:
                event = 'end_error'
            return event, update
        
        # Si la pompe est activée, vérifie que la capteur n'est pas en erreur et vérifie que le pression n'est pas trop faible
        STATE_WARNING_PUMP = ["HEATING","HOLD","COOLING"]
        if data.get("pump_activated") and data.get("state") in STATE_WARNING_PUMP:

            print(f"[EM] press_vide : {data.get('press_vide')}")
            if data.get('press_vide') is not None:

                if data.get("press_vide") == "ERROR_SENSOR":
                    update['error_sensor_flag'] = True
                    event='error_sensor'
                    return event, update
                
                if data.get("press_vide") > -0.5 :
                    event = 'warning_pump'
                    update['warning_pump_flag'] = True
                    return event, update



        # Si état IDLE -> cycle_validated si flag cycle validated activé / no transition sinon
        elif data.get("state") == "IDLE":

            if data.get("cycle_validated_flag"):

                text_temp = f"Température cible : {data['TEMP_CIBLE']} min - Temps de maintien : {data['TIME_HOLD']} °C"
                text_pump = f"Activée - Température d'arret : {data['TEMP_STOP_PUMP']} °C" if data['PUMP_ACTIVATION'] else f'Désactivée'

                text_log = f"Cycle validé - {text_temp} - Pompe : {text_pump}"
                self.logger.info(text_log)

                update["cycle_validated_flag"] = False
                event = "cycle_validated"
            else:
                event = "no_transition"
            return event, update
         
         # Si état START -> end_init si flag end init activé et ventilation - sensor (- pompe) activés / no transition sinon
        elif data.get("state") == "START":
            
            if data.get("ventilation_activated") and data.get("sensor_activated") :

                if data.get("PUMP_ACTIVATION")  and not data.get("pump_activated"):
                    event="no_transition"
                else:
                    if data.get("end_init_flag"):
                        update["end_init_flag"] = False
                        event = 'end_init' 
                    else:
                        event="no_transition"       
            else:
                event="no_transition"
            return event, update

        # Si état HEATING -> temperature reached si temp outil atteint / no transition sinon
        elif data.get("state") == "HEATING":
            temp_min_tool = min(data.get("temp1"), data.get("temp2"))

            if temp_min_tool >= data.get("TEMP_CIBLE"):
                event = 'temperature_reached'

            else:
                event="no_transition"

            return event, update
            
        # Si état HOLD -> time reached si durée de maitien atteinte / no transition sinon
        elif data.get("state") == "HOLD":
            elapsed = datetime.now() - data.get("time_start_hold")

            if elapsed.total_seconds() >= data.get("TIME_HOLD")*60: # temp_hold en minute, faire x60
                event = 'time_reached'
            
            else:
                event="no_transition"
            
            return event, update

        # Si état COOLING -> temperature low si temp outil inférieur à 30°C / no transition sinon (mettre 42°C)
        elif data.get("state") == "COOLING":
            temp_max_tool = max(data.get("temp1"), data.get("temp2"))
            if temp_max_tool < 30:
                event = 'temperature_low'

            else:
                event="no_transition"
                
            return event, update

        # Si état STOP -> cycle_end si relais éteints / no transition sinon
        elif data.get("state") == "STOP":

            if not data.get("ventilation_activated") and not data.get("P1_activated") and not data.get("P2_activated") and not data.get("pump_activated"):
                event = 'cycle_end'
                update["cycle_finished_flag"] = True

            else:
                event="no_transition"

            return event, update

        else:
            event = 'no_transition'
            return event, update
        
