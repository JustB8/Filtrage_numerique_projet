# audio_engine.py

import sounddevice as sd
import soundfile as sf
import numpy as np
from scipy import signal
import os

class Track:
    def __init__(self, data, fs, name):
        self.name = name
        self.data = data
        self.fs = fs
        self.current_frame = 0
        self.volume = 1.0
        self.is_playing = False
        self.is_selected = True # Pour la checkbox de gauche
        self.filters = {} # Filtres spécifiques à cette piste

class AudioEngine:
    def __init__(self):
        self.tracks = {}
        self.data = None
        self.fs = 44100
        self.stream = None
        self.current_frame = 0
        self.volume = 1.0
        self.is_playing = False

        # Configuration des filtres
        self.filters = {
            "Passe-Bas Ordre 1": {"active": False, "freq": 500, "sos": None, "zi": None},
            "Passe-Haut Ordre 1": {"active": False, "freq": 1000, "sos": None, "zi": None},
            "Passe-Bas Ordre 2": {"active": False, "freq": 500, "sos": None, "zi": None},
            "Passe-Haut Ordre 2": {"active": False, "freq": 1000, "sos": None, "zi": None},
            "Sélecteur (Bandpass)": {"active": False, "freq": 2500, "sos": None, "zi": None},
            "Réjecteur (Notch)": {"active": False, "freq": 5000, "sos": None, "zi": None}
        }

    def load_file(self, file_path):
        self.data, self.fs = sf.read(file_path, dtype='float32')
        if len(self.data.shape) == 1:
            self.data = np.column_stack((self.data, self.data))
        self.current_frame = 0
        # Initialiser les coefficients pour tous les filtres avec le nouveau fs
        for name in self.filters:
            self._compute_sos(name)

    def _compute_sos(self, name):
        """Calcule les coefficients SOS et initialise la mémoire zi."""
        f = self.filters[name]["freq"]
        # Protection contre la fréquence de Nyquist
        f = min(f, self.fs / 2 - 1)

        try:
            if "Ordre 1" in name:
                btype = 'low' if 'Bas' in name else 'high'
                self.filters[name]["sos"] = signal.butter(1, f, btype, fs=self.fs, output='sos')
            elif "Ordre 2" in name:
                btype = 'low' if 'Bas' in name else 'high'
                self.filters[name]["sos"] = signal.butter(2, f, btype, fs=self.fs, output='sos')
            elif "Bandpass" in name:
                self.filters[name]["sos"] = signal.butter(2, [f * 0.8, min(f * 1.2, self.fs / 2 - 1)], btype='bandpass', fs=self.fs, output='sos')
            elif "Notch" in name:
                b, a = signal.iirnotch(f, 30.0, fs=self.fs)
                self.filters[name]["sos"] = signal.tf2sos(b, a)

            # Initialisation de la mémoire (zi) pour le streaming stéréo
            zi = signal.sosfilt_zi(self.filters[name]["sos"])
            self.filters[name]["zi"] = np.repeat(zi[:, np.newaxis, :], 2, axis=1)
        except Exception as e:
            print(f"Erreur calcul {name}: {e}")

    def update_filter_status(self, name, is_active):
        if name in self.filters:
            self.filters[name]["active"] = is_active
            # Si on active, on s'assure que le SOS est prêt
            if is_active:
                self._compute_sos(name)

    def set_filter_freq(self, name, freq):
        if name in self.filters:
            self.filters[name]["freq"] = freq
            self._compute_sos(name)

    def add_track(self, file_path):
        data, fs = sf.read(file_path, dtype='float32')
        if len(data.shape) == 1:
            data = np.column_stack((data, data))
        name = os.path.basename(file_path)
        self.tracks[name] = Track(data, fs, name)
        return name

    def callback(self, outdata, frames, time, status):
        outdata.fill(0)
        for name, track in self.tracks.items():
            if track.is_playing and track.is_selected:
                chunksize = min(len(track.data) - track.current_frame, frames)
                samples = track.data[track.current_frame : track.current_frame + chunksize].copy()
                
                # Appliquer les filtres de LA piste
                for f_name, f_info in track.filters.items():
                    if f_info["active"]:
                        samples, f_info["zi"] = signal.sosfilt(f_info["sos"], samples, axis=0, zi=f_info["zi"])
                
                outdata[:chunksize] += samples * track.volume
                track.current_frame += chunksize
                # ... (gestion de la fin de lecture)

        if chunksize < frames:
            outdata[chunksize:].fill(0)
            self.is_playing = False
            self.current_frame = 0
        else:
            self.current_frame += chunksize

    def start(self):
        if self.data is not None:
            try:
                self.stream = sd.OutputStream(
                    samplerate=self.fs, channels=2,
                    callback=self.callback, blocksize=2048
                )
                self.is_playing = True
                self.stream.start()
            except Exception as e:
                print(f"Erreur audio : {e}")

    def stop(self):
        self.is_playing = False
        if self.stream:
            self.stream.stop()
            self.stream.close()