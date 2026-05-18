# gui.py

import customtkinter as ctk
from audio_engine import AudioEngine
from tkinter import filedialog
import os
import numpy as np

# Imports nécessaires pour Matplotlib dans Tkinter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Forcer le mode sombre globalement
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AudioVisualApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.engine = AudioEngine()

        self.title("Application de filtrage numérique")
        self.geometry("1100x750") # Augmentation de la hauteur pour le graphique

        self.is_playing = False
        self.file_path = None
        self.filters_state = {}

        # Configuration de la grille principale
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar : Contrôle ---
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.title_label = ctk.CTkLabel(self.sidebar, text="CONTRÔLES", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=(20, 10))

        self.file_label = ctk.CTkLabel(self.sidebar, text="Aucun fichier", font=ctk.CTkFont(size=11), wraplength=180)
        self.file_label.pack(pady=(0, 10))

        self.import_button = ctk.CTkButton(self.sidebar, text="Importer .wav", command=self.import_file)
        self.import_button.pack(pady=10, padx=20)

        self.play_pause_button = ctk.CTkButton(
            self.sidebar, text="Play", fg_color="#2ecc71", hover_color="#27ae60",
            command=self.toggle_playback
        )
        self.play_pause_button.pack(pady=10, padx=20)

        self.volume_label = ctk.CTkLabel(self.sidebar, text="Volume : 100%")
        self.volume_label.pack(pady=(30, 0))
        self.volume_slider = ctk.CTkSlider(self.sidebar, from_=0, to=1, command=self.update_volume_label)
        self.volume_slider.set(1)
        self.volume_slider.pack(pady=10, padx=20)

        # --- Zone Centrale : Conteneur global ---
        self.main_content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=20, pady=10)
        
        # Configuration interne du contenu principal
        self.main_content.grid_rowconfigure(1, weight=1) # Le graphique prendra l'espace libre
        self.main_content.grid_columnconfigure(0, weight=1)

        # --- Zone Centrale Haut : Réglages des Filtres ---
        self.filter_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.filter_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.filter_frame_title = ctk.CTkLabel(self.filter_frame, text="RÉGLAGES DES FILTRES",
                                               font=ctk.CTkFont(size=20, weight="bold"))
        self.filter_frame_title.pack(pady=(10, 15))

        filters_config = [
            ("Passe-Bas Ordre 1", 500),
            ("Passe-Haut Ordre 1", 1000),
            ("Passe-Bas Ordre 2", 500),
            ("Passe-Haut Ordre 2", 1000),
            ("Sélecteur (Bandpass)", 2500),
            ("Réjecteur (Notch)", 5000)
        ]

        for name, default_val in filters_config:
            self.add_filter_row(name, default_val)

        # --- Zone Centrale Bas : Graphique Matplotlib ---
        self.plot_frame = ctk.CTkFrame(self.main_content, fg_color="#242424") # Fond sombre assorti
        self.plot_frame.grid(row=1, column=0, sticky="nsew", pady=10)

        # Initialisation de la Figure Matplotlib avec un style sombre
        plt.style.use('dark_background')
        self.fig, self.ax = plt.subplots(figsize=(6, 3), dpi=100)
        self.fig.patch.set_facecolor('#242424')
        self.ax.set_facecolor('#1e1e1e')
        
        # Configuration initiale des axes
        self.ax.set_title("Réponse en fréquence globale (Bode)", fontsize=11, color="white")
        self.ax.set_xlabel("Fréquence (Hz)", fontsize=9, color="darkgray")
        self.ax.set_ylabel("Gain (dB)", fontsize=9, color="darkgray")
        self.ax.set_xscale('log')
        self.ax.set_xlim(20, 20000)
        self.ax.set_ylim(-40, 5)
        self.ax.grid(True, which="both", ls="-", color="#333333")
        self.fig.tight_layout()

        # Ligne vide qui sera mise à jour
        self.line, = self.ax.plot([], [], color="#2ecc71", lw=2)

        # Intégration de la figure dans CustomTkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        
        # Premier rendu du graphique
        self.update_plot()

    def import_file(self):
        file_selected = filedialog.askopenfilename(
            title="Sélectionner un fichier audio",
            filetypes=(("Fichiers WAV", "*.wav"), ("Tous les fichiers", "*.*"))
        )

        if file_selected:
            self.file_path = file_selected
            self.engine.load_file(file_selected)
            file_name = os.path.basename(file_selected)
            self.file_label.configure(text=f"Chargé : {file_name}", text_color="#2ecc71")
            self.update_plot() # Recalculer si la fréquence d'échantillonnage change

    def add_filter_row(self, name, default_val):
        row_frame = ctk.CTkFrame(self.filter_frame)
        row_frame.pack(fill="x", pady=3, padx=10)

        self.filters_state[name] = {"active": False, "freq": default_val}

        check = ctk.CTkCheckBox(row_frame, text=name, width=180, font=ctk.CTkFont(weight="bold"),
                                command=lambda n=name: self.toggle_filter(n))
        check.pack(side="left", padx=10)
        self.filters_state[name]["checkbox"] = check

        unit_label = ctk.CTkLabel(row_frame, text="Hz")
        unit_label.pack(side="right", padx=10)

        val_var = ctk.StringVar(value=str(default_val))
        entry = ctk.CTkEntry(row_frame, width=70, textvariable=val_var)
        entry.pack(side="right", padx=10)

        slider = ctk.CTkSlider(
            row_frame, from_=20, to=20000, width=400,
            command=lambda v, n=name, ev=val_var: self.update_filter_freq(n, v, ev)
        )
        slider.set(default_val)
        slider.pack(side="right", padx=20)

        val_var.trace_add("write", lambda *args, s=slider, ev=val_var, n=name: self.update_slider_from_entry(n, s, ev))

    def toggle_filter(self, name):
        is_active = self.filters_state[name]["checkbox"].get()
        self.filters_state[name]["active"] = bool(is_active)
        self.engine.update_filter_status(name, is_active)
        self.update_plot() # <--- Mise à jour ici !

    def update_filter_freq(self, name, value, entry_var):
        freq = int(value)
        self.filters_state[name]["freq"] = freq
        if entry_var.get() != str(freq):
            entry_var.set(str(freq))
        self.engine.set_filter_freq(name, freq)
        self.update_plot() # <--- Mise à jour ici !

    def update_slider_from_entry(self, name, slider, entry_var):
        try:
            content = entry_var.get()
            if content == "": return
            value = float(content)
            if 20 <= value <= 20000:
                slider.set(value)
                self.filters_state[name]["freq"] = value
                self.engine.set_filter_freq(name, value)
                self.update_plot() # <--- Mise à jour ici !
        except ValueError:
            pass

    def update_plot(self):
        """Récupère les données de réponse fréquentielle du moteur et met à jour le tracé."""
        frequencies, db_response = self.engine.compute_global_response()
        
        # Mise à jour rapide des données de la ligne sans reconstruire tout l'axe
        self.line.set_data(frequencies, db_response)
        
        # Forcer Matplotlib à redessiner le canvas
        self.canvas.draw_idle()

    def toggle_playback(self):
        if not self.file_path:
            return

        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_pause_button.configure(text="Pause", fg_color="#e67e22", hover_color="#d35400")
            self.engine.start()
        else:
            self.play_pause_button.configure(text="Play", fg_color="#2ecc71", hover_color="#27ae60")
            self.engine.stop()

    def update_volume_label(self, value):
        self.volume_label.configure(text=f"Volume : {int(value * 100)}%")
        self.engine.volume = float(value)

if __name__ == "__main__":
    app = AudioVisualApp()
    app.mainloop()