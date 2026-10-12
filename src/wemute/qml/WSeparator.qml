import QtQuick
import QtQuick.Controls
import "."

MenuSeparator {
    topPadding: 4
    bottomPadding: 4
    leftPadding: 8
    rightPadding: 8
    implicitHeight: visible ? 9 : 0
    contentItem: Rectangle {
        implicitHeight: 1
        color: Theme.hairline
    }
}
