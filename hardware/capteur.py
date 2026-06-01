import ctypes
from picosdk.usbtc08 import usbtc08 as tc08
from datetime import datetime


class Capteur:
    def __init__(self, logger, lock):
        
        # Initialise et configure le TC-08 sans dépendances externes.
        self.chandle = ctypes.c_int16()
        self.is_open = False

        # Lock pour protéger écriture données
        self.lock = lock

        # Connection log
        self.logger = logger

        # dictionnaire de toutes les mesures effectuées
        self.all_mesures = {
            "Time": [],
            "temp1": [],
            "temp2": [],
            "temp3": [],
            "temp4": [],
            "temp5": [],
            "temp6": [],
            "temp7": [],
            "press_vide": []
        }

    def configure_channels(self):

        # 1. Ouverture de l'unité
        open_unit = tc08.usb_tc08_open_unit() # open le driver pico TC-08 et attribut un identifiant
        self.chandle = open_unit 

        # Vérification ouverture
        if self.chandle == 0:
            self.logger.error("No TC-08 unit found")
            return False, -1
        elif self.chandle == -1:
            self.logger.error("TC-08 fail to open")
            return False, -1

        else:            
            self.logger.info("TC-08 unit open") 
            # 2. set mains rejection to 50 Hz
            set_mains = tc08.usb_tc08_set_mains(self.chandle,0)
            # Verification rejection
            if set_mains == 0:
                self.logger.error("Main rejection not set correctly")
                return False, -1

            else: 
                self.logger.info("Main rejection set correctly") 
                # 3. Configuration des canaux
                # therocouples types and int8 equivalent # B=66 , E=69 , J=74 , K=75 , N=78 , R=82 , S=83 , T=84 , ' '=32 , X=88 
                thermotype_k = ctypes.c_int8(75) 
                capteur_voltage = ctypes.c_int8(88) 
                    
                # Canaux 1 à 7 : Températures (Thermocouple Type K)
                for i in range(1, 8):
                    set_channel = tc08.usb_tc08_set_channel(self.chandle, i, thermotype_k)
                    if set_channel == 1:
                        self.logger.info(f"Capteur {i} configuré en thermocouple K") 
                    else:
                        self.logger.error(f"Capteur {i} non configuré") 
                        return False, -1
                        
                # Canal 8 : Tension de sortie du capteur de pression (CP01)
                set_channel = tc08.usb_tc08_set_channel(self.chandle, 8, capteur_voltage)
                if set_channel == 1:
                    self.logger.info(f"Capteur {8} configuré en capteur X") 
                else:
                    self.logger.error(f"Capteur {8} non configuré") 
                    return False, -1

                # Récupère la plus petite intervalle
                _min_interval =tc08.usb_tc08_get_minimum_interval_ms(self.chandle)
                if _min_interval == 0:
                    self.logger.error("Intervale minimum inaccessible") 
                    return False, -1

                self.is_open = True                
                self.logger.info("TC-08 configuré avec succés.")
                return True, _min_interval
        

    def lire_instantane(self, is_pressure=False):
        
        if not self.is_open:
            self.logger.error("Aucun TC-08 configuré")
            return None

        # Buffer pour recevoir les 9 valeurs (index 0 = soudure froide, 1-8 = canaux)
        temp_buffer = (ctypes.c_float * 9)()
        overflow = ctypes.c_int16(0)
        units = tc08.USBTC08_UNITS["USBTC08_UNITS_CENTIGRADE"]

        # Capture unique les données au temps t et les range dans temp_buffer
        get_single = tc08.usb_tc08_get_single(self.chandle, ctypes.byref(temp_buffer), ctypes.byref(overflow), units)

        if get_single == 0:
            self.logger.warning("Erreur de lecture du TC-08")
            temp_buffer = [None]*8
            press_vide = None
        
        else:
            # Converti la valeur et l'enregistre si la pump est activée
            if is_pressure:
                if temp_buffer[8] > 0.5 and temp_buffer[8] < 4.5:
                    press_vide = 1/4* temp_buffer[8] - 9/8
                else:
                    press_vide = 'ERROR_SENSOR'

                press_vide = press_vide_simu()
            else:
                press_vide = None

        # Organisation des données dans un dictionnaire
        mesures = {
            "Time": datetime.now(),
            "temp1": temp_buffer[1],
            "temp2": temp_buffer[1], # 1 pour tester, 2 en situation réelle
            "temp3": temp_3_error(temp_buffer[3]), # fonction pour tester error_temp
            "temp4": temp_buffer[4],
            "temp5": temp_buffer[5],
            "temp6": temp_buffer[6],
            "temp7": temp_buffer[7],
            "press_vide": press_vide
        }
        
        # enregistrement des données dans le dictionnaire (protégéees avec lock)
        with self.lock:
            for id, value in mesures.items():
                self.all_mesures[id].append(mesures[id])
            
            # Renvoie toutes les mesures pour mise à jour affichage
        with self.lock:
            mesures["_all_mesures"] = {k: list(v) for k, v in self.all_mesures.items()}

        return mesures

    def close_connection(self):
        # Ferme la connexion proprement.
        if self.is_open:
            close_unit = tc08.usb_tc08_close_unit(self.chandle)
            if close_unit==1:
                self.is_open = False
                self.logger.info("TC-08 déconnecté.")
                return False
            else :
                self.logger.warning("TC-08 non déconnecté.")
                return True
        
    def reset_mesures(self):
        with self.lock:
            for i in self.all_mesures:
                self.all_mesures[i] = []
        self.logger.info("Mesures remises à zero")

    def get_all_mesures(self):
        with self.lock:
            return {k: list(v) for k, v in self.all_mesures.items()}
        

# ─────────────────────────────────────────────    
# SIMULATION PRESSION et TEMPERATURE
# ─────────────────────────────────────────────
def press_vide_simu():
    import random

    random_fail = random.randint(1,10)
    if random_fail == 10:
        press_vide = -0.3
    else:
        press_vide = -0.9 + random.random()*0.05

    return press_vide

def temp_3_error(buffer3):
    import random

    random_fail = random.randint(1,50)
    if random_fail == 50:
        temp3 = 300
    else:
        temp3 = buffer3

    return temp3