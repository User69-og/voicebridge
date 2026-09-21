from typing import Callable

from pynput import keyboard

_NAME_TO_KEY = {k.name: k for k in keyboard.Key}


def _resolve(name: str):
    name = name.lower().strip()
    if name in _NAME_TO_KEY:
        return _NAME_TO_KEY[name]
    if len(name) == 1:
        return keyboard.KeyCode.from_char(name)
    raise ValueError(f"Unrecognized hotkey: {name!r}")


class PushToTalkListener:
    """Fires on_press when the hotkey goes down, on_release when it comes back up."""

    def __init__(self, hotkey: str, on_press: Callable[[], None], on_release: Callable[[], None]):
        self._key = _resolve(hotkey)
        self._on_press = on_press
        self._on_release = on_release
        self._held = False
        self._listener = keyboard.Listener(on_press=self._handle_press, on_release=self._handle_release)

    def _handle_press(self, key):
        if key == self._key and not self._held:
            self._held = True
            self._on_press()

    def _handle_release(self, key):
        if key == self._key and self._held:
            self._held = False
            self._on_release()

    def start(self) -> None:
        self._listener.start()

    def stop(self) -> None:
        self._listener.stop()
