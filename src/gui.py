# gui.py

import customtkinter as ctk
from audio_engine import AudioEngine
from tkinter import filedialog
import os

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    print("Garçon, il te manque un truc : pip install tkinterdnd2")

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

        # Initialise le support DND
        self.TkDnD_wrapper = TkinterDnD(self)

        # --- Sidebar : Contrôle ---
        self.sidebar = ctk.CTkFrame(self, width=250)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

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

        self.filter_frame_title = ctk.CTkLabel(self.filter_frame, text="TABLE DE MIXAGE",
                                               font=ctk.CTkFont(size=22, weight="bold"))
        self.filter_frame_title.pack(pady=(20, 10))

        self.scrollable_main_frame = ctk.CTkScrollableFrame(self.filter_frame, fg_color="transparent")
        self.scrollable_main_frame.pack(fill="both", expand=True)

        # Activer le Drop sur la sidebar
        self.sidebar.drop_target_register(DND_FILES)
        self.sidebar.dnd_bind('<<Drop>>', self.handle_drop)

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

    def handle_drop(self, event):
        file_path = event.data.strip('{}') # Nettoie le chemin (Windows ajoute des {})
        if file_path.endswith(".wav"):
            track_name = self.engine.add_track(file_path)
            self.create_track_ui(track_name)

    def create_track_ui(self, track_name):
        # Ajoute un TrackFrame dans la zone centrale (scrollable)
        new_track_ui = TrackFrame(self.scrollable_main_frame, self.engine, track_name)
        new_track_ui.pack(fill="x", pady=10, padx=10)

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

class TrackFrame(ctk.CTkFrame):
    def __init__(self, master, engine, track_name, **kwargs):
        super().__init__(master, **kwargs)
        self.engine = engine
        self.track_name = track_name
        self.track = engine.tracks[track_name]
        
        # En-tête du son
        header = ctk.CTkFrame(self, fg_color="#333333")
        header.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(header, text=track_name, font=("Arial", 13, "bold")).pack(side="left", padx=10)
        
        self.play_btn = ctk.CTkButton(header, text="Play", width=60, command=self.toggle_play)
        self.play_btn.pack(side="left", padx=5)
        
        ctk.CTkSlider(header, from_=0, to=1, width=100, command=self.set_volume).pack(side="left", padx=5)

        self.filter_menu = ctk.CTkOptionMenu(
            header, values=["Passe-Bas O1", "Passe-Haut O1", "Notch", "Bandpass"],
            command=self.add_filter_row
        )
        self.filter_menu.set("Ajouter un filtre...")
        self.filter_menu.pack(side="right", padx=10)

        # Conteneur pour les sliders de filtres
        self.filters_area = ctk.CTkFrame(self, fg_color="transparent")
        self.filters_area.pack(fill="x", padx=10, pady=5)

    def add_filter_row(self, filter_type):
        # On crée une petite ligne pour le slider
        row = ctk.CTkFrame(self.filters_area)
        row.pack(fill="x", pady=2)
        
        ctk.CTkLabel(row, text=filter_type, width=100).pack(side="left", padx=5)
        
        # Slider de fréquence
        s = ctk.CTkSlider(row, from_=20, to=15000, 
                          command=lambda v: self.engine.update_track_filter(self.track_name, filter_type, v))
        s.set(1000)
        s.pack(side="left", fill="x", expand=True, padx=5)
        
        # Bouton pour supprimer le filtre
        ctk.CTkButton(row, text="X", width=30, fg_color="#c0392b", 
                      command=row.destroy).pack(side="right", padx=5)
        
        # On active le filtre dans le moteur
        self.engine.update_track_filter(self.track_name, filter_type, 1000, active=True)

    def toggle_play(self):
        self.track.is_playing = not self.track.is_playing
        self.play_btn.configure(text="Pause" if self.track.is_playing else "Play")
        if not self.engine.is_playing: self.engine.start()

    def set_volume(self, v):
        self.track.volume = float(v)

if __name__ == "__main__":
    app = AudioVisualApp()
    app.mainloop()