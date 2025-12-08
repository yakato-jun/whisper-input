import queue
import threading
from typing import Optional


class StatusIndicator:
    """
    Tiny always-on-top window to show voice input status and last result.
    Falls back silently if tkinter is unavailable.
    """

    COLORS = {
        "idle": ("#f4f4f4", "#2f2f2f"),
        "recording": ("#ff4d4f", "#ffffff"),
        "transcribing": ("#ffa940", "#1f1f1f"),
        "done": ("#52c41a", "#ffffff"),
        "error": ("#cf1322", "#ffffff"),
    }

    DEFAULT_TEXT = {
        "idle": "Ready",
        "recording": "Rec...",
        "transcribing": "Transcribing...",
        "done": "Done",
        "error": "Error",
    }

    def __init__(self, geometry: str = "420x120+24+24") -> None:
        self._queue: "queue.Queue[tuple[str | None, Optional[str], Optional[str]]]" = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._started = False
        self._geometry = geometry
        self._enabled = True

    def start(self) -> bool:
        if self._started:
            return self._enabled
        self._started = True
        self._thread.start()
        return self._enabled

    def set_state(self, state: str, message: Optional[str] = None, preview: Optional[str] = None) -> None:
        if not self._enabled or not self._started:
            return
        self._queue.put((state, message, preview))

    def set_preview(self, preview: str) -> None:
        if not self._enabled or not self._started:
            return
        self._queue.put((None, None, preview))

    def _run(self) -> None:
        try:
            import tkinter as tk
        except Exception as exc:  # noqa: BLE001
            print(f"Status indicator disabled (tkinter unavailable): {exc}")
            self._enabled = False
            return

        root = tk.Tk()
        root.title("Voice Input")
        root.attributes("-topmost", True)
        root.resizable(False, False)
        try:
            root.attributes("-toolwindow", True)
        except Exception:
            pass
        root.geometry(self._geometry)

        frame = tk.Frame(root, borderwidth=1, relief="solid")
        frame.pack(fill="both", expand=True)

        status_label = tk.Label(
            frame,
            text=self.DEFAULT_TEXT["idle"],
            font=("Helvetica", 8, "bold"),
            anchor="w",
            justify="left",
        )
        status_label.pack(fill="x", padx=6, pady=(6, 2), anchor="nw")

        preview_label = tk.Label(
            frame,
            text="",
            font=("Helvetica", 6),
            anchor="nw",
            justify="left",
            wraplength=360,
        )
        preview_label.pack(fill="both", expand=True, padx=6, pady=(0, 6), anchor="nw")

        preview_text: Optional[str] = ""

        def apply_state(state: Optional[str], message: Optional[str], preview: Optional[str]) -> None:
            nonlocal preview_text
            if state is not None:
                bg, fg = self.COLORS.get(state, self.COLORS["idle"])
                text = message or self.DEFAULT_TEXT.get(state, self.DEFAULT_TEXT["idle"])
                frame.configure(background=bg)
                status_label.configure(text=text, background=bg, foreground=fg)
                root.configure(background=bg)
                preview_label.configure(background=bg)
            if preview is not None:
                preview_text = preview
            preview_label.configure(text=preview_text or "")

        def poll_queue() -> None:
            try:
                while True:
                    state, msg, preview = self._queue.get_nowait()
                    apply_state(state, msg, preview)
            except queue.Empty:
                pass
            root.after(100, poll_queue)

        apply_state("idle", None, "")
        root.after(100, poll_queue)
        try:
            root.mainloop()
        except Exception:
            self._enabled = False
