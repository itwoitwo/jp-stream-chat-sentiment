import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget
from PySide6.QtGui import QIcon
from src.tabs.tab1 import Tab1Widget
from src.tabs.tab2 import Tab2Widget
from src.utils import Store
from src.constants import COMMON_STYLE


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Archive Chat Downloader')
        self.setBaseSize(1024, 768)
        self.resize(1024, 768)
        self.store = Store()
        self.setWindowIcon(QIcon('favicon.ico'))

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create tab widget
        tab_widget = QTabWidget()
        tab_widget.setDocumentMode(True)
        main_layout.addWidget(tab_widget)

        tab1 = Tab1Widget(self.store)
        tab_widget.addTab(tab1, 'ダウンロード')

        self.tab2 = Tab2Widget(self.store)
        tab_widget.addTab(self.tab2, 'グラフの表示')

        tab_widget.currentChanged.connect(self.tab_changed)

        self.setStyleSheet(COMMON_STYLE)
        tab_widget.tabBar().setExpanding(True)

    def tab_changed(self, index):
        if index == 1:
            self.tab2.update_plot_from_store()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())