# VoiceBridge

A hands-free voice interface for talking to your AI (or anything else on your
screen). Hold a hotkey, speak, let go — your words get transcribed locally
and typed straight into whatever window has focus. No keyboard, no trackpad.

Inspired by a demo of "Infina," rebuilt from scratch for Windows.

## How it works

1. You hold down a push-to-talk hotkey (default: `F9`).
2. VoiceBridge records your microphone while it's held.
3. On release, the audio is transcribed **locally and offline** with
   [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — nothing is
   sent to any server.
4. The transcribed text is pasted into whatever application currently has
   focus — your editor, a chat window, a terminal, Slack, anything — and
   Enter is pressed automatically (configurable).

Runs as a system tray app in the background.

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
`base` size) and caches it. After that, hold `F9`, speak, release, and watch
your words appear wherever your cursor is focused.

A tray icon lets you toggle auto-Enter and quit.

## Configuration

Settings live in `%APPDATA%\VoiceBridge\config.json`:

| key          | default | notes                                      |
|--------------|---------|---------------------------------------------|
| `hotkey`     | `f9`    | any single key name pynput recognizes        |
| `auto_enter` | `true`  | press Enter automatically after injecting    |
| `model_size` | `base`  | whisper model size: tiny/base/small/medium   |
| `language`   | `en`    | transcription language                       |

## Testing

```bash
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python tests/smoke_test.py
```

This exercises the two riskiest paths end-to-end: it synthesizes speech with
the OS TTS engine and checks the transcription round-trips correctly, and it
opens a real Notepad window and verifies injected text actually lands there.

## Project layout

```
voicebridge/
  recorder.py     mic capture (sounddevice)
  transcriber.py  local speech-to-text (faster-whisper)
  injector.py     pastes text into the focused window (pynput + clipboard)
  hotkey.py       global push-to-talk listener (pynput)
  app.py          wires recorder -> transcriber -> injector together
  tray.py         system tray icon and menu
main.py           entry point
tests/smoke_test.py
```

## Notes

- Everything runs on-device; no API keys, no cloud calls.
- Because `inject_text` briefly overwrites and restores the system
  clipboard, avoid triggering it while you have something important copied
  mid-paste elsewhere.
