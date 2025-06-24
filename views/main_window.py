from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QComboBox, QLabel, QFrame, QSplitter, \
    QGroupBox, QGridLayout, QCheckBox, QSpinBox

import config
from models import City


class MainWindow(QMainWindow):
    city_selected_signal = Signal(City)
    bearing_selected_signal = Signal(int)
    month_selected_signal = Signal(int)
    start_analysis_signal = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zephyrus")
        self.resize(1200, 700)
        self.setMinimumSize(800, 500)

        self._init_ui()
        self._init_signals()
        self.populate_cities()
        self.populate_bearings()
        self.populate_months()

    def _init_ui(self):
        controls_layout = QVBoxLayout()
        controls_layout.setContentsMargins(10, 10, 10, 10)
        controls_layout.setSpacing(15)

        city_label = QLabel("City:")
        self.city_combo_box = QComboBox()

        bearing_label = QLabel("Bearing:")
        self.bearing_combo_box = QComboBox()

        self.distances_group_box = QGroupBox("Distances (км)")
        distances_layout = QGridLayout()
        self.distances_group_box.setLayout(distances_layout)

        step_label = QLabel("Step:")
        self.step_spinbox = QSpinBox()
        self.step_spinbox.setRange(1, 100)
        self.step_spinbox.setValue(10)

        max_dist_label = QLabel("Max:")
        self.max_dist_spinbox = QSpinBox()
        self.max_dist_spinbox.setRange(10, 500)
        self.max_dist_spinbox.setValue(200)

        distances_layout.addWidget(step_label, 0, 0)
        distances_layout.addWidget(self.step_spinbox, 0, 1)
        distances_layout.addWidget(max_dist_label, 1, 0)
        distances_layout.addWidget(self.max_dist_spinbox, 1, 1)

        month_label = QLabel("Month:")
        self.month_combo_box = QComboBox()

        self.distance_checkboxes: list[QCheckBox] = []

        self.start_button = QPushButton("Start")
        self.start_button.setMinimumHeight(40)

        controls_layout.addWidget(city_label)
        controls_layout.addWidget(self.city_combo_box)
        controls_layout.addWidget(bearing_label)
        controls_layout.addWidget(self.bearing_combo_box)
        controls_layout.addWidget(month_label)
        controls_layout.addWidget(self.month_combo_box)
        controls_layout.addWidget(self.distances_group_box)
        controls_layout.addSpacing(20)
        controls_layout.addWidget(self.start_button)
        controls_layout.addStretch()

        controls_widget = QWidget()
        controls_widget.setLayout(controls_layout)
        controls_widget.setMaximumWidth(350)

        plot_area_layout = QVBoxLayout()
        placeholder_label = QLabel("Graph")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet("font-size: 20px; color: #aaa;")
        plot_area_layout.addWidget(placeholder_label)

        plot_area_widget = QFrame()
        plot_area_widget.setLayout(plot_area_layout)

        plot_area_widget.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(controls_widget)
        splitter.addWidget(plot_area_widget)
        splitter.setSizes([300, 900])

        self.setCentralWidget(splitter)

    def _init_signals(self):
        self.start_button.clicked.connect(self.start_analysis_signal.emit)
        self.city_combo_box.currentIndexChanged.connect(self._on_city_changed)
        self.bearing_combo_box.currentIndexChanged.connect(self._on_bearing_changed)
        self.month_combo_box.currentIndexChanged.connect(self._on_month_changed)

    def _on_city_changed(self, index: int):
        city_data = self.city_combo_box.itemData(index)
        if city_data:
            self.city_selected_signal.emit(city_data)

    def _on_bearing_changed(self):
        bearing_data = self.bearing_combo_box.currentData()
        if bearing_data is not None:
            self.bearing_selected_signal.emit(bearing_data)

    def _on_month_changed(self, index: int):
        month_data = self.month_combo_box.itemData(index)
        if month_data is not None:
            self.month_selected_signal.emit(month_data)

    def populate_cities(self):
        for city in config.CITIES.values():
            self.city_combo_box.addItem(city.name, userData=city)

    def populate_bearings(self):
        for degrees, name in config.BEARINGS.items():
            self.bearing_combo_box.addItem(name, userData=degrees)

    def populate_months(self):
        for number, name in config.MONTHS.items():
            self.month_combo_box.addItem(name, userData=number)

    def get_distance_parameters(self) -> dict:
        return {
            'step': self.step_spinbox.value(),
            'max': self.max_dist_spinbox.value()
        }