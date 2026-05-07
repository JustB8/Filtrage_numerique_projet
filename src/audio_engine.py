import soundfile as sf
import numpy as np


class AudioEngine:
    def __init__(self):
        self.data = None
        self.samplerate = None
        self.current_frame = 0

    def load_file(self, path):
        try:
            # Lecture du fichier
            # soundfile supporte le mp3 si libsndfile est à jour (v1.1.0+)
            self.data, self.samplerate = sf.read(path)

            # Si le son est en stéréo, on peut le garder ou le sommer en mono
            # selon la complexité des filtres que vous voulez appliquer
            print(f"Fichier chargé avec succès. Sample Rate: {self.samplerate}")

        except Exception as e:
            print(f"Erreur lors du chargement : {e}")