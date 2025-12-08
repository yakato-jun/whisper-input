import shutil
import subprocess
import sys
from typing import Protocol


class TextInserter(Protocol):
    def insert_text(self, text: str) -> None: ...


class LinuxTextInserter:
    def __init__(self, auto_paste: bool = False) -> None:
        for cmd in ("xclip", "xdotool"):
            if shutil.which(cmd) is None:
                raise RuntimeError(f"{cmd} is required on Linux but was not found in PATH.")
        self.auto_paste = auto_paste

    def insert_text(self, text: str) -> None:
        subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=text.encode("utf-8"),
            check=True,
        )
        if self.auto_paste:
            subprocess.run(
                ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
                check=True,
            )


class WindowsTextInserter:
    def __init__(self, auto_paste: bool = False) -> None:
        self.auto_paste = auto_paste

    def insert_text(self, text: str) -> None:
        import pyperclip
        pyperclip.copy(text)
        if self.auto_paste:
            import time
            from pynput.keyboard import Controller, Key
            keyboard = Controller()
            time.sleep(0.05)
            keyboard.press(Key.ctrl)
            keyboard.press('v')
            keyboard.release('v')
            keyboard.release(Key.ctrl)


def get_text_inserter(auto_paste: bool = False) -> TextInserter:
    if sys.platform.startswith("linux"):
        return LinuxTextInserter(auto_paste=auto_paste)
    if sys.platform.startswith("win"):
        return WindowsTextInserter(auto_paste=auto_paste)
    raise NotImplementedError(f"Unsupported platform: {sys.platform}")
