from __future__ import annotations

from copy import deepcopy
from typing import Any

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from loguru import logger

from engine import AutomationEngine
from models import ACTION_TYPES, RULE_TYPES, TRIGGER_TYPES, default_action, default_group, default_rule, default_trigger, new_automation, normalize_automation, new_id


class AutomationBackend(QObject):
    """Stable QObject facade for the ClassIsland-style editor."""

    changed = Signal()
    undoAvailableChanged = Signal()

    def __init__(self, config, engine: AutomationEngine, parent: QObject | None = None):
        super().__init__(parent)
        self.config = config
        self.engine = engine
        self._selected_index = 0 if config.automations else -1
        self._status_text = "就绪"
        self._undo_item: dict[str, Any] | None = None
        self._undo_index = -1
        self._undo_timer = QTimer(self)
        self._undo_timer.setSingleShot(True)
        self._undo_timer.setInterval(10_000)
        self._undo_timer.timeout.connect(self._clear_undo)
        self.engine.changed.connect(self.changed)
        self.engine.activityChanged.connect(self._on_activity)

    def _on_activity(self, text: str) -> None:
        self._status_text = str(text)
        self.changed.emit()

    def _items(self) -> list[dict[str, Any]]:
        return [normalize_automation(item) for item in (self.config.automations or [])]

    def _commit(self, items: list[dict[str, Any]]) -> None:
        self.config.automations = [normalize_automation(item) for item in items]
        self.config.save()
        self.changed.emit()

    def _selected(self, items: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
        values = self._items() if items is None else items
        if 0 <= self._selected_index < len(values):
            return values[self._selected_index]
        return None

    def _update_selected(self, updater) -> None:
        values = self._items()
        item = self._selected(values)
        if item is None:
            return
        before = deepcopy(item)
        updater(item)
        if item != before:
            self._commit(values)

    def _update_nested(self, section: str, index: int, updater, group_index: int | None = None) -> None:
        values = self._items()
        item = self._selected(values)
        if item is None:
            return
        if section == "triggers":
            entries = item["triggers"]
        elif section == "groups":
            entries = item["ruleset"]["groups"]
        elif section == "rules":
            groups = item["ruleset"]["groups"]
            if group_index is None or not (0 <= group_index < len(groups)):
                return
            entries = groups[group_index]["rules"]
        else:
            entries = item["action_set"]["actions"]
        if not (0 <= index < len(entries)):
            return
        before = deepcopy(entries[index])
        updater(entries[index])
        if entries[index] != before:
            self._commit(values)

    @Property(bool, notify=changed)
    def automationEnabled(self) -> bool:
        return bool(self.config.automation_enabled)

    @Property(str, notify=changed)
    def configPath(self) -> str:
        return str(self.config.path)

    @Property(list, notify=changed)
    def profileNames(self) -> list[str]:
        return ["默认" if path == self.config.base_path else path.stem for path in self.config.profiles()]

    @Property(int, notify=changed)
    def profileIndex(self) -> int:
        return self.config.profiles().index(self.config.path)

    @Slot()
    def reportPageReady(self) -> None:
        logger.info("自动化设置页已连接后端，配置: {}", self.config.path)

    @Slot()
    def createProfile(self) -> None:
        self.config.create_profile()
        self._selected_index = -1
        self._clear_undo()
        self.changed.emit()
        logger.info("已新建自动化配置方案: {}", self.config.path)

    @Slot(int)
    def selectProfile(self, index: int) -> None:
        profiles = self.config.profiles()
        if 0 <= index < len(profiles) and self.config.switch_profile(profiles[index]):
            self._selected_index = 0 if self.config.automations else -1
            self._clear_undo()
            self.changed.emit()
            logger.info("已切换自动化配置方案: {}", self.config.path)

    @Property(list, notify=changed)
    def automations(self) -> list[dict[str, Any]]:
        return self._items()

    @Property(int, notify=changed)
    def selectedIndex(self) -> int:
        return self._selected_index

    @Property(dict, notify=changed)
    def selectedAutomation(self) -> dict[str, Any]:
        return deepcopy(self._selected() or {})

    @Property(list, notify=changed)
    def selectedTriggers(self) -> list[dict[str, Any]]:
        return deepcopy((self._selected() or {}).get("triggers", []))

    @Property(dict, notify=changed)
    def selectedRuleset(self) -> dict[str, Any]:
        return deepcopy((self._selected() or {}).get("ruleset", {}))

    @Property(list, notify=changed)
    def selectedGroups(self) -> list[dict[str, Any]]:
        groups = deepcopy((self._selected() or {}).get("ruleset", {}).get("groups", []))
        for group_index, group in enumerate(groups):
            group["_index"] = group_index
            for rule in group.get("rules", []):
                rule["_groupIndex"] = group_index
        return groups

    @Property(list, notify=changed)
    def selectedActions(self) -> list[dict[str, Any]]:
        actions = deepcopy((self._selected() or {}).get("action_set", {}).get("actions", []))
        for action_index, action in enumerate(actions):
            action["_index"] = action_index
        return actions

    @Property(list, constant=True)
    def triggerTypes(self) -> list[dict[str, str]]:
        return [{"id": key, **value} for key, value in TRIGGER_TYPES.items()]

    @Property(list, constant=True)
    def ruleTypes(self) -> list[dict[str, str]]:
        return [{"id": key, **value} for key, value in RULE_TYPES.items()]

    @Property(list, constant=True)
    def actionTypes(self) -> list[dict[str, str]]:
        return [{"id": key, **value} for key, value in ACTION_TYPES.items()]

    @Property(str, notify=changed)
    def statusText(self) -> str:
        return self._status_text

    @Property(bool, notify=undoAvailableChanged)
    def undoAvailable(self) -> bool:
        return self._undo_item is not None

    @Slot(bool)
    def setAutomationEnabled(self, enabled: bool) -> None:
        self.config.automation_enabled = bool(enabled)
        self.config.save()
        self.changed.emit()

    @Slot(int)
    def selectAutomation(self, index: int) -> None:
        values = self._items()
        self._selected_index = max(-1, min(int(index), len(values) - 1)) if values else -1
        self.changed.emit()

    @Slot()
    def addAutomation(self) -> None:
        values = self._items()
        values.insert(self._selected_index + 1 if self._selected_index >= 0 else len(values), new_automation())
        self._selected_index = min(self._selected_index + 1, len(values) - 1) if self._selected_index >= 0 else len(values) - 1
        self._commit(values)
        logger.debug("已添加自动化，当前数量: {}", len(values))

    @Slot()
    def removeAutomation(self) -> None:
        values = self._items()
        if not (0 <= self._selected_index < len(values)):
            return
        self._undo_item = deepcopy(values[self._selected_index])
        self._undo_index = self._selected_index
        values.pop(self._selected_index)
        self._selected_index = min(self._selected_index, len(values) - 1)
        self._undo_timer.start()
        self._commit(values)
        self.undoAvailableChanged.emit()

    @Slot()
    def undoDelete(self) -> None:
        if self._undo_item is None:
            return
        values = self._items()
        index = min(max(self._undo_index, 0), len(values))
        values.insert(index, self._undo_item)
        self._selected_index = index
        self._clear_undo()
        self._commit(values)

    def _clear_undo(self) -> None:
        self._undo_item = None
        self._undo_index = -1
        self._undo_timer.stop()
        self.undoAvailableChanged.emit()

    @Slot()
    def duplicateAutomation(self) -> None:
        source = self._selected()
        if not source:
            return
        copy = deepcopy(source)
        copy["id"] = new_id()
        copy["name"] = f"{source.get('name', '自动化')} - 副本"
        copy["action_set"]["name"] = copy["name"]
        copy["restore_state"] = {"active": False, "captured_at": "", "entries": []}
        copy["last_run"] = ""
        copy["run_count"] = 0
        values = self._items()
        values.insert(self._selected_index + 1, copy)
        self._selected_index += 1
        self._commit(values)

    @Slot(str)
    def renameSelected(self, name: str) -> None:
        value = str(name).strip() or "未命名自动化"
        self._update_selected(lambda item: (item.__setitem__("name", value), item["action_set"].__setitem__("name", value)))

    @Slot(bool)
    def toggleSelected(self, enabled: bool) -> None:
        self._update_selected(lambda item: (item.__setitem__("enabled", bool(enabled)), item["action_set"].__setitem__("enabled", bool(enabled))))

    @Slot(bool)
    def setConditionEnabled(self, value: bool) -> None:
        self._update_selected(lambda item: item.__setitem__("is_condition_enabled", bool(value)))

    @Slot(bool)
    def setRevertEnabled(self, value: bool) -> None:
        self._update_selected(lambda item: item["action_set"].__setitem__("revert_enabled", bool(value)))

    @Slot(int)
    def setCooldown(self, seconds: int) -> None:
        self._update_selected(lambda item: item.__setitem__("cooldown", max(0, int(seconds))))

    @Slot()
    def save(self) -> None:
        self.config.save()
        self.changed.emit()

    @Slot()
    def openConfigFolder(self) -> None:
        self.config.path.parent.mkdir(parents=True, exist_ok=True)
        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.config.path.parent)))
        logger.info("打开自动化配置文件夹: {}，结果: {}", self.config.path.parent, opened)

    @Slot()
    def runSelected(self) -> None:
        item = self._selected()
        if item:
            self.engine.run_now(item["id"])

    @Slot()
    def stopSelected(self) -> None:
        item = self._selected()
        if item:
            self.engine.stop_automation(item["id"])

    @Slot()
    def revertSelected(self) -> None:
        item = self._selected()
        if item:
            self.engine.revert_automation(item["id"])

    @Slot(int, str)
    def setTriggerType(self, index: int, value: str) -> None:
        self._update_nested("triggers", index, lambda entry: (entry.__setitem__("type", str(value)), entry.__setitem__("settings", {})))

    @Slot(int, str, "QVariant")
    def setTriggerSetting(self, index: int, key: str, value: Any) -> None:
        self._update_nested("triggers", index, lambda entry: entry["settings"].__setitem__(str(key), value))

    @Slot()
    def addTrigger(self) -> None:
        self._update_selected(lambda item: item["triggers"].append(default_trigger()))

    @Slot(int)
    def removeTrigger(self, index: int) -> None:
        def remove(item):
            if 0 <= index < len(item["triggers"]):
                item["triggers"].pop(index)
        self._update_selected(remove)

    @Slot(str)
    def setRulesMode(self, mode: str) -> None:
        self._update_selected(lambda item: item["ruleset"].__setitem__("mode", "any" if mode == "any" else "all"))

    @Slot(bool)
    def setRulesReversed(self, value: bool) -> None:
        self._update_selected(lambda item: item["ruleset"].__setitem__("reversed", bool(value)))

    @Slot()
    def addGroup(self) -> None:
        self._update_selected(lambda item: item["ruleset"]["groups"].append(default_group()))

    @Slot(int)
    def removeGroup(self, index: int) -> None:
        def remove(item):
            groups = item["ruleset"]["groups"]
            if 0 <= index < len(groups):
                groups.pop(index)
        self._update_selected(remove)

    @Slot(int)
    def duplicateGroup(self, index: int) -> None:
        def duplicate(item):
            groups = item["ruleset"]["groups"]
            if 0 <= index < len(groups):
                copy = deepcopy(groups[index])
                copy["id"] = new_id()
                for rule in copy["rules"]:
                    rule["id"] = new_id()
                groups.insert(index + 1, copy)
        self._update_selected(duplicate)

    @Slot(int, str)
    def setGroupMode(self, index: int, mode: str) -> None:
        self._update_nested("groups", index, lambda group: group.__setitem__("mode", "any" if mode == "any" else "all"))

    @Slot(int, bool)
    def setGroupReversed(self, index: int, value: bool) -> None:
        self._update_nested("groups", index, lambda group: group.__setitem__("reversed", bool(value)))

    @Slot(int, bool)
    def setGroupEnabled(self, index: int, value: bool) -> None:
        self._update_nested("groups", index, lambda group: group.__setitem__("enabled", bool(value)))

    @Slot(int)
    def addRule(self, group_index: int) -> None:
        self._update_nested("groups", group_index, lambda group: group["rules"].append(default_rule()))

    @Slot(int, int)
    def removeRule(self, group_index: int, rule_index: int) -> None:
        def remove(item):
            groups = item["ruleset"]["groups"]
            if not 0 <= group_index < len(groups):
                return
            rules = groups[group_index]["rules"]
            if 0 <= rule_index < len(rules):
                rules.pop(rule_index)
        self._update_selected(remove)

    @Slot(int, int, str)
    def setRuleType(self, group_index: int, rule_index: int, value: str) -> None:
        self._update_nested("rules", rule_index, lambda rule: (rule.__setitem__("type", str(value)), rule.__setitem__("settings", {})), group_index)

    @Slot(int, int, bool)
    def setRuleReversed(self, group_index: int, rule_index: int, value: bool) -> None:
        self._update_nested("rules", rule_index, lambda rule: rule.__setitem__("reversed", bool(value)), group_index)

    @Slot(int, int, str, "QVariant")
    def setRuleSetting(self, group_index: int, rule_index: int, key: str, value: Any) -> None:
        self._update_nested("rules", rule_index, lambda rule: rule["settings"].__setitem__(str(key), value), group_index)

    @Slot(str)
    def setActionSetName(self, name: str) -> None:
        self.renameSelected(name)

    @Slot(int, str)
    def setActionType(self, index: int, value: str) -> None:
        self._update_nested("actions", index, lambda action: (action.__setitem__("type", str(value)), action.__setitem__("settings", {})))

    @Slot(int, str, "QVariant")
    def setActionSetting(self, index: int, key: str, value: Any) -> None:
        self._update_nested("actions", index, lambda action: action["settings"].__setitem__(str(key), value))

    @Slot()
    def addAction(self) -> None:
        self._update_selected(lambda item: item["action_set"]["actions"].append(default_action()))

    @Slot(int)
    def removeAction(self, index: int) -> None:
        def remove(item):
            actions = item["action_set"]["actions"]
            if 0 <= index < len(actions):
                actions.pop(index)
        self._update_selected(remove)

    @Slot(int, int, int)
    def moveEntry(self, section: int, source: int, target: int) -> None:
        """Move entries for the QML drag handles (0 workflows, 1 triggers, 2 actions)."""
        values = self._items()
        if section == 0:
            entries = values
        else:
            item = self._selected(values)
            if not item:
                return
            entries = item["triggers"] if section == 1 else item["action_set"]["actions"]
        if not (0 <= source < len(entries) and 0 <= target < len(entries)):
            return
        entry = entries.pop(source)
        entries.insert(target, entry)
        if section == 0:
            self._selected_index = target
        self._commit(values)
