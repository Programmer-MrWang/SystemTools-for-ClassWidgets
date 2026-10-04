from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4


# The registries are shared by the editor and runtime.  A provider can expose
# its own settings editor without turning the page into another flat text form.
TRIGGER_TYPES = {
    "startup": {"name": "应用启动时", "icon": "ic_fluent_arrow_enter_20_regular", "editor": "none"},
    "interval": {"name": "间隔触发", "icon": "ic_fluent_arrow_repeat_all_20_regular", "editor": "number"},
    "status": {"name": "课程状态变化时", "icon": "ic_fluent_clock_20_regular", "editor": "text"},
    "subject": {"name": "当前科目变化时", "icon": "ic_fluent_book_20_regular", "editor": "text"},
}

RULE_TYPES = {
    "always": {"name": "始终满足", "icon": "ic_fluent_checkmark_20_regular", "editor": "none"},
    "status": {"name": "当前课程状态", "icon": "ic_fluent_clock_20_regular", "editor": "text"},
    "weekday": {"name": "星期", "icon": "ic_fluent_calendar_week_numbers_20_regular", "editor": "number"},
    "time_range": {"name": "是否在某时间段", "icon": "ic_fluent_history_20_regular", "editor": "time_range"},
    "process": {"name": "程序正在运行", "icon": "ic_fluent_window_20_regular", "editor": "text"},
}

ACTION_TYPES = {
    "notify": {"name": "显示提醒", "icon": "ic_fluent_alert_20_regular", "editor": "notify", "revertable": False},
    "log": {"name": "写入日志", "icon": "ic_fluent_document_text_20_regular", "editor": "text", "revertable": False},
    "open_url": {"name": "打开网址", "icon": "ic_fluent_globe_20_regular", "editor": "text", "revertable": False},
    "launch_process": {"name": "运行程序", "icon": "ic_fluent_play_20_regular", "editor": "text", "revertable": False},
    "switch_schedule": {"name": "切换课表", "icon": "ic_fluent_calendar_ltr_20_regular", "editor": "text", "revertable": True},
    "set_config": {"name": "修改应用设置", "icon": "ic_fluent_settings_20_regular", "editor": "text", "revertable": True},
}


def new_id() -> str:
    return str(uuid4())


def default_trigger() -> dict[str, Any]:
    return {"id": new_id(), "type": "startup", "settings": {}}


def default_rule() -> dict[str, Any]:
    return {"id": new_id(), "type": "always", "reversed": False, "settings": {}}


def default_group() -> dict[str, Any]:
    return {"id": new_id(), "mode": "all", "reversed": False, "enabled": True, "rules": [default_rule()], "state": 0}


def default_action() -> dict[str, Any]:
    return {
        "id": new_id(),
        "type": "notify",
        "settings": {"title": "SystemTools 自动化", "message": "自动化已执行"},
        "state": "normal",
        "progress": None,
        "error": "",
    }


def new_automation(name: str = "新自动化") -> dict[str, Any]:
    return {
        "id": new_id(),
        "name": name,
        "enabled": True,
        "triggers": [default_trigger()],
        "ruleset": {"mode": "all", "reversed": False, "groups": [default_group()], "state": 0},
        "is_condition_enabled": False,
        "action_set": {"name": name, "enabled": True, "revert_enabled": True, "status": "normal", "actions": [default_action()]},
        "restore_state": {"active": False, "captured_at": "", "entries": []},
        "cooldown": 0,
        "last_run": "",
        "run_count": 0,
    }


def _settings_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def normalize_automation(value: Any) -> dict[str, Any]:
    """Normalize both the old flat format and the nested workflow format."""
    source = dict(value) if isinstance(value, dict) else {}
    name = str(source.get("name") or "新自动化")
    item = new_automation(name)
    item["id"] = str(source.get("id") or item["id"])
    item["name"] = name
    item["enabled"] = bool(source.get("enabled", True))
    item["cooldown"] = max(0, int(source.get("cooldown", 0) or 0))
    item["run_count"] = max(0, int(source.get("run_count", 0) or 0))
    item["last_run"] = str(source.get("last_run") or "")
    item["is_condition_enabled"] = bool(source.get("is_condition_enabled", source.get("condition_enabled", False)))

    raw_triggers = source.get("triggers") if isinstance(source.get("triggers"), list) else []
    triggers = []
    for raw in raw_triggers:
        raw = dict(raw) if isinstance(raw, dict) else {}
        trigger = default_trigger()
        trigger.update(raw)
        trigger["id"] = str(raw.get("id") or trigger["id"])
        trigger["type"] = str(raw.get("type") or "startup")
        settings = _settings_dict(raw.get("settings"))
        if raw.get("value") not in (None, "") and "value" not in settings:
            settings["value"] = raw.get("value")
        trigger["settings"] = settings
        trigger.pop("value", None)
        triggers.append(trigger)
    item["triggers"] = triggers if isinstance(source.get("triggers"), list) else [default_trigger()]

    raw_ruleset = source.get("ruleset") if isinstance(source.get("ruleset"), dict) else {}
    raw_groups = raw_ruleset.get("groups") if isinstance(raw_ruleset.get("groups"), list) else None
    if raw_groups is None:
        flat_rules = source.get("rules") if isinstance(source.get("rules"), list) else []
        raw_groups = [{"mode": "any" if str(source.get("rules_mode", "all")).lower() == "any" else "all", "reversed": False, "enabled": True, "rules": flat_rules}]
    groups = []
    for raw_group in raw_groups:
        raw_group = dict(raw_group) if isinstance(raw_group, dict) else {}
        group = default_group()
        group.update(raw_group)
        group["id"] = str(raw_group.get("id") or group["id"])
        group["mode"] = "any" if str(raw_group.get("mode", "all")).lower() == "any" else "all"
        group["reversed"] = bool(raw_group.get("reversed", False))
        group["enabled"] = bool(raw_group.get("enabled", True))
        rules = []
        raw_rule_values = raw_group.get("rules") if isinstance(raw_group.get("rules"), list) else []
        for raw_rule in raw_rule_values:
            raw_rule = dict(raw_rule) if isinstance(raw_rule, dict) else {}
            rule = default_rule()
            rule.update(raw_rule)
            rule["id"] = str(raw_rule.get("id") or rule["id"])
            rule["type"] = str(raw_rule.get("type") or "always")
            rule["reversed"] = bool(raw_rule.get("reversed", False))
            settings = _settings_dict(raw_rule.get("settings"))
            if raw_rule.get("value") not in (None, "") and "value" not in settings:
                settings["value"] = raw_rule.get("value")
            rule["settings"] = settings
            rule["state"] = int(raw_rule.get("state", 0) or 0)
            rule.pop("value", None)
            rules.append(rule)
        group["rules"] = rules if isinstance(raw_group.get("rules"), list) else [default_rule()]
        group["state"] = int(raw_group.get("state", 0) or 0)
        groups.append(group)
    item["ruleset"] = {
        "mode": "any" if str(raw_ruleset.get("mode", source.get("rules_mode", "all"))).lower() == "any" else "all",
        "reversed": bool(raw_ruleset.get("reversed", source.get("rules_reversed", False))),
        "groups": groups,
        "state": int(raw_ruleset.get("state", 0) or 0),
    }

    raw_action_set = source.get("action_set") if isinstance(source.get("action_set"), dict) else {}
    old_actions = source.get("actions") if isinstance(source.get("actions"), list) else []
    raw_actions = raw_action_set.get("actions") if isinstance(raw_action_set.get("actions"), list) else old_actions
    actions = []
    for raw_action in raw_actions:
        raw_action = dict(raw_action) if isinstance(raw_action, dict) else {}
        action = default_action()
        action.update(raw_action)
        action["id"] = str(raw_action.get("id") or action["id"])
        action["type"] = str(raw_action.get("type") or "notify")
        settings = _settings_dict(raw_action.get("settings"))
        if raw_action.get("value") not in (None, "") and not settings:
            settings["value"] = raw_action["value"]
        if raw_action.get("title") and "title" not in settings:
            settings["title"] = raw_action["title"]
        action["settings"] = settings
        action["error"] = str(raw_action.get("error") or "")
        for legacy_key in ("value", "title", "revert"):
            action.pop(legacy_key, None)
        actions.append(action)
    item["action_set"] = {
        "name": str(raw_action_set.get("name") or name),
        "enabled": bool(raw_action_set.get("enabled", item["enabled"])),
        "revert_enabled": bool(raw_action_set.get("revert_enabled", source.get("revert_enabled", True))),
        "status": str(raw_action_set.get("status") or "normal"),
        "actions": actions if isinstance(raw_action_set.get("actions"), list) or isinstance(source.get("actions"), list) else [default_action()],
    }

    raw_restore = source.get("restore_state")
    if isinstance(raw_restore, dict):
        entries = raw_restore.get("entries")
        item["restore_state"] = {"active": bool(raw_restore.get("active", False)), "captured_at": str(raw_restore.get("captured_at") or ""), "entries": [dict(entry) for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []}
    return item


def format_last_run(value: str) -> str:
    if not value:
        return "尚未执行"
    try:
        return datetime.fromisoformat(value).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return value
