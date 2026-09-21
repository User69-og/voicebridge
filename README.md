# VoiceBridge

A hands-free voice interface for talking to your AI (or anything else on your
screen). Just speak — no hotkey, no push-to-talk — and your words get
transcribed locally and typed straight into whatever window has focus. No
keyboard, no trackpad.

Inspired by a demo of "Infina," rebuilt from scratch for Windows.

## How it works

1. VoiceBridge listens to your microphone continuously in the background.
2. It automatically detects when you start and stop speaking (voice activity
   detection by audio energy, calibrated to your room's ambient noise on
   startup) — no button to hold.
3. When you pause, that utterance is transcribed **locally and offline**
   with [faster-whisper](https://github.com/SYSTRAN/faster-whisper) —
   nothing is sent to any server.
4. The transcribed text is pasted into whatever application currently has
   focus — your editor, a chat window, a terminal, Slack, anything — and
   Enter is pressed automatically (configurable).

Runs as a system tray app in the background. The mic and transcriber never
stop — that's what lets it hear you resume — but you can pause and resume by
**voice** at any time:

- Say **"pause listening"** — VoiceBridge keeps listening and transcribing,
  but stops typing anything anywhere until you resume.
- Say **"resume listening"** — it starts injecting again.

Neither phrase itself ever gets typed into your focused window. You can also
toggle the same state from the tray menu ("Active (not paused)") with the
mouse.

## Setup

Requires Python 3.10+ on Windows.

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Run

```bash
.venv\Scripts\python main.py
```

The first run downloads the local Whisper model (~150MB for the default
`base` size) and caches it, then calibrates to the room's background noise
for about half a second. After that, just talk — pause for a beat and your
words appear wherever your cursor is focused.

## Configuration

Settings live in `%APPDATA%\VoiceBridge\config.json`:

| key            | default | notes                                       |
|----------------|---------|----------------------------------------------|
| `auto_enter`   | `true`  | press Enter automatically after injecting     |
| `model_size`   | `base`  | whisper model size: tiny/base/small/medium    |
| `language`     | `en`    | transcription language                        |
| `silence_ms`   | `700`   | pause length that ends an utterance           |
| `min_speech_ms`| `250`   | shortest sound treated as real speech         |

## Testing

```bash
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python tests/smoke_test.py
```

This exercises the riskiest paths end-to-end: feeding synthetic audio frames
through the always-listening speech detector to confirm it segments
utterances correctly without a hotkey, driving the pause/resume voice-command
logic to confirm paused speech is swallowed (never typed) while the pause and
resume phrases themselves are also never typed, synthesizing speech with the
OS TTS engine to check transcription round-trips correctly, and opening a
real Notepad window to verify injected text actually lands there.

## Project layout

```
voicebridge/
  recorder.py     always-on mic listener + automatic speech segmentation
  transcriber.py  local speech-to-text (faster-whisper)
  injector.py     pastes text into the focused window (pynput + clipboard)
  app.py          wires listener -> transcriber -> injector together
  tray.py         system tray icon and menu
main.py           entry point
tests/smoke_test.py
```

## Notes

- Everything runs on-device; no API keys, no cloud calls.
- Because `inject_text` briefly overwrites and restores the system
  clipboard, avoid triggering it while you have something important copied
  mid-paste elsewhere.
- Since it's always listening, pause it from the tray menu before saying
  anything you don't want typed into your currently focused window.
