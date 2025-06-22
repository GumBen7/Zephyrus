from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QComboBox, QHBoxLayout, QSpacerItem, \
    QSizePolicy

import config
from models import City


class MainWindow(QMainWindow):
    city_selected_signal = Signal(City)
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
        self.city_combo_box = QComboBox()

        city_layout = QHBoxLayout()
        city_layout.addWidget(self.city_combo_box)

        main_layout = QVBoxLayout()
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        main_layout.addLayout(city_layout)
        main_layout.addSpacing(20)

        main_layout.addWidget(self.start_button, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        central_widget = QWidget()
        central_widget.setLayout(main_layout)

        root_layout = QHBoxLayout()
        root_layout.addStretch()
        root_layout.addWidget(central_widget)
        root_layout.addStretch()

        final_widget = QWidget()
        final_widget.setLayout(root_layout)
        self.setCentralWidget(final_widget)

    def _init_signals(self):
        self.start_button.clicked.connect(self.start_analysis_signal.emit)
        self.city_combo_box.currentIndexChanged.connect(self._on_city_changed)

    def _on_city_changed(self, index: int):
        city_data = self.city_combo_box.itemData(index)
        if city_data:
            self.city_selected_signal.emit(city_data)

    def populate_cities(self):
        for city in config.CITIES.values():
            self.city_combo_box.addItem(city.name, userData=city)