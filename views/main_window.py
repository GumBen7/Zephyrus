from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget


class MainWindow(QMainWindow):
    start_analysis_signal = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zephyrus")
        self.resize(1000, 600)
        self.setMinimumSize(400, 250)

        self._init_ui()
        self._init_signals()

    def _init_ui(self):
        self.start_button = QPushButton("Start")

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(self.start_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def _init_signals(self):
        self.start_button.clicked.connect(self.start_analysis_signal.emit)