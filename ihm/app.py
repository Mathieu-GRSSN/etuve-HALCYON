import tkinter as tk
from tkinter import ttk
import threading
import time
from distro import name
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from datetime import datetime


# ─────────────────────────────────────────────
#  PALETTE & STYLE
# ─────────────────────────────────────────────

BG          = "#f7f9fc"   # fond principal (blanc cassé)
BG2         = "#ffffff"   # cartes / panels
BG3         = "#eef2f7"   # zones secondaires
DISABLE_BG  = "#D8D8D8"   # champ grisé

ACCENT      = "#0077ff"   # bleu technique (principal)
ACCENT2     = "#00aaff"   # bleu clair

RED         = "#e63946"
ORANGE      = "#ffa825"  
YELLOW      = "#fdee1b" 
GREEN       = "#2ecc71"
BLUE        = "#1f6feb"
PURPLE      = "#800fdd"
PINK        = "#f51ebf"

FG          = "#1a1f2b"   # texte principal (quasi noir)
FG_DIM      = "#6b7280"   # texte secondaire
DISABLE_FG  = "#9A9A9A"   # texte champ grisé

BORDER      = "#d0d7e2"   # bordures légères

WARNING     = "#ffb020"   
ERROR       = "#ff2020"   

FONT_MONO   = ("Lexend", 10)
FONT_TITLE  = ("Lexend", 11, "bold")
FONT_BIG    = ("Lexend", 28, "bold")
FONT_MED    = ("Lexend", 14, "bold")
FONT_MED2   = ("Lexend", 18, "bold")
FONT_LABEL  = ("Lexend", 10, "bold")
FONT_BTN    = ("Lexend", 11, "bold")

# Couleur du rond et de l'état selon la machine à états
STATE_COLORS = {
    "IDLE": FG_DIM,
    "START": GREEN,
    "HEATING": GREEN,
    "HOLD": GREEN,
    "COOLING": GREEN,
    "STOP": FG_DIM,
    "ERROR_SENSOR": RED,
}

# états où le rond doit clignoter (hors IDLE/STOP)
BLINK_STATES = {"START","HEATING", "HOLD", "COOLING"}
BLINK_INTERVAL = 0.5

# 
TEMP_LIM = 200

# ─────────────────────────────────────────────
#  WIDGETS RÉUTILISABLES
# ─────────────────────────────────────────────

def make_card(parent, title=None, **kwargs):
    """Cadre avec bordure et titre optionnel."""
    frame = tk.Frame(parent, bg=BG2, highlightbackground=BORDER,
                     highlightthickness=1, **kwargs)
    if title:
        lbl = tk.Label(frame, text=f"── {title.upper()} ──",
                       bg=BG2, fg=FG_DIM, font=FONT_LABEL)
        lbl.pack(anchor="w", padx=10, pady=(8, 2))
    return frame


# ─────────────────────────────────────────────
#  CLASSE PRINCIPALE
# ─────────────────────────────────────────────

class HalcyonIHM:
    def __init__(self, window, data: dict, lock):
        self.window = window
        self.data = data          # dictionnaire partagé avec main.py
        self.lock = lock
        self._running = True
        self._blink_visible = True
        self._popup_error_exist = False
        self._last_blink = time.time()
        self._curve_plotted = False
        self._cycle_locked = False

        self._build_window() # Crée la fenetre 
        self._build_layout() # Rempli la fenetre
        self._start_refresh() # Rafraichi la fenetre


    # ────────────────────────────────────────────
    # FENETRE RACINE
    # ────────────────────────────────────────────
    def _build_window(self):
        self.window.title("HALCYON — Contrôle étuve")
        self.window.configure(bg=BG)
        self.height = 1080
        self.width = 1920
        self.window.geometry(f"{self.width}x{self.height}")
        self.window.attributes('-fullscreen', True)  # True pour plein écran, False pour fenêtré
        self.window.resizable(False, False)

        # Ferme la fenetre avec Ctrl+Esc et fullscreen avec F11
        self.window.bind("<Control-Escape>", lambda e: self._quit())
        self.window.bind("<F11>", lambda e: self._toggle_fullscreen())


        # Barre de titre personnalisée
        bar = tk.Frame(self.window, bg=BG3, height=36)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # Titre (à gauche) et horloge (à droite)
        tk.Label(bar, text="▶  HALCYON  //  CONTRÔLE ÉTUVE", bg=BG3, fg=ACCENT, font=FONT_TITLE).pack(side="left", padx=14, pady=8)
        self._lbl_clock = tk.Label(bar, text="", bg=BG3, fg=FG_DIM, font=FONT_LABEL)
        self._lbl_clock.pack(side="right", padx=14)


    # ────────────────────────────────────────────
    # GRILLE PRINCIPALE
    # ────────────────────────────────────────────
    def _build_layout(self):
        """
        Deux colonnes principales :
          col 0 (gauche, weight=60) : état + capteurs + courbes
          col 1 (droite, weight=40) : cycle + composants + journal
        """
        
        body = tk.Frame(self.window, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=(12, 12))

        # CONFIGURATION DES COLONNES
        body.columnconfigure(0, weight=55, uniform="group1")  # gauche
        body.columnconfigure(1, weight=45, uniform="group1")  # droite
        body.rowconfigure(0, weight=1)
        # Colonne gauche
        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self._build_state(left)
        self._build_data_display(left)
        self._build_data_curves(left)

        # Colonne droite
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")

        self._build_cycle_choice(right)
        self._build_components_activation(right)
        self._build_bonton_controller(right)

    # ────────────────────────────────────────────
    # ETAT SYSTEME
    # ────────────────────────────────────────────
    def _build_state(self, parent):
        """
        Contenu (de gauche à droite) :
          - Rond de couleur clignotant
          - Label grand texte de l'état (ex : IDLE, HEATING)
        """

        title = "état du système"
        card = make_card(parent, title)
        card.pack(fill="x", pady=(0, 6))

        row = tk.Frame(card, bg=BG2)
        row.pack(fill="x", padx=10, pady=(0, 10))

        # Indicateur LED
        self._canvas_led = tk.Canvas(row, width=32, height=32, bg=BG2, highlightthickness=0)
        self._canvas_led.pack(side="left", padx=(0, 10), pady=2)
        self._led = self._canvas_led.create_oval(4, 4, 28, 28, fill=FG_DIM, outline="")

        # Label état
        self._lbl_state = tk.Label(row, text="IDLE", bg=BG2, fg=FG_DIM, font=FONT_BIG)
        self._lbl_state.pack(side="left")

    # ────────────────────────────────────────────
    # CAPTEURS (2 lignes à 4 valeurs)
    # ────────────────────────────────────────────
    def _build_data_display(self, parent):
        """
        8 cases en grille 2x4 :
          Ligne 1 : temp1 | temp2 | temp3 | temp4
          Ligne 2 : temp5 | temp6 | temp7 | press_vide

        Chaque case :
          - nom du capteur en petit, aligné en haut à droite
          - valeur en grand au centre
          - unité après la valeur
        """

        title = "capteurs"
        card = make_card(parent, title)
        card.pack(fill="x", pady=(0, 6))

        inner = tk.Frame(card, bg=BG2)
        inner.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # CONFIGURATION DES LIGNES ET COLONNES
        inner.columnconfigure(0, weight=1, uniform="group1")  # gauche
        inner.columnconfigure(1, weight=1, uniform="group1")  # droite
        inner.columnconfigure(2, weight=1, uniform="group1")  # gauche
        inner.columnconfigure(3,weight=1, uniform="group1")  # droite
        inner.rowconfigure(0, weight=1)
        inner.rowconfigure(1, weight=1)

        # Ligne haute: TEMP 1-4

        self._lbl_temp1 = self._make_data_value(inner, "TEMP 1", "°C")
        self._lbl_temp1["frame"].grid(row=0, column=0, padx=(0, 6))

        self._lbl_temp2 = self._make_data_value(inner, "TEMP 2", "°C")
        self._lbl_temp2["frame"].grid(row=0, column=1, padx=(0, 6))

        self._lbl_temp3 = self._make_data_value(inner, "TEMP 3", "°C")
        self._lbl_temp3["frame"].grid(row=0, column=2, padx=(0, 6))

        self._lbl_temp4 = self._make_data_value(inner, "TEMP 4", "°C")
        self._lbl_temp4["frame"].grid(row=0, column=3, padx=(0, 6))


        # Ligne basse: TEMP 5-7 et PRESSION

        self._lbl_temp5 = self._make_data_value(inner, "TEMP 5", "°C")
        self._lbl_temp5["frame"].grid(row=1, column=0, padx=(0, 6))

        self._lbl_temp6 = self._make_data_value(inner, "TEMP 6", "°C")
        self._lbl_temp6["frame"].grid(row=1, column=1, padx=(0, 6))

        self._lbl_temp7 = self._make_data_value(inner, "TEMP 7", "°C")
        self._lbl_temp7["frame"].grid(row=1, column=2, padx=(0, 6))

        self._lbl_press = self._make_data_value(inner, "PRESSION", "bar")
        self._lbl_press["frame"].grid(row=1, column=3, padx=(0, 6))

    def _make_data_value(self, parent, label, unit):
        frame = tk.Frame(parent, bg=BG2)
        tk.Label(frame, text=label, bg=BG2, fg=FG_DIM, font=FONT_LABEL).pack(pady=0)
        val_frame = tk.Frame(frame, bg=BG2)
        val_frame.pack()
        lbl_val = tk.Label(val_frame, text="---", bg=BG2, fg=FG, font=FONT_BIG)
        lbl_val.pack(side="left")
        tk.Label(val_frame, text=unit, bg=BG2, fg=FG_DIM, font=FONT_LABEL).pack(
            side="left", anchor="s", pady=(0, 6))
        return {"frame": frame, "val": lbl_val}
    # ────────────────────────────────────────────
    # COURBES 
    # ────────────────────────────────────────────
    def _build_data_curves(self, parent):
        card = make_card(parent, "courbes")
        card.pack(fill="both", expand=True, pady=(0, 6))

        inner = tk.Frame(card, bg=BG2)
        inner.pack(fill="both", expand=True)

        self._fig = Figure(facecolor=BG2)
        self._ax_t = self._fig.add_subplot(111)
        self._ax_t.grid()

        self._ax_t.set_xlabel("Temps (s)", fontsize=10, color=FG_DIM)
        self._ax_t.set_ylabel("Températures (°C)", fontsize=10, color=FG_DIM)
        self._ax_p = self._ax_t.twinx()
        self._ax_p.set_ylabel("Pression (bar)", fontsize=10, color=FG_DIM)

        self._fig.suptitle("COURBES TEMPERATURES ET PRESSION", fontsize=15, color=FG_DIM)

        canvas = FigureCanvasTkAgg(self._fig, master=inner)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._chart_canvas = canvas

        # Couleurs des 7 courbes de température
        self._temp_colors = [
            RED, ORANGE, YELLOW, BLUE, GREEN, PURPLE, PINK
        ]
        self._temp_keys = [f"temp{i}" for i in range(1, 8)]
        self._temp_names = [
            "Temp 1", "Temp 2", "Temp 3", "Temp 4",
            "Temp 5", "Temp 6", "Temp 7"
        ]
        self._press_color = FG

        # Cr�er les lignes une seule fois, vides
        self._temp_lines = []
        for i, name in enumerate(self._temp_names):
            line, = self._ax_t.plot([], [], color=self._temp_colors[i],
                                    linewidth=1.2, label=name)
            self._temp_lines.append(line)

        self._press_line, = self._ax_p.plot([], [], color=self._press_color,
                                            linewidth=1.0, linestyle="--",
                                            label="Pression")

        self._ax_t.legend(loc="upper left", fontsize=8, facecolor=BG3,
                        framealpha=0.8, edgecolor="#CCCCCC")
        self._ax_p.legend(loc="upper right", fontsize=8, facecolor=BG3,
                        framealpha=0.8, edgecolor="#CCCCCC")

    # ────────────────────────────────────────────
    # CHOIX CYCLE
    # ────────────────────────────────────────────
    def _build_cycle_choice(self, parent):
        """
        6 cases en 4 lignes :
          Ligne 1 : TEMP_CIBLE | TIME_HOLD 
          Ligne 2 : PUMP_ACTIVATION | TEMP_STOP_PUMP 
          Ligne 3 : SEND_DATA_MAIL
          Ligne 4 : Bouton Valider cycle

        Cases TEMP_CIBLE, TIME_HOLD, TEMP_STOP_PUMP :
          - nom de la donnée en petit, aligné en haut à droite
          - zone de texte avec fleches de sélection
          - unité après la valeur
          - PUMP_ACTIVATION = OFF, TEMP_STOP_PUMP grisée

        Case PUMP_ACTIVATION :
          - nom de la donnée en petit, aligné en haut à droite
          - Bouton ON / OFF

        Case SEND_DATA_MAIL :
          - nom de la donnée en petit, aligné en haut à droite
          - zone de texte
        """
        title = "paramètres cycle"
        card = make_card(parent, title)
        card.pack(fill="both",expand=True, pady=(0, 6))

        # Variables
        self._var_temp = tk.IntVar(value=self.data.get("TEMP_CIBLE", 120))
        self._var_hold = tk.IntVar(value=self.data.get("TIME_HOLD", 30))
        self._var_pump = tk.BooleanVar(value=bool(self.data.get("PUMP_ACTIVATION", True)))
        self._var_temp_pump = tk.IntVar(value=self.data.get("TEMP_STOP_PUMP", 70))
        self._var_mail = tk.StringVar(value = "mathieu.grossin@halcyon-performance.com")

        # Vérification bonne saisie SpinBox
        def _validate_temp(new_value):
            if new_value == "":
                return True

            if not new_value.isdigit():
                return False

            if len(new_value) > 3:
                return False

            return int(new_value) <= TEMP_LIM
        vcmd_temp = (self.window.register(_validate_temp), "%P")

        def _validate_time(new_value):
            if new_value == "":
                return True

            if not new_value.isdigit():
                return False

            if len(new_value) > 3:
                return False

            return int(new_value) <= 999
        vcmd_time = (self.window.register(_validate_time), "%P")

        # Empeche une spinbx vide
        def _fix_empty_spinbox(event):
            widget = event.widget
            if widget.get() == "":
                widget.delete(0, "end")
                widget.insert(0, "0")  # ou valeur par d�faut

        # LIGNE 1
        row1 = tk.Frame(card, bg=BG2)
        row1.pack(side = "top",fill="x", expand=True, padx=10, pady=(0, 10))

        row1.columnconfigure(0, weight=50, uniform="group1")  # gauche
        row1.columnconfigure(1, weight=50, uniform="group1")  # droite
        row1.rowconfigure(0, weight=1)
        

        ## Température cible
        row_temp = tk.Frame(row1, bg=BG2)
        row_temp.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self._lbl_temp = tk.Label(row_temp, text="Température cible", bg=BG2, fg=FG_DIM, font=FONT_MED)
        self._lbl_temp.pack(pady=(4, 0))

        _center_frame_temp = tk.Frame(row_temp, bg=BG2)
        _center_frame_temp.pack(expand=True)

        self._spin_temp = tk.Spinbox(_center_frame_temp, from_=20, to=TEMP_LIM, increment=5,
            textvariable=self._var_temp, width=6,justify="center",
            bg=BG3, fg=FG, font=FONT_BIG,
            buttonbackground=BG3, relief="flat",
            highlightbackground=BORDER, highlightthickness=1, insertbackground=FG,
            validate="key", validatecommand=vcmd_temp)
        self._spin_temp.pack(side = "left")

        # Empeche spinbox vide
        self._spin_temp.bind("<FocusOut>", _fix_empty_spinbox)

        self._lbl_temp_unit = tk.Label(_center_frame_temp, text="°C", bg=BG2, fg=FG_DIM, font=FONT_MED)
        self._lbl_temp_unit.pack(side = "left", padx=4)
 
        ## Temps de maintien
        row_hold = tk.Frame(row1, bg=BG2)
        row_hold.grid(row=0, column=1, sticky="nsew", padx=(0, 6))

        self._lbl_hold = tk.Label(row_hold, text="Temps de maintien", bg=BG2, fg=FG_DIM, font=FONT_MED)
        self._lbl_hold.pack(pady=(4, 0))

        _center_frame_time = tk.Frame(row_hold, bg=BG2)
        _center_frame_time.pack(expand=True)

        self._spin_time = tk.Spinbox(_center_frame_time, from_=10, to=999, increment=5,
            textvariable=self._var_hold, width=6,justify="center",
            bg=BG3, fg=FG, font=FONT_BIG,
            buttonbackground=BG3, relief="flat",
            highlightbackground=BORDER, highlightthickness=1, insertbackground=FG,
            validate="key", validatecommand=vcmd_time)
        self._spin_time.pack(side="left")

        # Empeche spinbox vide
        self._spin_time.bind("<FocusOut>", _fix_empty_spinbox)

        self._lbl_time_unit = tk.Label(_center_frame_time, text="min", bg=BG2, fg=FG_DIM, font=FONT_MED)
        self._lbl_time_unit.pack(side="left", padx=4)
        
        # LIGNE 2
        row2 = tk.Frame(card, bg=BG2)
        row2.pack(side = "top",fill="x", expand=True, padx=10, pady=(0, 10))

        row2.columnconfigure(0, weight=50, uniform="group1")  # gauche
        row2.columnconfigure(1, weight=50, uniform="group1")  # droite
        row2.rowconfigure(0, weight=1)

        ## Bouton ON/OFF pompe
        row_btn_pump = tk.Frame(row2, bg=BG2)
        row_btn_pump.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self._lbl_pump = tk.Label(row_btn_pump, text="Activation pompe", bg=BG2, fg=FG_DIM, font=FONT_MED)
        self._lbl_pump.pack(pady=(4, 0))

        self._btn_pump = tk.Button(row_btn_pump, text="ON" if self._var_pump.get() else "OFF",
            width = 10, font=FONT_BIG, bd=0, padx=8, pady=4, cursor="hand2", 
            bg=GREEN if self._var_pump.get() else RED, fg = 'white',
            command=self._toggle_pump)
        self._btn_pump.pack()

        ## Température stop pump
        row_temp_pump = tk.Frame(row2, bg=BG2)
        row_temp_pump.grid(row=0, column=1, sticky="nsew", padx=(0, 6))

        self._lbl_temp_pump = tk.Label(row_temp_pump, text="Température arrêt pompe", bg=BG2, fg=FG_DIM, font=FONT_MED)
        self._lbl_temp_pump.pack(pady=(4, 0))

        _center_frame_pump = tk.Frame(row_temp_pump, bg=BG2)
        _center_frame_pump.pack(expand=True)

        self._spin_temp_hold = tk.Spinbox(_center_frame_pump, from_=20, to=TEMP_LIM, increment=5,
            textvariable=self._var_temp_pump, width=6, justify="center",
            bg=BG3, fg=FG, font=FONT_BIG,
            buttonbackground=BG3, relief="flat",
            highlightbackground=BORDER, highlightthickness=1, insertbackground=FG,
            validate="key", validatecommand=vcmd_temp)
        self._spin_temp_hold.pack(side="left")

        # Empeche spinbox vide
        self._spin_temp_hold.bind("<FocusOut>", _fix_empty_spinbox)

        tk.Label(_center_frame_pump, text="°C", bg=BG2, fg=FG_DIM, font=FONT_MED).pack(
            side="left", padx=4)

        # LIGNE 3
        row3 = tk.Frame(card, bg=BG2)
        row3.pack(side = "top",fill="x", expand=True, padx=10, pady=(0, 10))

        row3.columnconfigure(0, weight=50, uniform="group1")  # gauche
        row3.columnconfigure(1, weight=50, uniform="group1")  # droite
        row3.rowconfigure(0, weight=1)

        self._lbl_mail = tk.Label(row3, text="Email de reception des données", bg=BG2, fg=FG_DIM, font=FONT_MED)
        self._lbl_mail.pack(pady=(4, 0))

        self._entry_mail = tk.Entry(row3, textvariable=self._var_mail,  
                    font=FONT_LABEL, bg=BG3,fg=FG, insertbackground=FG, justify="center",
                    relief="flat", highlightbackground=BORDER, highlightthickness=1)
        self._entry_mail.pack(fill="both", padx=10, pady=10)

        # LIGNE 4
        row4 = tk.Frame(card, bg=BG2)
        row4.pack(side = "top",fill="x", expand=True, padx=10, pady=(0, 10))

        row4.columnconfigure(0, weight=50, uniform="group1")  # gauche
        row4.columnconfigure(1, weight=50, uniform="group1")  # droite
        row4.rowconfigure(0, weight=1)

        ## Bouton Valider cycle
        self._btn_validate = tk.Button(row4, text="VALIDER LE CYCLE",
            width = 10, font=FONT_BIG, bd=0, padx=8, pady=10, cursor="hand2", 
            bg=GREEN, fg = 'white',
            command=self._cycle_confirmation_popup)
        self._btn_validate.pack(fill="both", padx=10, pady=10)

        # Liste des zones de saisie et des boutons
        self._spin_cycle = [ self._spin_temp,  self._spin_time,  self._spin_temp_hold, self._entry_mail]
        
    # ────────────────────────────────────────────
    # ACTIVATION DES COMPOSANTS
    # ────────────────────────────────────────────
    def _build_components_activation(self,parent):
        """
        4 cases en colonne :
          Ligne 1 : ventilation_activated
          Ligne 2 : P1_activated 
          Ligne 3 : P2_activated
          Ligne 4 : pump_activated

        Chaque case :
          - Rond de couleur (vert=activé, gris=désactivé)
          - Label grand texte du composant (vert=activé, gris=désactivé)
        """
        title = "activation composants"
        card = make_card(parent, title)
        card.pack(fill="x", expand=True, pady=(0, 6))

        COMPS = [
            ("ventilation_activated", "Ventilation"),
            ("P1_activated",          "Puissance 1  (7.5 kW)"),
            ("P2_activated",          "Puissance 2  (15 kW)"),
            ("pump_activated",        "Pompe à vide"),
        ]

        self._comp_widgets = {}   # {key: (canvas, oval_id)}

        for key, label in COMPS:
            row_f = tk.Frame(card, bg=BG2)
            row_f.pack(fill="x", pady=3, padx=2)

            cvs = tk.Canvas(row_f, width=30, height=30, bg=BG2, highlightthickness=0)
            cvs.pack(side="left", padx=(40, 8))
            dot = cvs.create_oval(2, 2, 28, 28, fill=BORDER, outline="")

            _lab_component = tk.Label(row_f, text=label, font=FONT_BIG, bg=BG2, fg=BORDER)
            _lab_component.pack(side="left")

            self._comp_widgets[key] = (cvs, dot,_lab_component)

    # ────────────────────────────────────────────
    # BOUTON - START/STOP
    # ────────────────────────────────────────────
    def _build_bonton_controller(self, parent):
        """
        2 cases en ligne :
          Bouton START : VERT, active le cycle, active uniquement si état IDLE
          BOUTON STOP : ROUGE, arrête le cycle, active uniquement si état différent de IDLE
        """
        card = make_card(parent, "panneau de controle")
        card.pack(fill="x", expand=True, pady=(0, 6))

        row = tk.Frame(card, bg=BG2)
        row.pack(fill="x", expand=True, padx=10, pady=(0, 10))

        row.columnconfigure(0, weight=50, uniform="group1")  # gauche
        row.columnconfigure(1, weight=50, uniform="group1")  # droite
        row.rowconfigure(0, weight=1)

        text_btn = "START"
        state_btn = "active"
        fg_btn = "white"
        bg_btn = GREEN
         
        self._btn_start_stop = tk.Button(row, text=text_btn, state = state_btn,
                height = 30, font=FONT_BIG, bd=0, padx=8, pady=10, cursor="hand2", 
                bg=bg_btn, fg = fg_btn,
                command=self._on_start_stop)
        self._btn_start_stop.pack(fill="both", padx=10, pady=10)

    # ────────────────────────────────────────────
    # REFRAICHISSEMENT
    # ────────────────────────────────────────────
    def _start_refresh(self):

        with self.lock:
            snapshot_data = dict(self.data)


        self._refresh_popup_error(snapshot_data)
        self._refresh_time()
        self._refresh_state(snapshot_data)
        self._refresh_cycle_buttons(snapshot_data)
        self._refresh_components(snapshot_data)
        self._refresh_btn_start_stop(snapshot_data)
        self._refresh_data(snapshot_data)
        self._refresh_curve(snapshot_data)

        # fréquence rafraichissement
        self._refresh_freq = 100
        self.window.after(round(self._refresh_freq), self._start_refresh) 

    def _refresh_popup_error(self, snapshot_data):
        """
        Affiche un popup s'il y a une erreur
        """

        if not snapshot_data.get("error_sensor_flag"):
            self._popup_error_exist = False
            return
        else :
            _error_title = "Erreur capteur"

        if self._popup_error_exist:
            return
        else:
            self._popup_error_exist = True

            popup = tk.Toplevel(self.window, bg=BG)
            popup.title(_error_title)
            popup.geometry("600x400")
            popup.transient(self.window)
            popup.grab_set()
            popup.focus_set()
            popup.protocol("WM_DELETE_WINDOW", lambda: self._on_validate_error(popup))

            inner = tk.Frame(popup, bg=BG2)
            inner.pack(fill="both", expand=True, padx=1, pady=1)

            # Texte de confirmation
            text_label = tk.Frame(inner, bg=BG2)
            text_label.pack(fill="both", expand=True, padx=10, pady=10)

            text_label.columnconfigure(0, weight=1) 
            text_label.rowconfigure(0, weight=1)    

            text = """
Une erreur a été détectée avec le TC-08.

Veuillez vérifier les branchements et relancer le cycle.

Valider pour fermer la fenêtre."""

            tk.Label(text_label, text=text,
                    bg=BG2, fg=ERROR, font=FONT_MED2,
                    wraplength=550, justify="center", anchor="center").grid(row = 0, column = 0)

            # Boutons
            btn_frame = tk.Frame(inner, bg=BG2)
            btn_frame.pack(fill="x", padx=10, pady=10)

            btn_frame.columnconfigure(0, weight=1) 
            btn_frame.rowconfigure(0, weight=1) 


            btn_yes = tk.Button(btn_frame, text="Valider", 
                                width = 10, font=FONT_BIG, bd=0, padx=8, pady=10, cursor="hand2", 
                                bg=GREEN, fg = 'white',
                                command=lambda:self._on_validate_error(popup))
            btn_yes.grid(row = 0, column = 0, padx=(6, 6), pady=4)

    def _refresh_time(self):
        # Horloge
        self._lbl_clock.config(text=time.strftime("%d/%m/%Y  %H:%M:%S"))

    def _refresh_state(self, snapshot_data):

        # État du sytème
        state = snapshot_data.get("state")
        color = STATE_COLORS.get(state)
        self._lbl_state.config(text=state, fg=color)

        # Clignotement LED selon état du sytème
        if state in BLINK_STATES:
            now = time.time()
            if now - self._last_blink >= BLINK_INTERVAL:
                self._blink_visible = not self._blink_visible
                self._last_blink = now
            fill_color = color if self._blink_visible else BG2
        else:
            self._blink_visible = True
            self._last_blink = time.time()
            fill_color = color
        self._canvas_led.itemconfig(self._led, fill=fill_color)

    def _refresh_data(self, snapshot_data):
        '''
        Données affichées uniquement hors IDLE et STOP
        '''
        if snapshot_data["state"] == "IDLE":
            data_active = False
        elif snapshot_data["state"] == "STOP":
            data_active = False
        else:
            data_active = True

        # Redessiner seulement si un nouveau point est arrivé
        mesures = snapshot_data.get("_all_mesures")
        n = len(mesures.get("Time", []))
        if n <= getattr(self, "_last_plot_data_n", -1):
            return  # rien de nouveau, on ne redessine pas
        self._last_plot_data_n = n

        if data_active:
            # Températures et pression
            t = [0]
            text_temp = [0]
            for i in range(1,8):
                t.append(snapshot_data.get(f"temp{i}", 0))
                if t[i] is None:
                    text_temp.append("None")
                else:
                    text_temp.append(f"{t[i]:.1f}")

            self._lbl_temp1["val"].config(text=text_temp[1])
            self._lbl_temp2["val"].config(text=text_temp[2])
            self._lbl_temp3["val"].config(text=text_temp[3])
            self._lbl_temp4["val"].config(text=text_temp[4])
            self._lbl_temp5["val"].config(text=text_temp[5])
            self._lbl_temp6["val"].config(text=text_temp[6])
            self._lbl_temp7["val"].config(text=text_temp[7])
            if snapshot_data["PUMP_ACTIVATION"]:
                press = snapshot_data.get("press_vide", 0)
                if press is None:
                    text_press = "None"
                else:
                    text_press = f"{press:.2f}"
            else:
                text_press="---"
            self._lbl_press["val"].config(text=text_press)

        else:
            self._lbl_temp1["val"].config(text="---")
            self._lbl_temp2["val"].config(text="---")
            self._lbl_temp3["val"].config(text="---")
            self._lbl_temp4["val"].config(text="---")
            self._lbl_temp5["val"].config(text="---")
            self._lbl_temp6["val"].config(text="---")
            self._lbl_temp7["val"].config(text="---")
            self._lbl_press["val"].config(text="---")
        
    def _refresh_curve(self, snapshot_data):
        # Redessine les courbes que hors IDLE STOP
        if snapshot_data["state"] not in ["IDLE", "STOP"]:
            mesures = snapshot_data.get("_all_mesures")
            if not mesures:
                return
 
            # Redessiner seulement si un nouveau point est arrivé
            n = len(mesures.get("Time", []))
            if n <= getattr(self, "_last_plot_curve_n", -1):
                return  # rien de nouveau, on ne redessine pas
            self._last_plot_curve_n = n

            self._update_plot(snapshot_data)
            self._chart_canvas.draw_idle()

    def _refresh_components(self, snapshot_data):
        """
        Gris  = composant à l'arret  (False)
        Vert = composant en marche  (True)
        """
        now = time.time()

        if now - self._last_blink >= BLINK_INTERVAL:
            self._blink_visible = not self._blink_visible
            self._last_blink = now

        for key, (cvs, dot, lbl) in self._comp_widgets.items():
            active = bool(snapshot_data.get(key, False))
            # Label
            if active:
                color_lbl = GREEN
            else:
                color_lbl = BORDER
            lbl.config(fg=color_lbl)
            # LED clignotante
            if active:
                color = GREEN if self._blink_visible else BG2
            else:
                color = BORDER
            # LED
            cvs.itemconfig(dot, fill=color)

    def _refresh_cycle_buttons(self, snapshot_data):
        """
            Si state différent de IDLE, choix cycle grisé
        """

        state_entry = "normal" if self._var_pump.get() else "disabled"
        self._spin_temp_hold.config(state=state_entry, bg=BG3 if self._var_pump.get() else DISABLE_BG)

        if snapshot_data['state'] != snapshot_data['previous_state']:
            if snapshot_data["state"] == "IDLE":
                self._cycle_locked = False
                self._set_cycle_lock(False)
            else:
                self._cycle_locked = True
                self._set_cycle_lock(True)

    def _refresh_btn_start_stop(self,snapshot_data):
        
        if snapshot_data["state"] == "IDLE":
            state_btn = "disabled"
            text_btn = "START"
            bg_btn = DISABLE_BG
            fg_btn = DISABLE_FG
        
        elif snapshot_data["state"] == "START":
            if self._curve_plotted == True:
                text_btn = "START"
                state_btn = "normal"
                fg_btn = "white"
                bg_btn = GREEN
            else:
                return

        else:
            text_btn = "STOP"
            
            if snapshot_data["state"] == "STOP":
                state_btn = "disabled"
                bg_btn = DISABLE_BG
                fg_btn = DISABLE_FG
            else:
                state_btn = "normal"
                bg_btn = RED
                fg_btn = "white"
            
        self._btn_start_stop.config(text=text_btn, state=state_btn, bg=bg_btn, fg=fg_btn)

    # ─────────────────────────────────────────────    
    # ACTIONS UTILISATEUR
    # ─────────────────────────────────────────────
    def _toggle_pump(self):
        """Bascule l'état du bouton pompe ON ? OFF."""
        self._var_pump.set(not self._var_pump.get())
        on = self._var_pump.get()
        self._btn_pump.config(
            text="ON" if on else "OFF",
            bg=GREEN if on else RED)

    def _on_validate(self, popup):
        """
        Valide le cycle :
          - Lit et vérifie les saisies
          - Met à jour data
          - Verrouille le formulaire
        """

        with self.lock:
            # Mise à jour du dictionnaire partagé
            self.data["TEMP_CIBLE"]      = int(self._var_temp.get())
            self.data["TIME_HOLD"]       = int(self._var_hold.get())
            self.data["PUMP_ACTIVATION"] = self._var_pump.get()
            self.data["TEMP_STOP_PUMP"]  = int(self._var_temp_pump.get()) if self._var_pump.get() else 0

            # signal pour l'event_manager
            self.data["cycle_validated_flag"] = True

        # Verrouillage du formulaire
        self._cycle_locked = True
        self._set_cycle_lock(True)

        popup.destroy()

    def _on_validate_error(self, popup):
        """
        Valide le cycle :
          - Lit et vérifie les saisies
          - Met à jour data
          - Verrouille le formulaire
        """
        with self.lock:
            # Mise à jour du dictionnaire partagé
            self.data["sensor_activated"]       = False
            self.data["min_interval_sensor"]    = None

            # signal pour l'event_manager
            self.data["error_sensor_flag"] = False

        popup.destroy()
        self._popup_error_exist = False
        self._quit()
 
    def _not_validated(self, popup):
        popup.destroy()

    def _on_start_stop(self):
        '''
        Si text = "START" lance le cycle
        Si text = "STOP" stop le système
        '''
        if self._btn_start_stop.cget("text") == "START":
            with self.lock:
                self.data["end_init_flag"] = True   # signal pour démarrer le chauffage
        else:
            with self.lock:
                self.data["force_stop_flag"] = True      # signal d'arret d'urgence

    def _quit(self):
        """Fermeture propre : coupe le refresh, détruit la fenetre, passe en état stop"""
        with self.lock:
            self.data["force_stop_flag"] = True 

        self._running = False
        self.window.destroy()
        
    def _toggle_fullscreen(self):
        """Bascule plein écran / fenêtre (utile pour le debug)."""
        is_fullscreen = self.window.attributes('-fullscreen')
        self.window.attributes('-fullscreen', not is_fullscreen)

    # ─────────────────────────────────────────────
    # UTILITAIRES
    # ─────────────────────────────────────────────

    def _update_plot(self, snapshot_data):
        mesures = snapshot_data.get("_all_mesures")
        if not mesures:
            self._curve_plotted = False
            return
        
        times_raw = mesures.get("Time", [])
        if len(times_raw) < 2:
            self._curve_plotted = False
            return
        self._curve_plotted = True

        for i, key in enumerate(self._temp_keys):
            vals = mesures.get(key, [])

            if vals:
                self._temp_lines[i].set_data(times_raw,vals)
     
        # Pression
        if snapshot_data["PUMP_ACTIVATION"]:
            self._fig.suptitle("COURBES TEMPERATURES ET PRESSION", fontsize=15, color=FG_DIM)
            # Crée l'axe pression s'il existe pas
            if self._ax_p is None:
                self._ax_p = self._ax_t.twinx()
                self._ax_p.set_ylabel("Pression (bar)", fontsize=10, color=FG_DIM)
                self._ax_p.legend(loc="upper right", fontsize=8, facecolor=BG3,framealpha=0.8, edgecolor="#CCCCCC")

            press = mesures.get("press_vide", [])

            valid_press = [v if isinstance(v, float) else None for v in press]

            self._press_line.set_data(times_raw, valid_press)
         
        else:
            self._fig.suptitle("COURBES TEMPERATURES", fontsize=15, color=FG_DIM)
            # Supprime l'axe pression s'il existe 
            if self._ax_p is not None:
                self._ax_p.cla()
      
        self._ax_t.relim()
        self._ax_t.autoscale_view()

        self._ax_t.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self._ax_t.xaxis.set_major_locator(mdates.AutoDateLocator())
        self._fig.autofmt_xdate()

        if self._ax_p:
            self._ax_p.relim()
            self._ax_p.autoscale_view()

            self._ax_p.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            self._ax_p.xaxis.set_major_locator(mdates.AutoDateLocator())
            self._fig.autofmt_xdate()

    def _set_cycle_lock(self, locked: bool):
        """Grise ou déverrouille les widgets du formulaire cycle."""
        self._cycle_locked = locked
        state  = "disabled" if locked else "normal"
        bg_var   = DISABLE_BG if locked else BG3
        bg_btn_validate   = DISABLE_BG if locked else GREEN
        bg_btn_pump = DISABLE_BG if locked else GREEN if self._var_pump.get() else RED
        fg_var   = DISABLE_FG if locked else FG
        fg_btn   = DISABLE_FG if locked else "white"

        for w in self._spin_cycle :
            w.config(state=state, bg=bg_var, fg=fg_var)

        self._btn_validate.config(state=state, bg=bg_btn_validate, fg=fg_btn)
        self._btn_pump.config(state=state, bg=bg_btn_pump, fg=fg_btn)

        # Active ou grise le champ Temp_pompe selon le bouton pompe si pas validation
        if state == "normal":
            state_entry = "normal" if self._var_pump.get() else "disabled"
            self._spin_temp_hold.config(state=state_entry, bg=BG3 if self._var_pump.get() else DISABLE_BG)

    def _cycle_confirmation_popup(self):
        """
        Popup pour double valider valider le cycle 
        Affichage :
            Température cible : XX °C
            Durée : XX min
            Pompe : Oui / Non
            Si pompe oui : Température arrêt pompe : XX °C
            Bouton Valider / Annuler
        2 colonnes : gauche = texte, droite = valeurs
        """
        popup = tk.Toplevel(self.window, bg=BG)
        popup.title("Confirmation du cycle")
        popup.geometry("600x400")
        popup.transient(self.window)
        popup.grab_set()
        popup.focus_set()

        inner = tk.Frame(popup, bg=BG2)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        # Texte de confirmation
        text_label = tk.Frame(inner, bg=BG2)
        text_label.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        text_label.columnconfigure(0, weight=1, uniform="group1")  # gauche
        text_label.columnconfigure(1, weight=1, uniform="group1")  # droite
        text_label.rowconfigure(0, weight=1)
        text_label.rowconfigure(1, weight=1)
        text_label.rowconfigure(2, weight=1)
        text_label.rowconfigure(3, weight=1)

        text = {
            "Température cible": f"{self._var_temp.get()} °C",
            "Durée": f"{self._var_hold.get()} min",
            "Pompe": "Oui" if self._var_pump.get() else "Non",
            "Température arrêt pompe": f"{self._var_temp_pump.get()} °C" if self._var_pump.get() else "N/A"
        }

        for i, (key, value) in enumerate(text.items()):
            tk.Label(text_label, text=key, bg=BG2, fg=FG_DIM, font=FONT_MED).grid(row=i, column=0, sticky="w", padx=(0, 6), pady=4)
            tk.Label(text_label, text=value, bg=BG2, fg=FG, font=FONT_BIG).grid(row=i, column=1, sticky="w", padx=(6, 0), pady=4)

        # Boutons
        btn_frame = tk.Frame(inner, bg=BG2)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        btn_frame.columnconfigure(0, weight=1, uniform="group1")  # gauche
        btn_frame.columnconfigure(1, weight=1, uniform="group1")  # droite
        btn_frame.rowconfigure(0, weight=1)

        btn_yes = tk.Button(btn_frame, text="Oui", 
                            width = 10, font=FONT_BIG, bd=0, padx=8, pady=10, cursor="hand2", 
                            bg=GREEN, fg = 'white',
                            command=lambda:self._on_validate(popup))
        btn_yes.grid(row=0, column=0, padx=(0, 6), pady=4)

        btn_no = tk.Button(btn_frame, text="Non", 
                           width = 10, font=FONT_BIG, bd=0, padx=8, pady=10, cursor="hand2", 
                           bg=RED, fg = 'white',
                           command=lambda:self._not_validated(popup))
        btn_no.grid(row=0, column=1, padx=(0, 6), pady=4)
     
    def run(self):
        """Lance la boucle principale tkinter (bloquant)."""
        self.window.mainloop()

    def _reset_ihm(self):

        with self.lock:
            # Reset des variables
            self._var_temp.set(self.data.get("TEMP_CIBLE", 120))
            self._var_hold.set(self.data.get("TIME_HOLD", 30))
            self._var_pump.set(bool(self.data.get("PUMP_ACTIVATION", True)))
            self._var_temp_pump.set(self.data.get("TEMP_STOP_PUMP", 70))

        # Reset courbes
        self._ax_t.remove()
        if self._ax_p is not None:
            self._ax_p.remove()
            
        self._fig.clear()
        self._ax_t = self._fig.add_subplot(111)
        self._ax_t.grid()
        self._ax_t.set_xlabel("Temps", fontsize=10, color=FG_DIM)
        self._ax_t.set_ylabel("Température (°C)", fontsize=10, color=FG_DIM)
        self._fig.suptitle("COURBES TEMPERATURES ET PRESSION", fontsize=15, color=FG_DIM)
        self._ax_p = self._ax_t.twinx()
        self._ax_p.set_ylabel("Pression (bar)", fontsize=10, color=FG_DIM)

        self._chart_canvas.draw_idle()


        # Déverrouiller boutons
        self._cycle_locked = False
        self._set_cycle_lock(False)

        # Active le bouton pump
        self._toggle_pump()

        # Reset données internes
        self._running = True
        self._blink_visible = True
        self._popup_error_exist = False
        self._last_blink = time.time()
        self._curve_plotted = False
        self._cycle_locked = False


# ─────────────────────────────────────────────
#  LANCEMENT STANDALONE (test sans hardware)
# ─────────────────────────────────────────────
if __name__ == "__main__":

    import math, random

    # Données simulées — remplacées par le dict partagé de main.py en prod
    data = {
        "temp1": 0,
        "temp2": 0,
        "temp3": 0,
        "temp4": 0,
        "temp5": 0,
        "temp6": 0,
        "temp7": 0,
        "press_vide": 0,
        "TEMP_CIBLE": 40,
        "TIME_HOLD": 10,
        "PUMP_ACTIVATION": True,
        "TEMP_STOP_PUMP": 35,
        "time_start_hold": None,
        "state": "IDLE",
        "previous_state": None,
        "sensor_activated": False,
        "ventilation_activated": True,
        "P1_activated": False,
        "P2_activated": True,
        "pump_activated": False,
        "_all_mesures": {          # simulées pour les courbes
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
    }

    # Simulateur de données capteurs à ajoute un point toutes les 200 ms
    t0 = datetime.now()
    def _sim_data():
        t = (datetime.now() - t0).total_seconds()
        m = data["_all_mesures"]
        m["Time"].append(datetime.now())
        for i in range(1, 8):
            m[f"temp{i}"].append(20 + 5 * math.sin(t / 10 + i) + random.uniform(-0.3, 0.3))
            data[f"temp{i}"] = m[f"temp{i}"][-1]
        m["press_vide"].append(-0.3 - 0.05 * math.sin(t / 15))
        data["press_vide"] = m["press_vide"][-1]
        ihm.window.after(200, _sim_data)


    window = tk.Tk()
    ihm = HalcyonIHM(window, data)
    ihm.window.after(500, _sim_data)
    print(data)
    ihm.run()