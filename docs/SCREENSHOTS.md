# Screenshots & Demo Media

This document lists recommended screenshots/gifs for releases and how to create them.

Recommended filenames (place in `media/`):

- `media/screenshot_main.png` — Main app window (800×450 or larger)
- `media/screenshot_face_select.png` — Face selection dialog
- `media/screenshot_settings.png` — Settings / execution provider selection
- `media/demo_short.gif` — Short looping GIF demo (~5–10s)
- `media/demo_record.mp4` — Original recorded short demo (use to make GIFs)

Capture guidance (Windows / PowerShell with `ffmpeg`):

1. Install `ffmpeg` and ensure it's on PATH.

2. To list available video devices (DirectShow):

```powershell
ffmpeg -list_devices true -f dshow -i dummy
```

3. Record a short clip from a camera (replace the device name from step 2):

```powershell
ffmpeg -f dshow -i video="<Your Camera Name>" -t 8 -r 30 media/demo_record.mp4
```

4. Convert the recorded clip to a GIF suitable for the README:

```powershell
ffmpeg -i media/demo_record.mp4 -vf "fps=15,scale=640:-1:flags=lanczos" -y media/demo_short.gif
```

Tips for high-quality screenshots:

- Use 1280×720 or 1920×1080 for clarity; reduce to 800×450 for README embedding.
- Hide any sensitive UI or personal data (e.g., OS taskbar, notifications).
- Record a short loop demonstrating: select source face → start Live → result preview.

Usage in releases:

- Include `demo_short.gif` in the top of `README.md` and in release notes.
- Add descriptive captions under images when uploading to GitHub Releases.

If you want, I can create a helper script `scripts/capture_demo.ps1` to automate steps 3–4. Would you like me to add that script now?