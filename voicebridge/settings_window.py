"""The Settings window: a small Tkinter dialog for the options a user would
actually want to flip — launch-on-startup, auto-enter, model size,
language, and how sensitive speech detection is."""
import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from . import autostart
from .config import Config

MODEL_SIZES = ["tiny", "base", "small", "medium"]
LANGUAGES = ["en", "es", "fr", "de", "hi", "ja", "zh", "auto"]

_window_open = False


def open_settings(config: Config, on_save: Optional[Callable[[], None]] = None) -> None:
    """Opens the settings window in its own thread. A second call while one
    is already open is a no-op instead of spawning a conflicting Tk root."""
    global _window_open
    if _window_open:
        return
    _window_open = True

    def _run():
        global _window_open
        try:
            _build_and_show(config, on_save)
        finally:
            _window_open = False

    threading.Thread(target=_run, daemon=True).start()


def _build_and_show(config: Config, on_save: Optional[Callable[[], None]]) -> None:
    root = tk.Tk()
    root.title("VoiceBridge Settings")
    root.resizable(False, False)
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass

    pad = {"padx": 14, "pady": 6}

    launch_var = tk.BooleanVar(value=autostart.is_enabled())
    auto_enter_var = tk.BooleanVar(value=config.auto_enter)
    model_var = tk.StringVar(value=config.model_size)
    lang_var = tk.StringVar(value=config.language)
    silence_var = tk.IntVar(value=config.silence_ms)
    min_speech_var = tk.IntVar(value=config.min_speech_ms)

    ttk.Checkbutton(root, text="Run VoiceBridge when Windows starts", variable=launch_var).pack(
        anchor="w", **pad
    )
    ttk.Checkbutton(root, text="Auto-press Enter after speaking", variable=auto_enter_var).pack(
        anchor="w", **pad
    )

    model_row = ttk.Frame(root)
    model_row.pack(fill="x", **pad)
    ttk.Label(model_row, text="Model size").pack(side="left")
    ttk.OptionMenu(model_row, model_var, model_var.get(), *MODEL_SIZES).pack(side="right")

    lang_row = ttk.Frame(root)
    lang_row.pack(fill="x", **pad)
    ttk.Label(lang_row, text="Language").pack(side="left")
    ttk.OptionMenu(lang_row, lang_var, lang_var.get(), *LANGUAGES).pack(side="right")

    silence_row = ttk.Frame(root)
    silence_row.pack(fill="x", **pad)
    ttk.Label(silence_row, text="Pause length that ends an utterance (ms)").pack(side="left")
    ttk.Spinbox(silence_row, from_=200, to=3000, increment=50, textvariable=silence_var, width=6).pack(
        side="right"
    )

    min_speech_row = ttk.Frame(root)
    min_speech_row.pack(fill="x", **pad)
    ttk.Label(min_speech_row, text="Shortest sound treated as speech (ms)").pack(side="left")
    ttk.Spinbox(
        min_speech_row, from_=50, to=2000, increment=50, textvariable=min_speech_var, width=6
    ).pack(side="right")

    ttk.Label(
        root,
        text="Model size / language changes take effect after restarting VoiceBridge.",
        foreground="#888888",
        wraplength=320,
        justify="left",
    ).pack(anchor="w", **pad)

    def save():
        config.auto_enter = auto_enter_var.get()
        config.model_size = model_var.get()
        config.language = lang_var.get()
        config.silence_ms = int(silence_var.get())
        config.min_speech_ms = int(min_speech_var.get())
        config.save()
        autostart.set_enabled(launch_var.get())
        if on_save:
            on_save()
        root.destroy()

    button_row = ttk.Frame(root)
    button_row.pack(fill="x", **pad)
    ttk.Button(button_row, text="Cancel", command=root.destroy).pack(side="right")
    ttk.Button(button_row, text="Save", command=save).pack(side="right", padx=(0, 8))

    root.mainloop()
