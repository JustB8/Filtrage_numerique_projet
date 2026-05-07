import sounddevice as sd
import soundfile as sf
import numpy as np


class AudioEngine:
    def __init__(self):
        self.data = None
        self.fs = None
        self.current_frame = 0
        self.stream = None
        self.volume = 1.0
        self.is_playing = False

    def load_file(self, file_path):
        # Lecture du fichier
        self.data, self.fs = sf.read(file_path, dtype='float32')
        self.current_frame = 0

    def callback(self, outdata, frames, time, status):
        if not self.is_playing:
            outdata.fill(0)
            return

        # Calcul des indices pour le bloc de données
        chunksize = min(len(self.data) - self.current_frame, frames)

        # Extraction du bloc
        samples = self.data[self.current_frame: self.current_frame + chunksize]

        # Application du volume (et futur emplacement des filtres !)
        processed_samples = samples * self.volume

        # Remplissage du buffer de sortie
        if chunksize < frames:
            outdata[:chunksize] = processed_samples
            outdata[chunksize:] = 0
            self.is_playing = False  # Fin du fichier
            self.current_frame = 0
        else:
            outdata[:] = processed_samples
            self.current_frame += chunksize

    def start(self):
        if self.data is not None:
            self.is_playing = True
            if self.stream is None:
                self.stream = sd.OutputStream(
                    samplerate=self.fs,
                    channels=self.data.shape[1] if len(self.data.shape) > 1 else 1,
                    callback=self.callback
                )
                self.stream.start()

    def stop(self):
        self.is_playing = False

    def set_volume(self, value):
        self.volume = float(value)