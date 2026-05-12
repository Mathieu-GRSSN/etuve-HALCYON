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
        
        temp_list = []
        for i in [1,7]:
            temp_list.append(data.get(f"temp{i}"))
            if data.get(f"temp{i}") is None:
                update['error_sensor_flag'] = True
                event='error_sensor'
                return event, update


        if data.get("force_stop_flag"):
            update["force_stop_flag"] = False
            event = 'force_stop'
            return event, update
        
        if max(temp_list)>=200:
            event='stop_heat'
            return event, update

        if data.get("min_interval_sensor") != None:
            if data.get("min_interval_sensor")<0:
                update['error_sensor_flag'] = True
                event='error_sensor'
                return event, update

        if data.get("state") == "ERROR_SENSOR":
            if data.get("error_sensor_flag"):
                event = "no_transition"

            else:
                event = 'end_error'
            return event, update

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

        elif data.get("state") == "HEATING":
            temp_min_tool = min(data.get("temp1"), data.get("temp2"))

            # # print(f'[event_manager] temp_min_tool : {temp_min_tool} temp cible : {data.get("TEMP_CIBLE")}')

            if temp_min_tool >= data.get("TEMP_CIBLE"):
                event = 'temperature_reached'

            else:
                event="no_transition"

            return event, update
            
        elif data.get("state") == "HOLD":
            elapsed = datetime.now() - data.get("time_start_hold")
            # # print(f'[event_manager] elapsed : {elapsed}')

            if elapsed.total_seconds() >= data.get("TIME_HOLD")*60: # temp_hold en minute, faire x60
                event = 'time_reached'
            
            else:
                event="no_transition"
            
            return event, update

        elif data.get("state") == "COOLING":
            temp_max_tool = min(data.get("temp1"), data.get("temp2"))
            if temp_max_tool < 30:
                event = 'temperature_low'

            else:
                event="no_transition"
                
            return event, update

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
        
