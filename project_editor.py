from sqlite3 import IntegrityError
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import Qt


class ProjectCreationDialog(QDialog):
    def __init__(self, connection):
        super().__init__()
        uic.loadUi('ui_files/project_creation_dialog.ui', self)
        self.init_ui()
        self.connection = connection

    def init_ui(self):
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.create_button.clicked.connect(self.create_record)

    def create_record(self):
        name = self.name_edit.text().strip()
        if not name:
            self.name_label.setStyleSheet('background-color: rgb(255, 0, 0)')
            self.error_label.setText('Вы не ввели название проекта')
            return

        cursor = self.connection.cursor()
        QUERY = '''
        INSERT INTO projects(name) VALUES(?)
        '''

        try:
            cursor.execute(QUERY, (name,))
        except IntegrityError:
            self.name_label.setStyleSheet('background-color: rgb(255, 0, 0)')
            self.error_label.setText('Проект с таким названием уже существует')
            return

        self.connection.commit()
        self.close()


class ProjectEditorDialog(QDialog):
    def __init__(self, connection):
        super().__init__()
        uic.loadUi('ui_files/project_editor_dialog.ui', self)
        self.init_ui()
        self.connection = connection

    def init_ui(self):
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.create_button.clicked.connect(self.show_creation_dialog)

    def show_creation_dialog(self):
        dialog = ProjectCreationDialog(self.connection)
        dialog.exec()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
