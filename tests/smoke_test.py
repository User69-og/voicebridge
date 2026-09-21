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


def test_pause_resume_voice_commands():
    """The mic and transcriber must never stop (that's the only way "resume
    listening" can ever be heard) — pausing only suppresses injection."""
    from voicebridge.app import decide_action

    paused = False

    paused, inject = decide_action("hello world", paused)
    assert inject and not paused, "normal speech should inject while active"

    paused, inject = decide_action("Pause listening.", paused)
    assert not inject and paused, "the pause phrase itself must not be typed"

    paused, inject = decide_action("are you still there", paused)
    assert not inject and paused, "speech while paused must be swallowed, not typed"

    paused, inject = decide_action("resume listening", paused)
    assert not inject and not paused, "the resume phrase itself must not be typed"

    paused, inject = decide_action("hello again", paused)
    assert inject and not paused, "normal speech should inject again after resuming"

    print("[PASS] pause_resume_voice_commands")


def test_state_change_hook_drives_tray_icon():
    """Every state transition VoiceBridge can reach (starting -> listening,
    pause/resume, and setup failures) must fire on_state_change exactly the
    way the tray icon relies on to pick its color: active/paused/error."""
    import voicebridge.app as appmod
    from voicebridge.config import Config

    # 1. model load failure -> error state, callback fires, listener never starts
    class ExplodingTranscriber:
        def __init__(self, *a, **kw):
            raise RuntimeError("no such model")

    real_transcriber_cls = appmod.Transcriber
    appmod.Transcriber = ExplodingTranscriber
    try:
        app = appmod.VoiceBridgeApp(Config())
        events = []
        app.on_state_change = lambda: events.append(app.status)
        app.start()
        assert app.status == "error", app.status
        assert app.error and "no such model" in app.error, app.error
        assert events == ["error"], events
        assert app.listener._stream is None, "mic must never start after a model-load failure"
    finally:
        appmod.Transcriber = real_transcriber_cls
    print("[PASS] error state on model-load failure")

    # 2. microphone failure -> error state, callback fires
    class StubTranscriber:
        def __init__(self, *a, **kw):
            pass

    appmod.Transcriber = StubTranscriber
    try:
        app = appmod.VoiceBridgeApp(Config())

        def boom():
            raise OSError("no default input device")

        app.listener.start = boom
        events = []
        app.on_state_change = lambda: events.append(app.status)
        app.start()
        assert app.status == "error", app.status
        assert "no default input device" in app.error, app.error
        assert events == ["error"], events
    finally:
        appmod.Transcriber = real_transcriber_cls
    print("[PASS] error state on microphone failure")

    # 3. once in error state, manual pause/resume toggling from the tray is a no-op
    app.set_enabled(True)
    assert app.status == "error", "toggling must not clear an error state"

    # 4. normal pause/resume still fires the hook so the icon can flip
    appmod.Transcriber = StubTranscriber
    try:
        app2 = appmod.VoiceBridgeApp(Config())
        app2.transcriber = StubTranscriber()
        events2 = []
        app2.on_state_change = lambda: events2.append((app2.status, app2.paused))
        app2.set_enabled(False)
        app2.set_enabled(True)
        assert events2 == [("paused", True), ("listening", False)], events2
    finally:
        appmod.Transcriber = real_transcriber_cls
    print("[PASS] state_change_hook_drives_tray_icon")


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
    test_pause_resume_voice_commands()
    test_state_change_hook_drives_tray_icon()
    test_transcription_roundtrip()
    test_text_injection_into_notepad()
    print("\nAll smoke tests passed.")
