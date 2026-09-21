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

Runs as a system tray app in the background. The tray icon itself shows what
state it's in — **orange** while actively listening and typing, **gray**
while paused or still starting up, **red** if something in setup is broken
(no model, no microphone) — so you can tell what's going on at a glance
without opening anything.

The mic and transcriber never stop — that's what lets it hear you resume —
but you can pause and resume by **voice** at any time:

- Say **"pause listening"** — VoiceBridge keeps listening and transcribing,
  but stops typing anything anywhere until you resume.
- Say **"resume listening"** — it starts injecting again.

Neither phrase itself ever gets typed into your focused window. You can also
toggle the same state from the tray menu ("Active (not paused)") with the
mouse.

## Get the app

**Option A — download the built app (no Python needed):**
Grab `VoiceBridge.exe` (with its `_internal` folder — keep them together) and
run it. It shows up in the system tray. First launch downloads the local
speech-to-text model (~150MB, one time).

**Option B — build it yourself:**

```powershell
powershell -File scripts/build_exe.ps1
```

This produces `dist\VoiceBridge\VoiceBridge.exe`. Distribute the whole
`dist\VoiceBridge` folder together — the exe depends on the `_internal`
folder next to it.

**Option C — run from source** (for development):

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

## Settings

Right-click the tray icon → **Settings...** opens a small window with the
options you'd actually want to flip:

- **Run VoiceBridge when Windows starts** — adds/removes VoiceBridge from
  your per-user Windows startup entries (no admin rights needed; easy to
  turn back off from the same checkbox).
- **Auto-press Enter after speaking** — submit automatically vs. just type.
- **Model size** (tiny/base/small/medium) and **language** — takes effect
  after restarting VoiceBridge.
- **Pause length that ends an utterance** and **shortest sound treated as
  speech** — tune how quickly it reacts and how much it filters out, applied
  live without a restart.

Everything is also stored in `%APPDATA%\VoiceBridge\config.json` if you'd
rather edit it directly. Logs go to `%APPDATA%\VoiceBridge\voicebridge.log`.

## Testing

```bash
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python tests/smoke_test.py
```

This exercises the riskiest paths end-to-end: feeding synthetic audio frames
through the always-listening speech detector to confirm it segments
utterances correctly without a hotkey; driving the pause/resume voice-command
logic to confirm paused speech is swallowed (never typed) while the pause and
resume phrases themselves are also never typed; confirming setup failures
(bad model, no microphone) surface as a visible error state instead of
crashing, and that the tray icon's state-change hook fires exactly on real
transitions; round-tripping the Windows startup registry toggle; synthesizing
speech with the OS TTS engine to check transcription accuracy; and opening a
real Notepad window to verify injected text actually lands there.

## Project layout

```
voicebridge/
  recorder.py         always-on mic listener + automatic speech segmentation
  transcriber.py       local speech-to-text (faster-whisper)
  injector.py           pastes text into the focused window (pynput + clipboard)
  app.py                 wires listener -> transcriber -> injector together
  tray.py                 system tray icon (3-state) and menu
  settings_window.py       the Settings dialog (Tkinter)
  autostart.py               Windows "launch on startup" registry toggle
main.py                       entry point (also configures file logging)
assets/icon.ico                  packaged app icon
VoiceBridge.spec                  PyInstaller build spec
scripts/build_exe.ps1              convenience build script
tests/smoke_test.py
```

## Notes

- Everything runs on-device; no API keys, no cloud calls.
- Because `inject_text` briefly overwrites and restores the system
  clipboard, avoid triggering it while you have something important copied
  mid-paste elsewhere.
- Since it's always listening, say "pause listening" (or use the tray menu)
  before saying anything you don't want typed into your currently focused
  window.
