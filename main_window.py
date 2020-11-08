import sqlite3
import sys
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import Qt
from project_editor import ProjectEditorDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('ui_files/timetracker_main.ui', self)
        self.init_ui()
        self.connection = sqlite3.connect('database.sqlite')

    def init_ui(self):
        self.project_editor_button.clicked.connect(self.show_project_editor)

    def show_project_editor(self):
        dialog = ProjectEditorDialog(self.connection)
        dialog.exec()

    def closeEvent(self, event):
        self.connection.close()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec())
