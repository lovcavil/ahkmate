from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def build_script_text(
    *,
    header_lines: Sequence[str],
    keyboard_profiles: Sequence[Mapping[str, Any]],
    actions_by_profile: Mapping[str, Any],
    key_name_overrides: Mapping[str, str],
    modifier_prefix: Mapping[str, str],
    modifier_options: Sequence[str],
) -> str:
    lines = list(header_lines)

    for profile in keyboard_profiles:
        profile_id = str(profile.get("id", "")).strip()
        if not profile_id:
            continue
        actions = actions_by_profile.get(profile_id, {})
        valid_actions: dict[str, dict[str, dict[str, Any]]] = {}

        if isinstance(actions, dict):
            for key, entry in actions.items():
                if not isinstance(entry, dict):
                    continue
                trimmed: dict[str, dict[str, Any]] = {}
                for modifier, modifier_data in entry.items():
                    if modifier not in modifier_options:
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
                if trimmed and isinstance(key, str):
                    valid_actions[key] = trimmed

        if not valid_actions:
            continue

        label = str(profile.get("label") or profile_id)
        lines.append(f"; {label}")

        condition = str(profile.get("condition", "")).strip()
        if condition:
            lines.append(f"#if {condition}")

        for key_id in sorted(valid_actions):
            entry = valid_actions[key_id]
            ahk_key = key_name_overrides.get(key_id, key_id.upper())
            for modifier in sorted(entry.keys()):
                modifier_entry = entry[modifier]
                if not isinstance(modifier_entry, dict):
                    continue
                enabled = bool(modifier_entry.get("enabled", True))
                action_text = str(modifier_entry.get("action", "")).strip()
                if not enabled or not action_text:
                    continue
                prefix = modifier_prefix.get(modifier, "")
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

