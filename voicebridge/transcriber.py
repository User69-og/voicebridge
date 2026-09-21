import numpy as np
from faster_whisper import WhisperModel


class Transcriber:
    """Wraps faster-whisper for local, offline speech-to-text."""

    def __init__(self, model_size: str = "base", language: str = "en"):
        self.language = language
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""
        segments, _ = self.model.transcribe(
            audio,
            language=self.language,
            vad_filter=True,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
