from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from loguru import logger

from models import normalize_automation


class AutomationConfig:
    """独立的自动化配置存储。

    Class Widgets 2 的全局配置只用于首次迁移旧版本数据；插件运行期间
    的读写都落在 ``configs/plugins/<plugin-id>.json``。
    """

    FORMAT_VERSION = 1

    def __init__(self, path: Path, legacy_data: Any = None):
        self.base_path = Path(path)
        self.profiles_dir = self.base_path.parent / f"{self.base_path.stem}.profiles"
        self.selection_path = self.profiles_dir / "active.json"
        self.path = self.base_path
        try:
            selected = json.loads(self.selection_path.read_text(encoding="utf-8")).get("file", "")
            if selected and Path(selected).name == selected and selected != "active.json":
                candidate = self.profiles_dir / selected
                if candidate.suffix == ".json" and candidate.is_file():
                    self.path = candidate
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        self.automations: list[dict[str, Any]] = []
        self.automation_enabled = True
        self.diagnostics_enabled = True
        self.migrated = False
        self.loaded = False
        self._load(legacy_data)

    def profiles(self) -> list[Path]:
        return [self.base_path, *sorted(
            (path for path in self.profiles_dir.glob("*.json") if path != self.selection_path),
            key=lambda path: path.stem,
        )]

    def switch_profile(self, path: Path) -> bool:
        if path not in self.profiles() or path == self.path:
            return False
        self.path = path
        self.loaded = False
        self._load(None)
        self._save_selection()
        return True

    def create_profile(self) -> None:
        number = 1
        while (self.profiles_dir / f"新配置{number}.json").exists():
            number += 1
        self.path = self.profiles_dir / f"新配置{number}.json"
        self.automations = []
        self.automation_enabled = True
        self.save()
        self._save_selection()

    def _save_selection(self) -> None:
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.selection_path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"file": self.path.name if self.path != self.base_path else ""}), encoding="utf-8")
        os.replace(temporary, self.selection_path)

    def _load(self, legacy_data: Any) -> None:
        if self.path.exists():
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("配置根节点必须是 JSON 对象")
                raw_automations = payload.get("automations")
                self.automations = self._normalize_items(raw_automations)
                self.automation_enabled = bool(payload.get("automation_enabled", True))
                self.diagnostics_enabled = bool(payload.get("diagnostics_enabled", True))
                try:
                    format_version = int(payload.get("format_version", 0) or 0)
                except (TypeError, ValueError):
                    format_version = 0
                # Existing plugin files may have a valid JSON root but still
                # use the pre-workflow flat schema.  Mark them dirty so the
                # normalized nested model is written back immediately.
                flat_items = isinstance(raw_automations, list) and any(
                    not isinstance(item, dict)
                    or "ruleset" not in item
                    or "action_set" not in item
                    for item in raw_automations
                )
                self.migrated = format_version < self.FORMAT_VERSION or flat_items
                self.loaded = True
                return
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
                logger.warning("读取独立自动化配置失败，将尝试迁移旧配置: {}", error)

        if isinstance(legacy_data, dict):
            self.automations = self._normalize_items(legacy_data.get("automations"))
            self.automation_enabled = bool(legacy_data.get("automation_enabled", True))
            self.diagnostics_enabled = bool(legacy_data.get("diagnostics_enabled", True))
            self.migrated = True
        else:
            self.automations = []

    @staticmethod
    def _normalize_items(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [normalize_automation(item) for item in value]

    def save(self) -> bool:
        payload = {
            "format_version": self.FORMAT_VERSION,
            "automation_enabled": bool(self.automation_enabled),
            "diagnostics_enabled": bool(self.diagnostics_enabled),
            "automations": self._normalize_items(self.automations),
        }
        self.automations = payload["automations"]

        temporary = self.path.with_name(f".{self.path.name}.tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, self.path)
            self.loaded = True
            return True
        except (OSError, TypeError, ValueError) as error:
            logger.error("保存独立自动化配置失败 {}: {}", self.path, error)
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            return False
