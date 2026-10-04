import QtQuick 2.15
import QtQuick.Controls.Basic 2.15
import QtQuick.Layouts 2.15
import RinUI

// FastExpander —— 插件自带的 Expander 变体。
// 结构、尺寸、圆角、配色与 RinUI Expander 完全一致，只替换动画参数：
//   * 时长更短，折叠/展开更利落；
//   * 缓动统一为 Linear，避免渐快/渐慢。
// 该文件只影响使用它的插件页面，不修改 RinUI 与主程序。
Item {
    id: root
    property bool enabled: true
    property bool expanded: false
    property alias headerHeight: header.height
    property alias contentHeight: content.height
    property alias contentPadding: content.padding
    property alias contentSpacing: contentLayout.spacing
    property real headerFixedHeight: -1
    property real headerControlExtent: 40
    property real headerContentMargin: 5
    // 标题栏是否继承主题强调色。为 false 时使用 RinUI 默认卡片色（仅用于
    // “启用自动化”这类不参与主题色的栏目标题）。
    property bool headerAccentColor: true
    enum ExpandDirection { Up, Down }
    property var expandDirection: FastExpander.Down
    readonly property bool directionUp: root.expandDirection === FastExpander.Up
    property bool roundContentEdgeItems: false
    property real radius: Theme.currentTheme.appearance.smallRadius

    // 唯一的调速旋钮：折叠/展开、内容位移、增删行过渡都使用它。
    // 箭头旋转取它的 80%，让两种动作同时收尾。
    property int animationDuration: 90
    readonly property int arrowDuration: Math.round(root.animationDuration * 0.8)

    property alias header: headerCustom.data
    property string text
    property alias contentFrame: content
    default property alias contentData: contentLayout.data  //折叠内容

    implicitWidth: Math.max(
        headerLayout.implicitWidth + 5 * 2,
        contentLayout.implicitWidth + contentPadding * 2,
        headerCustom.implicitWidth + 20 + expandBtn.width
    )
    implicitHeight: headerHeight + (content.height - 2) * expanded

    // 拦截交互
    MouseArea {
        z: 999
        anchors.fill: parent
        enabled: !root.enabled
        hoverEnabled: false
        preventStealing: true
        onClicked: {}  // 防止穿透
    }

    // 主体
    Clip {
        id: header
        objectName: "fastExpanderHeader"
        enabled: root.enabled
        y: directionUp ? content.height * expanded : 0
        width: parent.width
        height: root.headerFixedHeight > 0 ? root.headerFixedHeight : Math.max(
            headerCustom.implicitHeight + root.headerContentMargin * 2,
            headerLayout.implicitHeight + root.headerContentMargin * 2,
            48
        )
        // 标题栏跟随软件主题色（强调色）实时变化，语义对齐 ClassIsland 的
        // CustomizedAccentBarBackground1Brush：强调色 10% 透明度。
        // 悬停时略增强，但仍保持主题色，不退回中性卡片色。
        // headerAccentColor 为 false 时回到 RinUI 默认卡片色（如“启用自动化”栏）。
        color: root.headerAccentColor
            ? Qt.alpha(Theme.currentTheme.colors.primaryColor, header.hovered && header.enabled ? 0.16 : 0.10)
            : (header.hovered && header.enabled
                ? Theme.currentTheme.colors.controlSecondaryColor
                : Theme.currentTheme.colors.cardColor)
        border.color: Theme.currentTheme.colors.cardBorderColor
        // 折叠时全圆角；展开时与 content 衔接侧直角，外侧保留圆角
        radius: root.radius
        topLeftRadius: (!expanded || !directionUp) ? root.radius : 0
        topRightRadius: (!expanded || !directionUp) ? root.radius : 0
        bottomLeftRadius: (!expanded || directionUp) ? root.radius : 0
        bottomRightRadius: (!expanded || directionUp) ? root.radius : 0

        RowLayout {
            id: headerCustom
            anchors.fill: parent
            anchors.margins: root.headerContentMargin
            anchors.leftMargin: 15
            anchors.rightMargin: 5 + expandBtn.width
        }

        RowLayout {
            id: headerLayout
            anchors.fill: parent
            anchors.margins: root.headerContentMargin
            anchors.leftMargin: 15
            spacing: 0
            Text {
                Layout.fillWidth: true
                text: root.text
                opacity: headerCustom.children.length === 0
            }
            // 展开按钮
            ToolButton {
                id: expandBtn
                focusPolicy: Qt.NoFocus
                Layout.preferredWidth: root.headerControlExtent
                Layout.preferredHeight: root.headerControlExtent
                implicitWidth: root.headerControlExtent
                implicitHeight: root.headerControlExtent
                hoverable: false
                size: 14
                icon.name: directionUp ? "ic_fluent_chevron_up_20_filled" : "ic_fluent_chevron_down_20_filled"

                // 展开动画：线性，不做渐快/渐慢
                transform: Rotation {
                    angle: !expanded ? 0 : 180 ; origin.x: root.headerControlExtent / 2; origin.y: root.headerControlExtent / 2
                    Behavior on angle { NumberAnimation { duration: root.arrowDuration; easing.type: Easing.Linear } }
                }
                opacity: 0.7

                onClicked: expanded =!expanded
            }
        }

        onClicked: expanded =!expanded

        Behavior on y {
            NumberAnimation { duration: root.animationDuration; easing.type: Easing.Linear }
        }
    }

    // content
    Item {
        id: contentContainer
        width: parent.width
        height: directionUp
            ? expanded ? content.height : 0
            : content.height
        clip: true
        y: directionUp ? 0 : header.height
        z: -1  // 置底

        Frame {
            id: content
            padding: 7
            width: parent.width
            y: expanded
                ? directionUp ? 2 : - 2
                : directionUp ? height : - height
            radius: root.radius
            topLeftRadius: directionUp ? root.radius : 0
            topRightRadius: directionUp ? root.radius : 0
            bottomLeftRadius: directionUp ? 0 : root.radius
            bottomRightRadius: directionUp ? 0 : root.radius
            opacity: root.enabled ? 1 : 0.65

            color: Theme.currentTheme.colors.cardSecondaryColor
            // 内容区域 - 布局
            ColumnLayout {
                id: contentLayout
                property bool roundContentEdgeItems: root.roundContentEdgeItems
                property bool directionUp: root.directionUp
                anchors.fill: parent
                anchors.margins: content.border.width
            }

            Behavior on y {
                NumberAnimation { duration: root.animationDuration; easing.type: Easing.Linear }
            }

            Behavior on opacity {
                NumberAnimation { duration: root.animationDuration; easing.type: Easing.Linear }
            }
        }

        Behavior on height {
            NumberAnimation { duration: root.animationDuration; easing.type: Easing.Linear }
        }
    }

    // 动画
    Behavior on implicitHeight {
        NumberAnimation { duration: root.animationDuration; easing.type: Easing.Linear }
    }
}
