import logging
import threading

from .config import Config
from .hotkey import PushToTalkListener
from .injector import inject_text
from .recorder import AudioRecorder
from .transcriber import Transcriber

log = logging.getLogger("voicebridge")


class VoiceBridgeApp:
    """Hold the hotkey, speak, release: your words get typed into the focused app."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config.load()
        self.recorder = AudioRecorder(sample_rate=self.config.sample_rate)
        self.transcriber: Transcriber | None = None
        self._lock = threading.Lock()
        self._listener = PushToTalkListener(
            self.config.hotkey, on_press=self._on_press, on_release=self._on_release
        )
        self.status = "idle"

    def _ensure_transcriber(self) -> Transcriber:
        if self.transcriber is None:
            log.info("Loading whisper model %r ...", self.config.model_size)
            self.transcriber = Transcriber(self.config.model_size, self.config.language)
        return self.transcriber

    def _on_press(self) -> None:
        with self._lock:
            self.status = "recording"
            log.info("Recording...")
            self.recorder.start()

    def _on_release(self) -> None:
        with self._lock:
            self.status = "transcribing"
            audio = self.recorder.stop()
            log.info("Transcribing %d samples...", audio.size)
            text = self._ensure_transcriber().transcribe(audio)
            if text:
                log.info("Injecting: %r", text)
                inject_text(text, press_enter=self.config.auto_enter)
            self.status = "idle"

    def start(self) -> None:
        self._ensure_transcriber()
        self._listener.start()
        log.info("VoiceBridge ready. Hold [%s] to talk.", self.config.hotkey)

    def stop(self) -> None:
        self._listener.stop()
