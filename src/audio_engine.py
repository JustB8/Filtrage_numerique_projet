# audioengine.py

import sounddevice as sd
import soundfile as sf
import numpy as np


class AudioEngine:
    def __init__(self):
        self.data = None
        self.fs = 44100  # Valeur par défaut
        self.stream = None
        self.current_frame = 0
        self.volume = 1.0
        self.is_playing = False

    def load_file(self, file_path):
        self.data, self.fs = sf.read(file_path, dtype='float32')
        print(f"Fréquence d'échantillonnage du fichier : {self.fs} Hz")
        if len(self.data.shape) == 1:  # Mono -> Stéréo
            self.data = np.column_stack((self.data, self.data))
        self.current_frame = 0

    def callback(self, outdata, frames, time, status):
        if status:
            print(status)
        if not self.is_playing or self.data is None:
            outdata.fill(0)
            return

        chunksize = min(len(self.data) - self.current_frame, frames)
        samples = self.data[self.current_frame: self.current_frame + chunksize]

        # Traitement du volume
        processed_samples = samples * self.volume

        if chunksize < frames:
            outdata[:chunksize] = processed_samples
            outdata[chunksize:] = 0
            self.is_playing = False
            self.current_frame = 0
        else:
            outdata[:] = processed_samples
            self.current_frame += chunksize

    def start(self):
        if self.data is None:
            print("Erreur : Aucun fichier chargé.")
            return

        try:
            # Sécurité : Toujours fermer avant de réouvrir
            if self.stream is not None:
                self.stream.stop()
                self.stream.close()

            # Utiliser explicitement le device 'default' ou 'pulse'
            # pour éviter que sounddevice ne cherche à interroger le hardware direct (hw:0,0)
            self.stream = sd.OutputStream(
                samplerate=self.fs,
                channels=2,
                callback=self.callback,
                device='default', # FORCE l'utilisation du serveur audio Debian
                blocksize=2048,   # Taille intermédiaire pour limiter l'underflow
                latency='high'    # Crucial sur VM
            )
            self.is_playing = True
            self.stream.start()
        except Exception as e:
            print(f"La carte son a rejeté la connexion : {e}")

    def stop(self):
        self.is_playing = False
        if self.stream:
            self.stream.stop()