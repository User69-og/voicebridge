"""End-to-end smoke tests for VoiceBridge's riskiest pieces: automatic
speech segmentation, transcription accuracy, and text injection into a
real foreign window.
Run with the project's venv: .venv/Scripts/python.exe tests/smoke_test.py
"""
import subprocess
import sys
import tempfile
import time
import wave
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _synthesize_speech(text: str) -> str:
    import pyttsx3

    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    engine = pyttsx3.init()
    engine.save_to_file(text, path)
    engine.runAndWait()
    return path


def _load_wav_as_float32(path: str):
    import numpy as np

    with wave.open(path, "rb") as wf:
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        frame_rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    assert sample_width == 2, f"expected 16-bit PCM, got {sample_width * 8}-bit"
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if n_channels > 1:
        audio = audio.reshape(-1, n_channels).mean(axis=1)

    if frame_rate != 16000:
        # simple linear resample to 16kHz
        duration = audio.shape[0] / frame_rate
        target_len = int(duration * 16000)
        audio = np.interp(
            np.linspace(0, audio.shape[0], target_len, endpoint=False),
            np.arange(audio.shape[0]),
            audio,
        ).astype(np.float32)
    return audio


def test_vad_auto_segmentation():
    """Feeds synthetic frames through the always-listening state machine
    (silence -> speech -> silence) and checks it fires on_utterance exactly
    once, with no hotkey or real microphone involved."""
    import numpy as np
    from voicebridge.recorder import ContinuousListener

    utterances = []
    listener = ContinuousListener(
        on_utterance=lambda audio: utterances.append(audio),
        sample_rate=16000,
        silence_ms=300,
        min_speech_ms=150,
        calibration_ms=300,
    )

    rng = np.random.default_rng(0)
    quiet = lambda: (rng.uniform(-1, 1, listener.frame_samples) * 0.002).astype(np.float32)
    loud = lambda: (rng.uniform(-1, 1, listener.frame_samples) * 0.5).astype(np.float32)

    for _ in range(listener.calibration_frames + 2):
        listener.feed_frame(quiet())
    assert listener._calibrated, "listener should finish ambient-noise calibration"

    for _ in range(15):
        listener.feed_frame(loud())
    assert len(utterances) == 0, "should still be mid-utterance, not fired yet"

    for _ in range(listener.silence_frames_needed + 2):
        listener.feed_frame(quiet())

    assert len(utterances) == 1, f"expected exactly one utterance, got {len(utterances)}"
    assert utterances[0].size > 0
    print(f"[vad] captured utterance of {utterances[0].size} samples with no hotkey")
    print("[PASS] vad_auto_segmentation")


def test_transcription_roundtrip():
    from voicebridge.transcriber import Transcriber

    phrase = "hello world this is a voicebridge test"
    wav_path = _synthesize_speech(phrase)
    try:
        audio = _load_wav_as_float32(wav_path)
        transcriber = Transcriber(model_size="base", language="en")
        result = transcriber.transcribe(audio).lower()
        print(f"[transcription] expected phrase: {phrase!r}")
        print(f"[transcription] got:             {result!r}")
        assert "hello" in result and "world" in result, f"transcription mismatch: {result!r}"
        print("[PASS] transcription_roundtrip")
    finally:
        os.remove(wav_path)


def test_text_injection_into_notepad():
    # Windows 11's notepad.exe is an app-execution-alias stub: the process that
    # CreateProcess launches exits immediately once it hands off to the real
    # (differently-PID'd) Notepad window, so we find the window by title instead
    # of by the PID we launched.
    from voicebridge.injector import inject_text
    from pywinauto import Desktop

    subprocess.run(["taskkill", "/IM", "Notepad.exe", "/F"], capture_output=True)
    time.sleep(0.5)
    subprocess.Popen(["notepad.exe"])
    try:
        window = None
        deadline = time.time() + 10
        while time.time() < deadline and window is None:
            for w in Desktop(backend="uia").windows(title_re=".*Notepad.*"):
                window = w
                break
            if window is None:
                time.sleep(0.3)
        assert window is not None, "notepad window never appeared"

        window.set_focus()
        time.sleep(0.5)

        from pynput.keyboard import Controller, Key

        kb = Controller()
        with kb.pressed(Key.ctrl):
            kb.press("a")
            kb.release("a")
        kb.press(Key.delete)
        kb.release(Key.delete)
        time.sleep(0.3)

        sample = "VoiceBridge smoke test 123"
        inject_text(sample, press_enter=False)
        time.sleep(0.5)

        candidates = window.descendants(control_type="Document") or window.descendants(control_type="Edit")
        edit = candidates[0]
        content = edit.get_value() if hasattr(edit, "get_value") else edit.window_text()
        print(f"[injection] notepad now contains: {content!r}")
        assert sample in content, f"injected text not found in notepad: {content!r}"
        print("[PASS] text_injection_into_notepad")
    finally:
        subprocess.run(["taskkill", "/IM", "Notepad.exe", "/F"], capture_output=True)


if __name__ == "__main__":
    test_vad_auto_segmentation()
    test_transcription_roundtrip()
    test_text_injection_into_notepad()
    print("\nAll smoke tests passed.")
