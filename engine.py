from __future__ import annotations

import json
import shlex
import subprocess
import webbrowser
from datetime import datetime, time
from pathlib import Path
from time import monotonic
from typing import Any, Optional

from loguru import logger
from PySide6.QtCore import QObject, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices

from models import normalize_automation


class AutomationEngine(QObject):
    """Small, self-contained workflow engine owned by the plugin.

    The host exposes runtime signals but deliberately does not expose its own
    automation editor. This engine translates those signals into trigger events,
    evaluates the workflow's rules, and executes actions in order.
    """

    changed = Signal()
    activityChanged = Signal(str)
    RESTORABLE_ACTIONS = {"set_config", "switch_schedule"}

    def __init__(self, api, config, provider=None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.api = api
        self.config = config
        self.provider = provider
        self._running: set[str] = set()
        self._startup_pending = True
        self._last_status = ""
        self._last_subject = ""
        self._process_cache: dict[str, tuple[float, bool]] = {}

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._tick)
        self.timer.start()
        self.api.runtime.updated.connect(self._on_runtime_updated)
        self.api.runtime.statusChanged.connect(self._on_status_changed)

    @property
    def automations(self) -> list[dict[str, Any]]:
        return [normalize_automation(item) for item in (self.config.automations or [])]

    def _save(self, values: list[dict[str, Any]]) -> None:
        self.config.automations = values
        try:
            self.config.save()
        except Exception as error:
            logger.warning("Failed to save automation config: {}", error)
        self.changed.emit()

    def stop(self) -> None:
        self.timer.stop()
        self._running.clear()

    def _tick(self) -> None:
        if self._startup_pending:
            self._startup_pending = False
            self._consider("startup")
        self._consider("interval")
        self._restore_scan()

    def _on_runtime_updated(self) -> None:
        self._consider("interval")
        subject = self.api.runtime.current_subject or {}
        subject_key = str(subject.get("id") or subject.get("name") or "")
        if subject_key != self._last_subject:
            self._last_subject = subject_key
            self._consider("subject", subject_key)
            self._restore_scan("subject", subject_key)

    def _on_status_changed(self, status: str) -> None:
        self._last_status = str(status or "")
        self._consider("status", self._last_status)
        self._restore_scan("status", self._last_status)

    def _consider(self, event: str, value: str = "") -> None:
        if not self.config.automation_enabled:
            return
        for automation in self.automations:
            if not automation.get("enabled") or not automation.get("action_set", {}).get("enabled", True) or automation["id"] in self._running:
                continue
            if not self._trigger_matches(automation, event, value):
                continue
            if not self._rules_match(automation):
                continue
            if event == "interval" and not self._interval_due(automation):
                continue
            self.run_automation(automation["id"])

    def _trigger_matches(self, automation: dict[str, Any], event: str, value: str) -> bool:
        for trigger in automation.get("triggers", []):
            kind = str(trigger.get("type") or "")
            settings = trigger.get("settings") if isinstance(trigger.get("settings"), dict) else {}
            expected = str(settings.get("value", settings.get("status", settings.get("subject", ""))) or "").strip()
            if kind == event:
                if kind == "status" and expected and expected != value:
                    continue
                if kind == "subject" and expected and expected.lower() not in value.lower():
                    continue
                return True
        return False

    def _interval_due(self, automation: dict[str, Any]) -> bool:
        interval = 0.0
        for trigger in automation.get("triggers", []):
            if trigger.get("type") == "interval":
                try:
                    settings = trigger.get("settings") if isinstance(trigger.get("settings"), dict) else {}
                    interval = max(interval, float(settings.get("seconds", settings.get("value", 0)) or 0))
                except (TypeError, ValueError):
                    interval = 0.0
        if interval <= 0:
            return False
        last = self._parse_datetime(automation.get("last_run"))
        return last is None or (datetime.now().astimezone() - last).total_seconds() >= interval

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value))
            return parsed.astimezone() if parsed.tzinfo else parsed.astimezone()
        except (TypeError, ValueError):
            return None

    def _rules_match(self, automation: dict[str, Any]) -> bool:
        # A workflow can keep its rule editor configured while the whole
        # condition section is disabled.  In that state ClassIsland treats
        # the ruleset as bypassed and the trigger alone is sufficient.
        if not automation.get("is_condition_enabled", False):
            automation.setdefault("ruleset", {})["state"] = 0
            return True
        ruleset = automation.get("ruleset", {})
        group_results = []
        for group in ruleset.get("groups", []):
            group["state"] = 0
            for rule in group.get("rules", []):
                rule["state"] = 0
            if not group.get("enabled", True):
                continue
            results = []
            for rule in group.get("rules", []):
                result = self._rule_match(rule) ^ bool(rule.get("reversed", False))
                rule["state"] = 2 if result else 1
                results.append(result)
            if not results:
                continue
            result = any(results) if group.get("mode") == "any" else all(results)
            result = (not result) if group.get("reversed") else result
            group["state"] = 2 if result else 1
            group_results.append(result)
        if not group_results:
            ruleset["state"] = 0
            return False
        result = any(group_results) if ruleset.get("mode") == "any" else all(group_results)
        result = (not result) if ruleset.get("reversed") else result
        ruleset["state"] = 2 if result else 1
        return result

    def _rule_match(self, rule: dict[str, Any]) -> bool:
        kind = str(rule.get("type") or "always")
        settings = rule.get("settings") if isinstance(rule.get("settings"), dict) else {}
        value = str(settings.get("value", "") or "").strip()
        runtime = self.api.runtime
        if kind == "always":
            return True
        if kind == "status":
            return not value or runtime.current_status == value
        if kind == "weekday":
            try:
                return runtime.current_day_of_week == int(settings.get("day", value))
            except (TypeError, ValueError):
                return False
        if kind == "time_range":
            start = str(settings.get("start", ""))
            end = str(settings.get("end", ""))
            return self._in_time_range(f"{start}-{end}" if start or end else value, runtime.current_time.time())
        if kind == "process":
            return self._process_running(value)
        return False

    @staticmethod
    def _in_time_range(value: str, current: time) -> bool:
        try:
            start_text, end_text = [part.strip() for part in value.split("-", 1)]
            start = datetime.strptime(start_text, "%H:%M").time()
            end = datetime.strptime(end_text, "%H:%M").time()
        except (ValueError, TypeError):
            return False
        if start <= end:
            return start <= current <= end
        return current >= start or current <= end

    def _process_running(self, name: str) -> bool:
        if not name:
            return False
        now = monotonic()
        cached = self._process_cache.get(name.lower())
        if cached and now - cached[0] < 0.25:
            return cached[1]
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {name}"],
                capture_output=True,
                text=True,
                timeout=2,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            running = name.lower() in result.stdout.lower()
        except (OSError, subprocess.SubprocessError):
            running = False
        self._process_cache[name.lower()] = (now, running)
        return running

    def run_now(self, automation_id: str) -> bool:
        return self.run_automation(automation_id, force=True)

    def run_automation(self, automation_id: str, force: bool = False) -> bool:
        automation = next((item for item in self.automations if item["id"] == automation_id), None)
        if not automation or automation_id in self._running:
            return False
        if not force and not self._cooldown_due(automation):
            return False
        self._running.add(automation_id)
        action_set = automation.setdefault("action_set", {})
        action_set["status"] = "invoking"
        try:
            for action in action_set.get("actions", []):
                if automation_id not in self._running:
                    break
                action["state"] = "working"
                action["error"] = ""
                self._capture_restore_value(automation, action)
                try:
                    self._execute_action(action)
                except Exception as error:
                    action["error"] = str(error)
                    raise
                finally:
                    action["state"] = "completed"
            now = datetime.now().astimezone().isoformat(timespec="milliseconds")
            updated = []
            for item in self.automations:
                if item["id"] == automation_id:
                    item["last_run"] = now
                    item["run_count"] = int(item.get("run_count", 0)) + 1
                updated.append(item)
            self._save(updated)
            action_set["status"] = "is_on" if action_set.get("revert_enabled") else "normal"
            self.activityChanged.emit(f"{automation.get('name', '自动化')}：执行完成")
            return True
        except Exception as error:
            logger.exception("Automation execution failed: {}", error)
            self.activityChanged.emit(f"{automation.get('name', '自动化')}：执行失败：{error}")
            return False
        finally:
            if automation.get("action_set", {}).get("status") == "invoking":
                automation["action_set"]["status"] = "normal"
            self._running.discard(automation_id)

    def _cooldown_due(self, automation: dict[str, Any]) -> bool:
        cooldown = max(0, int(automation.get("cooldown", 0) or 0))
        last = self._parse_datetime(automation.get("last_run"))
        return cooldown <= 0 or last is None or (datetime.now().astimezone() - last).total_seconds() >= cooldown

    def stop_automation(self, automation_id: str) -> None:
        self._running.discard(automation_id)
        for item in self.automations:
            if item.get("id") == automation_id:
                item.setdefault("action_set", {})["status"] = "normal"
        self.activityChanged.emit("已请求停止当前行动")

    def revert_automation(self, automation_id: str) -> bool:
        automation = next((item for item in self.automations if item["id"] == automation_id), None)
        if not automation:
            return False
        try:
            state = automation.get("restore_state") or {}
            entries = state.get("entries") if isinstance(state, dict) else None
            if isinstance(entries, list) and entries:
                for entry in reversed(entries):
                    self._restore_entry(entry)
            elif automation.get("action_set", {}).get("revert_enabled"):
                # 兼容早期版本手工填写的恢复参数。
                for action in reversed(automation.get("action_set", {}).get("actions", [])):
                    value = str((action.get("settings") or {}).get("revert") or "")
                    if value:
                        self._execute_action(action, value)
            else:
                return False

            updated = []
            for item in self.automations:
                if item["id"] == automation_id:
                    item["restore_state"] = {"active": False, "captured_at": "", "entries": []}
                    item.setdefault("action_set", {})["status"] = "normal"
                updated.append(item)
            self._save(updated)
            self.activityChanged.emit(f"{automation.get('name', '自动化')}：已恢复")
            return True
        except Exception as error:
            logger.exception("Automation revert failed: {}", error)
            self.activityChanged.emit(f"{automation.get('name', '自动化')}：恢复失败：{error}")
            return False

    def _restore_scan(self, event: str = "", value: str = "") -> None:
        """条件失效或逆事件发生时，自动恢复仍处于活动状态的自动化。"""
        for automation in self.automations:
            if automation.get("id") in self._running:
                continue
            state = automation.get("restore_state") or {}
            if not isinstance(state, dict) or not state.get("active"):
                continue
            invalidated = not automation.get("enabled") or not self._rules_match(automation)
            if event:
                invalidated = invalidated or self._restore_event_invalidated(automation, event, value)
            if invalidated:
                self.revert_automation(automation["id"])

    @staticmethod
    def _restore_event_invalidated(automation: dict[str, Any], event: str, value: str) -> bool:
        for trigger in automation.get("triggers", []):
            kind = str(trigger.get("type") or "")
            settings = trigger.get("settings") if isinstance(trigger.get("settings"), dict) else {}
            expected = str(settings.get("value", settings.get("status", settings.get("subject", ""))) or "").strip()
            if kind == "status" and event == "status" and expected and expected != value:
                return True
            if kind == "subject" and event == "subject" and expected and expected.lower() not in value.lower():
                return True
        return False

    def _persist_automation(self, automation: dict[str, Any]) -> None:
        values = [
            automation if item.get("id") == automation.get("id") else item
            for item in self.automations
        ]
        self._save(values)

    def _capture_restore_value(self, automation: dict[str, Any], action: dict[str, Any]) -> None:
        if not automation.get("action_set", {}).get("revert_enabled"):
            return
        kind = str(action.get("type") or "")
        if kind not in self.RESTORABLE_ACTIONS:
            return

        state = automation.setdefault("restore_state", {})
        if not isinstance(state, dict):
            state = {"active": False, "captured_at": "", "entries": []}
            automation["restore_state"] = state
        entries = state.setdefault("entries", [])
        if not isinstance(entries, list):
            entries = []
            state["entries"] = entries

        if kind == "set_config":
            expression = str((action.get("settings") or {}).get("value", ""))
            path, _ = self._split_config_expression(expression)
            if not path or any(entry.get("key") == f"config:{path}" for entry in entries):
                return
            exists, original = self._read_config_value(path)
            if not exists:
                logger.warning("无法记录配置原值，路径不存在: {}", path)
                return
            entries.append({"key": f"config:{path}", "kind": "config", "path": path, "value": original})
        elif kind == "switch_schedule":
            if any(entry.get("key") == "schedule:current" for entry in entries):
                return
            current = getattr(self.api.globalconfig.configs.schedule, "current_schedule", "")
            current = getattr(current, "value", current)
            entries.append({"key": "schedule:current", "kind": "schedule", "value": str(current or "")})

        state["active"] = True
        state["captured_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        # 在执行行动前落盘，主程序意外退出时仍能在下次启动恢复。
        self._persist_automation(automation)

    def _restore_entry(self, entry: dict[str, Any]) -> None:
        kind = str(entry.get("kind") or "")
        if kind == "config":
            self._write_config_value(str(entry.get("path") or ""), entry.get("value"))
        elif kind == "schedule":
            original = str(entry.get("value") or "")
            if original:
                self.api.schedulemanagement.switch(original)
                try:
                    self.api.globalconfig.configs.save()
                except Exception as error:
                    logger.warning("保存恢复后的课表配置失败: {}", error)

    def _execute_action(self, action: dict[str, Any], override_value: Optional[str] = None) -> None:
        kind = str(action.get("type") or "")
        settings = action.get("settings") if isinstance(action.get("settings"), dict) else {}
        value = str(settings.get("value", settings.get("message", "")) if override_value is None else override_value or "")
        title = str(settings.get("title") or "SystemTools 自动化")
        if kind == "notify":
            if self.provider:
                self.provider.push(0, title, value, 5000, True)
        elif kind == "log":
            logger.info("Automation: {}", value)
        elif kind == "open_url":
            url = QUrl(value)
            if url.isValid() and url.scheme():
                QDesktopServices.openUrl(url)
            else:
                webbrowser.open(value)
        elif kind == "launch_process":
            args = shlex.split(value, posix=False)
            if args:
                subprocess.Popen(args, cwd=str(Path.cwd()))
        elif kind == "switch_schedule":
            self.api.schedulemanagement.switch(value)
        elif kind == "set_config":
            self._set_config(value)

    def _set_config(self, expression: str) -> None:
        path, raw = self._split_config_expression(expression)
        if not path:
            return
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        self._write_config_value(path, value)

    @staticmethod
    def _split_config_expression(expression: str) -> tuple[str, str]:
        if "=" not in expression:
            return "", ""
        path, raw = [part.strip() for part in expression.split("=", 1)]
        if not path or path.startswith("plugins.configs"):
            return "", ""
        return path, raw

    def _read_config_value(self, path: str) -> tuple[bool, Any]:
        if not path or path.startswith("plugins.configs"):
            return False, None
        target: Any = self.api.globalconfig.configs
        for bit in path.split("."):
            if isinstance(target, dict):
                if bit not in target:
                    return False, None
                target = target[bit]
            elif hasattr(target, bit):
                target = getattr(target, bit)
            else:
                return False, None
        value = getattr(target, "value", target)
        try:
            json.dumps(value)
        except TypeError:
            return False, None
        return True, value

    def _write_config_value(self, path: str, value: Any) -> bool:
        if not path or path.startswith("plugins.configs"):
            return False
        target: Any = self.api.globalconfig.configs
        bits = path.split(".")
        for bit in bits[:-1]:
            if isinstance(target, dict):
                target = target.get(bit)
            else:
                target = getattr(target, bit, None)
            if target is None:
                return False
        last = bits[-1]
        if isinstance(target, dict):
            target[last] = value
        elif hasattr(target, last):
            setattr(target, last, value)
        else:
            return False
        try:
            self.api.globalconfig.configs.save()
        except Exception as error:
            logger.warning("保存恢复后的全局配置失败: {}", error)
        return True
