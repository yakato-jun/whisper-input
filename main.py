import argparse
import sys
import threading
import time
from pathlib import Path

from audio_recorder import AudioRecorder
from config import load_config
from key_listener import KeyListener
from notifier import Notifier
from prompt_dialog import PromptDialog
from prompt_manager import PromptManager
from status_indicator import StatusIndicator
from text_formatter import TextFormatter
from text_inserter import get_text_inserter
from transcriber import Transcriber


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Voice input via OpenAI transcription.")
    parser.add_argument(
        "--prompts",
        type=str,
        default="",
        help="Comma-separated prompt identifiers to enable at startup (e.g. --prompts robotics,formatting).",
    )
    parser.add_argument(
        "--prompts-dir",
        type=str,
        default="prompts",
        help="Directory containing *.md prompt files (default: prompts).",
    )
    parser.add_argument(
        "--no-prompt-dialog",
        action="store_true",
        help="Do not open the prompt selection dialog at startup.",
    )
    parser.add_argument(
        "--formatter-model",
        type=str,
        default=None,
        help="Override formatter model (e.g. gpt-5.4-nano, gpt-5.4-mini, gpt-5.4). Default: from config.",
    )
    parser.add_argument(
        "--reasoning-effort",
        type=str,
        default=None,
        help="Override reasoning effort: low / medium / high / xhigh. Default: from config.",
    )
    parser.add_argument(
        "--no-formatter",
        action="store_true",
        help="Skip the formatter step entirely (transcribe only).",
    )
    return parser.parse_args(argv)


class VoiceInputApp:
    def __init__(self, args: argparse.Namespace) -> None:
        self.config = load_config()
        self.recorder = AudioRecorder(sample_rate=self.config.sample_rate)
        self.transcriber = Transcriber(api_key=self.config.openai_api_key, model=self.config.model)
        formatter_model = args.formatter_model or self.config.formatter_model
        reasoning_effort = args.reasoning_effort or self.config.reasoning_effort
        self.formatter = TextFormatter(
            api_key=self.config.openai_api_key,
            model=formatter_model,
            reasoning_effort=reasoning_effort,
        )
        self._formatter_enabled = not args.no_formatter
        self._formatter_model = formatter_model
        self._reasoning_effort = reasoning_effort
        self.text_inserter = get_text_inserter(auto_paste=self.config.auto_paste)
        self.indicator = StatusIndicator()
        self.notifier = Notifier()
        self.prompt_manager = PromptManager(prompts_dir=Path(args.prompts_dir))
        initial = [p.strip() for p in args.prompts.split(",") if p.strip()]
        if initial:
            self.prompt_manager.enable_many(initial)
        self.prompt_dialog: PromptDialog | None = None
        if not args.no_prompt_dialog:
            self.prompt_dialog = PromptDialog(self.prompt_manager)
        self._lock = threading.Lock()
        self._is_recording = False
        self._latched = False
        self._last_press_time = 0.0
        self._double_tap_window = 0.4
        self._active_prompt = ""

    def start(self) -> None:
        print(f"Voice input ready. Mode={self.config.mode}, trigger={self.config.trigger_key}")
        print(
            f"Transcribe model={self.config.model} | "
            f"Formatter: model={self._formatter_model} effort={self._reasoning_effort} "
            f"enabled={self._formatter_enabled}"
        )
        enabled_now = self.prompt_manager.get_enabled_identifiers()
        if enabled_now:
            print(f"Prompts enabled at startup: {', '.join(enabled_now)}")
        else:
            print("Prompts enabled at startup: (none)")
        self.indicator.start()
        if self.prompt_dialog is not None:
            self.prompt_dialog.start()
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
        snapshot = self.prompt_manager.build_merged_prompt()
        enabled_ids = self.prompt_manager.get_enabled_identifiers()
        with self._lock:
            if self._is_recording:
                return
            self._is_recording = True
            self._active_prompt = snapshot
            print("Recording started...")
            if enabled_ids:
                print(f"Active prompts: {', '.join(enabled_ids)} ({len(snapshot)} chars)")
                print(f"--- merged prompt ---\n{snapshot}\n---------------------")
            else:
                print("Active prompts: (none)")
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
            prompt = self._active_prompt

        if path is None:
            print("Recording skipped (too short or no audio).")
            self._set_state("idle", "Ready")
            return

        print("Recording stopped. Transcribing...")
        self.notifier.play_stop()
        self._set_state("transcribing", "Transcribing...")
        threading.Thread(
            target=self._transcribe_and_insert,
            args=(path, prompt),
            daemon=True,
        ).start()

    def _transcribe_and_insert(self, audio_path: Path, prompt: str = "") -> None:
        try:
            text = self.transcriber.transcribe(audio_path)
            if not text:
                print("No transcription result.")
                self._set_state("error", "No text")
                return
            print(f"Transcription (raw): {text}")
            if self._formatter_enabled:
                formatted = self.formatter.format_text(text, prompt)
                if formatted != text:
                    print(f"Transcription (formatted): {formatted}")
                text = formatted
            else:
                print("[formatter] disabled by --no-formatter")
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
        app = VoiceInputApp(_parse_args())
        app.start()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"Fatal error: {exc}")
        sys.exit(1)
