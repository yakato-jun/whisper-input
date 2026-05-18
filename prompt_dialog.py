import threading
from typing import Optional

from prompt_manager import PromptManager


class PromptDialog:
    """
    Tk dialog window with a checkbox list to toggle prompts on/off.
    Falls back silently if tkinter is unavailable. Closing the window
    is one-way: it does not reopen.
    """

    def __init__(self, manager: PromptManager, geometry: str = "360x320+460+24") -> None:
        self._manager = manager
        self._geometry = geometry
        self._thread: Optional[threading.Thread] = None
        self._started = False
        self._enabled = True

    def start(self) -> bool:
        if self._started:
            return self._enabled
        self._started = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self._enabled

    def _run(self) -> None:
        try:
            import tkinter as tk
        except Exception as exc:  # noqa: BLE001
            print(f"Prompt dialog disabled (tkinter unavailable): {exc}")
            self._enabled = False
            return

        root = tk.Tk()
        root.title("Voice Input — Prompts")
        root.attributes("-topmost", True)
        root.geometry(self._geometry)

        header = tk.Label(
            root,
            text="Active prompts (applied at recording start):",
            font=("Helvetica", 9, "bold"),
            anchor="w",
            justify="left",
        )
        header.pack(fill="x", padx=8, pady=(8, 4))

        body = tk.Frame(root)
        body.pack(fill="both", expand=True, padx=8, pady=4)

        entries = self._manager.list_entries()
        if not entries:
            empty = tk.Label(
                body,
                text="(no prompts found in prompts/ folder)",
                fg="#888",
                anchor="w",
                justify="left",
            )
            empty.pack(fill="x", pady=4)
        else:
            for entry in entries:
                var = tk.BooleanVar(master=root, value=self._manager.is_enabled(entry.identifier))

                def make_handler(ident: str, v: tk.BooleanVar):
                    def handler() -> None:
                        new_value = bool(v.get())
                        print(f"[dialog] checkbox toggled: {ident} -> {new_value}")
                        self._manager.set_enabled(ident, new_value)
                    return handler

                label = entry.name
                if entry.description:
                    label = f"{entry.name} — {entry.description}"
                cb = tk.Checkbutton(
                    body,
                    text=label,
                    variable=var,
                    command=make_handler(entry.identifier, var),
                    anchor="w",
                    justify="left",
                    wraplength=320,
                )
                cb.pack(fill="x", anchor="w")

        footer = tk.Label(
            root,
            text="Close to dismiss. Re-launch the app to reopen.",
            font=("Helvetica", 8),
            fg="#888",
            anchor="w",
            justify="left",
        )
        footer.pack(fill="x", padx=8, pady=(4, 8))

        try:
            root.mainloop()
        except Exception:
            self._enabled = False
