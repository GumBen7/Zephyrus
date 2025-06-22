from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget


class MainWindow(QMainWindow):
    start_analysis_signal = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zephyrus")

        self.start_button = QPushButton("Start")

        layout = QVBoxLayout()
        layout.addWidget(self.start_button)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.start_button.clicked.connect(self.start_analysis_signal.emit)