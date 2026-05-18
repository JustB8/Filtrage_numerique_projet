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

        # Variables pour l'analyse spectrale en temps réel
        self.current_chunk_in = None
        self.current_chunk_out = None

        # Configuration des filtres (Ordre 2 devient d'ordre variable, initialisé à 2)
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
            elif "Variable" in name:
                btype = 'low' if 'Bas' in name else 'high'
                # Récupération de l'ordre choisi par l'utilisateur (sécurité min 1)
                order = max(1, self.filters[name].get("order", 2))
                self.filters[name]["sos"] = signal.butter(order, f, btype, fs=self.fs, output='sos')
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
            if is_active:
                self._compute_sos(name)

    def set_filter_freq(self, name, freq):
        if name in self.filters:
            self.filters[name]["freq"] = freq
            self._compute_sos(name)

    def set_filter_order(self, name, order):
        """Permet de modifier l'ordre des filtres configurables"""
        if name in self.filters and "Variable" in name:
            self.filters[name]["order"] = order
            self._compute_sos(name)

    def callback(self, outdata, frames, time, status):
        if not self.is_playing or self.data is None:
            outdata.fill(0)
            self.current_chunk_in = None
            self.current_chunk_out = None
            return

        # 1. On calcule ce qu'il reste dans le fichier pour ce bloc
        chunksize = min(len(self.data) - self.current_frame, frames)
        samples = self.data[self.current_frame: self.current_frame + chunksize].copy()

        # 2. GESTION DE LA BOUCLE IMMÉDIATE : Si le morceau se termine, on comble le vide tout de suite
        if chunksize < frames:
            missing_frames = frames - chunksize
            loop_samples = self.data[0:missing_frames].copy()
            
            # Si samples est vide (chunksize=0), on prend juste le début du morceau
            if chunksize == 0:
                samples = loop_samples
            else:
                samples = np.vstack((samples, loop_samples))
                
            self.current_frame = missing_frames
        else:
            self.current_frame += chunksize

        # À ce stade, 'samples' a TOUJOURS la taille exacte demandée ('frames'), fini les tableaux vides !

        # 3. Sauvegarde du signal d'entrée (mix mono pour la FFT)
        self.current_chunk_in = np.mean(samples, axis=1)

        # 4. Application des filtres actifs en cascade
        for name, info in self.filters.items():
            if info["active"] and info["sos"] is not None:
                samples, info["zi"] = signal.sosfilt(info["sos"], samples, axis=0, zi=info["zi"])

        # 5. Sauvegarde du signal filtré (mix mono)
        self.current_chunk_out = np.mean(samples, axis=1)

        # 6. Écriture dans la carte son avec gestion du volume
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