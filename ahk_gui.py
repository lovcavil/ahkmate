#!/usr/bin/env python
import json
import os
from collections import defaultdict
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import tkinter.ttk as ttk

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
                "f6"
            ],
            [
                "f7",
                "f8",
                "f9",
                "f10",
                "f11",
                "f12",
            ]
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


class AHKBuilder(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AHK Macro Builder")
        self.configure(background="#f5f5f5")
        self.geometry("1024x640")
        self.selected_key_id = ""
        self.selected_key_label = tk.StringVar(value="No key selected")
        self.modifier_var = tk.StringVar(value="None")
        self.profile_var = tk.StringVar()
        self.keyboard_profiles = []
        self.profile_label_by_id = {}
        self.profile_id_by_label = {}
        self.profile_combo = None
        self.modifier_combo = None
        self.current_profile_id = ""
        self.actions_by_profile = {}
        self.key_buttons = defaultdict(list)
        self.settings_path = Path(__file__).resolve().parent / SETTINGS_FILENAME
        self.keyboards_path = Path(__file__).resolve().parent / KEYBOARD_PROFILES_FILENAME
        self.header_path = Path(__file__).resolve().parent / SCRIPT_HEADER_FILENAME
        self.restored_last_key = ""
        self.restored_last_text = ""
        self.restored_last_modifier = "None"
        self._suppress_profile_event = False
        self._modifier_event_suppress = False
        self.enabled_check = None
        self.enabled_var = tk.BooleanVar(value=True)
        self._load_keyboard_profiles()
        self.header_lines = self._load_script_header()
        self._load_settings()
        self.active_button = None
        self.key_labels = {}
        self._build_layout()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_keyboard_profiles(self):
        fallback = [
            {
                "id": "default",
                "label": "Default keyboard",
                "condition": "",
                "device_id": "",
                "description": "Global profile",
            },
            {
                "id": "id1",
                "label": "id1 keyboard",
                "condition": "cm1.IsActive",
                "device_id": "0x046D,0xC31C,1",
                "description": "Logitech profile",
            },
            {
                "id": "id2",
                "label": "id2 keyboard",
                "condition": "cm2.IsActive",
                "device_id": "0x258A,0x002A,1",
                "description": "Secondary profile",
            },
        ]
        data = {}
        try:
            with open(self.keyboards_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            data = {}
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showwarning(
                "Keyboard profiles",
                f"Unable to read {self.keyboards_path.name}:\n{exc}",
            )
            data = {}
        raw_profiles = data.get("profiles")
        profiles = []
        if isinstance(raw_profiles, list):
            for entry in raw_profiles:
                if not isinstance(entry, dict):
                    continue
                profile_id = str(entry.get("id", "")).strip()
                label = str(entry.get("label", "")).strip()
                if not profile_id or not label:
                    continue
                condition = str(entry.get("condition", "")).strip()
                profiles.append(
                    {
                        "id": profile_id,
                        "label": label,
                        "condition": condition,
                        "device_id": str(entry.get("device_id", "")).strip(),
                        "description": str(entry.get("description", "")).strip(),
                    }
                )
        if not profiles:
            profiles = fallback
        self.keyboard_profiles = profiles
        self.profile_label_by_id = {p["id"]: p["label"] for p in profiles}
        self.profile_id_by_label = {p["label"]: p["id"] for p in profiles}
        default_profile = str(data.get("default_profile", "")).strip()
        if default_profile not in self.profile_label_by_id:
            default_profile = profiles[0]["id"]
        self.current_profile_id = default_profile
        self.profile_var.set(self.profile_label_by_id.get(self.current_profile_id, profiles[0]["label"]))

    def _load_script_header(self):
        try:
            with open(self.header_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return list(DEFAULT_HEADER_LINES)
        header = data.get("header")
        if not isinstance(header, list) or not all(isinstance(line, str) for line in header):
            return list(DEFAULT_HEADER_LINES)
        return header

    def _load_settings(self):
        self.actions_by_profile = {}
        if not self.settings_path.exists():
            return
        try:
            with open(self.settings_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showwarning(
                "Settings load failed",
                f"Unable to read {self.settings_path.name}:\n{exc}",
            )
            return
        self.restored_last_key = str(data.get("last_key", "") or "")
        self.restored_last_text = data.get("last_text")
        if not isinstance(self.restored_last_text, str):
            self.restored_last_text = ""
        self.restored_last_modifier = str(data.get("last_modifier", "None") or "None")
        if self.restored_last_modifier not in MODIFIER_OPTIONS:
            self.restored_last_modifier = "None"
        last_profile = str(data.get("last_profile", "") or "")
        if last_profile in self.profile_label_by_id:
            self.current_profile_id = last_profile
        if not self.current_profile_id and self.keyboard_profiles:
            self.current_profile_id = self.keyboard_profiles[0]["id"]
        raw_actions = data.get("actions", {})
        sanitized = {}
        if isinstance(raw_actions, dict):
            for profile_id, action_data in raw_actions.items():
                if not isinstance(profile_id, str):
                    continue
                if not isinstance(action_data, dict):
                    continue
                cleaned = {}
                for key, entry in action_data.items():
                    if not isinstance(key, str):
                        continue
                    modifiers = {}
                    if isinstance(entry, dict):
                        for modifier_key, modifier_value in entry.items():
                            if (
                                isinstance(modifier_key, str)
                                and modifier_key in MODIFIER_OPTIONS
                                and isinstance(modifier_value, dict)
                            ):
                                action_text = modifier_value.get("action", "")
                                enabled = modifier_value.get("enabled", True)
                                if isinstance(action_text, str):
                                    text = action_text.strip()
                                    if text or not enabled:
                                        modifiers[modifier_key] = {
                                            "action": text,
                                            "enabled": bool(enabled),
                                        }
                    elif isinstance(entry, str):
                        text = entry.strip()
                        if text:
                            modifiers["None"] = {"action": text, "enabled": True}
                    if modifiers:
                        cleaned[key] = modifiers
                if cleaned:
                    sanitized[profile_id] = cleaned
        self.actions_by_profile = sanitized

    def _build_layout(self):
        keyboard_frame = tk.Frame(self, bg="#f5f5f5")
        keyboard_frame.pack(fill="x", padx=12, pady=8)
        for section_name, rows in KEY_SECTIONS:
            section_frame = tk.LabelFrame(
                keyboard_frame,
                text=section_name,
                background="#ffffff",
                fg="#333333",
                borderwidth=1,
                relief="ridge",
            )
            section_frame.pack(side="left", expand=True, fill="both", padx=6, pady=4)
            if section_name == "Function Keys":
                self._add_function_dropdown(section_frame)
            for row_index, row in enumerate(rows):
                row_frame = tk.Frame(section_frame, bg="#ffffff")
                row_frame.pack(fill="x", expand=True, pady=2)
                for col_index, raw_key in enumerate(row):
                    display = self._format_key_display(raw_key)
                    key_id = raw_key.strip().lower()
                    self.key_labels.setdefault(key_id, display)
                    btn = tk.Button(
                        row_frame,
                        text=display,
                        width=self._button_width(display, key_id),
                        relief="raised",
                        bd=2,
                        bg=KEY_DEFAULT_BUTTON_BG,
                        activebackground="#c5c5c5",
                    )
                    btn.grid(row=row_index, column=col_index, padx=2, sticky="nsew")
                    btn.configure(
                        command=lambda k=key_id, d=display, b=btn: self._select_key(k, d, b)
                    )
                    self.key_buttons[key_id].append(btn)
                for col in range(len(row)):
                    row_frame.grid_columnconfigure(col, weight=1)
        self._create_control_panel()
        self._apply_restored_profile()
        self._restore_selection()
        self._refresh_button_colors()
        self._refresh_script_preview()

    def _create_control_panel(self):
        control_frame = tk.Frame(self, bg="#f5f5f5")
        control_frame.pack(fill="both", expand=True, padx=12, pady=(4, 10))

        detail_frame = tk.LabelFrame(control_frame, text="Key Detail", bg="#ffffff")
        detail_frame.pack(side="left", fill="y", padx=6, pady=4)
        tk.Label(detail_frame, textvariable=self.selected_key_label, bg="#ffffff").pack(
            pady=8, padx=8
        )
        modifier_frame = tk.Frame(detail_frame, bg="#ffffff")
        modifier_frame.pack(fill="x", padx=8, pady=(0, 6))
        tk.Label(modifier_frame, text="Modifier:", bg="#ffffff").pack(side="left")
        modifier_combo = ttk.Combobox(
            modifier_frame,
            textvariable=self.modifier_var,
            values=MODIFIER_OPTIONS,
            state="readonly",
            width=8,
        )
        self.modifier_combo = modifier_combo
        modifier_combo.pack(side="left", padx=(6, 0))
        modifier_combo.bind("<<ComboboxSelected>>", self._on_modifier_selected)
        self._set_modifier_selection(self.modifier_var.get())
        modifier_combo.set(self.modifier_var.get())
        status_frame = tk.Frame(detail_frame, bg="#ffffff")
        status_frame.pack(fill="x", padx=8, pady=(0, 6))
        self.enabled_check = tk.Checkbutton(
            status_frame,
            text=MODIFIER_ENABLED_TEXT,
            bg="#ffffff",
            variable=self.enabled_var,
            command=self._on_enabled_change,
        )
        self.enabled_check.pack(side="left")
        tk.Button(detail_frame, text="Clear assignment", command=self._clear_assignment).pack(
            pady=4, padx=8, fill="x"
        )

        action_frame = tk.LabelFrame(control_frame, text="Action script", bg="#ffffff")
        action_frame.pack(side="left", fill="both", expand=True, padx=6, pady=4)
        self.action_entry = scrolledtext.ScrolledText(
            action_frame, height=8, width=36, wrap="word"
        )
        self.action_entry.pack(fill="both", expand=True, padx=6, pady=4)
        tk.Button(action_frame, text="Save action", command=self._save_action).pack(
            pady=2, padx=6, anchor="e"
        )

        preview_frame = tk.LabelFrame(control_frame, text="Script preview", bg="#ffffff")
        preview_frame.pack(side="left", fill="both", expand=True, padx=6, pady=4)
        self.preview_box = scrolledtext.ScrolledText(
            preview_frame, height=12, wrap="word", state="disabled"
        )
        self.preview_box.pack(fill="both", expand=True, padx=6, pady=(6, 2))
        button_frame = tk.Frame(preview_frame, bg="#ffffff")
        button_frame.pack(fill="x", padx=6, pady=(0, 6))
        tk.Button(button_frame, text="Export .ahk script", command=self._export_script).pack(
            side="left"
        )
        tk.Button(button_frame, text="Refresh preview", command=self._refresh_script_preview).pack(
            side="right"
        )

    def _add_function_dropdown(self, parent):
        drop_frame = tk.Frame(parent, bg="#ffffff")
        drop_frame.pack(fill="x", padx=6, pady=(4, 6))
        tk.Label(drop_frame, text="Profile", bg="#ffffff").pack(side="left", padx=(4, 6))
        labels = [profile["label"] for profile in self.keyboard_profiles]
        combo = ttk.Combobox(
            drop_frame,
            textvariable=self.profile_var,
            values=labels,
            state="readonly",
        )
        initial_label = self.profile_label_by_id.get(
            self.current_profile_id, labels[0] if labels else ""
        )
        self.profile_var.set(initial_label)
        self.profile_combo = combo
        self._suppress_profile_event = True
        combo.set(initial_label)
        self._suppress_profile_event = False
        combo.pack(side="left", fill="x", expand=True, padx=(0, 4))
        combo.bind("<<ComboboxSelected>>", self._on_profile_selected)

    def _on_profile_selected(self, event=None):
        if self._suppress_profile_event:
            return
        label = self.profile_var.get()
        profile_id = self.profile_id_by_label.get(label)
        if not profile_id:
            profile_id = self.keyboard_profiles[0]["id"]
            label = self.profile_label_by_id.get(profile_id, "")
            self.profile_var.set(label)
            if self.profile_combo:
                self.profile_combo.set(label)
        self.current_profile_id = profile_id
        if self.selected_key_id:
            display = self.key_labels.get(self.selected_key_id, self.selected_key_id)
            self._update_selected_key_label(display, self.selected_key_id)
        self._refresh_action_entry()
        self._refresh_button_colors()
        self._save_settings()

    def _restore_selection(self):
        if not self.restored_last_key:
            return
        buttons = self.key_buttons.get(self.restored_last_key, [])
        if not buttons:
            return
        display = self.key_labels.get(self.restored_last_key, self.restored_last_key)
        self._select_key(self.restored_last_key, display, buttons[0])
        entry = self._get_profile_entry(self.restored_last_key)
        modifier = self.modifier_var.get()
        stored_action = entry.get(modifier, "")
        if self.restored_last_text and self.restored_last_text != stored_action:
            self.action_entry.delete("1.0", "end")
            self.action_entry.insert("1.0", self.restored_last_text)
        self.restored_last_text = ""

    def _apply_restored_profile(self):
        if not self.profile_combo:
            return
        label = self.profile_label_by_id.get(self.current_profile_id)
        if not label and self.keyboard_profiles:
            self.current_profile_id = self.keyboard_profiles[0]["id"]
            label = self.profile_label_by_id.get(self.current_profile_id, "")
        if not label:
            return
        self.profile_var.set(label)
        self._suppress_profile_event = True
        self.profile_combo.set(label)
        self._suppress_profile_event = False

    def _set_modifier_selection(self, modifier):
        if modifier not in MODIFIER_OPTIONS:
            modifier = "None"
        self._modifier_event_suppress = True
        self.modifier_var.set(modifier)
        if self.modifier_combo:
            self.modifier_combo.set(modifier)
        self._modifier_event_suppress = False
        if self.enabled_check:
            entry = self._get_profile_entry(self.selected_key_id) if self.selected_key_id else {}
            info = entry.get(modifier, {})
            enabled = info.get("enabled", True)
            self.enabled_var.set(enabled)

    def _set_modifier_state(self, modifier, action_text, enabled):
        if not self.selected_key_id:
            return False
        profile_actions = self.actions_by_profile.setdefault(self.current_profile_id, {})
        entry = profile_actions.setdefault(self.selected_key_id, {})
        if not isinstance(entry, dict):
            entry = {}
            profile_actions[self.selected_key_id] = entry
        text = action_text.strip()
        if text or enabled:
            entry[modifier] = {"action": text, "enabled": bool(enabled)}
        else:
            entry.pop(modifier, None)
            if not entry:
                profile_actions.pop(self.selected_key_id, None)
        return True

    def _on_modifier_selected(self, event=None):
        if self._modifier_event_suppress:
            return
        self._refresh_action_entry()

    def _on_enabled_change(self):
        if self._modifier_event_suppress or not self.selected_key_id:
            return
        modifier = self.modifier_var.get()
        action_text = self.action_entry.get("1.0", "end").strip()
        enabled = self.enabled_var.get()
        self._set_modifier_state(modifier, action_text, enabled)
        self._save_settings()
        self._refresh_script_preview()
        self._refresh_button_colors()

    def _format_key_display(self, raw_key):
        cleaned = raw_key.strip()
        lower = cleaned.lower()
        if lower.startswith("numpad"):
            suffix = lower.replace("numpad", "", 1)
            display_map = {
                "div": "/",
                "mult": "*",
                "add": "+",
                "sub": "-",
                "enter": "Enter",
                "dot": ".",
            }
            return display_map.get(suffix, suffix.upper())
        if cleaned.lower() == "space":
            return "Space"
        if cleaned.isalpha():
            return cleaned.capitalize()
        if cleaned.isalnum():
            return cleaned.upper()
        return cleaned

    def _button_width(self, label, key_id):
        if key_id == "space":
            return 22
        return max(4, len(label) + 2)

    def _select_key(self, key_id, display_label, button):
        if self.active_button:
            self.active_button.configure(relief="raised", bg="#e1e1e1")
        self.active_button = button
        button.configure(relief="sunken", bg="#d4e0ff")
        self.selected_key_id = key_id
        self._update_selected_key_label(display_label, key_id)
        entry = self._get_profile_entry(key_id)
        chosen_modifier = self.modifier_var.get()
        if entry and chosen_modifier not in entry:
            if self.restored_last_key == key_id and self.restored_last_modifier in entry:
                chosen_modifier = self.restored_last_modifier
            else:
                chosen_modifier = next(iter(entry), "None")
        elif not entry:
            chosen_modifier = "None"
        self._set_modifier_selection(chosen_modifier)
        self._refresh_action_entry()
        self._refresh_button_colors()

    def _update_selected_key_label(self, display_label, key_id):
        profile_label = self.profile_label_by_id.get(self.current_profile_id, "")
        label = f"{display_label} ({key_id})"
        if profile_label:
            label = f"{label} · {profile_label}"
        self.selected_key_label.set(label)

    def _refresh_action_entry(self):
        if not hasattr(self, "action_entry") or not self.selected_key_id:
            return
        modifier = self.modifier_var.get()
        if modifier not in MODIFIER_OPTIONS:
            modifier = "None"
            self._set_modifier_selection("None")
        entry = self._get_profile_entry(self.selected_key_id)
        modifier_info = entry.get(modifier, {})
        enabled = True
        action_text = ""
        if isinstance(modifier_info, dict):
            action_text = modifier_info.get("action", "")
            enabled = modifier_info.get("enabled", True)
        elif isinstance(modifier_info, str):
            action_text = modifier_info
        if self.enabled_check:
            self._modifier_event_suppress = True
            self.enabled_var.set(enabled)
            self.enabled_check.select() if enabled else self.enabled_check.deselect()
            self._modifier_event_suppress = False
        self.action_entry.delete("1.0", "end")
        if action_text:
            self.action_entry.insert("1.0", action_text)

    def _get_profile_entry(self, key_id):
        return self.actions_by_profile.get(self.current_profile_id, {}).get(key_id, {})

    def _save_action(self):
        if not self.selected_key_id:
            messagebox.showinfo("Select a key", "Please choose a key before saving an action.")
            return
        action_text = self.action_entry.get("1.0", "end").strip()
        profile_actions = self.actions_by_profile.setdefault(self.current_profile_id, {})
        modifier = self.modifier_var.get()
        if modifier not in MODIFIER_OPTIONS:
            modifier = "None"
        enabled = self.enabled_var.get()
        self._set_modifier_state(modifier, action_text, enabled)
        self._refresh_script_preview()
        self.restored_last_text = action_text
        self.restored_last_modifier = modifier
        self._save_settings()
        self._refresh_button_colors()

    def _clear_assignment(self):
        if not self.selected_key_id:
            return
        profile_actions = self.actions_by_profile.get(self.current_profile_id, {})
        modifier = self.modifier_var.get()
        entry = profile_actions.get(self.selected_key_id, {})
        if isinstance(entry, dict):
            entry.pop(modifier, None)
            if not entry:
                profile_actions.pop(self.selected_key_id, None)
        self.action_entry.delete("1.0", "end")
        self.modifier_var.set("None")
        if self.enabled_check:
            self.enabled_var.set(True)
            self.enabled_check.select()
        self._refresh_script_preview()
        self.restored_last_text = ""
        self.restored_last_modifier = "None"
        self._save_settings()
        self._refresh_button_colors()

    def _save_settings(self):
        clean_actions = {}
        for profile_id, actions in self.actions_by_profile.items():
            cleaned = {}
            for key, entry in actions.items():
                if not isinstance(key, str):
                    continue
                if not isinstance(entry, dict):
                    continue
                trimmed = {}
                for modifier, modifier_data in entry.items():
                    if (
                        isinstance(modifier, str)
                        and modifier in MODIFIER_OPTIONS
                        and isinstance(modifier_data, dict)
                    ):
                        action_text = modifier_data.get("action", "")
                        enabled = modifier_data.get("enabled", True)
                        if not isinstance(action_text, str):
                            continue
                        text = action_text.strip()
                        if not text and enabled:
                            continue
                        trimmed[modifier] = {"action": text, "enabled": bool(enabled)}
                if trimmed:
                    cleaned[key] = trimmed
            if cleaned:
                clean_actions[profile_id] = cleaned
        last_text = ""
        if hasattr(self, "action_entry"):
            last_text = self.action_entry.get("1.0", "end").strip()
        payload = {
            "actions": clean_actions,
            "last_key": self.selected_key_id,
            "last_profile": self.current_profile_id,
            "last_text": last_text,
            "last_modifier": self.restored_last_modifier,
        }
        temp_path = self.settings_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
            os.replace(temp_path, self.settings_path)
        except OSError as exc:
            messagebox.showerror(
                "Save settings failed",
                f"Couldn't write {self.settings_path.name}:\n{exc}",
            )

    def _on_close(self):
        self._save_settings()
        self.destroy()

    def _refresh_script_preview(self):
        script = self._build_script_text()
        self.preview_box.configure(state="normal")
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", script)
        self.preview_box.configure(state="disabled")

    def _key_has_binding(self, key_id):
        entry = self.actions_by_profile.get(self.current_profile_id, {}).get(key_id, {})
        if not isinstance(entry, dict):
            return False
        for modifier_data in entry.values():
            if isinstance(modifier_data, dict):
                enabled = modifier_data.get("enabled", True)
                action_text = modifier_data.get("action", "")
                if enabled and isinstance(action_text, str) and action_text.strip():
                    return True
        return False

    def _refresh_button_colors(self):
        for key_id, buttons in self.key_buttons.items():
            state = KEY_BIND_COLOR if self._key_has_binding(key_id) else KEY_DEFAULT_BUTTON_BG
            for btn in buttons:
                btn.configure(bg=state)
        if self.active_button:
            self.active_button.configure(bg="#d4e0ff")

    def _build_script_text(self):
        lines = list(self.header_lines)
        
        for profile in self.keyboard_profiles:
            profile_id = profile["id"]
            actions = self.actions_by_profile.get(profile_id, {})
            valid_actions = {}
            for key, entry in actions.items():
                if not isinstance(entry, dict):
                    continue
                trimmed = {}
                for modifier, modifier_data in entry.items():
                    if modifier not in MODIFIER_OPTIONS:
                        continue
                    if not isinstance(modifier_data, dict):
                        continue
                    action_text = modifier_data.get("action", "")
                    enabled = modifier_data.get("enabled", True)
                    if not isinstance(action_text, str):
                        continue
                    text = action_text.strip()
                    if not text and enabled:
                        continue
                    trimmed[modifier] = {"action": text, "enabled": bool(enabled)}
                if trimmed:
                    valid_actions[key] = trimmed
            if not valid_actions:
                continue
            label = profile.get("label", profile_id)
            lines.append(f"; {label}")
            condition = profile.get("condition", "").strip()
            if condition:
                lines.append(f"#if {condition}")
            for key_id in sorted(valid_actions):
                entry = valid_actions[key_id]
                ahk_key = KEY_NAME_OVERRIDES.get(key_id, key_id.upper())
                for modifier in sorted(entry.keys()):
                    modifier_entry = entry[modifier]
                    if not isinstance(modifier_entry, dict):
                        continue
                    enabled = bool(modifier_entry.get("enabled", True))
                    action_text = modifier_entry.get("action", "").strip()
                    if not enabled or not action_text:
                        continue
                    prefix = MODIFIER_PREFIX.get(modifier, "")
                    hotkey = f"{prefix}{ahk_key}" if prefix else ahk_key
                    lines.append(f"{hotkey}::")
                    for action_line in action_text.splitlines():
                        lines.append(f"    {action_line}")
                    lines.append("return")
                    lines.append("")
            if condition:
                lines.append("#if")
            lines.append("")
        return "\n".join(lines).rstrip()

    def _export_script(self):
        script = self._build_script_text()
        if not script.strip():
            messagebox.showinfo("Empty script", "Add at least one assignment before exporting.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".ahk",
            filetypes=[("AutoHotkey script", "*.ahk"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(script)
        except OSError as exc:
            messagebox.showerror("Save failed", f"Couldn't write file:\n{exc}")
        else:
            messagebox.showinfo("Saved", f"Script written to {path}")


if __name__ == "__main__":
    app = AHKBuilder()
    app.mainloop()
