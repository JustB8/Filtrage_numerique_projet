# gui.py

import customtkinter as ctk
from audio_engine import AudioEngine
from tkinter import filedialog
import os

# Forcer le mode sombre globalement
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AudioVisualApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.engine = AudioEngine()

        self.title("Application de filtrage numérique")
        self.geometry("1100x600")

        self.is_playing = False
        self.file_path = None

        # Dictionnaire pour stocker l'état des filtres (activé/fréquence)
        # Utile pour faire le lien avec audio_engine.py
        self.filters_state = {}

        # Configuration de la grille
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

        # --- Zone Centrale : Filtres ---
        self.filter_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.filter_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=10)

        self.filter_frame_title = ctk.CTkLabel(self.filter_frame, text="RÉGLAGES DES FILTRES",
                                               font=ctk.CTkFont(size=22, weight="bold"))
        self.filter_frame_title.pack(pady=(20, 30))

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

    def add_filter_row(self, name, default_val):
        row_frame = ctk.CTkFrame(self.filter_frame)
        row_frame.pack(fill="x", pady=5, padx=10)

        # État initial pour ce filtre
        self.filters_state[name] = {"active": False, "freq": default_val}

        # Checkbox pour activer/désactiver le filtre
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

        # Lien entre l'entrée texte et le slider
        val_var.trace_add("write", lambda *args, s=slider, ev=val_var, n=name: self.update_slider_from_entry(n, s, ev))

    def toggle_filter(self, name):
        """Active ou désactive un filtre dans le moteur audio"""
        is_active = self.filters_state[name]["checkbox"].get()
        self.filters_state[name]["active"] = bool(is_active)
        # Appel vers audio_engine (à implémenter dans audio_engine.py)
        self.engine.update_filter_status(name, is_active)
        print(f"Filtre {name}: {'ON' if is_active else 'OFF'}")

    def update_filter_freq(self, name, value, entry_var):
        """Met à jour la fréquence via le slider"""
        freq = int(value)
        self.filters_state[name]["freq"] = freq
        if entry_var.get() != str(freq):
            entry_var.set(str(freq))
        # Appel vers audio_engine
        self.engine.set_filter_freq(name, freq)

    def update_slider_from_entry(self, name, slider, entry_var):
        """Met à jour le slider et l'état via l'entrée texte"""
        try:
            content = entry_var.get()
            if content == "": return
            value = float(content)
            if 20 <= value <= 20000:
                slider.set(value)
                self.filters_state[name]["freq"] = value
                self.engine.set_filter_freq(name, value)
        except ValueError:
            pass

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