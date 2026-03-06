import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SddmComponents 2.0

Rectangle {
    id: root
    width: 1920
    height: 1080
    color: "#0b0b12"

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0b0b12" }
            GradientStop { position: 1.0; color: "#19142a" }
        }
        opacity: 0.9
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            errorLabel.text = "Authentication failed"
            passwordField.text = ""
            passwordField.forceActiveFocus()
        }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 460
        radius: 12
        color: "#161727"
        border.color: "#ff2bd6"
        border.width: 2
        opacity: 0.95

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 14

            Label {
                text: "Saga // Cyberpunk"
                color: "#f4f2ff"
                font.pixelSize: 30
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
            }

            Label {
                text: Qt.formatDateTime(new Date(), "ddd MMM d  hh:mm")
                color: "#00eaff"
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
                text: "Enter"
                Layout.fillWidth: true
                onClicked: {
                    errorLabel.text = ""
                    sddm.login(userCombo.currentText, passwordField.text, sessionCombo.currentIndex)
                }
            }

            Label {
                id: errorLabel
                text: ""
                color: "#ff4f9f"
                horizontalAlignment: Text.AlignHCenter
                Layout.fillWidth: true
            }
        }
    }
}
