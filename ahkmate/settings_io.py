from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ActionEntry = dict[str, dict[str, Any]]
ActionsByKey = dict[str, ActionEntry]
ActionsByProfile = dict[str, ActionsByKey]


@dataclass(slots=True)
class LoadedSettings:
    last_key: str = ""
    last_text: str = ""
    last_modifier: str = "None"
    last_profile: str = ""
    actions_by_profile: ActionsByProfile = field(default_factory=dict)


def load_script_header(path: Path, default_lines: list[str]) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return list(default_lines)

    header = data.get("header")
    if not isinstance(header, list) or not all(isinstance(line, str) for line in header):
        return list(default_lines)
    return header


def load_settings(path: Path, *, modifier_options: list[str]) -> tuple[LoadedSettings, str | None]:
    settings = LoadedSettings()
    if not path.exists():
        return settings, None

    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        return settings, f"Unable to read {path.name}:\n{exc}"

    settings.last_key = str(data.get("last_key", "") or "")
    last_text = data.get("last_text")
    settings.last_text = last_text if isinstance(last_text, str) else ""

    settings.last_modifier = str(data.get("last_modifier", "None") or "None")
    if settings.last_modifier not in modifier_options:
        settings.last_modifier = "None"

    settings.last_profile = str(data.get("last_profile", "") or "")

    raw_actions = data.get("actions", {})
    sanitized: ActionsByProfile = {}
    if isinstance(raw_actions, dict):
        for profile_id, action_data in raw_actions.items():
            if not isinstance(profile_id, str) or not isinstance(action_data, dict):
                continue
            cleaned: ActionsByKey = {}
            for key, entry in action_data.items():
                if not isinstance(key, str):
                    continue
                modifiers: ActionEntry = {}
                if isinstance(entry, dict):
                    for modifier_key, modifier_value in entry.items():
                        if (
                            isinstance(modifier_key, str)
                            and modifier_key in modifier_options
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

    settings.actions_by_profile = sanitized
    return settings, None


def save_settings(
    path: Path,
    *,
    actions_by_profile: ActionsByProfile,
    last_key: str,
    last_profile: str,
    last_text: str,
    last_modifier: str,
    modifier_options: list[str],
) -> str | None:
    clean_actions: ActionsByProfile = {}
    for profile_id, actions in actions_by_profile.items():
        if not isinstance(profile_id, str) or not isinstance(actions, dict):
            continue
        cleaned: ActionsByKey = {}
        for key, entry in actions.items():
            if not isinstance(key, str) or not isinstance(entry, dict):
                continue
            trimmed: ActionEntry = {}
            for modifier, modifier_data in entry.items():
                if (
                    isinstance(modifier, str)
                    and modifier in modifier_options
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

    payload = {
        "actions": clean_actions,
        "last_key": last_key,
        "last_profile": last_profile,
        "last_text": last_text,
        "last_modifier": last_modifier,
    }

    temp_path = path.with_suffix(".tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
        os.replace(temp_path, path)
    except OSError as exc:
        return str(exc)
    return None

