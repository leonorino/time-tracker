from sqlite3 import IntegrityError
from datetime import datetime
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QWidget, QListWidgetItem
from PyQt5.QtWidgets import QMessageBox, QColorDialog
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPainterPath
from compiled_interfaces import *

class ProjectListWidget(ProjectListWidgetInterface, QWidget):
    def __init__(self, *args):
        super().__init__()
        self.setupUi(self)
        args = list(args)
        self.info = args
        self.init_ui()

    def init_ui(self):
        self.name_label.setText(f'Проект: {self.info[1]}')
        self.duration_label.setText(f'Затрачено времени: {self.info[2]}')
        self.tasks_label.setText(f'Количество подзадач: {self.info[3]}')


class TaskListWidget(TaskListWidgetInterface, QWidget):
    def __init__(self, *args, connection):
        super().__init__()
        self.setupUi(self)
        args = list(args)
        args[5] = map(int, args[5].split(', '))
        self.info = args
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


class ProjectEditDialog(ProjectEditDialogInterface, QDialog):
    def __init__(self, connection, update_id=None):
        super().__init__()
        self.setupUi(self)
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
            INSERT INTO projects(name, creation_date) VALUES('{}', '{}')
            '''.format(name, datetime.now().isoformat())
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


class ProjectEditorDialog(ProjectEditorDialogInterface, QDialog):
    def __init__(self, connection):
        super().__init__()
        self.setupUi(self)
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
            SELECT name, total_duration, creation_date FROM projects
                WHERE id = ?
            '''
            name, duration, creation_date = cursor.execute(QUERY, (project_id,)).fetchone()

            QUERY = '''
            SELECT COUNT(*) FROM tasks
                WHERE project_id = ?
            '''
            tasks = cursor.execute(QUERY, (project_id,)).fetchone()[0]

            widget = ProjectListWidget(project_id, name, duration, tasks, creation_date)
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


class ProjectInfoDialog(ProjectInfoDialogInterface, QDialog):
    def __init__(self, connection, info):
        super().__init__()
        self.setupUi(self)
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
        self.prepare_chart()

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
            SELECT name, total_duration, is_completed, color, creation_date FROM tasks
                WHERE id = ?
            '''

            elements = cursor.execute(QUERY, (task_id,)).fetchone()

            widget = TaskListWidget(task_id, self.info[0], *elements, connection=self.connection)
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
            DELETE FROM tasks
                WHERE project_id = ?
            '''
            cursor.execute(QUERY, (self.info[0],))
            QUERY = '''
            DELETE FROM projects
                WHERE id = ?
            '''
            cursor.execute(QUERY, (self.info[0],))
            self.connection.commit()
            self.close()
        else:
            return

    def prepare_chart(self):
        cursor = self.connection.cursor()
        QUERY = '''
        SELECT * FROM records
            WHERE task_id IN (
                SELECT id FROM tasks
                    WHERE project_id = ?
            )
        '''
        data = dict()
        result = cursor.execute(QUERY, (self.info[0], )).fetchall()
        creation_date = datetime.fromisoformat(self.info[-1])
        for line in result:
            task_id = line[1]
            start_delta = (datetime.fromisoformat(line[2]) - creation_date).seconds / 60
            duration = (datetime.fromisoformat(line[3]) - datetime.fromisoformat(line[2])).seconds / 60
            if task_id in data:
                data[task_id].append((start_delta, duration))
            else:
                data[task_id] = list()
                data[task_id].append((start_delta, duration))

        labels = list()
        for index, (key, data_line) in enumerate(data.items()):
            QUERY = '''
            SELECT name, color FROM tasks
                WHERE id = ?
            '''
            result = cursor.execute(QUERY, (key,)).fetchone()
            labels.append(result[0])
            color = tuple(map(int, result[1].split(', ')))
            color = f"#{''.join(f'{hex(c)[2:].upper():0>2}' for c in color)}"
            self.chart_widget.axes.broken_barh([*data_line], [5 + 15 * index, 10], facecolors=color)

        self.chart_widget.axes.set_yticks([10 + 15 * index for index in range(len(labels))])
        self.chart_widget.axes.set_yticklabels(labels)
        self.chart_widget.axes.grid(True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class TaskEditDialog(TaskEditDialogInterface, QDialog):
    def __init__(self, connection, project_id=None, update_id=None):
        super().__init__()
        self.setupUi(self)
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
            INSERT INTO tasks(project_id, name, color, creation_date) VALUES({}, '{}', '{}', '{}')
            '''.format(self.project_id, name, color, datetime.now().isoformat())

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


class TaskInfoDialog(TaskInfoDialogInterface, QDialog):
    def __init__(self, connection, info):
        super().__init__()
        self.setupUi(self)
        self.connection = connection
        self.info = info
        self.init_ui()

    def init_ui(self):
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.name_label.setText(f'Подзадача "{self.info[2]}"')
        self.edit_button.clicked.connect(self.show_edit_dialog)
        self.delete_button.clicked.connect(self.show_delete_dialog)

        self.prepare_chart()

    def prepare_chart(self):
        cursor = self.connection.cursor()
        QUERY = '''
        SELECT * FROM records WHERE task_id = {}
            ORDER BY datetime(start_time) ASC
        '''.format(self.info[0])
        plot = (list(), list())
        duration = 0
        start_time = datetime.fromisoformat(self.info[-1])
        result = cursor.execute(QUERY).fetchall()
        for line in result:
            session_start_time = datetime.fromisoformat(line[2])
            delta = (session_start_time - start_time).seconds // 60
            duration += line[4] / 60
            plot[0].append(delta)
            plot[1].append(duration)

        self.chart_widget.axes.plot(*plot)

    def show_edit_dialog(self):
        dialog = TaskEditDialog(self.connection, update_id=self.info[0])
        dialog.exec()
        if dialog.new_name is not None:
            self.info[2] = dialog.new_name
        self.name_label.setText(f'Подзадача "{self.info[2]}"')

    def show_delete_dialog(self):
        dialog = QMessageBox()
        dialog.setWindowTitle('Удаление подзадачи')
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

            QUERY = '''
            DELETE FROM records
                WHERE task_id = ?
            '''
            cursor.execute(QUERY, (self.info[0],))

            self.connection.commit()
            self.close()
        else:
            return
