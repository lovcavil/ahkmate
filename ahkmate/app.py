from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox, scrolledtext

from .constants import (
    DEFAULT_HEADER_LINES,
    EXPORT_PATH_FILENAME,
    KEY_BIND_COLOR,
    KEY_DEFAULT_BUTTON_BG,
    KEY_NAME_OVERRIDES,
    KEY_SECTIONS,
    KEYBOARD_PROFILES_FILENAME,
    MODIFIER_ENABLED_TEXT,
    MODIFIER_OPTIONS,
    MODIFIER_PREFIX,
    SCRIPT_HEADER_FILENAME,
    SETTINGS_FILENAME,
)
from .script_builder import build_script_text
from .settings_io import load_script_header, load_settings, save_settings


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
        self.settings_path = Path(__file__).resolve().parent.parent / SETTINGS_FILENAME
        self.keyboards_path = Path(__file__).resolve().parent.parent / KEYBOARD_PROFILES_FILENAME
        self.header_path = Path(__file__).resolve().parent.parent / SCRIPT_HEADER_FILENAME
        self.export_path_path = Path(__file__).resolve().parent.parent / EXPORT_PATH_FILENAME
        self.export_path = str(Path(__file__).resolve().parent.parent / "export.ahk")
        self.restored_last_key = ""
        self.restored_last_text = ""
        self.restored_last_modifier = "None"
        self._suppress_profile_event = False
        self._modifier_event_suppress = False
        self.enabled_check = None
        self.enabled_var = tk.BooleanVar(value=True)
        self.tooltip_window = None
        self._load_keyboard_profiles()
        self.header_lines = load_script_header(self.header_path, DEFAULT_HEADER_LINES)
        self._load_settings()
        self._load_export_path()
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

    def _load_settings(self):
        settings, error = load_settings(self.settings_path, modifier_options=MODIFIER_OPTIONS)
        if error:
            messagebox.showwarning("Settings load failed", error)
            return

        self.restored_last_key = settings.last_key
        self.restored_last_text = settings.last_text
        self.restored_last_modifier = settings.last_modifier
        if settings.last_profile in self.profile_label_by_id:
            self.current_profile_id = settings.last_profile
        if not self.current_profile_id and self.keyboard_profiles:
            self.current_profile_id = self.keyboard_profiles[0]["id"]

        self.actions_by_profile = settings.actions_by_profile

    def _load_export_path(self):
        try:
            with open(self.export_path_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
                saved_path = data.get("export_path", "").strip()
                if saved_path:
                    self.export_path = saved_path
        except FileNotFoundError:
            pass
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showwarning(
                "Export path load failed",
                f"Unable to read {self.export_path_path.name}:\n{exc}",
            )

    def _save_export_path(self):
        try:
            with open(self.export_path_path, "w", encoding="utf-8") as handle:
                json.dump({"export_path": self.export_path}, handle, indent=2)
        except OSError as exc:
            messagebox.showerror(
                "Save export path failed",
                f"Couldn't write {self.export_path_path.name}:\n{exc}",
            )

    def _on_export_path_changed(self, event=None):
        new_path = self.export_path_var.get().strip()
        if new_path and new_path != self.export_path:
            self.export_path = new_path
            self._save_export_path()

    def _browse_export_path(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".ahk",
            filetypes=[("AutoHotkey script", "*.ahk"), ("All files", "*.*")],
            initialfile=Path(self.export_path).name,
            initialdir=str(Path(self.export_path).parent),
        )
        if path:
            self.export_path = path
            self.export_path_var.set(path)
            self._save_export_path()

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
                    btn.configure(command=lambda k=key_id, d=display, b=btn: self._select_key(k, d, b))
                    btn.bind("<Enter>", lambda e, k=key_id: self._on_key_hover(e, k))
                    btn.bind("<Leave>", lambda e: self._hide_tooltip())
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
        tk.Label(detail_frame, textvariable=self.selected_key_label, bg="#ffffff").pack(pady=8, padx=8)
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
        self.action_entry = scrolledtext.ScrolledText(action_frame, height=8, width=36, wrap="word")
        self.action_entry.pack(fill="both", expand=True, padx=6, pady=4)
        tk.Button(action_frame, text="Save action", command=self._save_action).pack(pady=2, padx=6, anchor="e")

        preview_frame = tk.LabelFrame(control_frame, text="Script preview", bg="#ffffff")
        preview_frame.pack(side="left", fill="both", expand=True, padx=6, pady=4)
        self.preview_box = scrolledtext.ScrolledText(preview_frame, height=12, wrap="word", state="disabled")
        self.preview_box.pack(fill="both", expand=True, padx=6, pady=(6, 2))
        button_frame = tk.Frame(preview_frame, bg="#ffffff")
        button_frame.pack(fill="x", padx=6, pady=(0, 6))
        tk.Button(button_frame, text="Export .ahk script", command=self._export_script).pack(side="left")
        tk.Button(button_frame, text="Refresh preview", command=self._refresh_script_preview).pack(side="right")
        save_to_frame = tk.Frame(preview_frame, bg="#ffffff")
        save_to_frame.pack(fill="x", padx=6, pady=(0, 6))
        tk.Label(save_to_frame, text="Save to:", bg="#ffffff").pack(side="left")
        self.export_path_var = tk.StringVar(value=self.export_path)
        export_path_entry = tk.Entry(save_to_frame, textvariable=self.export_path_var, width=40)
        export_path_entry.pack(side="left", padx=(6, 0), fill="x", expand=True)
        export_path_entry.bind("<FocusOut>", self._on_export_path_changed)
        tk.Button(save_to_frame, text="Browse...", command=self._browse_export_path).pack(side="left", padx=(6, 0))

    def _add_function_dropdown(self, parent):
        drop_frame = tk.Frame(parent, bg="#ffffff")
        drop_frame.pack(fill="x", padx=6, pady=(4, 6))
        tk.Label(drop_frame, text="Profile", bg="#ffffff").pack(side="left", padx=(4, 6))
        labels = [profile["label"] for profile in self.keyboard_profiles]
        combo = ttk.Combobox(drop_frame, textvariable=self.profile_var, values=labels, state="readonly")
        initial_label = self.profile_label_by_id.get(self.current_profile_id, labels[0] if labels else "")
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
        self._refresh_script_preview()
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
        self._hide_tooltip()
        if self.active_button:
            self.active_button.configure(relief="raised", bg=KEY_DEFAULT_BUTTON_BG)
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
        last_text = ""
        if hasattr(self, "action_entry"):
            last_text = self.action_entry.get("1.0", "end").strip()
        error = save_settings(
            self.settings_path,
            actions_by_profile=self.actions_by_profile,
            last_key=self.selected_key_id,
            last_profile=self.current_profile_id,
            last_text=last_text,
            last_modifier=self.restored_last_modifier,
            modifier_options=MODIFIER_OPTIONS,
        )
        if error:
            messagebox.showerror("Save settings failed", f"Couldn't write {self.settings_path.name}:\n{error}")

    def _on_close(self):
        self._save_settings()
        self.destroy()

    def _build_script_text(self):
        return build_script_text(
            header_lines=self.header_lines,
            keyboard_profiles=self.keyboard_profiles,
            actions_by_profile=self.actions_by_profile,
            key_name_overrides=KEY_NAME_OVERRIDES,
            modifier_prefix=MODIFIER_PREFIX,
            modifier_options=MODIFIER_OPTIONS,
        )

    def _refresh_script_preview(self):
        script = self._build_script_text()
        self.preview_box.configure(state="normal")
        self.preview_box.delete("1.0", "end")
        self.preview_box.insert("1.0", script)
        self.preview_box.configure(state="disabled")

    def _tooltip_text_for_key(self, key_id):
        entry = self._get_profile_entry(key_id)
        if not isinstance(entry, dict):
            return ""
        lines = []
        for modifier in MODIFIER_OPTIONS:
            info = entry.get(modifier, {})
            action = ""
            if isinstance(info, dict):
                enabled = info.get("enabled", True)
                if not enabled:
                    continue
                action = info.get("action", "")
            elif isinstance(info, str):
                action = info
            if not isinstance(action, str):
                continue
            text = action.strip()
            if not text:
                continue
            header = modifier if modifier != "None" else "Base"
            lines.append(f"{header}: {text.splitlines()[0]}")
        return "\n".join(lines)

    def _on_key_hover(self, event, key_id):
        text = self._tooltip_text_for_key(key_id)
        if not text:
            self._hide_tooltip()
            return
        x = event.x_root + 10
        y = event.y_root + 10
        self._show_tooltip(text, x, y)

    def _show_tooltip(self, text, x, y):
        self._hide_tooltip()
        if not text:
            return
        win = tk.Toplevel(self)
        win.wm_overrideredirect(True)
        win.attributes("-topmost", True)
        label = tk.Label(
            win,
            text=text,
            bg="#ffffe1",
            fg="#000000",
            justify="left",
            relief="solid",
            borderwidth=1,
            padx=6,
            pady=4,
        )
        label.pack()
        win.wm_geometry(f"+{x}+{y}")
        self.tooltip_window = win

    def _hide_tooltip(self):
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except tk.TclError:
                pass
            self.tooltip_window = None

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

    def _export_script(self):
        script = self._build_script_text()
        if not script.strip():
            messagebox.showinfo("Empty script", "Add at least one assignment before exporting.")
            return
        path = self.export_path_var.get().strip()
        if not path:
            messagebox.showerror("Export failed", "Please specify a save path in the 'Save to' field.")
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(script)
        except OSError as exc:
            messagebox.showerror("Save failed", f"Couldn't write file:\n{exc}")
        else:
            messagebox.showinfo("Saved", f"Script written to {path}")

