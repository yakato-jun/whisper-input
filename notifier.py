import threading
import wave
from pathlib import Path
from typing import Iterable

import numpy as np
import sounddevice as sd


class Notifier:
    """Plays short bundled wav tones to signal start/stop/error."""

    def __init__(self, assets_dir: Path | None = None) -> None:
        base = assets_dir or Path(__file__).resolve().parent / "assets"
        self.assets_dir = base
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.start_file = self.assets_dir / "tone_start.wav"
        self.stop_file = self.assets_dir / "tone_stop.wav"
        self.error_file = self.assets_dir / "tone_error.wav"
        self._ensure_assets()

    def play_start(self) -> None:
        self._play_file(self.start_file)

    def play_stop(self) -> None:
        self._play_file(self.stop_file)

    def play_error(self) -> None:
        self._play_file(self.error_file)

    def _play_file(self, path: Path) -> None:
        threading.Thread(
            target=self._play_file_sync,
            args=(path,),
            daemon=True,
        ).start()

    def _play_file_sync(self, path: Path) -> None:
        try:
            with wave.open(str(path), "rb") as wf:
                sample_rate = wf.getframerate()
                channels = wf.getnchannels()
                frames = wf.readframes(wf.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16)
            if channels > 1:
                audio = audio.reshape(-1, channels)
            audio = audio.astype(np.float32) / 32768.0
            sd.play(audio, sample_rate, blocking=False)
        except Exception:
            # Best-effort: ignore playback errors to avoid interrupting main flow.
            pass

    def _ensure_assets(self) -> None:
        if not self.start_file.exists():
            self._write_tone(self.start_file, freqs=[660], duration=0.10)
        if not self.stop_file.exists():
            self._write_tone(self.stop_file, freqs=[440], duration=0.10)
        if not self.error_file.exists():
            self._write_tone(self.error_file, freqs=[330, 220], duration=0.16)

    def _write_tone(self, path: Path, freqs: Iterable[int], duration: float, sample_rate: int = 44100) -> None:
        freqs = list(freqs)
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        wave_sum = sum(np.sin(2 * np.pi * f * t) for f in freqs)
        wave_sum = wave_sum / max(len(freqs), 1)
        audio = (wave_sum * 0.25 * 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio.tobytes())
