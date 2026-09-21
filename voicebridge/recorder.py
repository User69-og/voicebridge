import queue
import numpy as np
import sounddevice as sd


class AudioRecorder:
    """Captures mono float32 audio from the default microphone while active."""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._queue: "queue.Queue[np.ndarray]" = queue.Queue()
        self._stream: sd.InputStream | None = None

    def _callback(self, indata, frames, time_info, status):
        self._queue.put(indata.copy())

    def start(self) -> None:
        self._queue = queue.Queue()
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        if self._stream is None:
            return np.zeros(0, dtype=np.float32)
        self._stream.stop()
        self._stream.close()
        self._stream = None

        chunks = []
        while not self._queue.empty():
            chunks.append(self._queue.get())
        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks, axis=0).reshape(-1)
