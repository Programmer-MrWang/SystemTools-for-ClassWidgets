import QtQuick
import RinUI

Segmented {
    id: root
    property string mode: "all"
    property string anyText
    property string allText
    property string namePrefix
    signal chosen(string mode)
    currentIndex: mode === "any" ? 0 : 1

    SegmentedItem {
        objectName: root.namePrefix + "AnyButton"
        text: root.anyText
        onClicked: root.chosen("any")
    }
    SegmentedItem {
        objectName: root.namePrefix + "AllButton"
        text: root.allText
        onClicked: root.chosen("all")
    }
}
