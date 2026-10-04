# SystemTools 自动化（Class Widgets 2 插件）

为 [Class Widgets 2](https://github.com/RinLit-233-shiroko/Class-Widgets-2) 提供一套对标 ClassIsland 的自动化系统。
插件完全独立运行，不修改 Class Widgets 2 主程序，配置也存放在独立文件中。

## 功能

每个“自动化”由触发器、规则集与行动三部分组成，可随时启用或停用。

- **触发器**：启动、间隔（秒）、课程状态、科目。
- **规则集**：始终满足、课程状态、星期、时间段、运行中的进程。
- **规则组合**：满足任一 / 满足全部，支持单条规则取反与整个规则集取反。
- **行动（顺序执行）**：发送通知、写入日志、打开链接、启动进程、切换课表、修改配置。
- **运行控制**：冷却时间、运行历史、手动运行 / 停止。
- **恢复**：开启后可自动记录并恢复被修改的原始值。

## 安装

1. 将本仓库内容放入 `Class-Widgets-2/plugins/com.classwidgets.systemtools.automation/`，
   确保 `cwplugin.json` 位于该目录根下。
2. 启动 Class Widgets 2，在设置中启用该插件。
3. 进入「自动化」设置页即可开始配置。

也可以直接通过插件广场安装。

## 配置

配置独立保存在：

```
Class-Widgets-2/configs/plugins/com.classwidgets.systemtools.automation.json
```

首次启动时，旧版插件配置段中的数据会自动迁移到该文件。

启用「恢复」后，`修改配置` 与 `切换课表` 两个行动会在执行前记录原始值；
可通过页面上的「恢复」手动还原，或在规则集、课程状态 / 科目触发器失效时自动还原。
引擎使用插件自有的精确 50 毫秒定时器。

## 填写示例

- `修改配置`：使用 `path=value` 形式，例如 `preferences.mini_mode=true`。
- `启动进程`：按命令行填写可执行文件与参数。
- 时间规则：使用 `08:00-17:30`。
- 星期规则：使用 `1` 到 `7`。

## 许可证

本项目遵循 [MIT 许可证](LICENSE)。
