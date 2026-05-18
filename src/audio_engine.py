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

        # Type de filtre global (Butterworth par défaut)
        self.filter_type = "Butterworth"

        # Variables pour l'analyse spectrale en temps réel
        self.current_chunk_in = None
        self.current_chunk_out = None

        # Configuration des filtres
        self.filters = {
            "Passe-Bas Ordre 1": {"active": False, "freq": 1500, "sos": None, "zi": None},
            "Passe-Haut Ordre 1": {"active": False, "freq": 1500, "sos": None, "zi": None},
            "Passe-Bas Variable": {"active": False, "freq": 1500, "order": 2, "sos": None, "zi": None},
            "Passe-Haut Variable": {"active": False, "freq": 1500, "order": 2, "sos": None, "zi": None},
            "Sélecteur (Bandpass)": {"active": False, "freq": 1500, "sos": None, "zi": None},
            "Réjecteur (Notch)": {"active": False, "freq": 1500, "sos": None, "zi": None}
        }

    def load_file(self, file_path):
        self.data, self.fs = sf.read(file_path, dtype='float32')
        if len(self.data.shape) == 1:
            self.data = np.column_stack((self.data, self.data))
        self.current_frame = 0
        self.update_all_filters()

    def set_global_filter_type(self, filter_type):
        """Change le type d'approximation pour tous les filtres et recalcule."""
        self.filter_type = filter_type
        self.update_all_filters()

    def update_all_filters(self):
        """Recalcule les SOS pour tous les filtres actifs."""
        for name in self.filters:
            if self.filters[name]["active"]:
                self._compute_sos(name)

    def _compute_sos(self, name):
        """Calcule les coefficients SOS selon le type de filtre sélectionné."""
        f = self.filters[name]["freq"]
        f = min(f, self.fs / 2 - 1)  # Protection Nyquist

        # Paramètres standards pour Chebyshev et Elliptique
        rp = 1.0   # Ondulation max en bande passante (dB)
        rs = 40.0  # Atténuation min en bande atténuée (dB)

        try:
            # Choix de la fonction de conception de Scipy en fonction de self.filter_type
            if self.filter_type == "Chebyshev Type I":
                filter_func = lambda ord, wn, btype: signal.cheby1(ord, rp, wn, btype, fs=self.fs, output='sos')
            elif self.filter_type == "Chebyshev Type II":
                filter_func = lambda ord, wn, btype: signal.cheby2(ord, rs, wn, btype, fs=self.fs, output='sos')
            elif self.filter_type == "Elliptique":
                filter_func = lambda ord, wn, btype: signal.ellip(ord, rp, rs, wn, btype, fs=self.fs, output='sos')
            else: # Butterworth par défaut
                filter_func = lambda ord, wn, btype: signal.butter(ord, wn, btype, fs=self.fs, output='sos')

            if "Ordre 1" in name:
                btype = 'low' if 'Bas' in name else 'high'
                # Note: Chebyshev/Elliptique d'ordre 1 avec ces specs équivalent globalement à un Butterworth customisé
                self.filters[name]["sos"] = filter_func(1, f, btype)

            elif "Variable" in name:
                btype = 'low' if 'Bas' in name else 'high'
                order = max(1, self.filters[name].get("order", 2))
                self.filters[name]["sos"] = filter_func(order, f, btype)

            elif "Bandpass" in name:
                # Pour un Bandpass, l'ordre Scipy génère un filtre d'ordre 2*N (ici N=2 -> Ordre global 4)
                f_band = [f * 0.8, min(f * 1.2, self.fs / 2 - 1)]
                self.filters[name]["sos"] = filter_func(2, f_band, btype='bandpass')

            elif "Notch" in name:
                # Le Notch (coupe-bande étroit IIR) utilise une structure dédiée indépendante du type global
                b, a = signal.iirnotch(f, 30.0, fs=self.fs)
                self.filters[name]["sos"] = signal.tf2sos(b, a)

            # Initialisation de la mémoire (zi) pour le streaming stéréo
            zi = signal.sosfilt_zi(self.filters[name]["sos"])
            self.filters[name]["zi"] = np.repeat(zi[:, np.newaxis, :], 2, axis=1)
        except Exception as e:
            print(f"Erreur calcul {name} ({self.filter_type}): {e}")

    def update_filter_status(self, name, is_active):
        if name in self.filters:
            self.filters[name]["active"] = is_active
            if is_active:
                self._compute_sos(name)

    def set_filter_freq(self, name, freq):
        if name in self.filters:
            self.filters[name]["freq"] = freq
            if self.filters[name]["active"]:
                self._compute_sos(name)

    def set_filter_order(self, name, order):
        if name in self.filters and "Variable" in name:
            self.filters[name]["order"] = order
            if self.filters[name]["active"]:
                self._compute_sos(name)

    def callback(self, outdata, frames, time, status):
        if not self.is_playing or self.data is None:
            outdata.fill(0)
            self.current_chunk_in = None
            self.current_chunk_out = None
            return

        chunksize = min(len(self.data) - self.current_frame, frames)
        samples = self.data[self.current_frame: self.current_frame + chunksize].copy()

        if chunksize < frames:
            missing_frames = frames - chunksize
            loop_samples = self.data[0:missing_frames].copy()
            if chunksize == 0:
                samples = loop_samples
            else:
                samples = np.vstack((samples, loop_samples))
            self.current_frame = missing_frames
        else:
            self.current_frame += chunksize

        self.current_chunk_in = np.mean(samples, axis=1)

        for name, info in self.filters.items():
            if info["active"] and info["sos"] is not None:
                samples, info["zi"] = signal.sosfilt(info["sos"], samples, axis=0, zi=info["zi"])

        self.current_chunk_out = np.mean(samples, axis=1)
        outdata[:] = samples * self.volume

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
        self.current_chunk_in = None
        self.current_chunk_out = None
        if self.stream:
            self.stream.stop()
            self.stream.close()

    def compute_global_response(self, worN=512):
        w_hz = np.logspace(np.log10(20), np.log10(self.fs / 2 - 1), worN)
        w_rad = 2 * np.pi * w_hz / self.fs
        h_total = np.ones(worN, dtype=complex)
        has_active_filter = False
        
        for name, info in self.filters.items():
            if info["active"] and info["sos"] is not None:
                has_active_filter = True
                _, h = signal.sosfreqz(info["sos"], worN=w_rad)
                h_total *= h
                
        if not has_active_filter:
            return w_hz, np.zeros(worN)
            
        amplitude_db = 20 * np.log10(np.maximum(np.abs(h_total), 1e-5))
        return w_hz, amplitude_db

    def get_fft_data(self):
        if self.current_chunk_in is None or self.current_chunk_out is None or len(self.current_chunk_in) < 128:
            return None, None, None

        n = len(self.current_chunk_in)
        window = np.hanning(n)
        
        fft_in = np.fft.rfft(self.current_chunk_in * window)
        fft_out = np.fft.rfft(self.current_chunk_out * window)
        freqs = np.fft.rfftfreq(n, d=1/self.fs)

        fft_in_db = 20 * np.log10(np.maximum(np.abs(fft_in), 1e-5))
        fft_out_db = 20 * np.log10(np.maximum(np.abs(fft_out), 1e-5))

        return freqs, fft_in_db, fft_out_db