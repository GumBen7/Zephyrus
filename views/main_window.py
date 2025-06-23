from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QComboBox, QLabel, QFrame, QSplitter, \
    QGroupBox, QGridLayout, QCheckBox

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
        distances_grid_layout = QGridLayout()
        self.distances_group_box.setLayout(distances_grid_layout)

        month_label = QLabel("Month:")
        self.month_combo_box = QComboBox()

        self.distance_checkboxes: list[QCheckBox] = []

        row, col = 0, 0
        for distance in config.DISTANCES_KM:
            checkbox = QCheckBox(str(distance))
            checkbox.setChecked(True)
            checkbox.setProperty("distance_value", distance)
            self.distance_checkboxes.append(checkbox)
            distances_grid_layout.addWidget(checkbox, row, col)

            col += 1
            if col > 1:
                col = 0
                row += 1

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

    def get_selected_distances(self) -> list[int]:
        selected = []
        for checkbox in self.distance_checkboxes:
            if checkbox.isChecked():
                selected.append(checkbox.property("distance_value"))
        return selected