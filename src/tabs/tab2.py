from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
                               QLineEdit, QLabel, QMessageBox, QSizePolicy)
from PySide6.QtWebEngineWidgets import QWebEngineView
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class Tab2Widget(QWidget):
    def __init__(self):
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

        # Plot area
        self.plot_widget = QWidget()
        self.plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.plot_widget, 1)

    def select_csv(self):
        file_name, _ = QFileDialog.getOpenFileName(self, 'Select CSV File', '', 'CSV Files (*.csv)')
        if file_name:
            self.csv_input.setText(file_name)
            self.load_and_plot_csv(file_name)

    def load_and_plot_csv(self, file_name):
        try:
            df = pd.read_csv(file_name)
            fig = make_subplots(rows=1, cols=1)
            for column in df.select_dtypes(include=['int64', 'float64']).columns:
                fig.add_trace(go.Histogram(x=df[column], name=column))

            fig.update_layout(
                title='Histogram of Numeric Columns',
                xaxis_title='Value',
                yaxis_title='Count',
                bargap=0.2,
                bargroupgap=0.1,
                template='plotly_white',
                height=600
            )

            plot_file = 'temp_plot.html'
            fig.write_html(plot_file, full_html=False, include_plotlyjs='cdn')

            for i in reversed(range(self.plot_widget.layout().count())):
                self.plot_widget.layout().itemAt(i).widget().setParent(None)

            web_view = QWebEngineView()
            web_view.load(plot_file)

            plot_layout = QVBoxLayout(self.plot_widget)
            plot_layout.addWidget(web_view)

        except Exception as e:
            QMessageBox.critical(self, 'Error', f"Error loading or plotting CSV: {e}")
