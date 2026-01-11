KEY_SECTIONS = [
    (
        "Function Keys",
        [
            [
                "esc",
                "f1",
                "f2",
                "f3",
                "f4",
                "f5",
                "f6",
            ],
            [
                "f7",
                "f8",
                "f9",
                "f10",
                "f11",
                "f12",
            ],
        ],
    ),
    (
        "Typing Keys",
        [
            ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "backspace"],
            ["tab", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]", "\\"],
            ["capslock", "a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'", "enter"],
            ["shift", "z", "x", "c", "v", "b", "n", "m", ",", ".", "/", "shift"],
            ["ctrl", "win", "alt", "space  ", "alt", "win", "[=]", "ctrl"],
        ],
    ),
    (
        "System, Editing & Navigation",
        [
            ["printscreen", "scrolllock", "pause"],
            ["insert", "home", "pageup"],
            ["delete", "end", "pagedown"],
            ["up"],
            ["left", "down", "right"],
        ],
    ),
    (
        "Numeric Keypad",
        [
            ["numlock", "numpaddiv", "numpadmult"],
            ["numpad7", "numpad8", "numpad9", "numpadadd"],
            ["numpad4", "numpad5", "numpad6", "numpadsub"],
            ["numpad1", "numpad2", "numpad3", "numpad0"],
            ["numpaddot", "numpadenter"],
        ],
    ),
]

KEY_NAME_OVERRIDES = {
    "esc": "Escape",
    "tab": "Tab",
    "capslock": "CapsLock",
    "shift": "Shift",
    "ctrl": "Ctrl",
    "alt": "Alt",
    "win": "LWin",
    "space": "Space",
    "numlock": "NumLock",
    "pageup": "PgUp",
    "pagedown": "PgDn",
    "printscreen": "PrintScreen",
    "scrolllock": "ScrollLock",
    "insert": "Insert",
    "delete": "Delete",
    "home": "Home",
    "end": "End",
    "pause": "Pause",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "backspace": "Backspace",
    "enter": "Enter",
    "`": "Grave",
    "~": "Tilde",
    "[=]": "Equal",
    "numpad0": "Numpad0",
    "numpad1": "Numpad1",
    "numpad2": "Numpad2",
    "numpad3": "Numpad3",
    "numpad4": "Numpad4",
    "numpad5": "Numpad5",
    "numpad6": "Numpad6",
    "numpad7": "Numpad7",
    "numpad8": "Numpad8",
    "numpad9": "Numpad9",
    "numpadadd": "NumpadAdd",
    "numpadsub": "NumpadSub",
    "numpaddiv": "NumpadDiv",
    "numpadmult": "NumpadMult",
    "numpadenter": "NumpadEnter",
    "numpaddot": "NumpadDot",
}

SETTINGS_FILENAME = "assignments.json"
KEYBOARD_PROFILES_FILENAME = "keyboards.json"
SCRIPT_HEADER_FILENAME = "script_header.json"
EXPORT_PATH_FILENAME = "export_path.json"

DEFAULT_HEADER_LINES = [
    "#SingleInstance force",
    "#Persistent",
    "#include Lib\\AutoHotInterception.ahk",
    "",
    "AHI := new AutoHotInterception()",
    "id1 := AHI.GetKeyboardId(0x046D, 0xC31C, 1)",
    "cm1 := AHI.CreateContextManager(id1)",
    "id2 := AHI.GetKeyboardId(0x258A, 0x002A, 1)",
    "cm2 := AHI.CreateContextManager(id2)",
    "return",
    "",
]

MODIFIER_OPTIONS = ["None", "Ctrl", "Win", "Alt", "Shift"]
MODIFIER_PREFIX = {"Ctrl": "^", "Win": "#", "Alt": "!", "Shift": "+"}

KEY_DEFAULT_BUTTON_BG = "#e1e1e1"
KEY_BIND_COLOR = "#8dd38d"
MODIFIER_ENABLED_TEXT = "Enabled"

