import time
from datetime import datetime
import sqlite3
import sys
import matplotlib
from matplotlib import pyplot as plt
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget
from PyQt5.QtWidgets import QListWidgetItem, QSystemTrayIcon, QStyle
from PyQt5.QtWidgets import QAction, QMenu
from PyQt5.QtCore import Qt, QTimer
from project_editor import ProjectEditorDialog
from compiled_interfaces import *

matplotlib.use('Qt5Agg')


class SessionListWidget(SessionListWidgetInterface, QWidget):
    def __init__(self, *info):
        super().__init__()
        self.setupUi(self)
        self.info = info
        self.init_ui()

    def init_ui(self):
        self.start_time_label.setText(f'Дата начала: {str(self.info[1])}')
        self.end_time_label.setText(f'Дата завершения: {self.info[2]}')
        self.duration_label.setText(f'Продолжительность: {str(self.info[3])}')
        self.task_label.setText(f'Подзадача: {self.info[4]}')
        self.project_label.setText(f'Проект: {self.info[5]}')


class MainWindow(MainWindowInterface, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.connection = sqlite3.connect('database.sqlite')
        self.countdown_start_time = None
        self.selected_task = None
        self.tasks = list()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time_label)
        self.init_ui()

    def init_ui(self):
        self.project_editor_button.clicked.connect(self.show_project_editor)
        self.action_button.clicked.connect(self.switch_countdown)
        self.records_list.itemDoubleClicked.connect(self.delete_session)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        show_action = QAction('Развернуть приложение', self)
        quit_action = QAction('Закрыть приложение', self)
        show_action.triggered.connect(self.show_and_hide_icon)
        quit_action.triggered.connect(self.close)
        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.setVisible(False)

        self.update_tasks_combobox()
        self.update_sessions_list()

    def show_project_editor(self):
        dialog = ProjectEditorDialog(self.connection)
        dialog.exec()
        self.update_tasks_combobox()

    def update_tasks_combobox(self):
        self.task_combobox.clear()
        cursor = self.connection.cursor()
        QUERY = '''
        SELECT tasks.name, projects.name, tasks.id, projects.id FROM
            tasks JOIN projects ON projects.id = tasks.project_id
            WHERE tasks.is_completed = 0
        '''
        results = cursor.execute(QUERY).fetchall()
        self.tasks = [line[2:] for line in results]
        results = [f'{line[0]} ({line[1]})' for line in results]
        self.task_combobox.addItems(results)

    def switch_countdown(self):
        if not self.tasks:
            self.statusbar.showMessage('Для начала создайте проект и добавьте в него подзадачи')
            self.statusbar.setStyleSheet('background-color: rgb(255, 0, 0)')
            return

        self.statusbar.showMessage('')
        self.statusbar.setStyleSheet('')

        if self.countdown_start_time is None:
            self.selected_task = self.tasks[self.task_combobox.currentIndex()]
            self.countdown_start_time = datetime.now()
            self.timer.start()
            self.action_button.setText('Стоп')
        else:
            cursor = self.connection.cursor()
            QUERY = '''
            INSERT INTO
                records(task_id, start_time, end_time, duration)
                VALUES(?, ?, ?, ?)
            '''
            end_time = datetime.now()
            cursor.execute(QUERY, (
                self.selected_task[0],
                self.countdown_start_time.isoformat(),
                end_time.isoformat(),
                (end_time - self.countdown_start_time).seconds
            ))

            QUERY = '''
            UPDATE tasks SET
                total_duration = (SELECT SUM(duration) FROM records WHERE task_id=?)
                WHERE id = ?
            '''
            cursor.execute(QUERY, (self.selected_task[0], self.selected_task[0]))

            QUERY = '''
            UPDATE projects SET
                total_duration = (SELECT SUM(total_duration) FROM tasks WHERE project_id = ?)
                WHERE id = ?
            '''
            cursor.execute(QUERY, (self.selected_task[1], self.selected_task[1]))

            self.connection.commit()

            self.countdown_start_time = None
            self.time_label.setText('00:00:00')
            self.timer.stop()
            self.action_button.setText('Старт')

            self.update_sessions_list()

    def update_sessions_list(self):
        self.records_list.clear()
        cursor = self.connection.cursor()
        QUERY = '''
        SELECT records.id, records.start_time, records.end_time, records.duration, tasks.name, projects.name FROM records
            JOIN tasks ON records.task_id = tasks.id
            JOIN projects ON tasks.project_id = projects.id
        '''
        results = cursor.execute(QUERY).fetchall()
        for line in results:
            widget = SessionListWidget(*line)
            item = QListWidgetItem()
            item.setSizeHint(widget.minimumSizeHint())
            self.records_list.addItem(item)
            self.records_list.setItemWidget(item, widget)

    def show_and_hide_icon(self):
        self.show()
        self.tray_icon.setVisible(False)

    def update_time_label(self):
        if self.countdown_start_time is None:
            return
        delta_time = datetime.now() - self.countdown_start_time
        hours = str(delta_time.seconds // 3600).rjust(2, '0')
        minutes = str(delta_time.seconds // 60).rjust(2, '0')
        seconds = str(delta_time.seconds % 60).rjust(2, '0')
        self.time_label.setText(f'{hours}:{minutes}:{seconds}')

    def delete_session(self, item):
        dialog = QMessageBox()
        dialog.setWindowTitle('Удаление записи')
        dialog.setText('Действительно хотите удалить запись?')
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        result = dialog.exec()
        if result == QMessageBox.Yes:
            info = self.records_list.itemWidget(item).info
            cursor = self.connection.cursor()
            QUERY = '''
            DELETE FROM records
                WHERE id = {}
            '''.format(info[0])
            cursor.execute(QUERY)
            self.connection.commit()
            self.update_sessions_list()
        else:
            return

    def closeEvent(self, event):
        dialog = QMessageBox()
        dialog.setWindowTitle('Точно ли вы хотите закрыть приложение?')
        dialog.setText('Да - свернуть, нет - закрыть')
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        result = dialog.exec()
        if result == QMessageBox.Yes:
            # Скрываем окно приложения и показываем иконку в трее
            self.hide()
            self.tray_icon.setVisible(True)
            event.ignore()
        elif result == QMessageBox.No:
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
