import os

import torch
from PySide6.QtCore import Qt, QTime, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
                               QLineEdit, QCheckBox, QComboBox, QProgressBar, QLabel,
                               QMessageBox, QTextEdit)

from src.constants import STEP_LABEL, BUTTON_LABEL
from src.utils import Worker, ModelLoader, ClickableLineEdit, StyledButton


class Tab1Widget(QWidget):
    def __init__(self, store):
        super().__init__()

        # init UI
        layout = QVBoxLayout(self)

        # Directory selection
        dir_layout = QHBoxLayout()
        self.save_file_input = ClickableLineEdit(self.get_save_file)
        self.save_file_input.setMinimumHeight(40)
        self.save_file_input.setPlaceholderText(
            'ダウンロードしたチャットの保存先を入力（既存のファイルを選択した場合はそのファイルの感情分析を実行）'
        )
        dir_button = QPushButton('名前をつけてチャットを保存')
        dir_button.setMinimumHeight(40)
        dir_button.clicked.connect(self.get_save_file)
        dir_layout.addWidget(QLabel('保存先:'))
        dir_layout.addWidget(self.save_file_input, 1)
        dir_layout.addWidget(dir_button)
        layout.addLayout(dir_layout)

        # URL input
        self.url_input = QLineEdit()
        self.url_input.setMinimumHeight(40)
        self.url_input.setPlaceholderText('YoutubeかTwitchのURLを入力（上で既存のファイルを選択している場合は不要）')
        layout.addWidget(QLabel('URL:'))
        layout.addWidget(self.url_input)
        layout.addSpacing(10)

        cuda_label = 'GPU(CUDA)モードで実行されます。' if torch.cuda.is_available() else 'CPUモードで実行されます。'
        cuda_link = QLabel('Nvidia GPU(RTX3060等)搭載PCの方はCUDA Toolkit12.1以上をインストールすることで高速化することが出来ます。→'
                           '''<a href='https://developer.nvidia.com/cuda-12-1-1-download-archive'>CUDA download</a>''')
        cuda_link.setOpenExternalLinks(True)
        layout.addWidget(cuda_link)
        layout.addWidget(QLabel(f"現在の状態:{cuda_label}"))

        # Checkbox
        self.checkbox_skip_analyze = QCheckBox('感情分析をスキップ(チャットのダウンロードのみ)')
        self.checkbox_skip_analyze.checkStateChanged.connect(self.toggle_analyze)
        self.checkbox_skip_analyze.setMinimumHeight(40)
        layout.addWidget(self.checkbox_skip_analyze)

        self.checkbox_force_cpu = QCheckBox('強制的にCPUモードで実行(非推奨)')
        self.checkbox_force_cpu.setMinimumHeight(40)
        layout.addWidget(self.checkbox_force_cpu)

        # Dropdown
        self.batch_size = QComboBox()
        self.batch_size.setMinimumHeight(40)
        self.batch_size.addItems(['1', '4', '16', '32', '64', '128', '256', '512'])
        self.batch_size.setCurrentIndex(2)
        self.batch_size_label = QLabel('バッチサイズ:デフォルト推奨。メモリ不足の場合は小さい数値にする。')
        layout.addWidget(self.batch_size_label)
        layout.addWidget(self.batch_size)

        self.token_size = QComboBox()
        self.token_size.setMinimumHeight(40)
        self.token_size.addItems(['16', '32', '64', '128', '256', '512'])
        self.token_size.setCurrentIndex(2)
        self.token_size_label = QLabel('トークンサイズ:デフォルト推奨。メモリ不足の場合は小さい数値にする。')
        layout.addWidget(self.token_size_label)
        layout.addWidget(self.token_size)

        # Start/Cancel button
        self.start_cancel_button = StyledButton(BUTTON_LABEL['LOADING'])
        self.start_cancel_button.setMinimumHeight(50)
        self.start_cancel_button.clicked.connect(self.toggle_process)
        layout.addWidget(self.start_cancel_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Step name label
        self.step_label = QLabel()
        layout.addWidget(self.step_label)

        # elapsed time label
        self.time_label = QLabel('00:00:00', self)
        layout.addWidget(self.time_label)

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

        # init worker
        self.worker = None
        self.is_processing = False
        self.nlp_components = None

        self.model_loader = ModelLoader()
        self.model_loader.finished.connect(self.on_model_loaded)
        self.load_model()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.time = None

        self.store = store

    def get_save_file(self):
        save_file, _ = QFileDialog.getSaveFileName(self, '名前をつけてチャットを保存', filter='csv(*.csv)')
        if save_file:
            self.save_file_input.setText(save_file)

    def toggle_process(self):
        if not self.is_processing:
            self.start_process()
        else:
            self.cancel_process()

    def start_process(self):
        if not self.save_file_input.text():
            QMessageBox.warning(self, 'エラー', '保存する場所を入力してください。')
            return
        if not os.path.exists(self.save_file_input.text()):
            if not self.url_input.text():
                QMessageBox.warning(self, 'エラー', 'URLを入力してください。')
                return
        if self.nlp_components is None:
            QMessageBox.warning(self, '警告', 'モデルがロードされていません。')
            return
        self.is_processing = True
        self.start_cancel_button.setText(BUTTON_LABEL['CANCEL'])
        self.progress_bar.setValue(0)
        self.error_display.clear()
        self.error_display.setVisible(False)

        self.worker = Worker(
            self.save_file_input.text(),
            self.url_input.text(),
            self.checkbox_skip_analyze.isChecked(),
            self.checkbox_force_cpu.isChecked(),
            int(self.batch_size.currentText()),
            int(self.token_size.currentText()),
            self.nlp_components,
            self.store
        )
        self.worker.step_name.connect(self.update_step_name)
        self.worker.progress.connect(self.update_progress)
        self.worker.error.connect(self.display_error)
        self.worker.finished.connect(self.process_finished)
        self.timer_reset()
        self.worker.start()

    def cancel_process(self):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.start_cancel_button.setText(BUTTON_LABEL['CANCELING'])
            self.start_cancel_button.setEnabled(False)
            self.process_finished()

    def update_step_name(self, step_name):
        self.step_label.setText(step_name)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def display_error(self, error_msg):
        self.error_display.setVisible(True)
        self.error_display.setTextColor(Qt.GlobalColor.red)
        self.error_display.append(error_msg)
        self.process_finished()

    def process_finished(self):
        self.is_processing = False
        self.start_cancel_button.setText(BUTTON_LABEL['START'])
        self.start_cancel_button.setEnabled(True)
        torch.cuda.empty_cache()
        self.timer.stop()
        if self.progress_bar.value() == 100:
            QMessageBox.information(self, 'Success', '処理が終わりました！')

    def load_model(self):
        self.model_loader.start()
        self.step_label.setText(STEP_LABEL['MODEL_LOADING'])
        self.start_cancel_button.setEnabled(False)

    def on_model_loaded(self, nlp_components):
        self.nlp_components = nlp_components
        self.step_label.setText(STEP_LABEL['MODEL_LOADED'])
        self.start_cancel_button.setEnabled(True)
        self.start_cancel_button.setText(BUTTON_LABEL['START'])

    def update_time(self):
        self.time = self.time.addSecs(1)
        self.time_label.setText(self.time.toString('hh:mm:ss'))

    def timer_reset(self):
        self.time = QTime(0, 0, 0)
        self.timer.start(1000)
        self.time_label.setText('00:00:00')

    def toggle_analyze(self, skip_analyze):
        is_visible = skip_analyze == Qt.CheckState.Unchecked
        self.token_size_label.setVisible(is_visible)
        self.token_size.setVisible(is_visible)
        self.batch_size_label.setVisible(is_visible)
        self.batch_size.setVisible(is_visible)
        self.checkbox_force_cpu.setVisible(is_visible)
