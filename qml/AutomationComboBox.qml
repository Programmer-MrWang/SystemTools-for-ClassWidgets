import QtQuick
import RinUI

ComboBox {
    id: root
    readonly property var popupObject: popup

    // The control follows the selected label, while the popup follows the
    // widest available label so a short selection never clips longer entries.
    property real minimumControlWidth: 64
    property real maximumControlWidth: 240
    // Matches RinUI ListViewDelegate padding (leftPadding 16 + rightPadding 5)
    // plus a small rounding margin so the longest label is never elided.
    readonly property real popupHorizontalPadding: 24

    // Widest label among the current options, measured with the same typography
    // as the popup delegates. Kept as a cached value so bindings stay inert.
    property real measuredWidestLabel: 0

    readonly property string measuredText: displayText !== undefined && displayText !== null
        ? String(displayText)
        : ""

    TextMetrics {
        id: labelMetrics
        font.family: Utils.fontFamily
        font.pixelSize: Theme.currentTheme.typography.bodySize
        text: root.measuredText
    }

    // Same Text type/typography as RinUI's ContextMenu and ListViewDelegate.
    Text {
        id: menuLabelProbe
        visible: false
        typography: Typography.Body
        wrapMode: Text.NoWrap
        text: ""
    }

    implicitWidth: Math.max(
        root.minimumControlWidth,
        Math.min(root.maximumControlWidth, labelMetrics.advanceWidth + 50))

    function entryLabel(entry) {
        if (entry === null || entry === undefined)
            return ""
        if (typeof entry === "object" && root.textRole
                && entry[root.textRole] !== undefined && entry[root.textRole] !== null)
            return String(entry[root.textRole])
        return String(entry)
    }

    // Backend models arrive from Python as array-like QVariantList objects.
    // RinUI's ContextMenu cannot enumerate those reliably, so collect labels
    // here and measure them for the popup.
    function collectLabels() {
        var labels = []
        var source = root.model
        if (source === null || source === undefined)
            return labels

        if (!Array.isArray(source) && typeof source.get !== "function"
                && source.model !== undefined && source.model !== null
                && typeof source.count !== "number")
            source = source.model

        var count = 0
        if (Array.isArray(source))
            count = source.length
        else if (typeof source.count === "number")
            count = source.count
        else if (typeof source.length === "number")
            count = source.length
        else
            return labels

        for (var i = 0; i < count; ++i) {
            var entry = undefined
            try {
                entry = typeof source.get === "function" ? source.get(i) : source[i]
            } catch (error) {
                entry = undefined
            }
            labels.push(root.entryLabel(entry))
        }
        return labels
    }

    function refreshPopupMetrics() {
        var labels = root.collectLabels()
        var widest = 0
        for (var i = 0; i < labels.length; ++i) {
            menuLabelProbe.text = labels[i]
            widest = Math.max(widest, menuLabelProbe.implicitWidth)
        }
        root.measuredWidestLabel = widest
    }

    readonly property real popupMinimumWidth: Math.max(
        root.width,
        root.measuredWidestLabel + root.popupHorizontalPadding)

    Component.onCompleted: root.refreshPopupMetrics()
    onModelChanged: root.refreshPopupMetrics()
    onTextRoleChanged: root.refreshPopupMetrics()

    Binding {
        target: root.popup
        property: "minimumWidth"
        value: root.popupMinimumWidth
        when: root.popup !== null
    }

    // RinUI's ContextMenu selects an index without emitting ComboBox.activated.
    Connections {
        target: root.popup
        function onItemSelected(index) { root.activated(index) }
        function onAboutToShow() { root.refreshPopupMetrics() }
    }
}
