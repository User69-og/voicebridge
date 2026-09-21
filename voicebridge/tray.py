from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

from .app import VoiceBridgeApp
from .config import Config
from .settings_window import open_settings

_ACTIVE_COLOR = (255, 90, 45, 255)    # orange: listening and acting on speech
_PAUSED_COLOR = (120, 120, 120, 255)  # gray: still listening, not acting (also used while starting)
_ERROR_COLOR = (210, 45, 45, 255)     # red: something in setup is broken


def _make_icon_image(color) -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, size - 4, size - 4), fill=color)
    draw.rounded_rectangle((24, 14, 40, 38), radius=8, fill=(20, 16, 14, 255))
    draw.rectangle((30, 38, 34, 48), fill=(20, 16, 14, 255))
    draw.line((22, 48, 42, 48), fill=(20, 16, 14, 255), width=4)
    return img


def run() -> None:
    config = Config.load()
    app = VoiceBridgeApp(config)

    active_image = _make_icon_image(_ACTIVE_COLOR)
    paused_image = _make_icon_image(_PAUSED_COLOR)
    error_image = _make_icon_image(_ERROR_COLOR)

    icon = Icon("VoiceBridge", paused_image, "VoiceBridge — starting...", Menu())

    def sync_icon() -> None:
        if app.status == "error":
            icon.icon = error_image
            icon.title = f"VoiceBridge — error: {app.error}"
        elif app.status == "starting":
            icon.icon = paused_image
            icon.title = "VoiceBridge — starting..."
        elif app.paused:
            icon.icon = paused_image
            icon.title = "VoiceBridge — paused (still listening)"
        else:
            icon.icon = active_image
            icon.title = "VoiceBridge — listening"
        icon.update_menu()

    app.on_state_change = sync_icon

    def toggle_active(icon, item):
        # Mic and transcription never stop (needed to hear "resume listening");
        # this only controls whether transcribed speech gets typed anywhere.
        app.set_enabled(not app.enabled)

    def toggle_auto_enter(icon, item):
        app.config.auto_enter = not app.config.auto_enter
        app.config.save()

    def show_settings(icon, item):
        def on_save():
            app.apply_live_settings()
            sync_icon()

        open_settings(app.config, on_save=on_save)

    def quit_app(icon, item):
        app.stop()
        icon.stop()

    def status_label(item):
        if app.status == "error":
            return f"Error: {app.error}"
        return f"Status: {app.status}"

    icon.menu = Menu(
        MenuItem("VoiceBridge", None, enabled=False),
        MenuItem(status_label, None, enabled=False),
        MenuItem(
            "Active (not paused)",
            toggle_active,
            checked=lambda item: app.enabled,
            enabled=lambda item: app.status != "error",
        ),
        MenuItem("Auto-press Enter", toggle_auto_enter, checked=lambda item: app.config.auto_enter),
        MenuItem("Settings...", show_settings),
        MenuItem("Quit", quit_app),
    )

    app.start()
    icon.run()


if __name__ == "__main__":
    run()
