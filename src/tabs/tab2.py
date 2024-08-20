import pandas as pd
import plotly.graph_objects as go
from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
                               QLabel, QMessageBox, QSizePolicy, QSpinBox, QTextBrowser)

from src.constants import EMOTION_COLORS
from src.utils import read_csv_with_metadata, ClickableLabel, ClickableLineEdit


class Tab2Widget(QWidget):
    def __init__(self, store):
        super().__init__()
        layout = QVBoxLayout(self)

        self.drag_drop_area = ClickableLabel('ドラッグ＆ドロップするか、クリックしてcsvファイルを選択してください')
        self.drag_drop_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drag_drop_area.setFixedHeight(80)
        self.drag_drop_area.clicked.connect(self.select_csv)
        layout.addWidget(self.drag_drop_area)

        # CSV file selection
        csv_layout = QHBoxLayout()
        self.csv_input = ClickableLineEdit(self.select_csv)
        self.csv_input.setMinimumHeight(40)
        csv_layout.addWidget(QLabel('CSV File:'))
        csv_layout.addWidget(self.csv_input, 1)
        layout.addLayout(csv_layout)

        # Metadata display
        self.metadata_browser = QTextBrowser()
        self.metadata_browser.setMaximumHeight(95)
        self.metadata_browser.setVisible(False)
        layout.addWidget(self.metadata_browser)

        # Bin width spinbox
        bin_width_layout = QHBoxLayout()
        self.bin_spinbox = QSpinBox()
        self.bin_spinbox.setMinimum(1)
        self.bin_spinbox.setMaximum(60)
        self.bin_spinbox.setValue(1)
        self.bin_spinbox.setSuffix('分間')
        self.bin_spinbox.valueChanged.connect(self.update_plot)
        bin_width_layout.addWidget(QLabel('集計間隔:'))
        bin_width_layout.addWidget(self.bin_spinbox)
        bin_width_layout.addStretch(1)
        layout.addLayout(bin_width_layout)

        # Plot area
        self.plot_widget = QWebEngineView()
        self.setMinimumHeight(700)
        self.plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.plot_widget.setHtml('')
        layout.addWidget(self.plot_widget, 1)

        self.store = store
        self.df = None  # Store the DataFrame
        self.metadata = None

        # Enable drag and drop
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for file_path in files:
            if file_path.lower().endswith('.csv'):
                self.csv_input.setText(file_path)
                self.load_and_plot_csv(file_path)

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
            self.update_metadata_display()
        except Exception as e:
            QMessageBox.critical(self, 'Error', f"Error loading or plotting CSV: {e}")

    def update_plot(self):
        bin_width = self.bin_spinbox.value()
        if self.df is None:
            return

        max_minutes = self.df['minute'].max()

        fig = go.Figure()
        if 'emotion' not in self.df.columns:
            self.df['emotion'] = '未分類'
        for emotion in reversed(EMOTION_COLORS.keys()):
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
            title=None,
            xaxis_title='時間 (分)',
            yaxis_title='コメント数',
            margin=dict(
                l=50, r=50, t=30, b=50
            ),
            legend=dict(
                font=dict(
                    size=16
                ),
                itemclick='toggleothers',
                itemdoubleclick='toggle'
            ),
            xaxis=dict(
                rangeslider=dict(
                    visible=True
                ),
                rangemode='nonnegative',
            ),
            yaxis=dict(
                rangemode='nonnegative',
            ),
            modebar=dict(
                remove=['toImage', 'select', 'lasso']
            )
        )

        if bin_width == 1:
            fig.update_traces(hovertemplate='%{x} - %{x}59秒<br>%{y}')
            fig.update_xaxes(dtick=5, ticksuffix='分')
        else:
            tick_vals = list(range(0, int(max_minutes) + bin_width, bin_width))
            tick_text = [f'{i}分' for i in tick_vals]
            fig.update_xaxes(tickvals=tick_vals, ticktext=tick_text, ticksuffix='分59秒')
        html = fig.to_html(include_plotlyjs='cdn')
        self.plot_widget.setHtml(html)

    def update_plot_from_store(self):
        if self.df is not None:
            return

        data = self.store.get_data()
        if data:
            self.df = data.get('df', None)
            self.metadata = data.get('metadata', None)
            self.update_plot()
            self.update_metadata_display()

    def update_metadata_display(self):
        if self.metadata:
            html_content = f"""
                <html>
                <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        font-size: 16px;
                        line-height: 1.4;
                        color: #333;
                    }}
                    a {{
                        color: #0066cc;
                        text-decoration: none;
                    }}
                </style>
                </head>
                <body>
                    <b>{self.metadata.get('title', 'Twitchでは放送タイトル等の情報が表示されません')}</b>
                    <div class="info">放送日: {self.metadata.get('upload_at', 'N/A')}</div>
                    <div class="info">
                        URL: <a href="{self.metadata.get('url', '#')}">{self.metadata.get('url', 'N/A')}</a>
                    </div>
                </body>
                </html>
            """
            self.metadata_browser.setHtml(html_content)
            self.metadata_browser.setOpenExternalLinks(True)
            self.metadata_browser.setVisible(True)
