from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
                               QLineEdit, QLabel, QMessageBox, QSizePolicy, QSlider)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt
import pandas as pd
import plotly.graph_objects as go
from src.utils import read_csv_with_metadata
from src.constants import EMOTION_COLORS


class Tab2Widget(QWidget):
    def __init__(self, store):
        super().__init__()
        layout = QVBoxLayout(self)

        # CSV file selection
        csv_layout = QHBoxLayout()
        self.csv_input = QLineEdit()
        self.csv_input.setMinimumHeight(40)
        csv_button = QPushButton('Select CSV')
        csv_button.setMinimumHeight(40)
        csv_button.clicked.connect(self.select_csv)
        csv_layout.addWidget(QLabel('CSV File:'))
        csv_layout.addWidget(self.csv_input, 1)
        csv_layout.addWidget(csv_button)
        layout.addLayout(csv_layout)

        # Bin width slider
        slider_layout = QHBoxLayout()
        self.bin_slider = QSlider(Qt.Orientation.Horizontal)
        self.bin_slider.setMinimum(1)
        self.bin_slider.setMaximum(10)
        self.bin_slider.setValue(1)
        self.bin_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.bin_slider.setTickInterval(1)
        self.bin_slider.valueChanged.connect(self.update_plot)
        slider_layout.addWidget(QLabel('Bin Width (minutes):'))
        slider_layout.addWidget(self.bin_slider)
        self.bin_label = QLabel('1')
        slider_layout.addWidget(self.bin_label)
        layout.addLayout(slider_layout)

        # Plot area
        self.plot_widget = QWebEngineView()
        self.plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.plot_widget.setHtml('')
        layout.addWidget(self.plot_widget, 1)

        self.store = store
        self.df = None  # Store the DataFrame
        self.metadata = None

    def select_csv(self):
        file_name, _ = QFileDialog.getOpenFileName(self, 'Select CSV File', '', 'CSV Files (*.csv)')
        if file_name:
            self.csv_input.setText(file_name)
            self.load_and_plot_csv(file_name)

    def load_and_plot_csv(self, file_name):
        try:
            self.df, self.metadata = read_csv_with_metadata(file_name)
            self.df['second'] = pd.to_numeric(self.df['second'])
            self.update_plot()
        except Exception as e:
            QMessageBox.critical(self, 'Error', f"Error loading or plotting CSV: {e}")

    def update_plot(self):
        if self.df is None:
            return

        bin_width = self.bin_slider.value()
        self.bin_label.setText(str(bin_width))
        max_minutes = self.df['minute'].max()

        fig = go.Figure()
        for emotion in self.df['emotion'].unique():
            emotion_data = self.df[self.df['emotion'] == emotion]
            fig.add_trace(go.Histogram(
                x=emotion_data['minute'],
                name=emotion,
                marker_color=EMOTION_COLORS.get(emotion, 'grey'),
                xbins=dict(start=0, end=max_minutes, size=bin_width),
                autobinx=False
            ))

        fig.update_layout(
            barmode='stack',
            title='時間ごとのコメント数と感情分布',
            xaxis_title='時間 (分)',
            yaxis_title='コメント数',
            bargap=0.1
        )

        # X軸のティックラベルをカスタマイズ
        tick_vals = list(range(0, int(max_minutes) + bin_width, bin_width))
        tick_text = [f'{i}分' for i in tick_vals[:-1]] + [f'{tick_vals[-1]}分~']
        fig.update_xaxes(tickvals=tick_vals, ticktext=tick_text)

        # PlotlyのグラフをHTMLに変換
        html = fig.to_html(include_plotlyjs='cdn')

        # WebEngineViewにHTMLを設定
        self.plot_widget.setHtml(html)

    def update_plot_from_store(self):
        if self.df is not None:
            return

        data = self.store.get_data()
        if data:
            self.df = data.get('df', None)
            self.metadata = data.get('metadata', None)
            self.update_plot()
