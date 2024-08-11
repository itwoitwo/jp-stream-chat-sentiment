import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget
from src.tabs.tab1 import Tab1Widget
from src.tabs.tab2 import Tab2Widget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PySide6 Application')
        self.setGeometry(100, 100, 1000, 800)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Create tab widget
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # Create and add Tab 1
        tab1 = Tab1Widget()
        tab_widget.addTab(tab1, 'Tab 1')

        # Create and add Tab 2
        tab2 = Tab2Widget()
        tab_widget.addTab(tab2, 'Tab 2')

        # Set larger font size for all widgets
        self.setStyleSheet('QWidget { font-size: 14px; }')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
