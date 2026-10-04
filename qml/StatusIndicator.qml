import QtQuick
import RinUI

Item {
    id: root

    property int state: 0
    readonly property color indicatorColor: state === 2
        ? Theme.currentTheme.colors.systemSuccessColor
        : state === 1
            ? Theme.currentTheme.colors.systemCriticalColor
            : Theme.currentTheme.colors.systemNeutralColor
    readonly property string stateText: state === 2
        ? qsTr("已满足")
        : state === 1
            ? qsTr("不满足")
            : qsTr("未知")

    implicitWidth: 16
    implicitHeight: 32

    Rectangle {
        width: 8
        height: 8
        anchors.centerIn: parent
        radius: width / 2
        color: root.indicatorColor
    }

    HoverHandler {
        id: hoverHandler
    }

    ToolTip {
        visible: hoverHandler.hovered
        text: root.stateText
    }
}
