import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SddmComponents 2.0

Rectangle {
    id: root
    width: 1920
    height: 1080
    color: "#11131a"

    Connections {
        target: sddm
        function onLoginFailed() {
            errorLabel.text = "Authentication failed"
            passwordField.text = ""
            passwordField.forceActiveFocus()
        }
    }

    ColumnLayout {
        anchors.centerIn: parent
        spacing: 14
        width: 420

        Label {
            text: "Saga"
            color: "#e8eefc"
            font.pixelSize: 34
            horizontalAlignment: Text.AlignHCenter
            Layout.fillWidth: true
        }

        Label {
            text: Qt.formatDateTime(new Date(), "ddd MMM d  hh:mm")
            color: "#9fb0cf"
            font.pixelSize: 14
            horizontalAlignment: Text.AlignHCenter
            Layout.fillWidth: true
        }

        ComboBox {
            id: userCombo
            model: userModel
            textRole: "name"
            Layout.fillWidth: true
        }

        TextField {
            id: passwordField
            echoMode: TextInput.Password
            placeholderText: "Password"
            Layout.fillWidth: true
            onAccepted: loginButton.clicked()
        }

        ComboBox {
            id: sessionCombo
            model: sessionModel
            textRole: "name"
            Layout.fillWidth: true
        }

        Button {
            id: loginButton
            text: "Login"
            Layout.fillWidth: true
            onClicked: {
                errorLabel.text = ""
                sddm.login(userCombo.currentText, passwordField.text, sessionCombo.currentIndex)
            }
        }

        Label {
            id: errorLabel
            text: ""
            color: "#ff5e8c"
            horizontalAlignment: Text.AlignHCenter
            Layout.fillWidth: true
        }
    }
}
