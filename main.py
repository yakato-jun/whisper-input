import sys
import threading
import time
from pathlib import Path

from audio_recorder import AudioRecorder
from config import load_config
from key_listener import KeyListener
from notifier import Notifier
from status_indicator import StatusIndicator
from text_inserter import get_text_inserter
from transcriber import Transcriber


class VoiceInputApp:
    def __init__(self) -> None:
        self.config = load_config()
        self.recorder = AudioRecorder(sample_rate=self.config.sample_rate)
        self.transcriber = Transcriber(api_key=self.config.openai_api_key, model=self.config.model)
        self.text_inserter = get_text_inserter(auto_paste=self.config.auto_paste)
        self.indicator = StatusIndicator()
        self.notifier = Notifier()
        self._lock = threading.Lock()
        self._is_recording = False
        self._latched = False
        self._last_press_time = 0.0
        self._double_tap_window = 0.4

    def start(self) -> None:
        print(f"Voice input ready. Mode={self.config.mode}, trigger={self.config.trigger_key}")
        self.indicator.start()
        self._set_state("idle", "Ready")
        listener = KeyListener(
            trigger_key=self.config.trigger_key,
            on_trigger_press=self._on_trigger_press,
            on_trigger_release=self._on_trigger_release,
        )
        listener.start()

    def _on_trigger_press(self) -> None:
        now = time.monotonic()
        double_tap = (now - self._last_press_time) <= self._double_tap_window
        self._last_press_time = now

        with self._lock:
            currently_recording = self._is_recording
            latched = self._latched

        if double_tap and not currently_recording:
            self._latched = True
            print("Double-tap detected: latched recording start.")
            self._start_recording()
            return

        if latched and currently_recording:
            self._latched = False
            print("Single tap detected: stopping latched recording.")
            self._stop_recording()
            return

        # Default: hold behavior
        self._start_recording()

    def _on_trigger_release(self) -> None:
        with self._lock:
            if self._latched:
                return
        self._stop_recording()

    def _start_recording(self) -> None:
        with self._lock:
            if self._is_recording:
                return
            self._is_recording = True
            print("Recording started...")
            self.recorder.start()
        self.notifier.play_start()
        self._set_state("recording", "Recording...")

    def _stop_recording(self) -> None:
        path: Path | None
        with self._lock:
            if not self._is_recording:
                return
            self._is_recording = False
            path = self.recorder.stop()

        if path is None:
            print("Recording skipped (too short or no audio).")
            self._set_state("idle", "Ready")
            return

        print("Recording stopped. Transcribing...")
        self.notifier.play_stop()
        self._set_state("transcribing", "Transcribing...")
        threading.Thread(
            target=self._transcribe_and_insert,
            args=(path,),
            daemon=True,
        ).start()

    def _transcribe_and_insert(self, audio_path: Path) -> None:
        try:
            text = self.transcriber.transcribe(audio_path)
            if not text:
                print("No transcription result.")
                self._set_state("error", "No text")
                return
            print(f"Transcription: {text}")
            self.indicator.set_preview(text)
            self.text_inserter.insert_text(text)
            print("Inserted transcription at cursor.")
            self._set_state("done", "Inserted")
        except Exception as exc:  # noqa: BLE001
            print(f"Error during transcription or insertion: {exc}")
            self.notifier.play_error()
            self._set_state("error", "Error")
        finally:
            try:
                audio_path.unlink()
            except OSError:
                pass
            # If it was latched, we stay idle; otherwise hold-mode already stopped.
            with self._lock:
                if not self._latched:
                    self._set_state("idle", "Ready")

    def _set_state(self, state: str, message: str | None = None) -> None:
        if self.indicator:
            self.indicator.set_state(state, message)


if __name__ == "__main__":
    try:
        app = VoiceInputApp()
        app.start()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"Fatal error: {exc}")
        sys.exit(1)
