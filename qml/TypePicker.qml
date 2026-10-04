import QtQuick
import RinUI

AutomationComboBox {
    id: root
    property string selectedValue
    signal chosen(string value)
    textRole: "name"
    valueRole: "id"
    minimumControlWidth: 96
    maximumControlWidth: 220
    currentIndex: {
        for (var i = 0; model && i < model.length; ++i)
            if (model[i].id === selectedValue) return i
        return -1
    }
    onActivated: function(index) {
        var value = root.model[index].id
        Qt.callLater(function() { root.chosen(value) })
    }
}