import QtQuick
import QtQuick.Layouts
import RinUI

FastExpander {
    id: root
    property string title
    property string iconName
    property alias action: actions.data
    Layout.minimumWidth: 0
    expanded: true
    contentPadding: 8
    contentSpacing: 6
    contentFrame.color: "transparent"

    // 默认给左侧工作流内的 触发器 / 规则集 / 行动 三栏使用紧凑标题栏。
    // “启用自动化”栏可覆盖为 -1 / 40 / 5，回到 RinUI 的默认尺寸。
    property bool acceptHeaderSettings: true
    headerFixedHeight: acceptHeaderSettings ? 33 : -1
    headerControlExtent: acceptHeaderSettings ? 26 : 40
    headerContentMargin: acceptHeaderSettings ? 2 : 5
    headerAccentColor: acceptHeaderSettings

    header: RowLayout {
        Layout.fillWidth: true
        Layout.minimumWidth: 0
        spacing: 10
        Icon { name: root.iconName; size: 20 }
        Text {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            text: root.title
            typography: Typography.BodyStrong
            elide: Text.ElideRight
        }
        RowLayout { id: actions; spacing: 4 }
    }
}
