import tempfile
import threading
import wave
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd


class AudioRecorder:
    MIN_DURATION_SEC = 1.0

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self._stream: Optional[sd.InputStream] = None
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._stream is not None:
                return

            self._frames = []
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                callback=self._callback,
            )
            self._stream.start()

    def stop(self) -> Optional[Path]:
        with self._lock:
            if self._stream is None:
                return None
            self._stream.stop()
            self._stream.close()
            self._stream = None

            if not self._frames:
                return None

            audio_data = np.concatenate(self._frames, axis=0)
            total_frames = audio_data.shape[0]
            duration_sec = total_frames / float(self.sample_rate)
            if duration_sec < self.MIN_DURATION_SEC:
                return None

            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            tmp_path = Path(tmp_file.name)
            tmp_file.close()

            with wave.open(str(tmp_path), "wb") as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # int16
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data.tobytes())

            return tmp_path

    def _callback(self, indata, frames, time, status) -> None:  # type: ignore[override]
        if status:
            # Status is informational; we log by ignoring for now to keep callback fast.
            pass
        self._frames.append(indata.copy())
