import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

class Relais:
    def __init__(self, RELAIS_ID, logger):
        self.RELAIS_ID = RELAIS_ID
        self.logger = logger
        for relay, id in self.RELAIS_ID.items():
            GPIO.setup(id, GPIO.OUT)

            self.logger.info(f"GPIO{id} setup -> {relay} OK")
            # print(f'[relais] GPIO{id} setup -> {relay} OK')

    # Set ventilation to high (on)
    def ventilation_on(self):
        GPIO.output(self.RELAIS_ID.get("RELAY1_VENTILATION"), GPIO.HIGH)
        
        self.logger.info(f'RELAY1_VENTILATION - GPIO{self.RELAIS_ID.get("RELAY1_VENTILATION")} -> HIGH')
        # print("[relais] Ventilation ON")

    # Set ventilation to low (off)
    def ventilation_off(self):
        GPIO.output(self.RELAIS_ID.get("RELAY1_VENTILATION"), GPIO.LOW)

        self.logger.info(f'RELAY1_VENTILATION - GPIO{self.RELAIS_ID.get("RELAY1_VENTILATION")} -> LOW')
        # print("[relais] Ventilation OFF")

    # Set heating power two 15kW to high (on)
    def heating_P2_on(self):
        GPIO.output(self.RELAIS_ID.get("RELAY2_R15kW"), GPIO.HIGH)

        self.logger.info(f'RELAY2_R15kW - GPIO{self.RELAIS_ID.get("RELAY2_R15kW")} -> HIGH')
        # print("[relais] Heating 15kW ON")
        
    # Set heating power max 15kW to low (off)
    def heating_P2_off(self):
        GPIO.output(self.RELAIS_ID.get("RELAY2_R15kW"), GPIO.LOW)

        self.logger.info(f'RELAY2_R15kW - GPIO{self.RELAIS_ID.get("RELAY2_R15kW")} -> LOW')
        # print("[relais] Heating 15kW OFF")

    # Set heating power one 7.5kW to high (on)
    def heating_P1_on(self):
        GPIO.output(self.RELAIS_ID.get("RELAY3_R7.5kW"), GPIO.HIGH)

        self.logger.info(f'RELAY3_R7.5kW - GPIO{self.RELAIS_ID.get("RELAY3_R7.5kW")} -> HIGH')
        # print("[relais] Heating 7.5kW ON")
        
    # Set heating power one 7.5kW to low (off)
    def heating_P1_off(self):
        GPIO.output(self.RELAIS_ID.get("RELAY3_R7.5kW"), GPIO.LOW)

        self.logger.info(f'RELAY3_R7.5kW - GPIO{self.RELAIS_ID.get("RELAY3_R7.5kW")} -> LOW')
        # print("[relais] Heating 7.5kW OFF")

    # Set heating power max 22.5kW to high (on)
    def heating_Pmax_on(self):
        GPIO.output(self.RELAIS_ID.get("RELAY2_R15kW"), GPIO.HIGH)
        GPIO.output(self.RELAIS_ID.get("RELAY3_R7.5kW"), GPIO.HIGH)

        self.logger.info(f'RELAY2_R15kW - GPIO{self.RELAIS_ID.get("RELAY2_R15kW")} -> HIGH')
        self.logger.info(f'RELAY3_R7.5kW - GPIO{self.RELAIS_ID.get("RELAY3_R7.5kW")} -> HIGH')
        # print("[relais] Heating 22.5kW ON")
        
    # Set heating power max 22.5kW to low (off)
    def heating_Pmax_off(self):
        GPIO.output(self.RELAIS_ID.get("RELAY2_R15kW"), GPIO.LOW)
        GPIO.output(self.RELAIS_ID.get("RELAY3_R7.5kW"), GPIO.LOW)

        self.logger.info(f'RELAY2_R15kW - GPIO{self.RELAIS_ID.get("RELAY2_R15kW")} -> LOW')
        self.logger.info(f'RELAY3_R7.5kW - GPIO{self.RELAIS_ID.get("RELAY3_R7.5kW")} -> LOW')
        # print("[relais] Heating 22.5kW OFF")
        
    # Set pump to high (on)
    def pump_on(self):
        GPIO.output(self.RELAIS_ID.get("RELAY4_PUMP"), GPIO.HIGH)

        self.logger.info(f'RELAY4_PUMP - GPIO{self.RELAIS_ID.get("RELAY4_PUMP")} -> HIGH')
        # print("[relais] Pump ON")

    # Set pump to low (off)
    def pump_off(self):
        GPIO.output(self.RELAIS_ID.get("RELAY4_PUMP"), GPIO.LOW)

        self.logger.info(f'RELAY4_PUMP - GPIO{self.RELAIS_ID.get("RELAY4_PUMP")} -> LOW')
        # print("[relais] Pump LOW")

    # Set all relay to low (off)
    def all_relay_off(self):
        for relay in self.RELAIS_ID:
            GPIO.output(self.RELAIS_ID.get(relay), GPIO.LOW)

            self.logger.info(f'{relay} - GPIO{self.RELAIS_ID.get(relay)} -> LOW')
        # print(f'[relais] all GPIO LOW and clean up')

    def cleanup(self):
        self.all_relay_off()
        GPIO.cleanup()

        self.logger.info("GPIO cleanup done")
        #print("[relais] GPIO cleanup done")

