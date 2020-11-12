from sqlite3 import IntegrityError
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QWidget, QListWidgetItem
from PyQt5.QtWidgets import QMessageBox, QColorDialog
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPainterPath


class ProjectListWidget(QWidget):
    def __init__(self, project_id, name, total_duration, tasks_amount):
        super().__init__()
        uic.loadUi('ui_files/project_listwidget.ui', self)
        self.info = [project_id, name, total_duration, tasks_amount]
        self.init_ui()

    def init_ui(self):
        self.name_label.setText(f'Проект: {self.info[1]}')
        self.duration_label.setText(f'Затрачено времени: {self.info[2]}')
        self.tasks_label.setText(f'Количество подзадач: {self.info[3]}')


class TaskListWidget(QWidget):
    def __init__(self, task_id, project_id, name, total_duration,
                 is_completed, color, connection):
        super().__init__()
        uic.loadUi('ui_files/task_listwidget.ui', self)
        color = tuple(map(int, color.split(', ')))
        self.info = [task_id, project_id, name, total_duration, is_completed, color]
        self.connection = connection
        self.init_ui()

    def set_rounded_pixmap(self):
        size = self.picture_label.minimumSizeHint().height()
        radius = size // 2
        color = QColor(*self.info[5])
        target = QPixmap(QSize(size, size))
        target.fill(Qt.transparent)
        painter = QPainter()
        painter.begin(target)

        pixmap = QPixmap(QSize(size, size))
        pixmap.fill(color)

        # Разобраться как это работает, пока что просто копипаста из интернета.
        path = QPainterPath()
        path.addRoundedRect(0, 0, size, size, radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        self.picture_label.setPixmap(target)

    def init_ui(self):
        self.set_rounded_pixmap()
        self.state_checkbox.stateChanged.connect(self.checkbox_state_changed)
        self.name_label.setText(f'Подзадача: {self.info[2]}')
        self.state_checkbox.setChecked(bool(self.info[4]))
        self.duration_label.setText(f'Затрачено времени: {self.info[3]}')

    def checkbox_state_changed(self, new_state):
        new_state = 1 if new_state else 0
        cursor = self.connection.cursor()
        QUERY = '''
        UPDATE tasks SET
            is_completed = ?
            WHERE id = ?
        '''
        cursor.execute(QUERY, (new_state, self.info[0]))
        self.connection.commit()


class ProjectEditDialog(QDialog):
    def __init__(self, connection, update_id=None):
        super().__init__()
        uic.loadUi('ui_files/project_creation_dialog.ui', self)
        self.connection = connection
        self.update_id = update_id
        self.new_name = None
        self.init_ui()

    def init_ui(self):
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.create_button.clicked.connect(self.create_record)

    def create_record(self):
        name = self.name_edit.text().strip().lower()
        if not name:
            self.name_label.setStyleSheet('background-color: rgb(255, 0, 0)')
            self.error_label.setText('Вы не ввели название проекта')
            return

        cursor = self.connection.cursor()
        if self.update_id is None:
            QUERY = '''
            INSERT INTO projects(name) VALUES('{}')
            '''.format(name)
        else:
            QUERY = '''
            UPDATE projects SET name = '{}'
                WHERE id = {}
            '''.format(name, self.update_id)

        try:
            cursor.execute(QUERY)
        except IntegrityError:
            self.name_label.setStyleSheet('background-color: rgb(255, 0, 0)')
            self.error_label.setText('Проект с таким названием уже существует')
            return

        self.new_name = name
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
        self.projects_list.itemDoubleClicked.connect(self.show_info_dialog)
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

            widget = ProjectListWidget(project_id, name, duration, tasks)
            item = QListWidgetItem()
            item.setSizeHint(widget.minimumSizeHint())
            self.projects_list.addItem(item)
            self.projects_list.setItemWidget(item, widget)

    def show_creation_dialog(self):
        dialog = ProjectEditDialog(self.connection)
        dialog.exec()
        self.update_projects_list()

    def show_info_dialog(self, item):
        info = self.projects_list.itemWidget(item).info
        dialog = ProjectInfoDialog(self.connection, info)
        dialog.exec()
        self.update_projects_list()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class ProjectInfoDialog(QDialog):
    def __init__(self, connection, info):
        super().__init__()
        uic.loadUi('ui_files/project_info_dialog.ui', self)
        self.connection = connection
        self.info = info
        self.init_ui()

    def init_ui(self):
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.name_label.setText(f'Проект "{self.info[1]}"')
        self.edit_button.clicked.connect(self.show_edit_dialog)
        self.delete_button.clicked.connect(self.show_delete_dialog)
        self.create_button.clicked.connect(self.show_task_add_dialog)
        self.tasks_list.itemDoubleClicked.connect(self.show_task_info_dialog)

        self.update_tasks_list()

    def show_edit_dialog(self):
        dialog = ProjectEditDialog(self.connection, self.info[0])
        dialog.exec()
        if dialog.new_name is not None:
            self.info[1] = dialog.new_name
        self.name_label.setText(f'Проект "{self.info[1]}"')

    def update_tasks_list(self):
        self.tasks_list.clear()
        QUERY = '''
        SELECT id FROM tasks
            WHERE project_id = ?
        '''

        cursor = self.connection.cursor()
        ids = [el[0] for el in cursor.execute(QUERY, (self.info[0],)).fetchall()]

        for task_id in ids:
            QUERY = '''
            SELECT name, total_duration, is_completed, color FROM tasks
                WHERE id = ?
            '''

            elements = cursor.execute(QUERY, (task_id,)).fetchone()

            widget = TaskListWidget(task_id, self.info[0], *elements, self.connection)
            item = QListWidgetItem()
            item.setSizeHint(widget.minimumSizeHint())
            self.tasks_list.addItem(item)
            self.tasks_list.setItemWidget(item, widget)

    def show_task_add_dialog(self):
        dialog = TaskEditDialog(self.connection, project_id=self.info[0])
        dialog.exec()
        self.update_tasks_list()

    def show_task_info_dialog(self, item):
        info = self.tasks_list.itemWidget(item).info
        dialog = TaskInfoDialog(self.connection, info)
        dialog.exec()
        self.update_tasks_list()

    def show_delete_dialog(self):
        dialog = QMessageBox()
        dialog.setWindowTitle('Удаление проекта')
        dialog.setText('Действительно хотите удалить проект?')
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        result = dialog.exec()
        if result == QMessageBox.Yes:
            cursor = self.connection.cursor()
            QUERY = '''
            DELETE FROM projects
                WHERE id = ?
            '''
            cursor.execute(QUERY, (self.info[0],))
            self.connection.commit()
            self.close()
        else:
            return

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class TaskEditDialog(QDialog):
    def __init__(self, connection, project_id=None, update_id=None):
        super().__init__()
        uic.loadUi('ui_files/task_edit_dialog.ui', self)
        self.connection = connection
        self.update_id = update_id
        self.project_id = project_id
        self.new_name = None
        self.new_color = None
        self.init_ui()

    def init_ui(self):
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.color_edit.setEnabled(False)
        self.create_button.clicked.connect(self.create_record)

    def create_record(self):
        name = self.name_edit.text().strip().lower()
        color = self.color_edit.text().strip()
        print(name, color)
        print(name and not color)

        self.error_label.setText('Нажмите Ctrl + G чтобы открыть средство для подбора цвета')
        if not name and color:
            self.error_label.setText('Вы не ввели название подзадачи')
            self.name_label.setStyleSheet('background-color: rgb(255, 0, 0)')
            self.color_label.setStyleSheet('')
            return
        elif name and not color:
            self.error_label.setText('Вы не выбрали цвет')
            self.name_label.setStyleSheet('')
            self.color_label.setStyleSheet('background-color: rgb(255, 0, 0)')
            return
        elif not name and not color:
            self.error_label.setText('Вы не ввели название и не выбрали цвет')
            self.name_label.setStyleSheet('background-color: rgb(255, 0, 0)')
            self.color_label.setStyleSheet('background-color: rgb(255, 0, 0)')
            return

        cursor = self.connection.cursor()

        if self.update_id is not None:
            QUERY = '''
            UPDATE tasks SET
                name = '{}',
                color = '{}'
                WHERE id = {}
            '''.format(name, color, self.update_id)
        else:
            QUERY = '''
            INSERT INTO tasks(project_id, name, color) VALUES({}, '{}', '{}')
            '''.format(self.project_id, name, color)

        print(QUERY)

        try:
            cursor.execute(QUERY)
        except IntegrityError:
            self.error_label.setText('Подзадача с таким именем/цветом уже существует')
            return

        self.new_name = name
        self.new_color = color

        self.connection.commit()
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_G:
            dialog = QColorDialog()
            result = dialog.getColor().getRgb()[:-1]
            self.color_edit.setText(f'{result[0]}, {result[1]}, {result[2]}')


class TaskInfoDialog(QDialog):
    def __init__(self, connection, info):
        super().__init__()
        uic.loadUi('ui_files/task_info_dialog.ui', self)
        self.connection = connection
        self.info = info
        self.init_ui()

    def init_ui(self):
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.name_label.setText(f'Подзадача "{self.info[2]}"')
        self.edit_button.clicked.connect(self.show_edit_dialog)
        self.delete_button.clicked.connect(self.show_delete_dialog)

    def show_edit_dialog(self):
        dialog = TaskEditDialog(self.connection, update_id=self.info[0])
        dialog.exec()
        if dialog.new_name is not None:
            self.info[2] = dialog.new_name
        self.name_label.setText(f'Подзадача "{self.info[2]}"')

    def show_delete_dialog(self):
        dialog = QMessageBox()
        dialog.setWindowTitle('Удаление проекта')
        dialog.setText('Действительно хотите удалить подзадачу?')
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        result = dialog.exec()
        if result == QMessageBox.Yes:
            cursor = self.connection.cursor()
            QUERY = '''
            DELETE FROM tasks
                WHERE id = ?
            '''
            cursor.execute(QUERY, (self.info[0],))
            self.connection.commit()
            self.close()
        else:
            return
