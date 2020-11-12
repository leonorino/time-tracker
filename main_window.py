import asyncio
import time
from datetime import datetime
import sqlite3
import sys
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from project_editor import ProjectEditorDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('ui_files/timetracker_main.ui', self)
        self.connection = sqlite3.connect('database.sqlite')
        self.countdown_start_time = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time_label)
        self.tasks = list()

        self.init_ui()

    def init_ui(self):
        self.project_editor_button.clicked.connect(self.show_project_editor)
        self.action_button.clicked.connect(self.switch_countdown)
        self.update_tasks_combobox()

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
        '''
        results = cursor.execute(QUERY).fetchall()
        self.tasks = [line[2:] for line in results]
        results = [f'{line[0]} ({line[1]})' for line in results]
        self.task_combobox.addItems(results)

    def paintEvent(self, event):
        self.update_time_label()

    def switch_countdown(self):
        if not self.tasks:
            return

        if self.countdown_start_time is None:
            selected_task = self.tasks[self.task_combobox.currentIndex()]
            self.countdown_start_time = datetime.now()
            self.timer.start()
            self.action_button.setText('Стоп')
        else:
            self.countdown_start_time = None
            self.time_label.setText('00:00:00')
            self.timer.stop()
            self.action_button.setText('Старт')
            # TODO: Создать запись тут

    def update_time_label(self):
        if self.countdown_start_time is None:
            return
        delta_time = datetime.now() - self.countdown_start_time
        hours = str(delta_time.seconds // 3600).rjust(2, '0')
        minutes = str(delta_time.seconds // 60).rjust(2, '0')
        seconds = str(delta_time.seconds % 60).rjust(2, '0')
        self.time_label.setText(f'{hours}:{minutes}:{seconds}')

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
