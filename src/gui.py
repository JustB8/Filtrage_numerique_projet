# gui.py

import customtkinter as ctk
from tkinter import filedialog
import os

class AudioVisualApp(ctk.CTk):
    def __init__(self, audio_engine):
        super().__init__()

        self.title("Application d'application de filtre à appliquer sur un signal sonore")
        self.geometry("1100x540")  # Augmenté un peu pour le confort

        self.is_playing = False

        # Grille principale
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar : Contrôle (Inchangée) ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.title_label = ctk.CTkLabel(self.sidebar, text="Fichier audio", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=(20, 30))

        self.import_button = ctk.CTkButton(self.sidebar, text="Importer Son")
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

        # --- Zone Centrale : Filtres (Version avec Saisie Numérique) ---
        self.filter_frame = ctk.CTkFrame(self, corner_radius=0)
        self.filter_frame_title = ctk.CTkLabel(self.filter_frame, text="Réglages des Filtres", font=ctk.CTkFont(size=20, weight="bold"))
        self.filter_frame_title.pack(pady=(20, 30))
        self.filter_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # Configuration des filtres
        filters_config = [
            ("Passe-Bas Ordre 1", 500),
            ("Passe-Haut Ordre 1", 1000),
            ("Passe-Bas Ordre 2", 500),
            ("Passe-Haut Ordre 2", 1000),
            ("Sélecteur", 2500),
            ("Réjecteur", 5000)
        ]

        self.filter_widgets = {}  # Pour stocker les références si besoin

        for name, default_val in filters_config:
            self.add_filter_row(name, default_val)

        self.audio_engine = audio_engine

        # Bouton Ajouter un son
        self.btn_import = ctk.CTkButton(
            self,
            border_spacing=20,
            text="Ajouter un son",
            command=self.import_audio
        )

    def add_filter_row(self, name, default_val):
        row_frame = ctk.CTkFrame(self.filter_frame)
        row_frame.pack(fill="x", pady=10, padx=10)

        # 1. Checkbox
        check = ctk.CTkCheckBox(row_frame, text=name, width=150, font=ctk.CTkFont(weight="bold"))
        check.pack(side="left", padx=10)

        # 2. Variable avec "trace" pour la mise à jour temps réel
        val_var = ctk.StringVar(value=str(default_val))

        unit_label = ctk.CTkLabel(row_frame, text="Hz")
        unit_label.pack(side="right", padx=10)

        # 4. Entry lié à la variable
        entry = ctk.CTkEntry(row_frame, width=70, textvariable=val_var)
        entry.pack(side="right", padx=10)

        # 3. Slider (configuré en premier pour être référencé)
        slider = ctk.CTkSlider(
            row_frame,
            from_=20,
            to=20000,
            width=400,
            number_of_steps=1000,
            command=lambda v, ev=val_var: self.update_entry_from_slider(v, ev)
        )
        slider.set(default_val)
        slider.pack(side="right", padx=20)

        # --- LA CORRECTION EST ICI ---
        # On ajoute une trace : chaque fois que le texte change ("w" pour write),
        # on appelle la fonction de mise à jour du slider.
        val_var.trace_add("write", lambda *args, s=slider, ev=val_var: self.update_slider_from_entry(s, ev))

    def update_entry_from_slider(self, value, entry_var):
        """Met à jour l'Entry sans déclencher de boucle infinie"""
        # On récupère la valeur actuelle pour éviter de réécrire la même chose
        new_val = str(int(value))
        if entry_var.get() != new_val:
            entry_var.set(new_val)

    def update_slider_from_entry(self, slider, entry_var):
        """Met à jour le slider en fonction de ce qui est tapé"""
        try:
            content = entry_var.get()
            if content == "": return  # Permet d'effacer pour retaper

            value = float(content)
            if 20 <= value <= 20000:
                slider.set(value)
                # Ici on pourrait appeler la fonction de traitement audio plus tard
        except ValueError:
            # Si l'utilisateur tape des lettres, on ignore simplement
            pass

    # Méthodes de contrôle (identiques au précédent)
    def toggle_playback(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_pause_button.configure(text="Pause", fg_color="#e67e22")
        else:
            self.play_pause_button.configure(text="Play", fg_color="#2ecc71")

    def update_volume_label(self, value):
        self.volume_label.configure(text=f"Volume : {int(value * 100)}%")

    def import_audio(self):
        print("Bouton cliqué !")  # Si ça n'affiche rien ici, le souci est le bouton
        file_path = filedialog.askopenfilename(
            parent=self,  # On lui dit qui est le patron
            title="Sélectionner un fichier audio",
            filetypes=[("Audio Files", "*.mp3 *.wav *.flac")]
        )
        if file_path:
            print(f"Chargement de : {file_path}")
            # On envoie le chemin au moteur audio pour traitement
            self.audio_engine.load_file(file_path)

if __name__ == "__main__":
    app = AudioVisualApp()
    app.mainloop()