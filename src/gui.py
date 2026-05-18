# gui.py

import customtkinter as ctk
from audio_engine import AudioEngine
from tkinter import filedialog
import os
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AudioVisualApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.engine = AudioEngine()

        self.title("Filtreur 3000")
        self.geometry("1150x880") # Légèrement agrandi en hauteur pour le nouveau menu

        self.is_playing = False
        self.file_path = None
        self.filters_state = {}

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Configuration de la grille principale
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar : Contrôle ---
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        self.title_label = ctk.CTkLabel(self.sidebar, text="CONTRÔLES", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=(20, 10))

        self.file_label = ctk.CTkLabel(self.sidebar, text="Aucun fichier", font=ctk.CTkFont(size=12), wraplength=180)
        self.file_label.pack(pady=(0, 10))

        self.import_button = ctk.CTkButton(self.sidebar, text="Importer .wav", command=self.import_file)
        self.import_button.pack(pady=10, padx=20)

        self.play_pause_button = ctk.CTkButton(
            self.sidebar, text="Play", fg_color="#2ecc71", hover_color="#27ae60",
            command=self.toggle_playback
        )
        self.play_pause_button.pack(pady=10, padx=20)

        self.volume_label = ctk.CTkLabel(self.sidebar, text="Volume : 100%")
        self.volume_label.pack(pady=(20, 0))
        self.volume_slider = ctk.CTkSlider(self.sidebar, from_=0, to=1, command=self.update_volume_label)
        self.volume_slider.set(1)
        self.volume_slider.pack(pady=10, padx=20)

        # --- AJOUT MULTI-FILTRES : Sélection du type d'approximation globale ---
        self.type_label = ctk.CTkLabel(self.sidebar, text="TYPE DE FILTRE :", font=ctk.CTkFont(size=12, weight="bold"))
        self.type_label.pack(pady=(25, 0))
        
        self.type_menu = ctk.CTkOptionMenu(
            self.sidebar, 
            values=["Butterworth", "Tchebychev de type 1", "Tchebychev de type 2", "Elliptique"],
            command=self.change_global_filter_type
        )
        self.type_menu.set("Butterworth")
        self.type_menu.pack(pady=10, padx=20)

        # --- Zone Centrale : Conteneur global ---
        self.main_content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=20, pady=10)
        
        self.main_content.grid_rowconfigure(1, weight=1) 
        self.main_content.grid_columnconfigure(0, weight=1)

        # --- Zone Centrale Haut : Réglages des Filtres ---
        self.filter_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.filter_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.filter_frame_title = ctk.CTkLabel(self.filter_frame, text="RÉGLAGES DES FILTRES",
                                               font=ctk.CTkFont(size=20, weight="bold"))
        self.filter_frame_title.pack(pady=(10, 15))

        # Remplacement des filtres fixes d'ordre 2 par des versions Variables
        filters_config = [
            ("Passe-bas d'ordre 1", 1500),
            ("Passe-haut d'ordre 1", 1500),
            ("Passe-bas d'ordre variable", 1500),
            ("Passe-haut d'ordre variable", 1500),
            ("Sélecteur", 1500),
            ("Coupe-bande", 1500)
        ]

        for name, default_val in filters_config:
            self.add_filter_row(name, default_val)

        # --- Zone Centrale Bas : Graphiques Matplotlib ---
        self.plot_frame = ctk.CTkFrame(self.main_content, fg_color="#242424")
        self.plot_frame.grid(row=1, column=0, sticky="nsew", pady=10)

        plt.style.use('dark_background')
        self.fig, (self.ax_bode, self.ax_fft) = plt.subplots(2, 1, figsize=(6, 5), dpi=100)
        self.fig.patch.set_facecolor('#242424')
        
        self.ax_bode.set_facecolor('#1e1e1e')
        self.ax_bode.set_title("Diagramme de Bode", fontsize=11, color="white")
        self.ax_bode.set_ylabel("Gain (dB)", fontsize=9, color="darkgray")
        self.ax_bode.set_xlabel("Fréquence (Hz)", fontsize=9, color="darkgray")
        self.ax_bode.set_xscale('log')
        self.ax_bode.set_xlim(20, 20000)
        self.ax_bode.set_ylim(-60, 5)
        self.ax_bode.grid(True, which="both", ls="-", color="#333333")
        self.line_bode, = self.ax_bode.plot([], [], color="#2ecc71", lw=2)

        self.num_bands = 128  
        self.ax_fft.set_facecolor('#1e1e1e')
        self.ax_fft.set_title("Spectre audio", fontsize=11, color="white")
        self.ax_fft.set_xlabel("Fréquence (Hz)", fontsize=9, color="darkgray")
        self.ax_fft.set_ylabel("Amplitude (dB)", fontsize=9, color="darkgray")
        self.ax_fft.set_xscale('log')
        self.ax_fft.set_xlim(20, 20000)
        self.ax_fft.set_ylim(-60, 60) 
        self.ax_fft.grid(True, which="both", ls="-", color="#333333")
        
        self.bar_freqs = np.logspace(np.log10(20), np.log10(20000), self.num_bands)
        widths = self.bar_freqs * 0.05 

        self.bars_in = self.ax_fft.bar(self.bar_freqs, np.zeros(self.num_bands), width=widths, 
                                       color="#e74c3c", alpha=0.6, label="Original", bottom=-60)
        self.bars_out = self.ax_fft.bar(self.bar_freqs, np.zeros(self.num_bands), width=widths, 
                                        color="#3498db", alpha=0.7, label="Filtré", bottom=-60)
        self.ax_fft.legend(loc="upper right", fontsize=8, framealpha=0.5)

        self.fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        
        self.update_bode_plot()
        self.update_live_fft()

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
            self.update_bode_plot()

    def add_filter_row(self, name, default_val):
        row_frame = ctk.CTkFrame(self.filter_frame)
        row_frame.pack(fill="x", pady=3, padx=10)

        self.filters_state[name] = {"active": False, "freq": default_val}

        check = ctk.CTkCheckBox(row_frame, text=name, width=180, font=ctk.CTkFont(weight="bold"),
                                command=lambda n=name: self.toggle_filter(n))
        check.pack(side="left", padx=10)
        self.filters_state[name]["checkbox"] = check

        if "variable" in name:
            order_label = ctk.CTkLabel(row_frame, text="Ordre (2 à 10) :", font=ctk.CTkFont(size=11, weight="bold"))
            order_label.pack(side="left", padx=(10, 2))
            
            order_var = ctk.StringVar(value="2")
            order_entry = ctk.CTkEntry(row_frame, width=35, textvariable=order_var, justify="center")
            order_entry.pack(side="left", padx=2)
            
            order_var.trace_add("write", lambda *args, n=name, ov=order_var: self.update_filter_order(n, ov))

        # Fréquence en Hz
        unit_label = ctk.CTkLabel(row_frame, text="Hz")
        unit_label.pack(side="right", padx=10)

        val_var = ctk.StringVar(value=str(default_val))
        entry = ctk.CTkEntry(row_frame, width=70, textvariable=val_var)
        entry.pack(side="right", padx=10)

        slider = ctk.CTkSlider(
            row_frame, from_=20, to=20000, width=350,
            command=lambda v, n=name, ev=val_var: self.update_filter_freq(n, v, ev)
        )
        slider.set(default_val)
        slider.pack(side="right", padx=20)

        val_var.trace_add("write", lambda *args, s=slider, ev=val_var, n=name: self.update_slider_from_entry(n, s, ev))

    def change_global_filter_type(self, choice):
        """Déclenché lors du changement d'approximation globale."""
        self.engine.set_global_filter_type(choice)
        self.update_bode_plot()

    def toggle_filter(self, name):
        is_active = self.filters_state[name]["checkbox"].get()
        self.filters_state[name]["active"] = bool(is_active)
        self.engine.update_filter_status(name, is_active)
        self.update_bode_plot()

    def update_filter_freq(self, name, value, entry_var):
        freq = int(value)
        self.filters_state[name]["freq"] = freq
        if entry_var.get() != str(freq):
            entry_var.set(str(freq))
        self.engine.set_filter_freq(name, freq)
        self.update_bode_plot()

    def update_filter_order(self, name, order_var):
        try:
            content = order_var.get()
            if content == "": return
            order_val = int(content)
            if 1 <= order_val <= 12:
                self.engine.set_filter_order(name, order_val)
                self.update_bode_plot()
        except ValueError:
            pass

    def update_slider_from_entry(self, name, slider, entry_var):
        try:
            content = entry_var.get()
            if content == "": return
            value = float(content)
            if 20 <= value <= 20000:
                slider.set(value)
                self.filters_state[name]["freq"] = value
                self.engine.set_filter_freq(name, value)
                self.update_bode_plot()
        except ValueError:
            pass

    def update_bode_plot(self):
        frequencies, db_response = self.engine.compute_global_response()
        self.line_bode.set_data(frequencies, db_response)
        self.canvas.draw_idle()

    def update_live_fft(self):
        if self.engine.is_playing:
            freqs, fft_in, fft_out = self.engine.get_fft_data()
            
            if freqs is not None:
                indices = np.digitize(freqs, self.bar_freqs)
                
                for i in range(self.num_bands):
                    mask = (indices == i)
                    if np.any(mask):
                        val_in = np.mean(fft_in[mask])
                        val_out = np.mean(fft_out[mask])
                        
                        self.bars_in[i].set_height(max(0, val_in - (-60)))
                        self.bars_out[i].set_height(max(0, val_out - (-60)))
                    else:
                        self.bars_in[i].set_height(0)
                        self.bars_out[i].set_height(0)
                
                self.canvas.draw_idle()
        else:
            if self.bars_in[0].get_height() > 0 or self.bars_out[0].get_height() > 0:
                for i in range(self.num_bands):
                    self.bars_in[i].set_height(0)
                    self.bars_out[i].set_height(0)
                self.canvas.draw_idle()

        self.after(100, self.update_live_fft)

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

    def on_closing(self):
        self.engine.stop()  # Coupe proprement le flux sounddevice
        self.destroy()      # Ferme la fenêtre Tkinter

if __name__ == "__main__":
    app = AudioVisualApp()
    app.mainloop()