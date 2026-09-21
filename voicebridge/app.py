import logging
import threading

from .config import Config
from .injector import inject_text
from .recorder import ContinuousListener
from .transcriber import Transcriber

log = logging.getLogger("voicebridge")


class VoiceBridgeApp:
    """Always listening: speak, pause, and your words get typed into whatever
    app currently has focus. No hotkey, no touching the keyboard or trackpad."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config.load()
        self.transcriber = Transcriber(self.config.model_size, self.config.language)
        self._lock = threading.Lock()
        self.status = "starting"
        self.listener = ContinuousListener(
            on_utterance=self._on_utterance,
            sample_rate=self.config.sample_rate,
            silence_ms=self.config.silence_ms,
            min_speech_ms=self.config.min_speech_ms,
        )

    def _on_utterance(self, audio) -> None:
        with self._lock:
            self.status = "transcribing"
            text = self.transcriber.transcribe(audio)
            if text:
                log.info("Injecting: %r", text)
                inject_text(text, press_enter=self.config.auto_enter)
            self.status = "listening"

    @property
    def enabled(self) -> bool:
        return self.listener.enabled

    def set_enabled(self, value: bool) -> None:
        self.listener.enabled = value
        self.status = "listening" if value else "paused"

    def start(self) -> None:
        self.listener.start()
        self.status = "listening"
        log.info("VoiceBridge is listening. Just speak, pause, and it types for you.")

    def stop(self) -> None:
        self.listener.stop()
