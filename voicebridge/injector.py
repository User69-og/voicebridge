import time

import pyperclip
from pynput.keyboard import Controller, Key

_controller = Controller()


def inject_text(text: str, press_enter: bool = False) -> None:
    """Pastes text into whichever window currently has focus, preserving the clipboard."""
    if not text:
        return

    previous_clipboard = None
    try:
        previous_clipboard = pyperclip.paste()
    except Exception:
        pass

    pyperclip.copy(text)
    time.sleep(0.05)

    with _controller.pressed(Key.ctrl):
        _controller.press("v")
        _controller.release("v")

    time.sleep(0.05)

    if press_enter:
        _controller.press(Key.enter)
        _controller.release(Key.enter)

    if previous_clipboard is not None:
        time.sleep(0.1)
        try:
            pyperclip.copy(previous_clipboard)
        except Exception:
            pass
