import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
                               QLineEdit, QCheckBox, QComboBox, QProgressBar, QLabel,
                               QMessageBox, QTextEdit)
from PySide6.QtCore import Qt
from src.utils import Worker


class Tab1Widget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # Directory selection
        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit()
        self.dir_input.setMinimumHeight(40)
        dir_button = QPushButton('Select Directory')
        dir_button.setMinimumHeight(40)
        dir_button.clicked.connect(self.select_directory)
        dir_layout.addWidget(QLabel('Directory:'))
        dir_layout.addWidget(self.dir_input, 1)
        dir_layout.addWidget(dir_button)
        layout.addLayout(dir_layout)

        # URL input
        self.url_input = QLineEdit()
        self.url_input.setMinimumHeight(40)
        self.url_input.setPlaceholderText('Enter URL here')
        layout.addWidget(QLabel('URL:'))
        layout.addWidget(self.url_input)

        # Checkbox
        self.checkbox = QCheckBox('Optional Checkbox')
        self.checkbox.setMinimumHeight(40)
        layout.addWidget(self.checkbox)

        # Dropdown
        self.dropdown = QComboBox()
        self.dropdown.setMinimumHeight(40)
        self.dropdown.addItems(['Option 1', 'Option 2', 'Option 3'])
        layout.addWidget(QLabel('Dropdown:'))
        layout.addWidget(self.dropdown)

        # Start/Cancel button
        self.start_cancel_button = QPushButton('Start Process')
        self.start_cancel_button.setMinimumHeight(50)
        self.start_cancel_button.clicked.connect(self.toggle_process)
        layout.addWidget(self.start_cancel_button)

        # Step name label
        self.step_label = QLabel('Ready')
        layout.addWidget(self.step_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(30)
        layout.addWidget(self.progress_bar)

        # Error display area
        self.error_display = QTextEdit()
        self.error_display.setReadOnly(True)
        self.error_display.setMinimumHeight(100)
        self.error_display.setVisible(False)
        layout.addWidget(self.error_display)

        layout.addStretch()

        self.worker = None
        self.is_processing = False

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, 'Select Directory')
        if directory:
            self.dir_input.setText(directory)

    def toggle_process(self):
        if not self.is_processing:
            self.start_process()
        else:
            self.cancel_process()

    def start_process(self):
        if not self.dir_input.text():
            QMessageBox.warning(self, 'Error', 'Please select a directory.')
            return
        if not self.url_input.text():
            QMessageBox.warning(self, 'Error', 'Please enter a URL.')
            return

        self.is_processing = True
        self.start_cancel_button.setText('Cancel')
        self.progress_bar.setValue(0)
        self.error_display.clear()
        self.error_display.setVisible(False)

        self.worker = Worker(self.dir_input.text(), self.url_input.text())
        self.worker.step_name.connect(self.update_step_name)
        self.worker.progress.connect(self.update_progress)
        self.worker.error.connect(self.display_error)
        self.worker.finished.connect(self.process_finished)
        self.worker.start()

    def cancel_process(self):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.start_cancel_button.setText('Cancelling...')
            self.start_cancel_button.setEnabled(False)
            self.process_finished()

    def update_step_name(self, step_name):
        self.step_label.setText(step_name)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def display_error(self, error_msg):
        self.error_display.setVisible(True)
        self.error_display.setTextColor(Qt.red)
        self.error_display.append(error_msg)
        self.process_finished()

    def process_finished(self):
        self.is_processing = False
        self.start_cancel_button.setText('Start Process')
        self.start_cancel_button.setEnabled(True)
        if self.progress_bar.value() == 100:
            QMessageBox.information(self, 'Success', 'Process completed successfully!')
        elif not self.error_display.isVisible():
            QMessageBox.information(self, 'Cancelled', 'Process has been cancelled.')
