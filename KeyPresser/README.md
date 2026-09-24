# KeyPresser

A key presser for game windows: build an ordered sequence of keystrokes, set how long
each key is held and how long to wait after it, loop it, and drive it all with global
hotkeys that work while the game has focus. Records live keystrokes with their real
timings. Windows only, Python 3 + WinAPI, **no third-party dependencies**.

**[Download KeyPresser.exe](https://github.com/arkhamvm/keypresser/releases/latest)** — Windows, portable, no installation.

[Русская версия документации](README.ru.md)

## Why another key presser

* **Keys are sent by physical scancode through `SendInput`.** That means the active
  keyboard layout does not matter — step `w` is always the same physical key, whether
  your layout is US, Russian or anything else — and games that read DirectInput /
  Raw Input (and therefore ignore most scripting libraries) do receive the keystroke.
* **It tells you why nothing happens.** Built-in diagnostics reads the privilege level
  of the game process, checks who owns the foreground window and whether Windows
  accepts the injected input at all, then prints a verdict. A self-test sends the
  sequence into KeyPresser's own window so you can tell "we are not sending" from
  "the game ignores it".
* **`Alt` and other modifiers are first-class.** A lone `alt` / `lalt` / `ralt` is a
  valid step, and the phantom `Ctrl` that Windows injects together with right Alt is
  filtered out of recordings.

## Requirements

* Windows 10 / 11
* Nothing else for the prebuilt `KeyPresser.exe`
* Python 3.11+ (3.13 tested) to run from source — standard library only, `tkinter`
  included; PyInstaller only if you want to build the exe yourself

## Run

```
KeyPresser.exe
```

From source:

```
run.bat
```

If the game runs with administrator rights, KeyPresser needs them too (see
[Privileges](#privileges)) — `run_admin.bat`, or right-click the exe → *Run as
administrator*. Only one copy can run at a time: a second one shows a message and
brings the first window to the front, because global hotkeys always belong to
whichever copy registered them first.

## Quick start

1. **Target window** → *Refresh* → pick the game. For fullscreen games use
   *Grab active in 3 s*: the window minimizes, you switch to the game, and it grabs
   whatever is in the foreground.
2. Build the sequence: *Capture key* for a single step, or *Start recording* (`F9`)
   to record live keystrokes with their real hold times and pauses.
3. Set **Hold, ms** (80–120 is a good default — games poll the keyboard once per
   frame and can swallow a shorter tap), **Delay after, ms** and **Repeat**.
4. Switch to the game and press **`F6`**. Do not click *Start* with the mouse: the
   keystrokes go to the active window, which would be KeyPresser itself.

## Hotkeys

| Default | Action |
|---|---|
| `F6` | start / stop the script |
| `F7` | pause / resume |
| `F8` | emergency stop (script and recording) |
| `F9` | recording: start / stop |

All four are configurable; *Set* captures the key physically, and combinations such as
`ctrl+alt+f6` work. A lone modifier cannot be a hotkey — `RegisterHotKey` needs a real
key — but it can be a step. If a hotkey is already taken by another program, the log
says so and that action stays unbound.

## How a key is written

| Form | Meaning |
|---|---|
| `space`, `alt`, `ralt`, `f5`, `num7`, `left` | by name |
| `alt+space`, `ctrl+shift+f1` | combination: modifiers are held, then the key |
| `sc:0x11` / `sc:17` | raw scancode |
| `sc:e0:0x35` | scancode with the E0 (extended) prefix |
| `vk:0x41` | raw virtual-key code |
| `mouse_left`, `mouse_right`, `mouse_middle` | mouse buttons |

Modifiers: `ctrl`, `shift`, `alt` (left ones), plus explicit `lalt`, `ralt`, `lctrl`,
`rctrl`, `lshift`, `rshift`, `lwin`.

The list shows what actually goes to the game: `w [sc 11 / ц]` — name, scancode, and
the letter printed on the same physical key in the ЙЦУКЕН layout. A trailing `e`
(`ralt [sc 38e]`) marks an extended key.

**A lone modifier:** in *Capture key*, press and **release** it — the combination is
committed on release, so `lalt` alone is recorded as its own step. Hold it and press
another key to get a combination instead.

## A step

| Field | Meaning |
|---|---|
| Key | what to press (see the forms above) |
| Action | `press` (down+up), `hold down` (down only), `release` (up only) |
| Hold, ms | how long the key stays down |
| Delay after, ms | pause before the next step |
| Repeat | how many times to repeat this step |
| On | disabled steps are skipped (double-click a row to toggle) |

`hold down` + `release` let a key stay pressed across other steps. Everything still
held is force-released when the script stops, so keys never stick.

Editing any field applies to the selected step immediately — the row updates as
you type, so there is no way to leave a value sitting in the editor unapplied.
*Apply to selected* stays for when you want it explicit. Edits do not disturb a
run already in progress: it keeps the steps it started with.

## Recording

*Start recording* installs a low-level keyboard and mouse hook and records real
keystrokes: the time a key was held becomes `hold_ms`, the gap until the next press
becomes `delay_ms`. A modifier held around another key is merged into a combination
(`ctrl+c` is one step); a lone modifier tap stays its own step. KeyPresser's own
injected input and the hotkeys themselves are never recorded. Since the hook reports
the physical scancode, recording is layout-independent too: pressing `ц` on a Russian
layout is recorded as step `w`.

## Loop

* **Loop repeats** — `0` means forever, until `F6` / `F8`.
* **Delay between loops**.
* **Random delay spread, %** — ±% applied to every pause and hold, so the timing is
  not perfectly even.
* **Delay before start** — time to switch to the game after pressing `F6`.

## Send modes

1. **Only while the game window is active** (default, safe) — if the window loses
   focus the script waits instead of typing into other windows.
2. **Activate the window, then press** — brings the game to the front itself.
3. **Background, `PostMessage`** — posts messages straight to the window, so you can
   work in another window. Many games ignore this; test it with yours.

## Privileges

Windows silently drops synthetic input sent from a process with lower privileges into
a window owned by a higher-privileged one. The classic case: **Steam started as
administrator** — every game it launches inherits that token, so the game window ends
up at `high` integrity even though you "just launched it from Steam".

KeyPresser reads the integrity level of every window's process and marks such windows
in the dropdown as **`[ADMIN]`**. Pick one, and it offers to restart itself as
administrator: settings and the current sequence are saved, the new process is raised
through UAC, the old one exits. Decline the UAC prompt and it keeps running as before
and says in the log that keystrokes into that window will be blocked.

## When nothing happens in the game

* **Diagnostics (in 3 s)** — switch to the game and get a report: own PID / integrity
  level, the foreground window with its process, privilege comparison, whether the
  target matches the foreground window, the result of a test `SendInput`, and a
  verdict. The same report is appended to `%APPDATA%\KeyPresser\diagnostics.log`.
* **Send test** — runs the sequence into KeyPresser's own window and lists what
  arrived. Arrived → sending works, the problem is on the game side. Nothing arrived →
  privileges or blocked input. If focus moves away, the test stops instead of typing
  into someone else's window.

Then, by frequency: keystrokes went to the wrong window (start with `F6` from inside
the game); the game is elevated and KeyPresser is not; the hold time is too short
(raise to 80–120 ms); an anti-cheat filters synthetic input (nothing to configure
here); `PostMessage` mode simply ignored by the game.

## Profiles and settings

*Profile → Save as...* writes JSON into `profiles/` next to the executable
(`profiles/example.json` is included). Session settings — language, hotkeys, loop
parameters, last target — live in `%APPDATA%\KeyPresser\settings.json`.

## Interface language

English by default; switch it live with the *Language* dropdown or the *Language*
menu. The choice is stored in the settings and in the profile. All strings live in
`i18n.py` — a new language is one more dictionary in `CATALOG` plus a line in
`LANGUAGES`, no GUI code involved.

## Versioning

The version is the build timestamp in `yyMMddHHmm` format (e.g. `2608221446` =
2026-08-22 14:46). It is shown in the window title, in the log at startup and in
*Help → How it works*, and it is embedded into the exe file properties.
`make_version.py` generates `version.py` and `version_info.txt`; `build.bat` runs it
on every build.

## Build from source

```
python -m pip install pyinstaller
build.bat
```

Produces `dist\KeyPresser.exe` — one portable file, ~11 MB, no console window, icon
generated by `make_icon.py` (a 16/24/32/48 ICO written by hand, no image libraries).
`--onefile` unpacks itself on every start (~1 s); replace it with `--onedir` in
`build.bat` for instant startup and ship the whole folder.

Do not overwrite the exe while a copy of it is running: a `--onefile` build reads its
own modules from the file as it goes, and replacing it mid-run ends with
`Error -3 while decompressing data`.

## Project layout

| File | Responsibility |
|---|---|
| `main.py` | entry point, DPI awareness, single-instance check |
| `gui.py` | window, step list, editor, diagnostics, self-test, profiles |
| `engine.py` | playback thread: order, hold / delay / repeat, loops, jitter |
| `recorder.py` | recording via `WH_KEYBOARD_LL` / `WH_MOUSE_LL` → steps |
| `sender.py` | `SendInput` with scancodes + `PostMessage` mode |
| `hotkeys.py` | global hotkeys (`RegisterHotKey` + its own message loop) |
| `keys.py` | VK / scancode table, combination parsing, ЙЦУКЕН hints |
| `winutil.py` | window list, activation, focus and integrity-level checks |
| `instance.py` | single instance, restart through UAC |
| `profiles.py` | JSON profiles, validation, session settings |
| `i18n.py` | EN / RU catalogs, `t()` with English fallback |
| `make_version.py`, `make_icon.py`, `build.bat` | version, icon, exe build |

## What this program does not do

It sends keystrokes through the documented Windows input API. It does not touch game
memory, does not inject code into other processes and does not try to defeat
anti-cheat systems — if a game filters synthetic input, KeyPresser will not get around
that, by design. Automating online games may violate their rules; that is on you.

## License

MIT — see [LICENSE](LICENSE).
