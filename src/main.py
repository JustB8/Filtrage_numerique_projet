from gui import AudioVisualApp
from audio_engine import *

if __name__ == "__main__":
    audioEngine = AudioEngine()
    app = AudioVisualApp(audioEngine)
    app.mainloop()