import threading

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QComboBox, QLabel, QFrame, QSplitter, \
    QGroupBox, QGridLayout, QCheckBox, QSpinBox, QTreeView, QStatusBar

import config
from models import City
from models.routes import MonthlyDataRoute


class MainWindow(QMainWindow):
    city_selected_signal = Signal(City)
    bearing_selected_signal = Signal(int)
    month_selected_signal = Signal(int)
    start_analysis_signal = Signal()
    data_route_selected_signal = Signal(MonthlyDataRoute)

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

        self.data_tree_view = QTreeView()
        self.tree_model = QStandardItemModel()
        self.data_tree_view.setModel(self.tree_model)
        self.data_tree_view.setHeaderHidden(True)

        controls_layout.addWidget(city_label)
        controls_layout.addWidget(self.city_combo_box)
        controls_layout.addWidget(bearing_label)
        controls_layout.addWidget(self.bearing_combo_box)
        controls_layout.addWidget(month_label)
        controls_layout.addWidget(self.month_combo_box)
        controls_layout.addWidget(self.distances_group_box)
        controls_layout.addSpacing(20)
        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(QLabel("Загруженные данные:"))
        controls_layout.addWidget(self.data_tree_view)
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

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

    def _init_signals(self):
        self.start_button.clicked.connect(self.start_analysis_signal.emit)
        self.city_combo_box.currentIndexChanged.connect(self._on_city_changed)
        self.bearing_combo_box.currentIndexChanged.connect(self._on_bearing_changed)
        self.month_combo_box.currentIndexChanged.connect(self._on_month_changed)
        self.data_tree_view.clicked.connect(self._on_data_tree_item_clicked)

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

    def _on_data_tree_item_clicked(self, index):
        """Обрабатывает клик по элементу в древовидном представлении."""
        item = self.tree_model.itemFromIndex(index)
        if item:
            data_obj = item.data()
            # Проверяем, что это тот тип данных, который нас интересует (MonthlyDataRoute)
            if isinstance(data_obj, MonthlyDataRoute):
                print(f"Выбран маршрут: Bearing={data_obj.bearing}, Month={data_obj.month}, Year={data_obj.year}")
                self.data_route_selected_signal.emit(data_obj)

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

    def update_data_tree(self, cities_data: dict[str, City]):
        """
        Полностью перерисовывает дерево на основе данных из модели.
        Этот метод будет вызывать Презентер.
        """
        self.tree_model.clear()  # Очищаем старое дерево

        # Устанавливаем заголовок колонок (хоть он и скрыт, это хорошая практика)
        self.tree_model.setHorizontalHeaderLabels(['Загруженные данные'])

        root_node = self.tree_model.invisibleRootItem()

        for city_id, city_obj in cities_data.items():
            # Пропускаем города без загруженных маршрутов (или те, где нет MonthlyDataRoute с данными)
            has_valid_routes = False
            for route_r in city_obj.routes:
                if isinstance(route_r, MonthlyDataRoute) and route_r.densities:
                    has_valid_routes = True
                    break
            if not has_valid_routes:
                continue

                # Уровень 1: Город
            city_item = QStandardItem(city_obj.name)
            city_item.setEditable(False)
            city_item.setSelectable(False)  # Город не кликабельный для данных
            root_node.appendRow(city_item)

            # Для каждого города, группируем маршруты по азимуту и месяцу
            # Это необходимо, потому что у нас теперь список routes, а не dict по bearing
            routes_by_bearing_month: dict[tuple[int, int], list[MonthlyDataRoute]] = {}
            for route_r in city_obj.routes:
                if isinstance(route_r, MonthlyDataRoute) and route_r.densities:
                    key = (route_r.bearing, route_r.month)
                    if key not in routes_by_bearing_month:
                        routes_by_bearing_month[key] = []
                    routes_by_bearing_month[key].append(route_r)

            for (bearing, month_num), monthly_routes in routes_by_bearing_month.items():
                # Уровень 2: Маршрут (группа по азимуту и месяцу)
                bearing_name = config.BEARINGS.get(bearing, f"{bearing}°")
                month_name = config.MONTHS.get(month_num, f"Месяц {month_num}")
                route_item_text = f"{bearing_name}, {month_name}"
                route_item = QStandardItem(route_item_text)
                route_item.setEditable(False)
                route_item.setSelectable(False)  # Группа маршрутов не кликабельная для данных
                city_item.appendRow(route_item)

                # Сортируем маршруты по году для более аккуратного отображения
                monthly_routes.sort(key=lambda r: r.year)

                for route_obj in monthly_routes:
                    # Уровень 3: Конкретный год (этот элемент будет кликабельным)
                    year_item_text = f"Данные за {route_obj.year} год"
                    year_item = QStandardItem(year_item_text)
                    year_item.setEditable(False)
                    # Сохраняем весь объект маршрута внутри элемента дерева!
                    year_item.setData(route_obj)
                    route_item.appendRow(year_item)

        self.data_tree_view.expandAll()

    def set_ui_enabled(self, enabled: bool):
        """Включает или отключает элементы управления UI."""
        self.city_combo_box.setEnabled(enabled)
        self.bearing_combo_box.setEnabled(enabled)
        self.month_combo_box.setEnabled(enabled)
        self.step_spinbox.setEnabled(enabled)
        self.max_dist_spinbox.setEnabled(enabled)
        self.start_button.setEnabled(enabled)
        self.data_tree_view.setEnabled(enabled)  # Отключаем дерево во время анализа

    def set_status_message(self, message: str):
        """Устанавливает сообщение в статус-баре."""
        print("Current thread:", threading.current_thread().name)
        self.statusBar.showMessage(message)
