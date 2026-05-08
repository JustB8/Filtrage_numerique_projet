# audio_engine.py

import sounddevice as sd
import soundfile as sf
import numpy as np
from scipy import signal


class AudioEngine:
    def __init__(self):
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

    def callback(self, outdata, frames, time, status):
        if not self.is_playing or self.data is None:
            outdata.fill(0)
            return

        chunksize = min(len(self.data) - self.current_frame, frames)
        # On travaille sur une copie pour ne pas modifier le fichier original
        samples = self.data[self.current_frame: self.current_frame + chunksize].copy()

        # Application des filtres actifs en cascade
        for name, info in self.filters.items():
            if info["active"] and info["sos"] is not None:
                # Utilisation de zi pour la continuité du flux
                samples, info["zi"] = signal.sosfilt(info["sos"], samples, axis=0, zi=info["zi"])

        outdata[:chunksize] = samples * self.volume

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