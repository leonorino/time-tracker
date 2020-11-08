from sqlite3 import IntegrityError
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QWidget, QListWidgetItem
from PyQt5.QtCore import Qt


class ProjectListWidget(QWidget):
    def __init__(self, name, total_duration, tasks_amount):
        super().__init__()
        uic.loadUi('ui_files/project_listwidget.ui', self)
        self.init_ui(name, total_duration, tasks_amount)

    def init_ui(self, name, total_duration, tasks_amount):
        self.name_label.setText(f'Проект: {name}')
        self.duration_label.setText(f'Затрачено времени: {total_duration}')
        self.tasks_label.setText(f'Количество подзадач: {tasks_amount}')


class ProjectCreationDialog(QDialog):
    def __init__(self, connection):
        super().__init__()
        uic.loadUi('ui_files/project_creation_dialog.ui', self)
        self.connection = connection
        self.init_ui()

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
        self.connection = connection
        self.init_ui()

    def init_ui(self):
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.create_button.clicked.connect(self.show_creation_dialog)
        self.update_projects_list()

    def update_projects_list(self):
        self.projects_list.clear()

        cursor = self.connection.cursor()
        QUERY = '''
        SELECT id FROM projects
        '''
        ids = [el[0] for el in cursor.execute(QUERY).fetchall()]

        for project_id in ids:
            QUERY = '''
            SELECT name, total_duration FROM projects
                WHERE id = ?
            '''
            name, duration = cursor.execute(QUERY, (project_id,)).fetchone()

            QUERY = '''
            SELECT COUNT(*) FROM tasks
                WHERE project_id = ?
            '''
            tasks = cursor.execute(QUERY, (project_id,)).fetchone()[0]

            widget = ProjectListWidget(name, duration, tasks)
            item = QListWidgetItem()
            item.setSizeHint(widget.minimumSizeHint())
            self.projects_list.addItem(item)
            self.projects_list.setItemWidget(item, widget)

    def show_creation_dialog(self):
        dialog = ProjectCreationDialog(self.connection)
        dialog.exec()
        self.update_projects_list()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
