# Système de contrôle de l'étuve Halcyon

Le projet vise à automatiser l'étuve Halcyon. Pour cela, le système de contrôle du chauffage ETV22 a été substitué par un nouveau système contrôlable via une application sur mesure. Ce système est contrôlé grâce à une interface-homme machine. L'**objectif** de ce programme, est de créer cette IHM et de contrôler les différents éléments électriques afin de pouvoir optimiser la chauffe des pièces.

## Description

L'application permet de piloter l'étuve via une interface graphique locale.

Elle assure :
- l'affichage en temps réel des capteurs (températures, pression)
- le contrôle des cycles de chauffe
- le pilotage des relais via GPIO
- la gestion de la machine à états
- l'enregistrement des données

L'application fonctionne en local sur la Raspberry Pi.

**Le système est composé des éléments suivants :**
- Raspberry PI 5 8Go (contrôle le système)
- Enregistreur de données Pico Technology TC-08 (7 entrées pour température étuve/pièce, 1 entrée pression dans la pièce), branché en usb
- Carte 8 relay (relay1: ventilation, relay2: résistance 15kW, relay 3: résistance 7.5kW, relay4: pompe à vide, relay5 : servomoteur arrivée d'air), branché et alimenté sur le GPIO
- Capteur de pression CP-01 (sortie analogique: 0.5-4.5V)
- Écran (affichage de l'interface homme machine)
- Clavier/Souris

**La répartition des capteurs du TC-08 est la suivante :**
| Identifiant entrée | Variable | Valeur rélevée | Capteur |
|-----|-----|-----|-----|
| 1 | temp1 | Température de la pièce | Thermocouple Type K |
| 2 | temp2 | Température de la pièce | Thermocouple Type K |
| 3 | temp3 | Température d'entrée | Thermocouple Type K |
| 4 | temp4 | Température de sortie | Thermocouple Type K |
| 5 | temp5 | Température du mur du fond | Thermocouple Type K |
| 6 | temp6 | Température du mur de droite | Thermocouple Type K |
| 7 | temp7 | Température du mur de gauche | Thermocouple Type K |
| 8 | press_vide | Pression dans la pièce | CP01 & |

**Fréquence d'acquisition**
- acquisition température : 10 Hz
- acquisition pression : 10 Hz

**Mapping GPIO**
| borne | GPIO | Fonction | Composant |
|-------|------|--------|--------|
| 2 | 5V Power | Alimentation relais | Carte 8 relay |
| 6 | Ground | Alimentation relais | Carte 8 relay |
| 8 | GPIO14 | ventilation | relay1 |
| 10 | GPIO15 | résistance 15kW | relay2 |
| 12 | GPIO18 | résistance 7.5kW | relay3 |
| 16 | GPIO23 | pompe à vide | relay4 |
| 18 | GPIO24 | servomoteur arrivée d'air | relay5 |

## Prérequis logiciel
- Python
- picosdk (https://github.com/picotech/picosdk-python-wrappers/tree/master), gestion du TC-08
- RPi.GPIO, gestion des bornes GPIO
- pandas, gestion CSV
- tkinter, gestion interface

## Architecture logicielle

- main.py : boucle principale
- state_machine.py : gestion des états
- hardware/relais.py : pilotage GPIO
- hardware/capteur.py : lecture TC-08
- ihm/app.py : interface tkinter
- utils/logger.py : gestion des logs
- utils/save.py : enregistrement des données en CSV et PNG
- utils/mail_sender.py : envoie le CSV et PNG par mail

# Fonctionnement du système

**L'interface homme-machine (IHM) permet de :**
- visualiser la variation des températures;
- visualiser la variation du vide;
- choisir le cycle de chauffe (température, durée, vide);
- choisir le répértoire de sauvegarde des données capteurs;
- activer la pompe à vide;
- lancer le cycle.

Il existe trois principaux cycles de chauffe :
| Température cible | Durée de maintien | Pompe      | Température d'arrêt de pompe en descente |
| ----------------- | ----------------- | ---------- | ---------------------------------------- |
| 120°              | 30 min            | activée    | 70°                                      |
| 120°              | 1h30              | activée    | 70°                                      |
| 180°              | 7h                | désactivée | -                                        |

Des cycles de chauffe personnalisés peuvent être choisis. Pour cela, il faut rentrer la température cible, la durée de maintien en température et si la pompe doit être mise en route.\
\
⚠️ La température cible correspond à la température la plus basse mesurée dans la pièce (minimum(temp1,temp2))\
⚠️ La température d'arrêt de pompe en descente correspond à la température la plus haute mesurée dans la pièce (maximum(temp1,temp2))\

**Le fonctionnement de l'étuve est le suivant :**
- choix courbe de chauffe sur l'IHM (standard ou optionnel)
- (optionnel) lancement pompe à vide (relay4 ON) 
- fermeture arrivée d'air frais (relay5 ON) 
- lancement ventilation (relay1 ON)
- lancement résistances en pleine puissance (relay2 et relay3 ON)
- lorsque température cible atteinte -> arrêt des résistances (relay2 et relay3 OFF)
- maintien en température autour de la température cible, oscillation de 2° en première puissance (relay3 ON/OFF)
- lorsque durée de maintien atteinte -> arrêt des résistances (relay2 et relay3 OFF) et ouverture arrivée d'air frais (relay5 OFF)
- (optionnel) lorsque température inférieure température d'arrêt de la pompe en descente -> arrêt de la pompe (relay4 OFF)
- lorsque la température en dessous de 40°C, arrêt de la ventilation (relay1 OFF)

## Sécurité
- Tous les relais OFF au démarrage
- Si température > 200°C arrêt immédiat résistances (relay2 et relay3 OFF)
- Si erreur -> arrêt immédiat résistances

# Machine à état
IDLE         → système arrêté\
START        → initialisation cycle\
HEATING      → montée en température\
HOLD         → maintien température\
COOLING      → refroidissement\
STOP         → fin normale\
ERROR_TEMP   → sécurité température maximale\
ERROR_PUMP   → sécurité état du vide\
ERROR_SENSOR → sécurité fonctionnement capteurs\

| état actuel     | Transition                              | état suivant   |
| --------------- | --------------------------------------- | -------------- |
| IDLE            | Lancement cycle                         | START          |
| START           | init terminée                           | HEATING        |
| HEATING         | min(temp1,temp2) >= TEMP_CIBLE          | HOLD           |
| HOLD            | time_hold >= TIME_HOLD                  | COOLING        |
| COOLING         | max(temp1, temp2) < 40°C                | STOP           |
| STOP            | enregistrements terminés                | IDLE           |
| HEATIG or HOLD  | max(temp) > 250°C                       | ERROR_TEMP     |
| HEATIG or HOLD or COOLING | press_vide > -0.5bar          | WARNING_PUMP   |
| START           | capteurs non fonctionnels               | ERROR_SENSOR   |
| START or HEATING or HOLD or COOLING | Arrêt utilisateur   | STOP           |
| ERROR_TEMP      | Erreur validée                          | STOP           |
| WARNING_PUMP    | Erreur validée & press_vide < -0.5 bar  | état précédent |
| ERROR_SENSOR    | Erreur validée                          | Arret cycle    |

## Etat intial (démarrage ou redémarrage)
- tous les relais OFF
- état système = IDLE
- aucun cycle repris automatiquement

## IDLE
**Objectif** :
- Définir cycle de chauffe

**Actions en entrée** :
- réinitilisation de data

**Actions pendant l'état** :
- Choix température cible → TEMP_CIBLE (int)
- Choix durée maintien → TIME_HOLD  (int)
- Choix état pompe → PUMP_ACTIVATION (boolean)
- Choix température arrêt pompe → TEMP_STOP_PUMP (int)
- Choix de l'adresse mail de reception

**Condition de sortie** :
- Utilisateur appuie sur le bouton "Valider cycle"
- Validation du cycle : cycle_validated

## START
**Objectif** :
- Lancer le système

**Actions en entrée d'état**:
- Mise en route ventilation (relay1 ON)
- Fermeture arrivée d'air (relay5 OFF)
- Ouverture TC-08
- Initialisation capteur → temp1, temp2, temp3, temp4, temp5, temp6, temp7, press_vide
- Affichage des mesures
- Si PUMP_ACTIVATION = True, mise en route pompe (relay4 ON)

**Actions pendant l'état** :
- mesure des capteurs

**Condition de sortie** :
- Ventilation activée
- Capteurs initialisés
- Si PUMP_ACTIVATION = True, pompe activée
- Utilisateur appuie sur le bouton "Lancer cycle"
- fin initialisation : end_init

## HEATING
**Objectif** :
- atteindre température cible

**Actions en entrée de l'état** :
- activer résistances pleine puissance (relay2 & relay3 ON)

**Actions pendant l'état** :
- mesure des capteurs
- limite la température maximale (200°c)

**Condition de sortie** :
- température minimum pièce atteint température cible (min(temp1,temp2) >= TEMP_CIBLE) : temperature_reached

## HOLD
**Objectif** : 
- maintenir en température

**Actions en entrée de l'état** :
- arrêt résistances (relay2 & relay3 OFF)
- enregistrement de l'heure de début : time_start_hold

**Actions pendant l'état** :
- logique ON/OFF première puissance sensibilité +/- 2°C (relay3 ON/OFF)
- mesure des capteurs
- limite la température maximale (200°c)


**Condition de sortie** :
- durée de maintien atteinte (time_now >= time_start_hold + TIME_HOLD) : time_reached

## COOLING
**Objectif** :
- refroidir

**Actions en entrée d'état** :
- arrêt résistances (relay2 & relay3 OFF)
- ouvrir arrivée air (relay5 ON)

**Actions pendant l'état** :
- gérer pompe, si max(temp1, temp2) < TEMP_STOP_PUMP, arrêt (relay4 OFF)
- mesure des capteurs


**Condition de sortie** :
- température de la pièce faible (max(temp1, temp2) < 40°C ) : temperature_low

## STOP
**Objectif** :
- Fin du cycle

**Actions en entrée d'état** :
- arrêt de la ventilation (relay1 OFF)
- ferme le TC-08
- Sauvegarde des données capteur en CSV, format : Time, temp1, temp2, temp3, temp4, temp5, temp6, temp7, press_vide
- Sauvegarde du fichier log
- envoie les fichier data.csv et log par mail

**Actions pendant l'état** :
- arrêt tous les relais (relay1, relay2, relay3, relay4 OFF)

**Condition de sortie** :
- Tous les relais arrêtés
- Enregistrement terminés : cycle_end

## ERROR_TEMP
**Objectif** :
- Sécurité maximale

**Actions en entrée d'état** :
- arrêt des résistances (relay2 & relay3 OFF)

**Condition de sortie** :
- Envoie d'un message d'alerte par email
- Validation fin erreur par l'utilisateur : error_end

## WARNING_PUMP
**Objectif** :
- Maintenir le vide

**Actions en entrée d'état** :
- envoie un message d'alerte

**Conditions de sortie** :
- la pression du vide redescend en dessous de -0.5bar (press_vide < -0.5 bar)
- Validation fin erreur par l'utilisateur : error_end

## ERROR_SENSOR
**Objectif** :
- Assurer le bon fonctionnement des capteurs

**Actions en entrée d'état** :
- envoie un message d'alerte si le TC-08 s'initalise mal
- arret relay

**Conditions de sortie** :
- Validation fin erreur par l'utilisateur : error_end

# Interface Homme -Machine

L'IHM est composé d'un seul écran principal composé de 6 cadres:
- **Etat du système** en haut à gauche
- **Capteurs** au milieu à gauche
- **Courbes** en bas à gauche
- **Choix du cycle** en haut à droite
- **Etats composants** au milieu à droite
- **Bouton** : en bas à droite

## Etat du système
**Objectif**:
- Afficher l'état du système

**Compositon**:
- Etat du système : en gras et grande police 
- Rond de couleur : 
    - "IDLE" et "START" en vert, 
    - autres état en rouge et clignotant

## Capteurs
**Objectif**:
- Afficher la valeurs des capteurs en temps réel

**Composition**:
- une case par données, deux lignes de quatres cases : 
    - Nom de la données en petite police en haut à droite
    - Valeur de la donnée au centre en grande police :
        - Pour les températures, unitée "°C" après la valeur,
        - Pour la pression, unitées "bar" après la valeur, si PUMP_ACTIVATION = False case grisée

## Courbes
**Objectif**:
- Afficher les valeurs des capteurs sous forme de courbe

**Composition**:
- une courbe affichant les données de capteurs :
    - si PUMP_ACTIVATION = True, 8 donnée (températures + pression). Un axe des ordonnées de chaque coté (Température °C, Pression bar)
    - si PUMP_ACTIVATION = False, 7 donnée (pression). Un seul axe des ordonnées (Température °C)
- un cadre avec les legendes correspondante à droite de la coubre
(les valeurs sont enregistrées dans self.all_mesures de la classe capteur)

## Choix du cycle
**Objectif**:
- Permettre le choix du cycle

**Composition**:
- une ligne de 4 cases :
    - une case TEMP_CIBLE pour choisir la température visée, case pour rentrer des nombres
     (uniquement les chiffres autorisées, pas la possibilitée de mettre plus que 200)
    - une case TEMP_HOLD pour choisir la durée de maintien en température, case pour rentrer des nombres
     (uniquement les chiffres autorisées)
    - une case PUMP_ACTIVATION pour choisir si la pompe doit etre activée, bouton ON/OFF
    - une case TEMP_STOP_PUMP pour choisir la température d'arret de la pompe, , case pour rentrer des nombres
     (uniquement les chiffres autorisées), grisée et bloquée si la case PUMP_ACTIVATION est sur OFF
- une case pour choisir l'emplacement de sauvegarde du fichier data
- un bouton "Valider cycle", lorsque appuyer, grise et bloque les cases au dessus, lance l'état "start", case grisé or état "IDLE"

## Etats composants
**Objectif**:
- Afficher l'état des composants'

**Composition**:
- Une colonne de 4 cases :
    - case avec un rond rouge et le nom du composant à coté, vert lorsqu'il est à l'arret, rouge lorsqu'il est en marche

## Bouton
**Objectif**:
- Bouton START / STOP

**Composition**:
- Bouton START / STOP

Rafraichissement : 0.1s