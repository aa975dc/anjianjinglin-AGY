# SourceForge project page — ready-to-paste text

Everything below is written for end users, not developers. Copy each block into the
matching field of the SourceForge project page.

---

## Summary (one line, max ~100 characters)

```
Key presser for games: ordered key sequences, hold/delay control, recording, global hotkeys
```

## Categories

Games/Entertainment · Desktop Environment → Automation · Windows · Python

## License

MIT

---

## Description

**KeyPresser** presses keys for you in a game window: you build a list of keystrokes in
the order you need, say how long each key is held and how long to wait after it, and
run the whole list in a loop with a single hotkey. It can also record what you press
live — with your real timings — and turn that into the sequence.

It is a single portable `KeyPresser.exe` for Windows. Nothing to install, no runtime to
download, no registry changes, no network access at all. Your sequences are plain JSON
files you can copy between machines.

**What makes it different from the usual auto-clicker:**

* **Keys are sent as physical keys (scancodes) through the documented Windows input
  API.** Two practical consequences. First, your keyboard layout does not matter: a
  step written as `w` always presses the same physical key, whether your layout is
  English, Russian or anything else — the list even shows you the letter printed on
  that key in your layout. Second, games that read the keyboard directly
  (DirectInput / Raw Input) — the ones that ignore most scripting tools — do receive
  the keystrokes.

* **When nothing happens in the game, the program tells you why.** One button collects
  a diagnostic report: which window is really in focus, which process owns it, whether
  that process has higher privileges than KeyPresser (the classic case: Steam started
  as administrator, so every game it launches inherits that), and whether Windows
  accepted a test keystroke at all. A second button, *Send test*, fires your sequence
  into KeyPresser's own window and shows what arrived — so you can immediately tell
  "we are not sending anything" from "the game is ignoring it".

* **If the game needs administrator rights, KeyPresser offers to restart itself with
  them.** Windows blocks keystrokes sent from a normal program into an elevated game
  window. Such windows are marked `[ADMIN]` in the window list; pick one and KeyPresser
  saves your work, asks Windows for elevation and comes back ready to go.

* **`Alt`, `Ctrl`, `Shift` and the right-hand variants are proper keys here.** A lone
  `Alt` is a valid step (many tools cannot express that), and combinations like
  `Alt+Space` or `Ctrl+Shift+F1` are single steps.

## Features

* Ordered sequence of steps: key, hold time (ms), pause after the step (ms), repeat
  count, on/off switch, free-text comment
* `press` / `hold down` / `release` actions — a key can stay held across other steps,
  and everything held is force-released on stop, so keys never stick
* Loop the whole sequence: N times or forever, pause between loops, optional random
  spread (±%) so intervals are not perfectly even, countdown before start
* Recording of live keystrokes and mouse buttons with real hold times and pauses;
  modifiers held around a key are merged into one combination automatically
* Configurable global hotkeys that work while the game has focus: start/stop,
  pause/resume, emergency stop, recording start/stop
* Three send modes: only while the game window is active (safe default), activate the
  window first, or background `PostMessage` (games differ — test yours)
* Target window picker with a *Grab active in 3 s* button for fullscreen games
* Keys can also be written as raw codes — `sc:0x11`, `sc:e0:0x35`, `vk:0x41` — and
  mouse buttons are supported as steps
* Profiles saved as readable JSON; interface in English or Russian, switchable on the
  fly; only one copy runs at a time so hotkeys never end up in the wrong window
* Built-in diagnostics and self-test, plus a log you can read and a report file

## Requirements

Windows 10 or 11, 64-bit. Nothing else — the exe is self-contained (~11 MB).

To run from source instead: Python 3.11 or newer (3.13 tested), standard library only.

## Install and run

1. Download `KeyPresser.exe`.
2. Run it. No installer, no admin rights needed for the program itself.
3. If your game (or Steam) runs as administrator, KeyPresser will notice and offer to
   restart with the same rights — or right-click the exe and choose *Run as
   administrator*.

Portable by design: keep the exe wherever you like. Profiles are stored in a `profiles`
folder next to it; window size, hotkeys and the last used settings go to
`%APPDATA%\KeyPresser`.

## Quick start

1. *Refresh* the window list and pick your game (or use *Grab active in 3 s* for
   fullscreen).
2. Add steps with *Capture key*, or press `F9` and simply play — your keystrokes and
   pauses are recorded as they happen.
3. Leave *Hold* around 80–120 ms: games check the keyboard once per frame and can miss
   a shorter tap.
4. Switch to the game and press `F6`. Press `F6` again (or `F8`) to stop.

## Version numbers

Versions are build timestamps in `yyMMddHHmm` form — for example `2608221446` means
2026-08-22, 14:46. Higher is newer. The version is shown in the window title and in
*Help → How it works*, and it is embedded in the exe's file properties.

## Honest limitations

KeyPresser sends keystrokes through the documented Windows input API. It does not read
or write game memory, does not inject code into other processes, and makes no attempt
to defeat anti-cheat systems. If a game filters synthetic input, this program will not
get around that — by design. Automating an online game may be against its rules; that
decision, and its consequences, are yours.

---

# Описание для русскоязычных пользователей

**KeyPresser** нажимает клавиши за вас в окне игры: вы собираете список нажатий в
нужном порядке, указываете, сколько держать каждую клавишу и сколько ждать после неё,
и запускаете весь список циклом одной горячей клавишей. Программа умеет и записать
то, что вы нажимаете вживую, — с вашими реальными задержками — и превратить это в
последовательность.

Это один переносимый `KeyPresser.exe` для Windows: ничего не нужно устанавливать,
нет обращений к сети, настройки лежат в обычных JSON-файлах.

**Чем отличается от обычного автокликера:**

* **Клавиши отправляются как физические (по скан-кодам) через документированный API
  ввода Windows.** Отсюда два следствия. Раскладка не важна: шаг `w` всегда нажимает
  одну и ту же физическую клавишу, хоть при английской, хоть при русской раскладке — в
  списке даже показано, какая буква написана на этой клавише в вашей раскладке. И
  игры, читающие клавиатуру напрямую (DirectInput / Raw Input), нажатия получают.

* **Если в игре ничего не происходит, программа объясняет почему.** Кнопка диагностики
  собирает отчёт: какое окно на самом деле активно, какому процессу оно принадлежит,
  выше ли у него права, чем у KeyPresser (типичный случай — Steam запущен от
  администратора, и игра наследует его права), принял ли Windows тестовое нажатие.
  Вторая кнопка, «Проверка отправки», прогоняет вашу последовательность в собственное
  окно и показывает, что дошло: сразу видно, мы не отправляем или игра игнорирует.

* **Нужны права администратора — программа предложит перезапуститься с ними.** Такие
  окна помечены в списке как `[АДМИН]`; выберите его, и KeyPresser сохранит работу,
  запросит повышение прав через UAC и вернётся готовым к работе.

* **`Alt`, `Ctrl`, `Shift` и правые варианты — полноценные клавиши.** Одиночный `Alt`
  можно записать отдельным шагом, а `Alt+Space` или `Ctrl+Shift+F1` — одним шагом.

**Возможности:** очерёдность шагов с удержанием, паузой, повторами и включением каждого
шага; действия «нажать» / «зажать» / «отпустить»; цикл N раз или бесконечно со
случайным разбросом задержек; запись живых нажатий и кнопок мыши; настраиваемые
глобальные хоткеи, работающие внутри игры; три режима отправки; выбор окна с кнопкой
«Взять активное через 3 с» для полного экрана; профили в JSON; интерфейс на английском
или русском с переключением на ходу.

**Требования:** Windows 10 или 11 (64-бит). Больше ничего — exe самодостаточен.

**Быстрый старт:** обновите список окон и выберите игру → добавьте шаги кнопкой
«Записать клавишу» или нажмите `F9` и просто поиграйте → удержание оставьте 80–120 мс →
переключитесь в игру и нажмите `F6`.

**Версии** — это время сборки в формате `yyMMddHHmm`: `2608221446` = 22.08.2026, 14:46.
Больше значит новее.

**Честные ограничения:** программа отправляет нажатия через документированный API
ввода Windows. Она не читает и не пишет память игры, не внедряет код в другие процессы
и не пытается обойти античиты. Если игра фильтрует синтетический ввод, обойти это
KeyPresser не сможет — так и задумано. Автоматизация в онлайн-играх может нарушать их
правила; это решение и его последствия — на вас.
