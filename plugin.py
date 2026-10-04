from __future__ import annotations

from ClassWidgets.SDK import CW2Plugin
from loguru import logger
from src.core.plugin.bridge import PluginBackendBridge

from backend import AutomationBackend
from config import AutomationConfig
from engine import AutomationEngine
from models import new_automation


class Plugin(CW2Plugin):
    """SystemTools automation for Class Widgets 2."""

    def on_load(self):
        super().on_load()

        config_path = self.PATH.parent.parent / "configs" / "plugins" / f"{self.pid}.json"
        legacy_data = self._read_legacy_config()
        self.config = AutomationConfig(config_path, legacy_data=legacy_data)
        if not self.config.automations and not self.config.loaded:
            example = new_automation("示例：课程状态通知")
            example["enabled"] = False
            example["triggers"] = [{"id": example["triggers"][0]["id"], "type": "status", "value": "class", "settings": {}}]
            example["action_set"]["actions"][0]["settings"]["message"] = "当前课程已开始"
            self.config.automations = [example]
        if self.config.migrated or not self.config.loaded:
            self.config.save()
        if self.config.migrated:
            logger.info("已将旧版插件配置迁移到独立文件: {}", self.config.path)

        self.provider = self.api.notification.register_provider(
            f"{self.pid}.notifications",
            "SystemTools 自动化",
            icon=self.PATH / "icon.png",
            use_system_notify=True,
        )
        self.engine = AutomationEngine(self.api, self.config, self.provider, self)
        self.backend = AutomationBackend(self.config, self.engine, self)
        PluginBackendBridge.register_backend(self.pid, self.backend)
        self.api.ui.register_settings_page(
            "qml/AutomationPage.qml",
            title="自动化",
            icon="ic_fluent_script_20_regular",
        )

    def on_unload(self):
        if getattr(self, "engine", None):
            self.engine.stop()
        super().on_unload()

    def _read_legacy_config(self):
        """读取旧版 configs.json 中的插件配置，仅用于一次性迁移。"""
        try:
            root = self.api.globalconfig.configs
            plugins = getattr(root, "plugins", None)
            configs = getattr(plugins, "configs", None) if plugins is not None else None
            value = configs.get(self.pid) if isinstance(configs, dict) else None
            return dict(value) if isinstance(value, dict) else None
        except Exception as error:
            logger.warning("读取旧版插件配置失败，将使用独立配置初始值: {}", error)
            return None
