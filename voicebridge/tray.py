from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

from .app import VoiceBridgeApp
from .config import Config


def _make_icon_image() -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, size - 4, size - 4), fill=(255, 90, 45, 255))
    draw.rounded_rectangle((24, 14, 40, 38), radius=8, fill=(20, 16, 14, 255))
    draw.rectangle((30, 38, 34, 48), fill=(20, 16, 14, 255))
    draw.line((22, 48, 42, 48), fill=(20, 16, 14, 255), width=4)
    return img


def run() -> None:
    config = Config.load()
    app = VoiceBridgeApp(config)

    def toggle_active(icon, item):
        # Mic and transcription never stop (needed to hear "resume listening");
        # this only controls whether transcribed speech gets typed anywhere.
        app.set_enabled(not app.enabled)

    def toggle_auto_enter(icon, item):
        app.config.auto_enter = not app.config.auto_enter
        app.config.save()

    def quit_app(icon, item):
        app.stop()
        icon.stop()

    menu = Menu(
        MenuItem("VoiceBridge", None, enabled=False),
        MenuItem(lambda item: f"Status: {app.status}", None, enabled=False),
        MenuItem("Active (not paused)", toggle_active, checked=lambda item: app.enabled),
        MenuItem("Auto-press Enter", toggle_auto_enter, checked=lambda item: app.config.auto_enter),
        MenuItem("Quit", quit_app),
    )

    icon = Icon("VoiceBridge", _make_icon_image(), "VoiceBridge", menu)
    app.start()
    icon.run()


if __name__ == "__main__":
    run()
