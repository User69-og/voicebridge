import queue
import threading
from typing import Callable, List, Optional

import numpy as np
import sounddevice as sd


class ContinuousListener:
    """Always listening: detects when you start and stop speaking by audio
    energy (no hotkey needed) and calls on_utterance(audio) once you pause."""

    FRAME_MS = 30

    def __init__(
        self,
        on_utterance: Callable[[np.ndarray], None],
        sample_rate: int = 16000,
        silence_ms: int = 700,
        min_speech_ms: int = 250,
        calibration_ms: int = 500,
    ):
        self.sample_rate = sample_rate
        self.on_utterance = on_utterance
        self.frame_samples = int(sample_rate * self.FRAME_MS / 1000)
        self.silence_frames_needed = max(1, silence_ms // self.FRAME_MS)
        self.min_speech_frames = max(1, min_speech_ms // self.FRAME_MS)
        self.calibration_frames = max(1, calibration_ms // self.FRAME_MS)

        self.enabled = True
        self.threshold = 0.02  # overwritten by ambient-noise calibration on start()

        self._stream: Optional[sd.InputStream] = None
        self._thread: Optional[threading.Thread] = None
        self._queue: "queue.Queue[np.ndarray]" = queue.Queue()
        self._running = False

        # segmentation state, reset by reset_state()
        self._speech_frames: List[np.ndarray] = []
        self._silence_run = 0
        self._in_speech = False
        self._ambient_samples: List[float] = []
        self._calibrated = False

    @staticmethod
    def rms(frame: np.ndarray) -> float:
        return float(np.sqrt(np.mean(np.square(frame)))) if frame.size else 0.0

    def reset_state(self) -> None:
        self._speech_frames = []
        self._silence_run = 0
        self._in_speech = False

    def feed_frame(self, frame: np.ndarray) -> None:
        """Advances the speech/silence state machine by one frame. Public so
        the segmentation logic can be unit-tested without real audio hardware."""
        if frame.shape[0] != self.frame_samples:
            return

        level = self.rms(frame)

        if not self._calibrated:
            self._ambient_samples.append(level)
            if len(self._ambient_samples) >= self.calibration_frames:
                ambient = float(np.median(self._ambient_samples))
                self.threshold = max(ambient * 4.0, 0.01)
                self._calibrated = True
            return

        if not self.enabled:
            self.reset_state()
            return

        is_speech = level >= self.threshold

        if is_speech:
            self._speech_frames.append(frame)
            self._silence_run = 0
            self._in_speech = True
        elif self._in_speech:
            self._speech_frames.append(frame)
            self._silence_run += 1
            if self._silence_run >= self.silence_frames_needed:
                spoken_frames = len(self._speech_frames) - self._silence_run
                if spoken_frames >= self.min_speech_frames:
                    audio = np.concatenate(self._speech_frames)
                    self.on_utterance(audio)
                self.reset_state()

    def _callback(self, indata, frames, time_info, status):
        self._queue.put(indata.copy().reshape(-1))

    def start(self) -> None:
        self._running = True
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self.frame_samples,
            callback=self._callback,
        )
        self._stream.start()
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _process_loop(self) -> None:
        while self._running:
            try:
                frame = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            self.feed_frame(frame)
