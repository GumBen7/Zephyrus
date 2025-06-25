import threading
import math

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QComboBox, QLabel, QFrame, QSplitter, \
    QGroupBox, QGridLayout, QSpinBox, QTreeView, QStatusBar

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np  # Для работы с массивами

import config
from models import City
from models.routes import MonthlyDataRoute


class MainWindow(QMainWindow):
    city_selected_signal = Signal(City)
    bearing_selected_signal = Signal(int)
    month_selected_signal = Signal(int)
    start_analysis_signal = Signal()
    data_route_selected_signal = Signal(MonthlyDataRoute)

    plot_clicked_signal = Signal(float, float, int)  # x, y, button (1 for left, 3 for right)
    export_data_signal = Signal()  # НОВОЕ: Сигнал для экспорта данных

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zephyrus")
        self.resize(1200, 700)
        self.setMinimumSize(800, 500)

        self.current_plot_ax = None
        self._plot_model_line1 = None
        self._plot_model_line2 = None
        self._plot_point1_marker = None
        self._plot_point2_marker = None
        self.current_plotted_route: MonthlyDataRoute | None = None
        self._max_actual_density_on_plot: float = 0.0

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

        step_label = QLabel("Шаг:")
        self.step_spinbox = QSpinBox()
        self.step_spinbox.setRange(1, 100)
        self.step_spinbox.setValue(10)

        max_dist_label = QLabel("Макс.:")
        self.max_dist_spinbox = QSpinBox()
        self.max_dist_spinbox.setRange(10, 500)
        self.max_dist_spinbox.setValue(200)

        distances_layout.addWidget(step_label, 0, 0)
        distances_layout.addWidget(self.step_spinbox, 0, 1)
        distances_layout.addWidget(max_dist_label, 1, 0)
        distances_layout.addWidget(self.max_dist_spinbox, 1, 1)

        month_label = QLabel("Месяц:")
        self.month_combo_box = QComboBox()

        self.start_button = QPushButton("Начать анализ")
        self.start_button.setMinimumHeight(40)

        # НОВОЕ: Кнопка экспорта
        self.export_button = QPushButton("Экспортировать данные")
        self.export_button.setMinimumHeight(40)
        self.export_button.setEnabled(False)  # Изначально отключена, пока нет данных

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
        controls_layout.addWidget(self.export_button)  # НОВОЕ: Добавляем кнопку экспорта
        controls_layout.addWidget(QLabel("Загруженные данные:"))
        controls_layout.addWidget(self.data_tree_view)
        controls_layout.addStretch()

        controls_widget = QWidget()
        controls_widget.setLayout(controls_layout)
        controls_widget.setMaximumWidth(350)

        self.plot_area_layout = QVBoxLayout()
        self.plot_area_layout.setContentsMargins(5, 5, 5, 5)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.plot_area_layout.addWidget(self.canvas)

        self.plot_area_widget = QFrame()
        self.plot_area_widget.setLayout(self.plot_area_layout)
        self.plot_area_widget.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(controls_widget)
        splitter.addWidget(self.plot_area_widget)
        splitter.setSizes([300, 900])

        self.setCentralWidget(splitter)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

    def _init_signals(self):
        self.start_button.clicked.connect(self.start_analysis_signal.emit)
        self.export_button.clicked.connect(self.export_data_signal.emit)  # НОВОЕ: Подключаем сигнал к кнопке
        self.city_combo_box.currentIndexChanged.connect(self._on_city_changed)
        self.bearing_combo_box.currentIndexChanged.connect(self._on_bearing_changed)
        self.month_combo_box.currentIndexChanged.connect(self._on_month_changed)
        self.data_tree_view.clicked.connect(self._on_data_tree_item_clicked)
        self.canvas.mpl_connect('button_press_event', self._on_plot_click)

    def _on_plot_click(self, event):
        if event.inaxes:
            x_clicked = event.xdata
            y_clicked = event.ydata
            button = event.button
            print(f"Клик на графике: x={x_clicked:.2f}, y={y_clicked:.2f}, кнопка={button}")
            self.plot_clicked_signal.emit(x_clicked, y_clicked, button)
        else:
            print("Клик вне области графика.")
            if event.button == 3:
                self.plot_clicked_signal.emit(0.0, 0.0, event.button)

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
            if isinstance(data_obj, MonthlyDataRoute):
                print(
                    f"Выбран маршрут: Bearing={data_obj.bearing}, Month={data_obj.month}, Year={data_obj.year}. Densities: {data_obj.densities}")
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
        self.tree_model.clear()
        self.tree_model.setHorizontalHeaderLabels(['Загруженные данные'])
        root_node = self.tree_model.invisibleRootItem()

        has_any_valid_routes = False  # НОВОЕ: Флаг для определения, есть ли вообще данные для экспорта

        for city_id, city_obj in cities_data.items():
            has_valid_routes_for_city = False
            for route_r in city_obj.routes:
                if isinstance(route_r, MonthlyDataRoute) and route_r.densities:
                    if any(not math.isnan(val) for val in route_r.densities.values()):
                        has_valid_routes_for_city = True
                        has_any_valid_routes = True  # Обновляем глобальный флаг
                        break
            if not has_valid_routes_for_city:
                continue

            city_item = QStandardItem(city_obj.name)
            city_item.setEditable(False)
            city_item.setSelectable(False)
            root_node.appendRow(city_item)

            routes_by_bearing_month: dict[tuple[int, int], list[MonthlyDataRoute]] = {}
            for route_r in city_obj.routes:
                if isinstance(route_r, MonthlyDataRoute) and route_r.densities:
                    if any(not math.isnan(val) for val in route_r.densities.values()):
                        key = (route_r.bearing, route_r.month)
                        if key not in routes_by_bearing_month:
                            routes_by_bearing_month[key] = []
                        routes_by_bearing_month[key].append(route_r)

            for (bearing, month_num), monthly_routes in routes_by_bearing_month.items():
                bearing_name = config.BEARINGS.get(bearing, f"{bearing}°")
                month_name = config.MONTHS.get(month_num, f"Месяц {month_num}")
                route_item_text = f"{bearing_name}, {month_name}"
                route_item = QStandardItem(route_item_text)
                route_item.setEditable(False)
                route_item.setSelectable(False)
                city_item.appendRow(route_item)

                monthly_routes.sort(key=lambda r: r.year)

                for route_obj in monthly_routes:
                    year_item_text = f"Данные за {route_obj.year} год"
                    year_item = QStandardItem(year_item_text)
                    year_item.setEditable(False)
                    year_item.setData(route_obj)
                    route_item.appendRow(year_item)

        self.data_tree_view.expandAll()
        self.export_button.setEnabled(has_any_valid_routes)  # НОВОЕ: Включаем/отключаем кнопку экспорта
        # в зависимости от наличия данных

    def set_ui_enabled(self, enabled: bool):
        """Включает или отключает элементы управления UI."""
        self.city_combo_box.setEnabled(enabled)
        self.bearing_combo_box.setEnabled(enabled)
        self.month_combo_box.setEnabled(enabled)
        self.step_spinbox.setEnabled(enabled)
        self.max_dist_spinbox.setEnabled(enabled)
        self.start_button.setEnabled(enabled)
        # self.export_button.setEnabled(enabled) # Эту строку убираем, чтобы логика включения/отключения кнопки
        # экспорта была централизована в update_data_tree
        self.data_tree_view.setEnabled(enabled)

    def set_status_message(self, message: str):
        """Устанавливает сообщение в статус-баре."""
        self.statusBar.showMessage(message)

    def plot_data(self, data_route: MonthlyDataRoute):
        """
        Отрисовывает базовый график плотности NO2 по расстоянию для выбранного маршрута.
        Сбрасывает все модельные элементы.
        """
        self.current_plotted_route = data_route
        self.figure.clear()  # Полностью очищаем фигуру (и все старые оси/артисты)
        self.current_plot_ax = self.figure.add_subplot(111)

        # Сброс ссылок на старые объекты после figure.clear()
        self._plot_model_line1 = None
        self._plot_model_line2 = None
        self._plot_point1_marker = None
        self._plot_point2_marker = None

        distances = []
        densities = []

        sorted_densities = sorted(data_route.densities.items())

        for dist, density in sorted_densities:
            if not math.isnan(density):
                distances.append(dist)
                densities.append(density)

        if not distances:
            self.current_plot_ax.text(0.5, 0.5, "Нет данных для отображения",
                                      horizontalalignment='center', verticalalignment='center',
                                      transform=self.current_plot_ax.transAxes, fontsize=14, color='gray')
            self.canvas.draw()
            self._update_ylim_auto([])  # Передаем пустой список, чтобы установить дефолтный масштаб
            self._max_actual_density_on_plot = 0.0  # Сброс max_actual_density_on_plot
            return

        self.current_plot_ax.plot(distances, densities, marker='o', linestyle='-', label='Полученные данные')
        self.current_plot_ax.set_title(
            f"Плотность NO2 для {config.CITIES[data_route.city_id].name}, {config.BEARINGS[data_route.bearing]}°, {config.MONTHS[data_route.month]} ({data_route.year})")
        self.current_plot_ax.set_xlabel("Расстояние от центра (км)")
        self.current_plot_ax.set_ylabel("Плотность NO2 ($\mu$моль/м$^2$)")
        self.current_plot_ax.grid(True)
        self.current_plot_ax.legend()

        self._max_actual_density_on_plot = max(densities)

        self._update_ylim_auto(densities)

        self.canvas.draw()

    def plot_single_point_model(self, point1_coords: tuple[float, float], model_distances: list[float],
                                model_densities: list[float]):
        if self.current_plot_ax is None: return

        self.clear_model_elements()

        self._plot_point1_marker, = self.current_plot_ax.plot(
            point1_coords[0], point1_coords[1], marker='X', color='green', markersize=10, linestyle='None',
            label=f'Опорная точка 1: ({point1_coords[0]:.0f}км, {point1_coords[1]:.2f})'
        )

        dynamic_clip_limit = self._max_actual_density_on_plot + 50
        clipped_model_densities = [min(val, dynamic_clip_limit) for val in model_densities]

        self._plot_model_line1, = self.current_plot_ax.plot(
            model_distances, clipped_model_densities, color='red', linestyle='--', label='Модель (Q = $\\Theta_1$/r)'
        )
        self._update_ylim_dynamic(clipped_model_densities + [point1_coords[1]], dynamic_clip_limit)
        self.current_plot_ax.legend()
        self.canvas.draw()

    def plot_double_point_model(self, point1_coords: tuple[float, float], point2_coords: tuple[float, float],
                                model_distances: list[float], model_densities: list[float], theta2_value: float):
        if self.current_plot_ax is None: return

        self.clear_model_elements()

        self._plot_point1_marker, = self.current_plot_ax.plot(
            point1_coords[0], point1_coords[1], marker='X', color='green', markersize=10, linestyle='None',
            label=f'Опорная точка 1: ({point1_coords[0]:.0f}км, {point1_coords[1]:.2f})'
        )
        self._plot_point2_marker, = self.current_plot_ax.plot(
            point2_coords[0], point2_coords[1], marker='X', color='blue', markersize=10, linestyle='None',
            label=f'Опорная точка 2: ({point2_coords[0]:.0f}км, {point2_coords[1]:.2f})'
        )

        dynamic_clip_limit = self._max_actual_density_on_plot + 50
        clipped_model_densities = [min(val, dynamic_clip_limit) for val in model_densities]

        self._plot_model_line2, = self.current_plot_ax.plot(
            model_distances, clipped_model_densities, color='purple', linestyle='-',
            label=f'Модель (Q = $\\Theta_1$/r + $\\Theta_2$, Фон $\\Theta_2$={theta2_value:.2f})'
        )

        self._update_ylim_dynamic(clipped_model_densities + [point1_coords[1], point2_coords[1]], dynamic_clip_limit)
        self.current_plot_ax.legend()
        self.canvas.draw()

    def clear_model_elements(self):
        """
        Удаляет все модельные линии и маркеры опорных точек с графика.
        Применяет remove() только если объект существует и привязан к текущему ax.
        """
        elements_to_remove = [
            self._plot_model_line1,
            self._plot_model_line2,
            self._plot_point1_marker,
            self._plot_point2_marker
        ]

        for element in elements_to_remove:
            if element and element.axes == self.current_plot_ax:
                try:
                    element.remove()
                except NotImplementedError:
                    print(f"Warning: Could not remove element {element}. It might already be removed or not supported.")

        self._plot_model_line1 = None
        self._plot_model_line2 = None
        self._plot_point1_marker = None
        self._plot_point2_marker = None

        if self.current_plot_ax:
            if self.current_plotted_route and self.current_plotted_route.densities:
                densities_from_route = [q for q in self.current_plotted_route.densities.values() if not math.isnan(q)]
                self._update_ylim_auto(densities_from_route)
            else:
                self._update_ylim_auto([])

            self.current_plot_ax.legend()
            self.canvas.draw()

    def _update_ylim_auto(self, current_visible_densities: list[float]):
        """
        Обновляет пределы оси Y, основываясь на переданных плотностях (для базового графика).
        """
        if self.current_plot_ax is None:
            return

        if not current_visible_densities:
            self.current_plot_ax.set_ylim(0, 1)
            return

        min_val = min(current_visible_densities)
        max_val = max(current_visible_densities)

        padding_factor = 0.1
        y_range = max_val - min_val

        if y_range == 0:
            if min_val == 0:
                y_min_padded = -0.1
                y_max_padded = 0.1
            else:
                y_min_padded = min_val * (1 - padding_factor)
                y_max_padded = min_val * (1 + padding_factor)
                if min_val > 0 and y_min_padded < 0:
                    y_min_padded = 0
        else:
            y_min_padded = min_val - (y_range * padding_factor)
            y_max_padded = max_val + (y_range * padding_factor)

            if y_min_padded < 0 and min_val >= 0:
                y_min_padded = 0

        self.current_plot_ax.set_ylim(y_min_padded, y_max_padded)

    def _update_ylim_dynamic(self, model_densities_clipped: list[float], dynamic_clip_limit: float):
        """
        Обновляет пределы оси Y, основываясь на исходных и обрезанных модельных плотностях.
        Учитывает динамический предел обрезки.
        """
        if self.current_plot_ax is None or self.current_plotted_route is None:
            return

        all_densities_to_consider = []
        for val in self.current_plotted_route.densities.values():
            if not math.isnan(val):
                all_densities_to_consider.append(val)

        for val in model_densities_clipped:
            if not math.isnan(val):
                all_densities_to_consider.append(val)

        if not all_densities_to_consider:
            self.current_plot_ax.set_ylim(0, 1)
            return

        min_val_combined = min(all_densities_to_consider)
        max_val_combined = max(all_densities_to_consider)

        padding_factor = 0.1
        y_range_combined = max_val_combined - min_val_combined

        if y_range_combined == 0:
            if min_val_combined == 0:
                y_min_padded = -0.1
                y_max_padded = 0.1
            else:
                y_min_padded = min_val_combined * (1 - padding_factor)
                y_max_padded = min_val_combined * (1 + padding_factor)
                if min_val_combined > 0 and y_min_padded < 0:
                    y_min_padded = 0
        else:
            y_min_padded = min_val_combined - (y_range_combined * padding_factor)
            y_max_padded = max_val_combined + (y_range_combined * padding_factor)

            if y_min_padded < 0 and min_val_combined >= 0:
                y_min_padded = 0

        actual_max_plot_limit = dynamic_clip_limit + (dynamic_clip_limit * padding_factor * 0.1)
        y_max_padded = max(y_max_padded, actual_max_plot_limit)

        self.current_plot_ax.set_ylim(y_min_padded, y_max_padded)
