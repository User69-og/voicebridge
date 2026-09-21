import logging
import re
import threading
from typing import Tuple

from .config import Config
from .injector import inject_text
from .recorder import ContinuousListener
from .transcriber import Transcriber

log = logging.getLogger("voicebridge")

PAUSE_PHRASES = {"pause listening", "pause voicebridge", "voicebridge pause"}
RESUME_PHRASES = {"resume listening", "resume voicebridge", "voicebridge resume", "unpause listening"}


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[.!?,]+$", "", text)
    return re.sub(r"\s+", " ", text)


def decide_action(text: str, paused: bool) -> Tuple[bool, bool]:
    """Given a fresh transcript and the current paused state, returns
    (new_paused, should_inject). Pure and hotkey-free: mic and transcription
    always keep running (that's how "resume listening" can ever be heard) —
    only whether the words get typed anywhere changes."""
    normalized = _normalize(text)

    if paused:
        if normalized in RESUME_PHRASES:
            return False, False
        return True, False

    if normalized in PAUSE_PHRASES:
        return True, False

    return paused, bool(text)


class VoiceBridgeApp:
    """Always listening and always transcribing, so it can hear "resume
    listening" even while paused. While paused, transcribed speech is
    swallowed instead of being typed into the focused window."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config.load()
        self.transcriber = Transcriber(self.config.model_size, self.config.language)
        self._lock = threading.Lock()
        self.status = "starting"
        self.paused = False
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
            self.paused, should_inject = decide_action(text, self.paused)

            if should_inject:
                log.info("Injecting: %r", text)
                inject_text(text, press_enter=self.config.auto_enter)
            elif text:
                log.info("Not injecting (%r) -> paused=%s", text, self.paused)

            self.status = "paused" if self.paused else "listening"

    @property
    def enabled(self) -> bool:
        return not self.paused

    def set_enabled(self, value: bool) -> None:
        """Manual override from the tray menu; independent of voice commands."""
        self.paused = not value
        self.status = "paused" if self.paused else "listening"

    def start(self) -> None:
        self.listener.start()
        self.status = "listening"
        log.info(
            "VoiceBridge is listening. Just speak, pause, and it types for you. "
            "Say 'pause listening' / 'resume listening' to toggle."
        )

    def stop(self) -> None:
        self.listener.stop()
