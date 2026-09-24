"""Локализация интерфейса. По умолчанию английский.

t("some.key", n=3) -> строка на текущем языке; если ключа нет в текущем языке,
берётся английский, если нет и там -- сам ключ (сразу видно, что забыли).
"""

LANGUAGES = {"zh": "简体中文", "en": "English", "ru": "Русский"}
DEFAULT_LANGUAGE = "zh"

_current = DEFAULT_LANGUAGE

EN: dict[str, str] = {
    # --- общее -------------------------------------------------------------
    "app.title": "KeyPresser",
    "app.version": "version {v}",
    "lang.label": "Language:",
    "lang.changed": "Interface language: {name}",

    # --- меню --------------------------------------------------------------
    "menu.profile": "Profile",
    "menu.new": "New",
    "menu.open": "Open...",
    "menu.save": "Save",
    "menu.save_as": "Save as...",
    "menu.exit": "Exit",
    "menu.language": "Language",
    "menu.help": "Help",
    "menu.how": "How it works",

    # --- целевое окно ------------------------------------------------------
    "target.frame": "Target window",
    "target.window": "Window:",
    "target.refresh": "Refresh",
    "target.grab": "Grab active in 3 s",
    "target.none": "(not selected - send to the active window)",
    "mode.foreground": "Only while the game window is active (safe)",
    "mode.activate": "Activate the window, then press",
    "mode.post": "Background, PostMessage (not every game accepts it)",

    # --- последовательность -----------------------------------------------
    "seq.frame": "Sequence",
    "col.n": "#",
    "col.key": "Key (physical)",
    "col.act": "Action",
    "col.hold": "Hold, ms",
    "col.delay": "Delay after, ms",
    "col.rep": "Repeat",
    "col.on": "On",
    "col.cm": "Comment",
    "btn.up": "Move up",
    "btn.down": "Move down",
    "btn.dup": "Duplicate",
    "btn.toggle": "On / off",
    "btn.delete": "Delete",
    "btn.clear": "Clear all",
    "yes": "yes",
    "no": "no",

    # --- редактор шага ----------------------------------------------------
    "step.frame": "Step",
    "step.key": "Key:",
    "step.capture": "Capture key",
    "step.action": "Action:",
    "step.hold": "Hold, ms",
    "step.delay": "Delay, ms",
    "step.repeat": "Repeat",
    "step.comment": "Comment:",
    "step.add": "Add step",
    "step.apply": "Apply to selected",
    "action.tap": "press",
    "action.down": "hold down",
    "action.up": "release",
    "preview.ok": "-> sent to the game: {desc}   (scancode = physical key, "
                  "keyboard layout does not matter)",
    "preview.err": "x {err}",

    # --- запись -----------------------------------------------------------
    "rec.frame": "Recording",
    "rec.start": "Start recording",
    "rec.stop": "Stop recording",
    "rec.mouse": "record mouse buttons",
    "rec.replace": "replace the sequence (otherwise append)",
    "rec.tail": "Delay after the last step, ms:",
    "rec.off": "Recording off",
    "rec.on": "RECORDING - press keys in the game",
    "rec.progress": "RECORDING: {n} presses, last one - {key}",
    "rec.started": "Recording started. Presses and pauses are captured as they are; "
                   "hotkeys are excluded.",
    "rec.done": "Steps recorded: {n}.",
    "rec.empty": "Recording stopped: no presses captured.",
    "rec.engine_busy": "The script is running - stopping it before recording.",
    "rec.hook_failed": "could not install the keyboard hook (code {code})",
    "rec.prefix": "Recording: {msg}",

    # --- цикл -------------------------------------------------------------
    "loop.frame": "Loop and delays",
    "loop.cycles": "Loop repeats (0 = infinite):",
    "loop.cycle_delay": "Delay between loops, ms:",
    "loop.jitter": "Random delay spread, %:",
    "loop.start_delay": "Delay before start, ms:",

    # --- хоткеи -----------------------------------------------------------
    "hk.frame": "Hotkeys (work inside the game)",
    "hk.run_toggle": "Start script",
    "hk.pause": "Pause / resume",
    "hk.stop": "Emergency stop",
    "hk.record_toggle": "Recording: start / stop",
    "hk.minimize": "Minimize window",
    "hk.set": "Set",
    "hk.apply": "Apply hotkeys",
    "hk.assigned": "Hotkeys assigned: {list}",
    "hk.prefix": "Hotkey: {msg}",
    "hk.err.parse": "'{combo}' ({action}): {err}",
    "hk.err.busy": "{combo} is taken by another program - action '{action}' not assigned",
    "hk.err.raw": "a hotkey needs a key with a VK code, a raw scancode will not work",
    "hk.err.handler": "handler: {err}",

    # --- управление -------------------------------------------------------
    "ctl.start": "Start",
    "ctl.pause": "Pause",
    "ctl.resume": "Resume",
    "ctl.stop": "Stop",
    "ctl.minimize": "Minimize",
    "log.frame": "Log",
    "status.ready": "Ready",
    "status.running": "Running",
    "status.paused": "Paused",
    "status.stopped": "Stopped",
    "status.starting": "Starting...",
    "status.waiting": "Waiting for the window",
    "status.recording": "Recording",

    # --- диалог захвата клавиши ------------------------------------------
    "dlg.step_key": "Step key",
    "dlg.hotkey": "Hotkey: {action}",
    "dlg.hint": "Press the key or the combination you need.\n"
                "Modifiers (Ctrl / Shift / Alt) can be held down.",
    "dlg.hint_mouse": "Click this area with the mouse = mouse button.",
    "dlg.hint_modifier": "A single modifier (Alt, Ctrl, Shift): press and release it.",
    "dlg.mod_not_hotkey": "a modifier alone cannot be a hotkey - add a key",
    "dlg.cancel": "Cancel",
    "dlg.unknown": "unknown key (vk {vk})",
    "msg.hk_modifier_only": "{action}: a modifier alone cannot be a hotkey. "
                            "Use a combination, for example ctrl+alt+f6.",

    # --- сообщения --------------------------------------------------------
    "msg.select_step": "Select a step in the list first.",
    "msg.numbers": "Check hold / delay / repeat.",
    "msg.settings_numbers": "Check the numeric fields.",
    "msg.param_clamped": "Out-of-range values were corrected: {list}",
    "msg.clear_title": "Clear",
    "msg.clear_text": "Delete every step?",
    "msg.new_title": "New profile",
    "msg.new_text": "The current sequence will be cleared. Continue?",
    "msg.open_error": "Could not read the file:\n{err}",
    "msg.saved": "Saved: {name}",
    "msg.loaded": "Profile loaded: {name} (steps: {n})",
    "msg.new_profile": "New profile.",
    "msg.step_added": "Step {n} added: {key}",
    "msg.rec_running": "Recording is in progress - stop it first.",
    "msg.target": "Target window: {title}",
    "msg.grab_hint": "Switch to the game window - grabbing it in 3 seconds...",
    "msg.grab_fail": "Could not determine the active window.",
    "msg.admin_hint": "Hint: if the game runs as administrator, start KeyPresser as "
                      "administrator too (run_admin.bat), otherwise Windows blocks "
                      "the keystrokes.",
    "title.key": "Key",
    "title.hotkey": "Hotkey",
    "title.numbers": "Numbers",
    "title.settings": "Settings",
    "title.open": "Open profile",
    "title.save": "Save profile",
    "title.profile_filter": "KeyPresser profile",
    "title.all_files": "All files",
    "help.text":
        "1. Pick the game window (or use \"Grab active in 3 s\" for fullscreen).\n"
        "2. Build the sequence: \"Capture key\", or record live presses with\n"
        "   \"Start recording\" (F9 by default).\n"
        "3. Set hold time, delay after the step and the repeat count.\n"
        "4. Start - F1, pause - F2, stop - F3 (configurable).\n\n"
        "Keys are sent by physical scancode through SendInput, so the keyboard\n"
        "layout does not matter: step \"w\" is always the same physical key.\n\n"
        "If the game runs as administrator, start KeyPresser the same way,\n"
        "otherwise Windows will not let the keystrokes through (run_admin.bat).",

    # --- диагностика ------------------------------------------------------
    "diag.button": "Diagnostics (in 3 s)",
    "diag.wait": "Switch to the game window - collecting diagnostics in 3 seconds...",
    "diag.header": "--------- diagnostics ---------",
    "diag.footer": "------- end of diagnostics -------",
    "diag.file": "The same report is saved to: {path}",
    "diag.self": "KeyPresser: PID {pid}, administrator: {admin}, integrity level: {level}",
    "diag.fg": "Active window: '{title}' [class {cls}], PID {pid}, process: {exe}",
    "diag.fg_integrity": "Privileges: game process {level}, KeyPresser {own}",
    "diag.fg_higher": "The game runs with HIGHER privileges than KeyPresser, so Windows "
                      "blocks our keystrokes. This is exactly what happens when Steam is "
                      "started as administrator: the game inherits its token.",
    "diag.fg_same": "The game's privileges are not higher than ours - nothing is blocked at this level",
    "diag.fg_unknown": "Could not read the game process privileges (not a problem by "
                       "itself)",
    "diag.target": "Selected target: '{title}' (hwnd {hwnd})",
    "diag.target_none": "No target window selected - keys go to whatever window is active",
    "diag.target_is_fg": "The target window is the active one - correct",
    "diag.target_not_fg": "The target window is NOT active right now",
    "diag.mode": "Send mode: {mode}",
    "diag.test_ok": "Test keystroke (right Shift, harmless): SendInput accepted it",
    "diag.test_fail": "Test keystroke: SendInput REFUSED -> {err}",
    "diag.verdict": "VERDICT: {text}",
    "diag.verdict_admin": "Windows is blocking the input. Close KeyPresser and start it "
                          "as administrator (right-click the exe -> Run as administrator, "
                          "or run_admin.bat).",
    "diag.verdict_focus": "The game window was not active. Keys always go to the active "
                          "window, so press the start hotkey (F1) while you are in the "
                          "game, or switch the mode to 'Activate the window, then press'.",
    "diag.verdict_ok": "The input path works. If the game still ignores the keys: raise "
                       "'Hold, ms' to 80-120, check that the game reads that exact key, "
                       "and if nothing helps the game filters synthetic input (anti-cheat).",
    "selftest.button": "Send test",
    "selftest.title": "Send test",
    "selftest.hint": "The sequence is being sent into this window right now.\n"
                     "Everything that arrives is listed below.",
    "selftest.got": "Arrived ({n}): {list}",
    "selftest.none": "NOTHING arrived - the keystrokes are not being delivered even to "
                     "our own window. Run diagnostics.",
    "selftest.sending": "sending: {key}",
    "selftest.done": "done",
    "selftest.close": "Close",
    "selftest.no_steps": "Add at least one step first.",
    "err.send.title": "Input blocked",
    "inst.title": "KeyPresser is already running",
    "inst.blocked": "KeyPresser is already running.\n\nA second copy is not allowed: the "
                    "global hotkeys would go to the first one. Opening the existing "
                    "window.",
    "target.admin_mark": "ADMIN",
    "admin.ask_title": "Administrator rights needed",
    "admin.ask": "The window \"{title}\" runs with administrator rights ({level}), while "
                 "KeyPresser runs with normal rights ({own}).\n\nWindows will drop every "
                 "keystroke KeyPresser sends into that window.\n\nRestart KeyPresser as "
                 "administrator now? The current sequence and settings are kept.",
    "admin.restarting": "Restarting as administrator...",
    "admin.declined": "Left as is: keystrokes into \"{title}\" will be blocked by Windows "
                      "until KeyPresser runs as administrator.",
    "admin.failed": "Could not restart as administrator ({err}).",
    "admin.blocked_start": "The target window runs as administrator and KeyPresser does "
                           "not - Windows will block the keystrokes. Restart as "
                           "administrator.",

    # --- движок -----------------------------------------------------------
    "eng.no_steps": "No enabled steps in the sequence.",
    "eng.hold_hint": "Note: hold time {ms} ms is short. Unity/Unreal games poll the keyboard once per frame and can swallow a tap shorter than ~50 ms - try 80-120 ms.",
    "eng.step_bad": "Error in step '{key}': {err}",
    "eng.window_not_found": "Window '{title}' not found.",
    "eng.post_needs_window": "PostMessage mode needs a selected window.",
    "eng.countdown": "Starting in {sec} s",
    "eng.started": "Started.",
    "eng.cycle": "Loop {i}/{n}",
    "eng.done": "Finished: loops completed - {n}.",
    "eng.stopped": "Stopped.",
    "eng.paused": "Paused.",
    "eng.resumed": "Resumed.",
    "eng.window_inactive": "The game window is not active - waiting (no keys sent).",
    "eng.window_closed": "The target window has been closed.",
    "eng.window_active": "The window is active again - continuing.",
    "eng.step_failed": "Step {n} ({key}): {err}",
    "eng.force_release": "Emergency key release: {names}",

    # --- ввод -------------------------------------------------------------
    "send.rejected": "SendInput rejected (code {code}). If the game runs as "
                     "administrator, KeyPresser has to run as administrator too.",

    # --- ошибки разбора клавиш -------------------------------------------
    "keys.unknown": "unknown key: {name}",
    "keys.not_modifier": "'{name}' cannot be used as a modifier",
    "keys.empty": "no key set",
    "keys.bad_code": "cannot parse the code: {spec}",
    "keys.range": "the code must be in the range 1..255",
    "mouse.left": "LMB",
    "mouse.right": "RMB",
    "mouse.middle": "MMB",
}

ZH: dict[str, str] = {
    # --- общее -------------------------------------------------------------
    "app.title": "自动按键工具",
    "app.version": "版本 {v}",
    "lang.label": "界面语言：",
    "lang.changed": "界面语言：{name}",

    # --- меню --------------------------------------------------------------
    "menu.profile": "配置",
    "menu.new": "新建",
    "menu.open": "打开…",
    "menu.save": "保存",
    "menu.save_as": "另存为…",
    "menu.exit": "退出",
    "menu.language": "语言",
    "menu.help": "帮助",
    "menu.how": "使用说明",

    # --- целевое окно ------------------------------------------------------
    "target.frame": "目标窗口",
    "target.window": "窗口：",
    "target.refresh": "刷新",
    "target.grab": "3 秒后抓取当前窗口",
    "target.none": "（未选择 —— 发送给当前活动窗口）",
    "mode.foreground": "仅在目标窗口激活时发送（安全）",
    "mode.activate": "先激活目标窗口，再按键",
    "mode.post": "后台 PostMessage（部分程序不支持）",

    # --- последовательность -----------------------------------------------
    "seq.frame": "按键序列",
    "col.n": "序号",
    "col.key": "按键（物理键）",
    "col.act": "动作",
    "col.hold": "按住(毫秒)",
    "col.delay": "间隔(毫秒)",
    "col.rep": "重复",
    "col.on": "启用",
    "col.cm": "备注",
    "btn.up": "上移",
    "btn.down": "下移",
    "btn.dup": "复制一份",
    "btn.toggle": "启用/停用",
    "btn.delete": "删除",
    "btn.clear": "清空全部",
    "yes": "是",
    "no": "否",

    # --- редактор шага ----------------------------------------------------
    "step.frame": "步骤设置",
    "step.key": "按键：",
    "step.capture": "按下要按的键",
    "step.action": "动作：",
    "step.hold": "按住(毫秒)",
    "step.delay": "间隔(毫秒)",
    "step.repeat": "重复次数",
    "step.comment": "备注：",
    "step.add": "添加步骤",
    "step.apply": "应用到选中项",
    "action.tap": "按一下",
    "action.down": "按住不放",
    "action.up": "松开",
    "preview.ok": "→ 将发送：{desc}（使用物理扫描码，不受键盘布局影响）",
    "preview.err": "× {err}",

    # --- запись -----------------------------------------------------------
    "rec.frame": "录制",
    "rec.start": "开始录制",
    "rec.stop": "停止录制",
    "rec.mouse": "同时录制鼠标按键",
    "rec.replace": "覆盖现有序列（否则追加）",
    "rec.tail": "最后一步之后的间隔(毫秒)：",
    "rec.off": "未在录制",
    "rec.on": "录制中 —— 请在目标窗口中操作按键",
    "rec.progress": "录制中：已捕获 {n} 次按键，最后一个是 {key}",
    "rec.started": "已开始录制。按键与停顿会按真实节奏记录，热键本身不会被录进去。",
    "rec.done": "已录制 {n} 个步骤。",
    "rec.empty": "录制已停止：没有捕获到任何按键。",
    "rec.engine_busy": "脚本正在运行 —— 先停止再录制。",
    "rec.hook_failed": "无法安装键盘钩子（错误码 {code}）",
    "rec.prefix": "录制：{msg}",

    # --- цикл -------------------------------------------------------------
    "loop.frame": "循环与延时",
    "loop.cycles": "循环次数（0 = 无限）：",
    "loop.cycle_delay": "每轮之间的间隔(毫秒)：",
    "loop.jitter": "随机浮动幅度(%)：",
    "loop.start_delay": "启动前延时(毫秒)：",

    # --- хоткеи -----------------------------------------------------------
    "hk.frame": "热键（在目标窗口中依然生效）",
    "hk.run_toggle": "启动脚本",
    "hk.pause": "暂停 / 继续",
    "hk.stop": "停止脚本",
    "hk.record_toggle": "录制：开始 / 停止",
    "hk.minimize": "最小化窗口",
    "hk.set": "设置",
    "hk.apply": "应用热键",
    "hk.assigned": "已绑定的热键：{list}",
    "hk.prefix": "热键：{msg}",
    "hk.err.parse": "“{combo}”（{action}）：{err}",
    "hk.err.busy": "{combo} 已被其他程序占用 —— 动作“{action}”未绑定",
    "hk.err.raw": "热键需要一个有虚拟键码的按键，原始扫描码不能用作热键",
    "hk.err.handler": "热键处理出错：{err}",

    # --- управление -------------------------------------------------------
    "ctl.start": "启动",
    "ctl.pause": "暂停",
    "ctl.resume": "继续",
    "ctl.stop": "停止",
    "ctl.minimize": "最小化",
    "log.frame": "运行日志",
    "status.ready": "就绪",
    "status.running": "运行中",
    "status.paused": "已暂停",
    "status.stopped": "已停止",
    "status.starting": "正在启动…",
    "status.waiting": "等待窗口激活",
    "status.recording": "录制中",

    # --- диалог захвата клавиши ------------------------------------------
    "dlg.step_key": "设置按键",
    "dlg.hotkey": "热键：{action}",
    "dlg.hint": "请按下你需要的按键或组合键。\nCtrl / Shift / Alt 等修饰键可以按住不放。",
    "dlg.hint_mouse": "用鼠标点击此区域 = 鼠标按键。",
    "dlg.hint_modifier": "单独的修饰键（Alt、Ctrl、Shift）：按一下再松开即可。",
    "dlg.mod_not_hotkey": "单独的修饰键不能作为热键 —— 请再按一个普通键",
    "dlg.cancel": "取消",
    "dlg.unknown": "未知按键（vk {vk}）",
    "msg.hk_modifier_only": "{action}：单独的修饰键不能作为热键。"
                            "请使用组合键，例如 ctrl+alt+f6。",

    # --- сообщения --------------------------------------------------------
    "msg.select_step": "请先在列表中选中一个步骤。",
    "msg.numbers": "请检查“按住 / 间隔 / 重复”的数值。",
    "msg.settings_numbers": "请检查数值栏填写是否正确。",
    "msg.param_clamped": "已自动修正越界的数值：{list}",
    "msg.clear_title": "清空",
    "msg.clear_text": "确定要删除全部步骤吗？",
    "msg.new_title": "新建配置",
    "msg.new_text": "当前序列将被清空。是否继续？",
    "msg.open_error": "无法读取文件：\n{err}",
    "msg.saved": "已保存：{name}",
    "msg.loaded": "已载入配置：{name}（步骤数：{n}）",
    "msg.new_profile": "已新建配置。",
    "msg.step_added": "已添加第 {n} 步：{key}",
    "msg.rec_running": "正在录制 —— 请先停止录制。",
    "msg.target": "目标窗口：{title}",
    "msg.grab_hint": "请切换到目标窗口 —— 3 秒后自动抓取…",
    "msg.grab_fail": "无法确定当前活动窗口。",
    "msg.admin_hint": "提示：如果目标程序以管理员身份运行，本工具也必须以管理员身份"
                      "启动（运行 run_admin.bat），否则 Windows 会拦截模拟按键。",
    "title.key": "按键",
    "title.hotkey": "热键",
    "title.numbers": "数值",
    "title.settings": "设置",
    "title.open": "打开配置",
    "title.save": "保存配置",
    "title.profile_filter": "配置档案",
    "title.all_files": "所有文件",
    "help.text":
        "1. 选择目标窗口（全屏程序可用“3 秒后抓取当前窗口”）。\n"
        "2. 添加要按的键：点“按下要按的键”直接按一下，\n"
        "   或用“开始录制”记录真实操作（默认热键 F9）。\n"
        "3. 设置按住时长、间隔和重复次数。\n"
        "4. 启动 F1、暂停 F2、停止 F3（均可改绑）。\n\n"
        "按键通过 SendInput 以物理扫描码发送，因此不受键盘布局影响：\n"
        "步骤里的 w 永远是同一个物理键。\n\n"
        "如果目标程序以管理员身份运行，本工具也要以管理员身份启动，\n"
        "否则 Windows 不会放行这些按键（run_admin.bat）。",

    # --- диагностика ------------------------------------------------------
    "diag.button": "诊断（3 秒后）",
    "diag.wait": "请切换到目标窗口 —— 3 秒后开始收集诊断信息…",
    "diag.header": "--------- 诊断信息 ---------",
    "diag.footer": "------- 诊断信息结束 -------",
    "diag.file": "同一份报告已保存到：{path}",
    "diag.self": "本程序：PID {pid}，管理员权限：{admin}，完整性级别：{level}",
    "diag.fg": "当前活动窗口：'{title}' [类名 {cls}]，PID {pid}，进程：{exe}",
    "diag.fg_integrity": "权限对比：目标进程 {level}，本程序 {own}",
    "diag.fg_higher": "目标程序权限高于本程序，Windows 会拦截我们的按键。"
                      "这正是“以管理员身份启动 Steam”时发生的情况：游戏继承了它的令牌。",
    "diag.fg_same": "目标程序权限不高于本程序 —— 在这一层没有被拦截",
    "diag.fg_unknown": "无法读取目标进程权限（这本身不是问题）",
    "diag.target": "已选目标：'{title}'（hwnd {hwnd}）",
    "diag.target_none": "未选择目标窗口 —— 按键会发送给当前活动窗口",
    "diag.target_is_fg": "目标窗口正是当前活动窗口 —— 正确",
    "diag.target_not_fg": "目标窗口当前不是活动窗口",
    "diag.mode": "发送模式：{mode}",
    "diag.test_ok": "测试按键（右 Shift，无副作用）：SendInput 已接受",
    "diag.test_fail": "测试按键：SendInput 被拒绝 → {err}",
    "diag.verdict": "结论：{text}",
    "diag.verdict_admin": "Windows 正在拦截输入。请关闭本工具，并以管理员身份重新启动"
                          "（右键 → 以管理员身份运行，或使用 run_admin.bat）。",
    "diag.verdict_focus": "目标窗口当时不是活动窗口。按键永远发送给活动窗口，"
                          "所以请在目标窗口中按启动热键（F1），"
                          "或把模式改为“先激活目标窗口，再按键”。",
    "diag.verdict_ok": "输入通道正常。如果目标程序仍然不响应：把“按住”提高到 "
                       "80–120 毫秒，确认程序读取的确实是这个键；"
                       "若都不行，说明程序过滤了模拟输入（反作弊）。",
    "selftest.button": "发送测试",
    "selftest.title": "发送测试",
    "selftest.hint": "正在把序列发送到本窗口。\n收到的内容会列在下方。",
    "selftest.got": "已收到（{n}）：{list}",
    "selftest.none": "什么也没收到 —— 连发到本窗口都收不到。请运行诊断。",
    "selftest.sending": "正在发送：{key}",
    "selftest.done": "完成",
    "selftest.close": "关闭",
    "selftest.no_steps": "请先添加至少一个步骤。",
    "err.send.title": "输入被拦截",
    "inst.title": "程序已在运行",
    "inst.blocked": "自动按键工具已在运行。\n\n不允许打开第二份：全局热键只会归"
                    "第一份所有。正在打开已有的窗口。",
    "target.admin_mark": "管理员",
    "admin.ask_title": "需要管理员权限",
    "admin.ask": "窗口“{title}”以管理员权限运行（{level}），"
                 "而本工具以普通权限运行（{own}）。\n\n"
                 "Windows 会丢弃本工具发送到该窗口的所有按键。\n\n"
                 "是否立即以管理员身份重启本工具？当前序列和设置会保留。",
    "admin.restarting": "正在以管理员身份重启…",
    "admin.declined": "保持现状：在本工具以管理员身份运行之前，"
                      "Windows 会一直拦截发送到“{title}”的按键。",
    "admin.failed": "无法以管理员身份重启（{err}）。",
    "admin.blocked_start": "目标窗口以管理员身份运行，而本工具没有 —— "
                           "Windows 会拦截按键。请以管理员身份重启。",

    # --- движок -----------------------------------------------------------
    "eng.no_steps": "序列中没有已启用的步骤。",
    "eng.hold_hint": "提示：按住时长 {ms} 毫秒偏短。Unity/Unreal 类程序每帧才轮询"
                     "一次键盘，短于约 50 毫秒的按键可能被吞掉 —— 建议改成 80–120 毫秒。",
    "eng.step_bad": "步骤“{key}”有误：{err}",
    "eng.window_not_found": "找不到窗口“{title}”。",
    "eng.post_needs_window": "PostMessage 模式必须先选择目标窗口。",
    "eng.countdown": "{sec} 秒后启动",
    "eng.started": "已启动。",
    "eng.cycle": "第 {i}/{n} 轮",
    "eng.done": "已完成：共 {n} 轮。",
    "eng.stopped": "已停止。",
    "eng.paused": "已暂停。",
    "eng.resumed": "已继续。",
    "eng.window_inactive": "目标窗口未激活 —— 等待中（不发送按键）。",
    "eng.window_closed": "目标窗口已关闭。",
    "eng.window_active": "窗口已重新激活 —— 继续发送。",
    "eng.step_failed": "第 {n} 步（{key}）：{err}",
    "eng.force_release": "强制松开残留按键：{names}",

    # --- ввод -------------------------------------------------------------
    "send.rejected": "SendInput 被拒绝（错误码 {code}）。如果目标程序以管理员身份"
                     "运行，本工具也必须以管理员身份运行。",

    # --- ошибки разбора клавиш -------------------------------------------
    "keys.unknown": "未知按键：{name}",
    "keys.not_modifier": "“{name}”不能用作修饰键",
    "keys.empty": "未设置按键",
    "keys.bad_code": "无法解析该编码：{spec}",
    "keys.range": "编码必须在 1..255 范围内",
    "mouse.left": "左键",
    "mouse.right": "右键",
    "mouse.middle": "中键",
}

RU: dict[str, str] = {
    "app.title": "KeyPresser",
    "app.version": "версия {v}",
    "lang.label": "Язык:",
    "lang.changed": "Язык интерфейса: {name}",

    "menu.profile": "Профиль",
    "menu.new": "Новый",
    "menu.open": "Открыть...",
    "menu.save": "Сохранить",
    "menu.save_as": "Сохранить как...",
    "menu.exit": "Выход",
    "menu.language": "Язык",
    "menu.help": "Справка",
    "menu.how": "Как это работает",

    "target.frame": "Целевое окно",
    "target.window": "Окно:",
    "target.refresh": "Обновить",
    "target.grab": "Взять активное через 3 с",
    "target.none": "(не выбрано - жать в активное окно)",
    "mode.foreground": "Только когда окно игры активно (безопасно)",
    "mode.activate": "Активировать окно и жать",
    "mode.post": "В фоне, PostMessage (не все игры понимают)",

    "seq.frame": "Последовательность",
    "col.n": "#",
    "col.key": "Клавиша (физическая)",
    "col.act": "Действие",
    "col.hold": "Удерж., мс",
    "col.delay": "Пауза после, мс",
    "col.rep": "Повтор",
    "col.on": "Вкл",
    "col.cm": "Комментарий",
    "btn.up": "Вверх",
    "btn.down": "Вниз",
    "btn.dup": "Дублировать",
    "btn.toggle": "Вкл / выкл",
    "btn.delete": "Удалить",
    "btn.clear": "Очистить всё",
    "yes": "да",
    "no": "нет",

    "step.frame": "Шаг",
    "step.key": "Клавиша:",
    "step.capture": "Записать клавишу",
    "step.action": "Действие:",
    "step.hold": "Удерж., мс",
    "step.delay": "Пауза, мс",
    "step.repeat": "Повтор",
    "step.comment": "Комментарий:",
    "step.add": "Добавить шаг",
    "step.apply": "Применить к выбранному",
    "action.tap": "нажать",
    "action.down": "зажать",
    "action.up": "отпустить",
    "preview.ok": "-> уйдёт в игру: {desc}   (скан-код = физическая клавиша, "
                  "раскладка не важна)",
    "preview.err": "x {err}",

    "rec.frame": "Запись нажатий",
    "rec.start": "Начать запись",
    "rec.stop": "Остановить запись",
    "rec.mouse": "писать кнопки мыши",
    "rec.replace": "заменять последовательность (иначе дописать в конец)",
    "rec.tail": "Пауза после последнего шага, мс:",
    "rec.off": "Запись выключена",
    "rec.on": "ЗАПИСЬ ИДЁТ - жмите клавиши в игре",
    "rec.progress": "ЗАПИСЬ: {n} нажатий, последнее - {key}",
    "rec.started": "Запись началась. Нажатия и паузы фиксируются как есть; "
                   "хоткеи в запись не попадают.",
    "rec.done": "Записано шагов: {n}.",
    "rec.empty": "Запись остановлена: нажатий не поймано.",
    "rec.engine_busy": "Скрипт работает - останавливаю перед записью.",
    "rec.hook_failed": "не удалось поставить хук клавиатуры (код {code})",
    "rec.prefix": "Запись: {msg}",

    "loop.frame": "Цикл и задержки",
    "loop.cycles": "Повторов цикла (0 = бесконечно):",
    "loop.cycle_delay": "Пауза между циклами, мс:",
    "loop.jitter": "Случайный разброс задержек, %:",
    "loop.start_delay": "Задержка перед стартом, мс:",

    "hk.frame": "Горячие клавиши (работают внутри игры)",
    "hk.run_toggle": "Запуск скрипта",
    "hk.pause": "Пауза / продолжить",
    "hk.stop": "Аварийный стоп",
    "hk.record_toggle": "Запись: старт / стоп",
    "hk.minimize": "Свернуть окно",
    "hk.set": "Задать",
    "hk.apply": "Применить хоткеи",
    "hk.assigned": "Хоткеи назначены: {list}",
    "hk.prefix": "Хоткей: {msg}",
    "hk.err.parse": "'{combo}' ({action}): {err}",
    "hk.err.busy": "{combo} занят другой программой - действие '{action}' не назначено",
    "hk.err.raw": "для хоткея нужна клавиша с VK-кодом, сырой скан-код не подходит",
    "hk.err.handler": "обработчик: {err}",

    "ctl.start": "Старт",
    "ctl.pause": "Пауза",
    "ctl.resume": "Продолжить",
    "ctl.stop": "Стоп",
    "ctl.minimize": "Свернуть",
    "log.frame": "Журнал",
    "status.ready": "Готово",
    "status.running": "Работает",
    "status.paused": "Пауза",
    "status.stopped": "Остановлено",
    "status.starting": "Запуск...",
    "status.waiting": "Ожидание окна",
    "status.recording": "Запись",

    "dlg.step_key": "Клавиша шага",
    "dlg.hotkey": "Хоткей: {action}",
    "dlg.hint": "Нажмите нужную клавишу или комбинацию.\n"
                "Модификаторы (Ctrl / Shift / Alt) можно удерживать.",
    "dlg.hint_mouse": "Клик мышью по этой области = кнопка мыши.",
    "dlg.hint_modifier": "Одиночный модификатор (Alt, Ctrl, Shift): нажмите и отпустите его.",
    "dlg.mod_not_hotkey": "модификатор сам по себе не может быть хоткеем - добавьте клавишу",
    "dlg.cancel": "Отмена",
    "dlg.unknown": "неизвестная клавиша (vk {vk})",
    "msg.hk_modifier_only": "{action}: модификатор сам по себе не может быть хоткеем. "
                            "Используйте комбинацию, например ctrl+alt+f6.",

    "msg.select_step": "Сначала выберите шаг в списке.",
    "msg.numbers": "Проверьте удержание / паузу / повтор.",
    "msg.settings_numbers": "Проверьте числовые поля.",
    "msg.param_clamped": "Значения вне диапазона исправлены: {list}",
    "msg.clear_title": "Очистить",
    "msg.clear_text": "Удалить все шаги?",
    "msg.new_title": "Новый профиль",
    "msg.new_text": "Текущая последовательность будет очищена. Продолжить?",
    "msg.open_error": "Не удалось прочитать файл:\n{err}",
    "msg.saved": "Сохранено: {name}",
    "msg.loaded": "Загружен профиль: {name} (шагов: {n})",
    "msg.new_profile": "Новый профиль.",
    "msg.step_added": "Добавлен шаг {n}: {key}",
    "msg.rec_running": "Идёт запись - сначала остановите её.",
    "msg.target": "Целевое окно: {title}",
    "msg.grab_hint": "Переключитесь в окно игры - заберу его через 3 секунды...",
    "msg.grab_fail": "Не удалось определить активное окно.",
    "msg.admin_hint": "Подсказка: если игра запущена от администратора, запустите "
                      "KeyPresser тоже от администратора (run_admin.bat), иначе "
                      "Windows заблокирует нажатия.",
    "title.key": "Клавиша",
    "title.hotkey": "Хоткей",
    "title.numbers": "Числа",
    "title.settings": "Настройки",
    "title.open": "Открыть профиль",
    "title.save": "Сохранить профиль",
    "title.profile_filter": "Профиль KeyPresser",
    "title.all_files": "Все файлы",
    "help.text":
        "1. Выберите окно игры (или «Взять активное через 3 с» для полного экрана).\n"
        "2. Соберите последовательность: «Записать клавишу» или запись живых\n"
        "   нажатий кнопкой «Начать запись» (по умолчанию F9).\n"
        "3. Задайте удержание, паузу после шага и число повторов.\n"
        "4. Старт - F1, пауза - F2, стоп - F3 (настраиваются).\n\n"
        "Клавиши отправляются по физическому скан-коду через SendInput,\n"
        "поэтому раскладка не мешает: шаг «w» - всегда та же физическая клавиша.\n\n"
        "Если игра запущена от администратора - запускайте KeyPresser так же,\n"
        "иначе Windows не пропустит нажатия (run_admin.bat).",

    "diag.button": "Диагностика (через 3 с)",
    "diag.wait": "Переключитесь в окно игры - собираю диагностику через 3 секунды...",
    "diag.header": "--------- диагностика ---------",
    "diag.footer": "------- конец диагностики -------",
    "diag.file": "Этот же отчёт сохранён в файл: {path}",
    "diag.self": "KeyPresser: PID {pid}, администратор: {admin}, "
                 "уровень целостности: {level}",
    "diag.fg": "Активное окно: '{title}' [класс {cls}], PID {pid}, процесс: {exe}",
    "diag.fg_integrity": "Права: процесс игры {level}, KeyPresser {own}",
    "diag.fg_higher": "У игры права ВЫШЕ, чем у KeyPresser, поэтому Windows блокирует "
                      "наши нажатия. Так и бывает, когда Steam запущен от администратора: "
                      "игра наследует его токен.",
    "diag.fg_same": "Права игры не выше наших - на этом уровне ничего не блокируется",
    "diag.fg_unknown": "Права процесса игры прочитать не удалось (само по себе не "
                       "проблема)",
    "diag.target": "Выбранная цель: '{title}' (hwnd {hwnd})",
    "diag.target_none": "Целевое окно не выбрано - нажатия уходят в активное окно",
    "diag.target_is_fg": "Целевое окно активно - верно",
    "diag.target_not_fg": "Целевое окно сейчас НЕ активно",
    "diag.mode": "Режим отправки: {mode}",
    "diag.test_ok": "Тестовое нажатие (правый Shift, безобидный): SendInput принял",
    "diag.test_fail": "Тестовое нажатие: SendInput ОТКАЗАЛ -> {err}",
    "diag.verdict": "ВЫВОД: {text}",
    "diag.verdict_admin": "Windows блокирует ввод. Закройте KeyPresser и запустите его от "
                          "администратора (ПКМ по exe -> «Запуск от имени администратора» "
                          "или run_admin.bat).",
    "diag.verdict_focus": "Окно игры не было активным. Нажатия всегда идут в активное окно, "
                          "поэтому жмите хоткей старта (F1), находясь в игре, либо "
                          "переключите режим на «Активировать окно и жать».",
    "diag.verdict_ok": "Путь ввода работает. Если игра всё равно не реагирует: поднимите "
                       "«Удерж., мс» до 80-120, проверьте, что игра ждёт именно эту "
                       "клавишу, а если ничего не помогает - игра фильтрует синтетический "
                       "ввод (античит).",
    "selftest.button": "Проверка отправки",
    "selftest.title": "Проверка отправки",
    "selftest.hint": "Последовательность сейчас отправляется в это окно.\n"
                     "Всё, что доходит, показано ниже.",
    "selftest.got": "Дошло ({n}): {list}",
    "selftest.none": "НЕ дошло НИЧЕГО - нажатия не доставляются даже в наше собственное "
                     "окно. Запустите диагностику.",
    "selftest.sending": "отправляю: {key}",
    "selftest.done": "готово",
    "selftest.close": "Закрыть",
    "selftest.no_steps": "Сначала добавьте хотя бы один шаг.",
    "err.send.title": "Ввод заблокирован",
    "inst.title": "KeyPresser уже запущен",
    "inst.blocked": "KeyPresser уже запущен.\n\nВторая копия не разрешена: глобальные "
                    "хоткеи достались бы первой. Открываю уже запущенное окно.",
    "target.admin_mark": "АДМИН",
    "admin.ask_title": "Нужны права администратора",
    "admin.ask": "Окно «{title}» работает с правами администратора ({level}), а "
                 "KeyPresser -- с обычными ({own}).\n\nWindows будет отбрасывать все "
                 "нажатия, которые KeyPresser отправит в это окно.\n\nПерезапустить "
                 "KeyPresser от администратора? Текущая последовательность и настройки "
                 "сохранятся.",
    "admin.restarting": "Перезапускаюсь от администратора...",
    "admin.declined": "Оставляем как есть: нажатия в «{title}» будут блокироваться "
                      "Windows, пока KeyPresser не запущен от администратора.",
    "admin.failed": "Не удалось перезапуститься от администратора ({err}).",
    "admin.blocked_start": "Целевое окно работает от администратора, а KeyPresser нет -- "
                           "Windows заблокирует нажатия. Перезапустите от администратора.",

    "eng.no_steps": "В последовательности нет активных шагов.",
    "eng.hold_hint": "Внимание: удержание {ms} мс - мало. Игры на Unity/Unreal опрашивают клавиатуру раз в кадр и могут проглотить тап короче ~50 мс, попробуйте 80-120 мс.",
    "eng.step_bad": "Ошибка в шаге '{key}': {err}",
    "eng.window_not_found": "Окно '{title}' не найдено.",
    "eng.post_needs_window": "Режим PostMessage требует выбранного окна.",
    "eng.countdown": "Старт через {sec} с",
    "eng.started": "Запуск.",
    "eng.cycle": "Цикл {i}/{n}",
    "eng.done": "Готово: выполнено циклов - {n}.",
    "eng.stopped": "Остановлено.",
    "eng.paused": "Пауза.",
    "eng.resumed": "Продолжаем.",
    "eng.window_inactive": "Окно игры не активно - ждём (нажатия не отправляются).",
    "eng.window_closed": "Целевое окно закрылось.",
    "eng.window_active": "Окно снова активно - продолжаем.",
    "eng.step_failed": "Шаг {n} ({key}): {err}",
    "eng.force_release": "Аварийное отпускание зажатых клавиш: {names}",

    "send.rejected": "SendInput отклонён (код {code}). Если игра запущена от имени "
                     "администратора, KeyPresser тоже нужно запустить от администратора.",

    "keys.unknown": "неизвестная клавиша: {name}",
    "keys.not_modifier": "'{name}' нельзя использовать как модификатор",
    "keys.empty": "клавиша не задана",
    "keys.bad_code": "не удалось разобрать код: {spec}",
    "keys.range": "код должен быть в диапазоне 1..255",
    "mouse.left": "ЛКМ",
    "mouse.right": "ПКМ",
    "mouse.middle": "СКМ",
}

CATALOG = {"en": EN, "ru": RU, "zh": ZH}


def set_language(code: str) -> str:
    global _current
    _current = code if code in CATALOG else DEFAULT_LANGUAGE
    return _current


def language() -> str:
    return _current


def t(key: str, /, **fmt) -> str:
    """Ключ -- строго позиционный: иначе t("...", key=...) конфликтует с ним самим."""
    text = CATALOG.get(_current, EN).get(key) or EN.get(key) or key
    if fmt:
        try:
            return text.format(**fmt)
        except (KeyError, IndexError):
            return text
    return text
