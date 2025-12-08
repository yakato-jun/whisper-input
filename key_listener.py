from typing import Callable

from pynput import keyboard


def _parse_trigger_key(trigger_key: str) -> keyboard.Key | keyboard.KeyCode:
    try:
        return getattr(keyboard.Key, trigger_key)
    except AttributeError:
        if len(trigger_key) == 1:
            return keyboard.KeyCode.from_char(trigger_key)
        raise ValueError(f"Unsupported trigger key: {trigger_key}")


class KeyListener:
    def __init__(
        self,
        trigger_key: str,
        on_trigger_press: Callable[[], None],
        on_trigger_release: Callable[[], None],
    ) -> None:
        self._trigger = _parse_trigger_key(trigger_key)
        self._on_press = on_trigger_press
        self._on_release = on_trigger_release
        self._listener: keyboard.Listener | None = None

    def _matches(self, key: keyboard.Key | keyboard.KeyCode) -> bool:
        return key == self._trigger

    def _handle_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if self._matches(key):
            self._on_press()

    def _handle_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if self._matches(key):
            self._on_release()

    def start(self) -> None:
        self._listener = keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
        )
        self._listener.start()
        self._listener.join()
