import logging
import re
import threading
from typing import Callable, Optional, Tuple

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
    swallowed instead of being typed into the focused window.

    status is one of: "starting", "listening", "transcribing", "paused",
    "error". `on_state_change`, if set, is called after every transition so
    a UI (the tray icon) can reflect it live.
    """

    def __init__(self, config: Config | None = None):
        self.config = config or Config.load()
        self._lock = threading.Lock()
        self.status = "starting"
        self.paused = False
        self.error: Optional[str] = None
        self.transcriber: Optional[Transcriber] = None
        self.on_state_change: Optional[Callable[[], None]] = None
        self.listener = ContinuousListener(
            on_utterance=self._on_utterance,
            sample_rate=self.config.sample_rate,
            silence_ms=self.config.silence_ms,
            min_speech_ms=self.config.min_speech_ms,
        )

    def _set_state(self, status: str, paused: Optional[bool] = None, error: Optional[str] = None) -> None:
        self.status = status
        if paused is not None:
            self.paused = paused
        self.error = error
        if self.on_state_change:
            self.on_state_change()

    def _on_utterance(self, audio) -> None:
        with self._lock:
            if self.transcriber is None or self.status == "error":
                return

            self.status = "transcribing"
            try:
                text = self.transcriber.transcribe(audio)
            except Exception:
                log.exception("Transcription failed for this utterance; still listening")
                self._set_state("paused" if self.paused else "listening")
                return

            new_paused, should_inject = decide_action(text, self.paused)

            if should_inject:
                try:
                    inject_text(text, press_enter=self.config.auto_enter)
                    log.info("Injected: %r", text)
                except Exception:
                    log.exception("Failed to inject transcribed text")
            elif text:
                log.info("Not injecting (%r) -> paused=%s", text, new_paused)

            self._set_state("paused" if new_paused else "listening", new_paused)

    @property
    def enabled(self) -> bool:
        return not self.paused

    def set_enabled(self, value: bool) -> None:
        """Manual override from the tray menu; independent of voice commands."""
        if self.status == "error":
            return
        self._set_state("paused" if not value else "listening", not value)

    def start(self) -> None:
        try:
            self.transcriber = Transcriber(self.config.model_size, self.config.language)
        except Exception as exc:
            log.exception("Failed to load the local speech-to-text model")
            self._set_state("error", error=f"Model load failed: {exc}")
            return

        try:
            self.listener.start()
        except Exception as exc:
            log.exception("Failed to start listening to the microphone")
            self._set_state("error", error=f"Microphone error: {exc}")
            return

        self._set_state("listening", paused=False)
        log.info(
            "VoiceBridge is listening. Just speak, pause, and it types for you. "
            "Say 'pause listening' / 'resume listening' to toggle."
        )

    def stop(self) -> None:
        self.listener.stop()
