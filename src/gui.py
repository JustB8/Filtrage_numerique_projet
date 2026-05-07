# gui.py

import customtkinter as ctk
from tkinter import filedialog
import os


class AudioVisualApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Application de filtrage numérique")
        self.geometry("1100x540")

        self.is_playing = False
        self.file_path = None  # Stocke le chemin du fichier importé

        # Grille principale
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar : Contrôle ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.title_label = ctk.CTkLabel(self.sidebar, text="Fichier audio", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=(20, 10))

        # Label pour afficher le nom du fichier chargé
        self.file_label = ctk.CTkLabel(self.sidebar, text="Aucun fichier", font=ctk.CTkFont(size=11), wraplength=180)
        self.file_label.pack(pady=(0, 10))

        # BOUTON IMPORTER lié à la méthode import_file
        self.import_button = ctk.CTkButton(self.sidebar, text="Importer un son (.wav)", command=self.import_file)
        self.import_button.pack(pady=10, padx=20)

        self.play_pause_button = ctk.CTkButton(
            self.sidebar, text="Play", fg_color="#2ecc71",
            command=self.toggle_playback
        )
        self.play_pause_button.pack(pady=10, padx=20)

        self.volume_label = ctk.CTkLabel(self.sidebar, text="Volume : 100%")
        self.volume_label.pack(pady=(30, 0))
        self.volume_slider = ctk.CTkSlider(self.sidebar, from_=0, to=1, command=self.update_volume_label)
        self.volume_slider.set(1)
        self.volume_slider.pack(pady=10, padx=20)

        # --- Zone Centrale : Filtres ---
        self.filter_frame = ctk.CTkFrame(self, corner_radius=0)
        self.filter_frame_title = ctk.CTkLabel(self.filter_frame, text="Réglages des Filtres",
                                               font=ctk.CTkFont(size=20, weight="bold"))
        self.filter_frame_title.pack(pady=(20, 30))
        self.filter_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        filters_config = [
            ("Passe-Bas Ordre 1", 500),
            ("Passe-Haut Ordre 1", 1000),
            ("Passe-Bas Ordre 2", 500),
            ("Passe-Haut Ordre 2", 1000),
            ("Sélecteur", 2500),
            ("Réjecteur", 5000)
        ]

        for name, default_val in filters_config:
            self.add_filter_row(name, default_val)

    def import_file(self):
        """Ouvre une boîte de dialogue pour sélectionner un fichier WAV"""
        file_selected = filedialog.askopenfilename(
            title="Sélectionner un fichier audio",
            filetypes=(("Fichiers WAV", "*.wav"), ("Tous les fichiers", "*.*"))
        )

        if file_selected:
            self.file_path = file_selected
            # Mise à jour de l'affichage (nom du fichier uniquement)
            file_name = os.path.basename(file_selected)
            self.file_label.configure(text=f"Chargé : {file_name}", text_color="#2ecc71")
            print(f"Fichier chargé : {self.file_path}")
            # Ici, tu pourras appeler une méthode de audio_engine pour charger les données

    def add_filter_row(self, name, default_val):
        row_frame = ctk.CTkFrame(self.filter_frame)
        row_frame.pack(fill="x", pady=10, padx=10)

        check = ctk.CTkCheckBox(row_frame, text=name, width=150, font=ctk.CTkFont(weight="bold"))
        check.pack(side="left", padx=10)

        val_var = ctk.StringVar(value=str(default_val))
        unit_label = ctk.CTkLabel(row_frame, text="Hz")
        unit_label.pack(side="right", padx=10)

        entry = ctk.CTkEntry(row_frame, width=70, textvariable=val_var)
        entry.pack(side="right", padx=10)

        slider = ctk.CTkSlider(
            row_frame, from_=20, to=20000, width=400, number_of_steps=1000,
            command=lambda v, ev=val_var: self.update_entry_from_slider(v, ev)
        )
        slider.set(default_val)
        slider.pack(side="right", padx=20)

        val_var.trace_add("write", lambda *args, s=slider, ev=val_var: self.update_slider_from_entry(s, ev))

    def update_entry_from_slider(self, value, entry_var):
        new_val = str(int(value))
        if entry_var.get() != new_val:
            entry_var.set(new_val)

    def update_slider_from_entry(self, slider, entry_var):
        try:
            content = entry_var.get()
            if content == "": return
            value = float(content)
            if 20 <= value <= 20000:
                slider.set(value)
        except ValueError:
            pass

    def toggle_playback(self):
        if not self.file_path:
            print("Erreur : Aucun fichier chargé !")
            return

        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_pause_button.configure(text="Pause", fg_color="#e67e22")
        else:
            self.play_pause_button.configure(text="Play", fg_color="#2ecc71")

    def update_volume_label(self, value):
        self.volume_label.configure(text=f"Volume : {int(value * 100)}%")


if __name__ == "__main__":
    app = AudioVisualApp()
    app.mainloop()