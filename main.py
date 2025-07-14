import sys
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QTabWidget, QTextEdit, QLineEdit,
                               QPushButton, QListWidget, QLabel, QDialog,
                               QDialogButtonBox, QFormLayout, QFileDialog,
                               QMessageBox, QSplitter, QFrame)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from database_setup import DatabaseSetup
from GatewayRouterAgent import GatewayRouterAgent
import sqlite3


class ComponentDialog(QDialog):
    def __init__(self, parent=None, component_data=None):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit Component")
        self.setModal(True)
        self.resize(400, 300)

        layout = QFormLayout()

        self.name_input = QLineEdit()
        self.file_input = QLineEdit()
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_input)
        file_btn = QPushButton("Browse")
        file_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(file_btn)

        layout.addRow("Component Name:", self.name_input)
        layout.addRow("Python File:", file_layout)
        layout.addRow("Description:", self.description_input)

        if component_data:
            self.name_input.setText(component_data[0])
            self.file_input.setText(component_data[1])
            self.description_input.setPlainText(component_data[2])

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addRow(buttons)
        self.setLayout(layout)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Python File", "", "Python Files (*.py)")
        if file_path:
            self.file_input.setText(file_path)

    def get_data(self):
        return {
            'name': self.name_input.text(),
            'file': self.file_input.text(),
            'description': self.description_input.toPlainText()
        }


class SettingsWidget(QWidget):
    def __init__(self, db_setup):
        super().__init__()
        self.db_setup = db_setup
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()

        # API Key section
        api_layout = QFormLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        api_layout.addRow("Gemini API Key:", self.api_key_input)

        save_api_btn = QPushButton("Save API Key")
        save_api_btn.clicked.connect(self.save_api_key)
        api_layout.addRow(save_api_btn)

        layout.addLayout(api_layout)

        # Components section
        layout.addWidget(QLabel("Component Management"))

        self.components_list = QListWidget()
        layout.addWidget(self.components_list)

        btn_layout = QHBoxLayout()
        add_component_btn = QPushButton("Add Component")
        edit_component_btn = QPushButton("Edit Component")
        delete_component_btn = QPushButton("Delete Component")

        add_component_btn.clicked.connect(self.add_component)
        edit_component_btn.clicked.connect(self.edit_component)
        delete_component_btn.clicked.connect(self.delete_component)

        btn_layout.addWidget(add_component_btn)
        btn_layout.addWidget(edit_component_btn)
        btn_layout.addWidget(delete_component_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.load_components()

    def load_settings(self):
        conn = self.db_setup.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM Settings WHERE key = 'gemini_api_key'")
        result = cursor.fetchone()
        if result:
            self.api_key_input.setText(result[0])
        conn.close()

    def save_api_key(self):
        api_key = self.api_key_input.text()
        conn = self.db_setup.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO Settings (key, value) VALUES (?, ?)",
                       ("gemini_api_key", api_key))
        conn.commit()
        conn.close()
        QMessageBox.information(self, "Success", "API Key saved successfully!")

    def load_components(self):
        self.components_list.clear()
        conn = self.db_setup.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ComponentName, PythonFile, Description FROM ComponentLookup")
        components = cursor.fetchall()
        conn.close()

        for component in components:
            self.components_list.addItem(f"{component[0]} - {component[2]}")

    def add_component(self):
        dialog = ComponentDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if data['name'] and data['file'] and data['description']:
                conn = self.db_setup.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO ComponentLookup (ComponentName, PythonFile, Description) VALUES (?, ?, ?)",
                    (data['name'], data['file'], data['description']))
                conn.commit()
                conn.close()
                self.load_components()
                QMessageBox.information(self, "Success", "Component added successfully!")

    def edit_component(self):
        current_item = self.components_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a component to edit.")
            return

        component_name = current_item.text().split(' - ')[0]
        conn = self.db_setup.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ComponentName, PythonFile, Description FROM ComponentLookup WHERE ComponentName = ?",
                       (component_name,))
        component_data = cursor.fetchone()
        conn.close()

        if component_data:
            dialog = ComponentDialog(self, component_data)
            if dialog.exec() == QDialog.Accepted:
                data = dialog.get_data()
                if data['name'] and data['file'] and data['description']:
                    conn = self.db_setup.get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE ComponentLookup SET ComponentName = ?, PythonFile = ?, Description = ? WHERE ComponentName = ?",
                        (data['name'], data['file'], data['description'], component_name))
                    conn.commit()
                    conn.close()
                    self.load_components()
                    QMessageBox.information(self, "Success", "Component updated successfully!")

    def delete_component(self):
        current_item = self.components_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a component to delete.")
            return

        component_name = current_item.text().split(' - ')[0]
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete component '{component_name}'?")
        if reply == QMessageBox.Yes:
            conn = self.db_setup.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ComponentLookup WHERE ComponentName = ?", (component_name,))
            conn.commit()
            conn.close()
            self.load_components()
            QMessageBox.information(self, "Success", "Component deleted successfully!")


class ChatWidget(QWidget):
    def __init__(self, db_setup):
        super().__init__()
        self.db_setup = db_setup
        self.router_agent = GatewayRouterAgent(db_setup)
        self.chat_history = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Consolas", 10))
        layout.addWidget(self.chat_display)

        # Input area
        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type your message here...")
        self.chat_input.returnPressed.connect(self.send_message)

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_message)

        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(send_btn)

        layout.addLayout(input_layout)
        self.setLayout(layout)

    def send_message(self):
        message = self.chat_input.text().strip()
        if not message:
            return

        # Add user message to chat
        self.add_message("User", message)
        self.chat_input.clear()

        # Process message through router
        try:
            response = self.router_agent.process_request(message, self.chat_history)
            self.add_message("Assistant", response)
        except Exception as e:
            self.add_message("System", f"Error: {str(e)}")

    def add_message(self, sender, message):
        self.chat_history.append({"sender": sender, "message": message})
        self.chat_display.append(f"<b>{sender}:</b> {message}")
        self.chat_display.ensureCursorVisible()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_setup = DatabaseSetup()
        self.setWindowTitle("Modular Chat Task Management")
        self.setGeometry(100, 100, 1200, 800)

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout with splitter
        main_layout = QHBoxLayout()
        splitter = QSplitter(Qt.Horizontal)

        # Left side menu
        left_menu = QFrame()
        left_menu.setFrameStyle(QFrame.StyledPanel)
        left_menu.setFixedWidth(200)

        menu_layout = QVBoxLayout()
        menu_layout.addWidget(QLabel("Menu"))

        # Menu buttons
        chat_btn = QPushButton("Chat")
        settings_btn = QPushButton("Settings")

        chat_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(0))
        settings_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(1))

        menu_layout.addWidget(chat_btn)
        menu_layout.addWidget(settings_btn)
        menu_layout.addStretch()

        left_menu.setLayout(menu_layout)
        splitter.addWidget(left_menu)

        # Main content area with tabs
        self.tab_widget = QTabWidget()

        # Chat tab
        self.chat_widget = ChatWidget(self.db_setup)
        self.tab_widget.addTab(self.chat_widget, "Chat")

        # Settings tab
        self.settings_widget = SettingsWidget(self.db_setup)
        self.tab_widget.addTab(self.settings_widget, "Settings")

        splitter.addWidget(self.tab_widget)
        splitter.setSizes([200, 1000])

        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()