import QtQuick
import QtQuick as Quick
import QtQuick.Controls
import QtQuick.Layouts
import RinUI

Page {
    id: root
    // A fixed fallback also works on hosts whose navigation omits pluginId.
    property string pluginId: "com.classwidgets.systemtools.automation"
    readonly property var backend: typeof PluginBackendBridge !== "undefined" && PluginBackendBridge
        ? PluginBackendBridge.get_backend(pluginId)
        : null
    title: ""
    padding: 12
    clip: true

    readonly property color elevated: Theme.currentTheme.colors.subtleSecondaryColor
    readonly property color accent: Theme.currentTheme.colors.primaryColor
    readonly property color primaryText: Theme.currentTheme.colors.textColor
    readonly property color secondaryText: Theme.currentTheme.colors.textSecondaryColor
    readonly property color danger: Theme.currentTheme.colors.systemCriticalColor
    readonly property color success: Theme.currentTheme.colors.systemSuccessColor
    readonly property color neutral: Theme.currentTheme.colors.systemNeutralColor
    // 工具栏小按钮的图标尺寸。RinUI ToolButton 默认 20px，这里略微收紧，
    // 只影响本插件页面，便于整体微调。
    readonly property int toolIconSize: 16
    // 行内删除按钮的按钮本体尺寸（RinUI ToolButton 默认隐式尺寸至少 40x32）。
    readonly property int compactIconButtonSize: 26
    // 同一行内标准控件的隐式高度（RinUI Button/ToggleButton/ToolButton 均为 32）。
    // 用于把隐式高度更小的控件（如 Switch 只有 20）在行内做垂直居中。
    readonly property int standardControlHeight: 32
    property int menuActionIndex: -2
    readonly property bool backendReady: backend !== null && backend !== undefined
    readonly property bool stacked: availableWidth < 740

    Component.onCompleted: {
        if (backendReady)
            backend.reportPageReady()
        else
            console.error("SystemTools: automation settings backend is unavailable")
    }

    function setting(item, key, fallback) {
        return item && item.settings && item.settings[key] !== undefined ? item.settings[key] : fallback
    }

    function chooseAction(type) {
        actionMenu.close()
        actionMenu.parent = root
        if (!backendReady) {
            return
        }
        if (menuActionIndex === -1) {
            backend.addAction()
            backend.setActionType(backend.selectedActions.length - 1, type)
        } else if (menuActionIndex >= 0) {
            backend.setActionType(menuActionIndex, type)
        }
    }

    function openActionMenu(button, index) {
        menuActionIndex = index
        actionMenu.parent = button
        actionMenu.open()
    }

    function triggerEditor(item) {
        return backendReady && item && item.type && backend.triggerTypes.length > 0
            ? backend.triggerTypes.find(function(entry) { return entry.id === item.type })
            : null
    }

    // FluentWindow supplies the acrylic/theme background shared by every CW2
    // settings page. The plugin page must remain transparent so it does not
    // paint a second opaque background over the host window.
    background: Item { }

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        SplitView {
            id: splitView
            orientation: root.stacked ? Qt.Vertical : Qt.Horizontal
            Layout.fillWidth: true
            Layout.fillHeight: true
            handle: Rectangle { implicitWidth: 1; implicitHeight: 1; color: Theme.currentTheme.colors.dividerBorderColor }

            Rectangle {
                id: navigationPane
                objectName: "navigationPane"
                color: "transparent"
                clip: true
                SplitView.preferredWidth: Math.max(300, Math.min(460, root.availableWidth * 0.42))
                SplitView.minimumWidth: root.stacked ? 0 : 300
                SplitView.preferredHeight: 220
                SplitView.minimumHeight: root.stacked ? 140 : 0
                SplitView.maximumHeight: root.stacked ? Math.max(140, root.availableHeight * 0.45) : Infinity

                ColumnLayout {
                    anchors.fill: parent
                    anchors.rightMargin: root.stacked ? 0 : 12
                    spacing: 6

                    AutomationSection {
                        Layout.fillWidth: true
                        title: qsTr("启用自动化")
                        iconName: "ic_fluent_script_20_regular"
                        // 左上方这一栏保持原状：默认高度/控件尺寸，不跟主题色。
                        acceptHeaderSettings: false
                        action: RowLayout {
                            spacing: 6
                            ToolButton {
                                objectName: "automationHelpButton"
                                icon.name: "ic_fluent_question_circle_20_regular"
                                size: root.toolIconSize
                                flat: true
                                ToolTip { visible: parent.hovered; text: qsTr("打开自动化帮助文档") }
                                onClicked: Qt.openUrlExternally("https://docs.classisland.tech/app/automation.html")
                            }
                            Switch {
                                objectName: "automationEnabledSwitch"
                                enabled: root.backendReady
                                checked: backendReady ? backend.automationEnabled : false
                                text: checked ? qsTr("开") : qsTr("关")
                                onToggled: if (backendReady) backend.setAutomationEnabled(checked)
                            }
                        }
                        Text {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            text: qsTr("自动化是一种可使 Class Widgets 自动作出行动的功能。")
                            color: root.secondaryText
                            wrapMode: Text.Wrap
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Button {
                            objectName: "addAutomationButton"
                            enabled: root.backendReady
                            icon.name: "ic_fluent_add_20_regular"
                            text: qsTr("添加自动化")
                            flat: true
                            highlighted: true
                            onClicked: if (backendReady) backend.addAutomation()
                        }
                        // 弹性占位：把配置方案选择与两个图标按钮推到该行最右侧。
                        // 窄屏（上下堆叠）时隐藏占位，保持原有靠左排列。
                        Item {
                            Layout.fillWidth: true
                            visible: !root.stacked
                            Layout.preferredWidth: 0
                        }
                        AutomationComboBox {
                            id: profileBox
                            objectName: "profileBox"
                            Layout.minimumWidth: 88
                            Layout.maximumWidth: 240
                            minimumControlWidth: 88
                            maximumControlWidth: 240
                            model: backendReady ? backend.profileNames : []
                            currentIndex: backendReady ? backend.profileIndex : -1
                            enabled: root.backendReady
                            onActivated: function(index) {
                                if (backendReady) backend.selectProfile(index)
                                currentIndex = Qt.binding(function() { return root.backendReady ? root.backend.profileIndex : -1 })
                            }
                        }
                        ToolButton {
                            objectName: "createProfileButton"
                            enabled: root.backendReady
                            Layout.preferredWidth: 32
                            icon.name: "ic_fluent_document_add_20_regular"
                            size: root.toolIconSize
                            flat: true
                            ToolTip { visible: parent.hovered; text: qsTr("新建自动化配置方案") }
                            onClicked: if (backendReady) backend.createProfile()
                        }
                        ToolButton {
                            objectName: "openConfigFolderButton"
                            enabled: root.backendReady
                            Layout.preferredWidth: 32
                            icon.name: "ic_fluent_folder_open_20_regular"
                            size: root.toolIconSize
                            flat: true
                            ToolTip { visible: parent.hovered; text: qsTr("打开配置文件夹") }
                            onClicked: if (backendReady) backend.openConfigFolder()
                        }
                    }

                    Quick.ListView {
                        id: workflowList
                        property int dragSource: -1
                        property int dragTarget: -1
                        property real dragTranslation: 0
                        readonly property bool dragging: dragSource >= 0
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 2
                        model: backendReady ? backend.automations : []
                        currentIndex: backendReady ? backend.selectedIndex : -1
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                        delegate: Rectangle {
                            id: workflowDelegate
                            property bool isDragging: workflowList.dragSource === index
                            width: workflowList.width
                            height: 42
                            color: ListView.isCurrentItem || workflowHover.hovered ? root.elevated : "transparent"
                            radius: Theme.currentTheme.appearance.buttonRadius
                            z: isDragging ? 10 : 0
                            opacity: isDragging ? 0.88 : 1
                            transform: Translate { y: workflowDelegate.isDragging ? workflowList.dragTranslation : 0 }
                            HoverHandler { id: workflowHover }

                            Rectangle {
                                width: 4
                                height: parent.height - 14
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                radius: 2
                                color: ListView.isCurrentItem ? root.accent : "transparent"
                            }
                            RowLayout {
                                anchors.fill: parent
                                z: 1
                                anchors.leftMargin: 12
                                anchors.rightMargin: 8
                                spacing: 6
                                ToolButton {
                                    id: workflowDragButton
                                    objectName: "workflowDragButton"
                                    icon.name: "ic_fluent_re_order_dots_vertical_20_regular"
                                    flat: true
                                    Layout.preferredWidth: 24
                                    ToolTip { visible: parent.hovered; text: qsTr("拖动排序") }

                                    DragHandler {
                                        id: workflowDragHandler
                                        target: null
                                        grabPermissions: PointerHandler.CanTakeOverFromAnything

                                        onActiveChanged: {
                                            if (active) {
                                                workflowList.dragSource = index
                                                workflowList.dragTarget = index
                                                workflowList.dragTranslation = 0
                                            } else if (workflowList.dragSource >= 0) {
                                                var source = workflowList.dragSource
                                                var target = workflowList.dragTarget
                                                workflowList.dragSource = -1
                                                workflowList.dragTarget = -1
                                                workflowList.dragTranslation = 0
                                                if (backendReady && source !== target)
                                                    backend.moveEntry(0, source, target)
                                            }
                                        }

                                        onTranslationChanged: {
                                            if (!active)
                                                return
                                            workflowList.dragTranslation = translation.y
                                            var centerY = workflowDelegate.y + workflowDelegate.height / 2 + translation.y
                                            var target = Math.floor((centerY + workflowList.contentY) / (workflowDelegate.height + workflowList.spacing))
                                            workflowList.dragTarget = Math.max(0, Math.min(workflowList.count - 1, target))
                                        }
                                    }
                                }
                                Text {
                                    text: modelData.name || qsTr("未命名自动化")
                                    color: root.primaryText
                                    typography: Typography.Body
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                }
                                ProgressBar {
                                    visible: modelData.action_set && modelData.action_set.status !== "normal"
                                    indeterminate: true
                                    Layout.preferredWidth: 24
                                    Layout.preferredHeight: 3
                                }
                                Switch {
                                    checked: modelData.enabled || false
                                    text: checked ? qsTr("开") : qsTr("关")
                                    onToggled: {
                                        if (backendReady) {
                                            var value = checked
                                            backend.selectAutomation(index)
                                            backend.toggleSelected(value)
                                        }
                                    }
                                }
                            }
                            MouseArea {
                                anchors.fill: parent
                                z: 0
                                onClicked: if (backendReady) backend.selectAutomation(index)
                            }
                        }
                    }
                }
            }

            Rectangle {
                id: detailPane
                objectName: "detailPane"
                color: "transparent"
                clip: true
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                SplitView.minimumWidth: 0
                SplitView.minimumHeight: 0

                Item {
                    anchors.fill: parent
                    visible: !backendReady || backend.selectedIndex < 0
                    ColumnLayout {
                        width: Math.max(0, parent.width - 32)
                        anchors.centerIn: parent
                        spacing: 10
                        Text {
                            objectName: "emptyStateText"
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            text: backendReady ? qsTr("在左侧选择或添加一个自动化，然后在此处进行设置。") : qsTr("自动化后端加载失败，请查看调试日志。")
                            color: root.secondaryText
                            wrapMode: Text.Wrap
                            horizontalAlignment: Text.AlignHCenter
                        }
                        Button { objectName: "emptyAddButton"; Layout.alignment: Qt.AlignHCenter; text: qsTr("添加自动化"); enabled: backendReady; onClicked: backend.addAutomation() }
                    }
                }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.leftMargin: root.stacked ? 0 : 8
                    spacing: 6
                    visible: backendReady && backend.selectedIndex >= 0

                    GridLayout {
                        id: detailHeader
                        Layout.fillWidth: true
                        Layout.minimumHeight: 42
                        columns: width < 620 ? 1 : 2
                        TextField {
                            id: workflowName
                            objectName: "automationNameField"
                            Layout.minimumWidth: 0
                            Layout.preferredWidth: 188
                            Layout.fillWidth: false
                            text: backendReady ? (backend.selectedAutomation.name || "") : ""
                            placeholderText: qsTr("自动化名称")
                            onTextEdited: if (backendReady) backend.renameSelected(text)
                        }
                        Quick.Flow {
                            Layout.fillWidth: true
                            spacing: 4
                        CheckBox {
                            text: qsTr("启用恢复")
                            checked: backendReady && backend.selectedAutomation.action_set ? backend.selectedAutomation.action_set.revert_enabled : false
                            onToggled: if (backendReady) backend.setRevertEnabled(checked)
                        }
                        Button { objectName: "runButton"; text: qsTr("触发"); icon.name: "ic_fluent_play_circle_20_regular"; onClicked: if (backendReady) backend.runSelected() }
                        ToolButton { objectName: "stopButton"; width: 32; size: root.toolIconSize; icon.name: "ic_fluent_stop_20_regular"; ToolTip { visible: parent.hovered; text: qsTr("中断当前行动") } onClicked: if (backendReady) backend.stopSelected() }
                        ToolButton { objectName: "revertButton"; width: 32; size: root.toolIconSize; icon.name: "ic_fluent_arrow_undo_20_regular"; enabled: !!(backendReady && backend.selectedAutomation.restore_state && backend.selectedAutomation.restore_state.active); ToolTip { visible: parent.hovered; text: qsTr("恢复原值") } onClicked: if (backendReady) backend.revertSelected() }
                        ToolButton { objectName: "copyAutomationButton"; width: 32; size: root.toolIconSize; icon.name: "ic_fluent_copy_20_regular"; flat: true; ToolTip { visible: parent.hovered; text: qsTr("复制") } onClicked: if (backendReady) backend.duplicateAutomation() }
                        ToolButton { objectName: "deleteAutomationButton"; width: 32; size: root.toolIconSize; icon.name: "ic_fluent_delete_20_regular"; flat: true; ToolTip { visible: parent.hovered; text: qsTr("删除") } onClicked: if (backendReady) backend.removeAutomation() }
                        }
                    }

                    ScrollView {
                        id: detailScrollView
                        objectName: "detailScrollView"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumWidth: 0
                        Layout.minimumHeight: 0
                        clip: true
                        ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AlwaysOff }
                        ScrollBar.vertical: ScrollBar {
                            policy: ScrollBar.AsNeeded
                        }

                        ColumnLayout {
                            id: detailContent
                            objectName: "detailContent"
                            width: Math.max(0, detailScrollView.availableWidth)
                            Layout.minimumWidth: 0
                            spacing: 8

                            AutomationSection {
                                Layout.fillWidth: true
                                title: qsTr("当事件触发时")
                                iconName: "ic_fluent_flash_20_regular"
                                expanded: true

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4
                                    Repeater {
                                        model: backendReady ? backend.selectedTriggers : []
                                        delegate: Frame {
                                            id: triggerRow
                                            property int triggerIndex: index
                                            property var entry: modelData
                                            Layout.fillWidth: true
                                            padding: 8
                                            ColumnLayout {
                                                anchors.fill: parent
                                                spacing: 5
                                                RowLayout {
                                                    spacing: 5
                                                    ToolButton { objectName: "removeTriggerButton"; size: root.toolIconSize; implicitWidth: root.compactIconButtonSize; implicitHeight: root.compactIconButtonSize; icon.name: "ic_fluent_dismiss_20_regular"; flat: true; ToolTip { visible: parent.hovered; text: qsTr("删除触发器") } onClicked: if (backendReady) backend.removeTrigger(triggerRow.triggerIndex) }
                                                    TypePicker {
                                                        objectName: "triggerTypePicker"
                                                        Layout.minimumWidth: 96
                                                        Layout.maximumWidth: 220
                                                        model: backendReady ? backend.triggerTypes : []
                                                        selectedValue: triggerRow.entry.type
                                                        onChosen: function(value) { if (backendReady) backend.setTriggerType(triggerRow.triggerIndex, value) }
                                                    }
                                                }
                                                Loader {
                                                    Layout.fillWidth: true
                                                    Layout.minimumWidth: 0
                                                    active: triggerRow.entry.type !== "startup"
                                                    sourceComponent: RowLayout {
                                                        spacing: 4
                                                        SpinBox {
                                                            objectName: "triggerSecondsInput"
                                                            visible: triggerRow.entry.type === "interval"
                                                            from: 1; to: 86400
                                                            value: Number(root.setting(triggerRow.entry, "seconds", 120))
                                                            onValueModified: if (backendReady) backend.setTriggerSetting(triggerRow.triggerIndex, "seconds", value)
                                                        }
                                                        Text { visible: triggerRow.entry.type === "interval"; text: qsTr("秒"); color: root.secondaryText }
                                                        TextField {
                                                            objectName: "triggerValueInput"
                                                            visible: triggerRow.entry.type !== "interval"
                                                            Layout.fillWidth: true
                                                            Layout.minimumWidth: 0
                                                            text: String(root.setting(triggerRow.entry, "value", ""))
                                                            placeholderText: qsTr("触发参数")
                                                            onEditingFinished: if (backendReady) backend.setTriggerSetting(triggerRow.triggerIndex, "value", text)
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                    Button {
                                        objectName: "addTriggerButton"
                                        flat: true
                                        text: qsTr("添加触发器")
                                        icon.name: "ic_fluent_add_20_regular"
                                         onClicked: if (backendReady) backend.addTrigger()
                                    }
                                }
                            }

                            AutomationSection {
                                Layout.fillWidth: true
                                title: qsTr("并且满足规则集时")
                                iconName: "ic_fluent_tag_20_regular"
                                expanded: true
                                action: Switch {
                                    objectName: "conditionEnabledSwitch"
                                    checked: backendReady && backend.selectedAutomation.is_condition_enabled || false
                                    text: checked ? qsTr("开") : qsTr("关")
                                    onToggled: if (backendReady) backend.setConditionEnabled(checked)
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    visible: backendReady && backend.selectedAutomation.is_condition_enabled || false
                                    spacing: 6
                                    Quick.Flow {
                                        Layout.fillWidth: true
                                        spacing: 4
                                        ToggleButton { text: qsTr("非"); checked: backendReady && backend.selectedRuleset.reversed || false; ToolTip { visible: parent.hovered; text: qsTr("对规则集结果取反") } onToggled: if (backendReady) backend.setRulesReversed(checked) }
                                        ModeSelector {
                                            id: rulesetMode
                                            width: Math.min(parent.width, 280)
                                            namePrefix: "ruleset"
                                            mode: backendReady ? backend.selectedRuleset.mode || "all" : "all"
                                            anyText: qsTr("规则组任一满足时")
                                            allText: qsTr("规则组全部满足时")
                                            onChosen: function(mode) { if (backendReady) backend.setRulesMode(mode) }
                                        }
                                        Button { objectName: "addGroupButton"; text: qsTr("添加组"); icon.name: "ic_fluent_add_20_regular"; onClicked: if (backendReady) backend.addGroup() }
                                        StatusIndicator {
                                            objectName: "rulesetStateIndicator"
                                            state: backendReady ? Number(backend.selectedRuleset.state || 0) : 0
                                            Layout.alignment: Qt.AlignVCenter
                                        }
                                    }

                                    Repeater {
                                        model: backendReady ? backend.selectedGroups : []
                                        delegate: Frame {
                                            id: groupFrame
                                            property int groupIndex: modelData._index
                                            Layout.fillWidth: true
                                            padding: 8
                                            ColumnLayout {
                                                anchors.fill: parent
                                                spacing: 4
                                                Quick.Flow {
                                                    Layout.fillWidth: true
                                                    spacing: 4
                                                    ToggleButton { text: qsTr("非"); checked: modelData.reversed || false; ToolTip { visible: parent.hovered; text: qsTr("对规则组结果取反") } onToggled: if (backendReady) backend.setGroupReversed(groupFrame.groupIndex, checked) }
                                                    ModeSelector {
                                                        width: Math.min(parent.width, 260)
                                                        namePrefix: "group"
                                                        mode: modelData.mode
                                                        anyText: qsTr("规则任一满足时")
                                                        allText: qsTr("规则全部满足时")
                                                        onChosen: function(mode) { if (backendReady) backend.setGroupMode(groupFrame.groupIndex, mode) }
                                                    }
                                                    Button { objectName: "addRuleButton"; text: qsTr("规则"); icon.name: "ic_fluent_add_20_regular"; onClicked: if (backendReady) backend.addRule(groupFrame.groupIndex) }
                                                    StatusIndicator {
                                                        objectName: "groupStateIndicator"
                                                        state: Number(modelData.state || 0)
                                                        Layout.alignment: Qt.AlignVCenter
                                                    }
                                                    // RinUI 的 Switch 隐式高度只有 20，而本行其他控件都是 32；
                                                    // Quick.Flow 顶部对齐会让开关整体偏上，这里用等高容器把它垂直居中。
                                                    Item {
                                                        implicitWidth: groupEnabledSwitch.implicitWidth
                                                        implicitHeight: root.standardControlHeight
                                                        Switch {
                                                            id: groupEnabledSwitch
                                                            objectName: "groupEnabledSwitch"
                                                            anchors.verticalCenter: parent.verticalCenter
                                                            checked: modelData.enabled !== false
                                                            text: checked ? qsTr("开") : qsTr("关")
                                                            onToggled: if (backendReady) backend.setGroupEnabled(groupFrame.groupIndex, checked)
                                                        }
                                                    }
                                                    // 紧凑按钮比同行其他控件矮，同样需要容器居中，否则会贴着行顶部。
                                                    Item {
                                                        implicitWidth: groupButtonRow.implicitWidth
                                                        implicitHeight: root.standardControlHeight
                                                        RowLayout {
                                                            id: groupButtonRow
                                                            anchors.verticalCenter: parent.verticalCenter
                                                            spacing: 4
                                                            ToolButton { objectName: "copyGroupButton"; size: root.toolIconSize; implicitWidth: root.compactIconButtonSize; implicitHeight: root.compactIconButtonSize; icon.name: "ic_fluent_copy_20_regular"; flat: true; ToolTip { visible: parent.hovered; text: qsTr("复制规则组") } onClicked: if (backendReady) backend.duplicateGroup(groupFrame.groupIndex) }
                                                            ToolButton { objectName: "removeGroupButton"; size: root.toolIconSize; implicitWidth: root.compactIconButtonSize; implicitHeight: root.compactIconButtonSize; icon.name: "ic_fluent_delete_20_regular"; flat: true; ToolTip { visible: parent.hovered; text: qsTr("删除规则组") } onClicked: if (backendReady) backend.removeGroup(groupFrame.groupIndex) }
                                                        }
                                                    }
                                                }
                                                Repeater {
                                                    model: modelData.rules
                                                    delegate: ColumnLayout {
                                                        id: ruleRow
                                                        property int ruleIndex: index
                                                        property var entry: modelData
                                                        property int groupIndex: groupFrame.groupIndex
                                                        Layout.fillWidth: true
                                                        spacing: 5
                                                        RowLayout {
                                                            spacing: 5
                                                            ToolButton { objectName: "removeRuleButton"; size: root.toolIconSize; implicitWidth: root.compactIconButtonSize; implicitHeight: root.compactIconButtonSize; icon.name: "ic_fluent_dismiss_20_regular"; flat: true; ToolTip { visible: parent.hovered; text: qsTr("删除规则") } onClicked: if (backendReady) backend.removeRule(ruleRow.groupIndex, ruleRow.ruleIndex) }
                                                            StatusIndicator {
                                                                objectName: "ruleStateIndicator"
                                                                state: Number(modelData.state || 0)
                                                                Layout.alignment: Qt.AlignVCenter
                                                            }
                                                            ToggleButton { text: qsTr("非"); checked: modelData.reversed || false; ToolTip { visible: parent.hovered; text: qsTr("对规则结果取反") } onToggled: if (backendReady) backend.setRuleReversed(ruleRow.groupIndex, ruleRow.ruleIndex, checked) }
                                                            TypePicker {
                                                                objectName: "ruleTypePicker"
                                                                Layout.minimumWidth: 96
                                                                Layout.maximumWidth: 220
                                                                model: backendReady ? backend.ruleTypes : []
                                                                selectedValue: ruleRow.entry.type
                                                                onChosen: function(value) { if (backendReady) backend.setRuleType(ruleRow.groupIndex, ruleRow.ruleIndex, value) }
                                                            }
                                                        }
                                                        Loader {
                                                            Layout.fillWidth: true
                                                            Layout.minimumWidth: 0
                                                            active: ruleRow.entry.type !== "always"
                                                            sourceComponent: RowLayout {
                                                                spacing: 4
                                                                TextField {
                                                                    visible: ruleRow.entry.type !== "time_range"
                                                                    Layout.fillWidth: true
                                                                    Layout.minimumWidth: 0
                                                                    text: String(root.setting(ruleRow.entry, "value", ruleRow.entry.type === "weekday" ? 1 : ""))
                                                                    placeholderText: qsTr("规则参数")
                                                                    onEditingFinished: if (backendReady) backend.setRuleSetting(ruleRow.groupIndex, ruleRow.ruleIndex, "value", text)
                                                                }
                                                                TextField { visible: ruleRow.entry.type === "time_range"; Layout.minimumWidth: 0; Layout.fillWidth: true; text: String(root.setting(ruleRow.entry, "start", "06:00")); placeholderText: qsTr("开始"); onEditingFinished: if (backendReady) backend.setRuleSetting(ruleRow.groupIndex, ruleRow.ruleIndex, "start", text) }
                                                                Text { visible: ruleRow.entry.type === "time_range"; text: qsTr("至"); color: root.secondaryText }
                                                                TextField { visible: ruleRow.entry.type === "time_range"; Layout.minimumWidth: 0; Layout.fillWidth: true; text: String(root.setting(ruleRow.entry, "end", "12:00")); placeholderText: qsTr("结束"); onEditingFinished: if (backendReady) backend.setRuleSetting(ruleRow.groupIndex, ruleRow.ruleIndex, "end", text) }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                                Text { Layout.fillWidth: true; Layout.minimumWidth: 0; wrapMode: Text.Wrap; visible: !backendReady || !(backend.selectedAutomation.is_condition_enabled || false); text: qsTr("工作流运行时不会考虑规则集。"); color: root.secondaryText }
                            }

                            AutomationSection {
                                Layout.fillWidth: true
                                title: qsTr("触发行动")
                                iconName: "ic_fluent_play_circle_20_regular"
                                expanded: true
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    Repeater {
                                        model: backendReady ? backend.selectedActions : []
                                        delegate: Frame {
                                            property int actionIndex: modelData._index
                                            Layout.fillWidth: true
                                            padding: 8
                                            ColumnLayout {
                                                anchors.fill: parent
                                                spacing: 8
                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    Button {
                                                        id: actionTypeButton
                                                        objectName: "actionTypeButton"
                                                        Layout.minimumWidth: 112
                                                        Layout.maximumWidth: 240
                                                        text: root.actionName(modelData.type)
                                                        icon.name: root.actionIcon(modelData.type)
                                                        suffixIconName: "ic_fluent_chevron_down_20_filled"
                                                        onClicked: root.openActionMenu(this, actionIndex)
                                                    }
                                                    Rectangle { width: 8; height: 8; radius: 4; color: modelData.error ? root.danger : "transparent" }
                                                    ProgressBar { visible: modelData.state === "working"; indeterminate: true; Layout.preferredWidth: 20 }
                                                    Item { Layout.fillWidth: true }
                                                    ToolButton {
                                                        objectName: "removeActionButton"
                                                        size: root.toolIconSize
                                                        implicitWidth: root.compactIconButtonSize
                                                        implicitHeight: root.compactIconButtonSize
                                                        Layout.alignment: Qt.AlignTop | Qt.AlignRight
                                                        icon.name: "ic_fluent_dismiss_20_regular"
                                                        flat: true
                                                        ToolTip { visible: parent.hovered; text: qsTr("删除行动") }
                                                        onClicked: if (backendReady) backend.removeAction(actionIndex)
                                                    }
                                                }
                                                TextField {
                                                    objectName: "actionTitleInput"
                                                    visible: modelData.type === "notify"
                                                    Layout.fillWidth: true
                                                    text: root.setting(modelData, "title", "SystemTools 自动化")
                                                    placeholderText: qsTr("提醒标题")
                                                    onEditingFinished: if (backendReady) backend.setActionSetting(actionIndex, "title", text)
                                                }
                                                TextField {
                                                    objectName: "actionValueInput"
                                                    Layout.fillWidth: true
                                                    text: root.setting(modelData, modelData.type === "notify" ? "message" : "value", "")
                                                    placeholderText: modelData.type === "notify" ? qsTr("提醒内容") : qsTr("行动参数")
                                                    onEditingFinished: if (backendReady) backend.setActionSetting(actionIndex, modelData.type === "notify" ? "message" : "value", text)
                                                }
                                            }
                                        }
                                    }
                                    Button {
                                        objectName: "addActionButton"
                                        flat: true
                                        text: qsTr("添加行动")
                                        icon.name: "ic_fluent_add_20_regular"
                                        onClicked: root.openActionMenu(this, -1)
                                    }
                                }
                            }

                            Text {
                                visible: !!(backendReady && backend.selectedAutomation.action_set && backend.selectedAutomation.action_set.revert_enabled)
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                wrapMode: Text.Wrap
                                text: qsTr("当规则集不再满足时，将自动恢复行动。")
                                color: root.secondaryText
                                Layout.leftMargin: 10
                                Layout.bottomMargin: 10
                            }
                        }
                    }
                }
            }
        }
    }

    function actionName(type) {
        if (!backendReady) return qsTr("未知行动")
        for (var i = 0; i < backend.actionTypes.length; ++i)
            if (backend.actionTypes[i].id === type) return backend.actionTypes[i].name
        return qsTr("未知行动")
    }

    function actionIcon(type) {
        if (!backendReady) return "ic_fluent_question_20_regular"
        for (var i = 0; i < backend.actionTypes.length; ++i)
            if (backend.actionTypes[i].id === type) return backend.actionTypes[i].icon
        return "ic_fluent_question_20_regular"
    }



    Menu {
        id: actionMenu
        objectName: "actionMenu"
        parent: root
        position: Position.Bottom
        width: 220
        MenuItem { objectName: "notifyActionItem"; icon.name: root.actionIcon("notify"); text: qsTr("显示提醒"); onTriggered: root.chooseAction("notify") }
        MenuItem { objectName: "logActionItem"; icon.name: root.actionIcon("log"); text: qsTr("写入日志"); onTriggered: root.chooseAction("log") }
        MenuItem { icon.name: root.actionIcon("open_url"); text: qsTr("打开网址"); onTriggered: root.chooseAction("open_url") }
        MenuItem { icon.name: root.actionIcon("launch_process"); text: qsTr("运行程序"); onTriggered: root.chooseAction("launch_process") }
        MenuSeparator { }
        MenuItem { icon.name: root.actionIcon("switch_schedule"); text: qsTr("切换课表"); onTriggered: root.chooseAction("switch_schedule") }
        MenuItem { icon.name: root.actionIcon("set_config"); text: qsTr("修改应用设置"); onTriggered: root.chooseAction("set_config") }
    }

    Frame {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 12
        z: 10
        visible: backendReady && backend.undoAvailable
        RowLayout {
            spacing: 12
            Text {
                text: qsTr("已删除自动化")
                color: root.primaryText
            }
            Button {
                text: qsTr("撤销")
                objectName: "undoDeleteButton"
                onClicked: if (backendReady) backend.undoDelete()
            }
        }
    }
}
