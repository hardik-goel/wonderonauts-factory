# Fonts

Drop `Poppins-Bold.ttf` here and every frame, thumbnail and title card picks it
up automatically — it is the channel's intended display face.

Poppins is licensed under the SIL Open Font License (free for commercial use);
download it from Google Fonts and copy the `.ttf` into this folder. It is not
vendored in the repo so that nothing here ships someone else's binary.

Without it the toolkit falls back, in order, to:

1. `fonts/Poppins-SemiBold.ttf`
2. DejaVu Sans Bold (Linux / CI)
3. Arial Rounded Bold, then Arial Bold, then Helvetica (macOS)
4. Arial Bold / Segoe UI Bold (Windows)
5. Pillow's built-in font (last resort — noticeably plainer)

For non-Latin language variants (`--lang hi`, etc.) the toolkit first looks for
a Unicode-wide face: `fonts/NotoSans-Bold.ttf`, then Noto Sans Devanagari,
Arial Unicode, or Mangal. Add `NotoSans-Bold.ttf` here before shipping a
variant in a script the fallbacks do not cover.

Check what is actually being used with:

```bash
python3 factory.py --check
```
