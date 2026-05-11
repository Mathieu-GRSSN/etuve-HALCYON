import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

def get_unique_filepath(filepath):

    if not os.path.exists(filepath):
        return filepath

    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)

    name, extension = os.path.splitext(filename)

    counter = 1

    while True:
        new_filename = f"{name}_{counter}{extension}"
        new_filepath = os.path.join(directory, new_filename)

        if not os.path.exists(new_filepath):
            return new_filepath

        counter += 1

def save_all_mesures(mesures):

    try :
        DATA_DIR = "data"
        os.makedirs(DATA_DIR, exist_ok=True)

        filename = datetime.now().strftime("data-%d-%m-%Y.csv")
        filepath = os.path.join(DATA_DIR, filename)

        filepath = get_unique_filepath(filepath)

        df = pd.DataFrame(mesures)
        df.to_csv(filepath, index = False, sep=";", encoding = 'utf-8') # exporte les données dans un csv

        return 1
    
    except Exception as e:
        print(e)
        return 0

def save_graph(mesures, pressure):

    BG2         = "#ffffff"   # cartes / panels
    BG3         = "#eef2f7"   # zones secondaires
    BORDER      = "#d0d7e2"   # bordures légères
    FG          = "#1a1f2b"
    FG_DIM      = "#6b7280"   # texte secondaire

    RED         = "#e63946"
    ORANGE      = "#ffa825"  
    YELLOW      = "#fdee1b" 
    GREEN       = "#2ecc71"
    BLUE        = "#1f6feb"
    PURPLE      = "#800fdd"
    PINK        = "#f51ebf"

    _temp_colors = [RED, ORANGE, YELLOW, BLUE, GREEN, PURPLE, PINK]
    _press_color = FG

    try :
        DATA_DIR = "data"
        os.makedirs(DATA_DIR, exist_ok=True)

        filename = datetime.now().strftime("data-%d-%m-%Y.png")
        filepath = os.path.join(DATA_DIR, filename)

        filepath = get_unique_filepath(filepath)

        times_raw = mesures.get("Time", [])

        # Création d'une figure 
        fig, ax_t = plt.subplots(figsize=(16, 8), facecolor=BG2)
        ax_t.set_facecolor(BG2)
        ax_t.grid(True, color=BORDER, linewidth=0.5)
        ax_t.set_xlabel("Temps", fontsize=10, color=FG_DIM)
        ax_t.set_ylabel("Température (°C)", fontsize=10, color=FG_DIM)


        # Tracé des températures
        _temp_keys = [f"temp{i}" for i in range(1, 8)]
        _temp_names = ["Temp 1", "Temp 2", "Temp 3", "Temp 4", "Temp 5", "Temp 6", "Temp 7"]
        for i, (key, name) in enumerate(zip(_temp_keys, _temp_names)):
            vals = mesures.get(key, [])

            if vals:
                ax_t.plot(times_raw[-len(vals):], vals, color=_temp_colors[i],linewidth=1.2,label=name)
     
        ax_t.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax_t.xaxis.set_major_locator(mdates.AutoDateLocator())
        fig.autofmt_xdate()
        ax_t.legend(loc="upper left", fontsize=8, facecolor=BG3, framealpha=0.8, edgecolor="#CCCCCC")

        if pressure:
            fig.suptitle("COURBES TEMPERATURES ET PRESSION", fontsize=15, color=FG_DIM)
            ax_p = ax_t.twinx()
            ax_p.set_ylabel("Pression (bar)", fontsize=10, color=FG_DIM)
            ax_p.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            ax_p.xaxis.set_major_locator(mdates.AutoDateLocator())
            fig.autofmt_xdate()
            ax_p.legend(loc="upper right", fontsize=8, facecolor=BG3, framealpha=0.8, edgecolor="#CCCCCC")

            press = mesures.get("press_vide", [])
            valid_press = [v for v in press if isinstance(v, float)]

            if valid_press:
                valid_times = times_raw[-len(valid_press):]
                ax_p.plot(valid_times, valid_press, color=_press_color, linewidth=1.0, linestyle="--", label="Pression")
                
            else:
                ax_p.plot([], [],color=_press_color,linewidth=1.0,linestyle="--",label="Pression")   

        else :
            fig.suptitle("COURBES TEMPERATURES", fontsize=15, color=FG_DIM)



        # Sauvegarde
        fig.savefig(filepath, dpi=150, bbox_inches="tight")

        # libérer la mémoire 
        plt.close(fig)  

        return 1

    except Exception as e:
        print(e)
        return 0