import threading
import math
import numpy as np

from PySide6.QtCore import QThread, Slot, QCoreApplication, Qt, QObject

import config
from models import City
from models.analysis import Analysis
from models.routes import MonthlyDataRoute
from presenters.analysis_worker import AnalysisWorker
from views.main_window import MainWindow


class MainPresenter(QObject):
    # Track selected points and model parameters
    _selected_point1: tuple[float, float] | None = None  # (r, q)
    _selected_point2: tuple[float, float] | None = None  # (r, q)
    _calculated_theta1: float | None = None
    _calculated_theta2: float | None = None

    def on_progress_update(self, percent: int, message: str):
        self.view.set_status_message(f"Прогресс: {percent}%, {message}")
        print(
            f"Progress update: {percent}%, {message} (Thread: {threading.current_thread().name} / QObject thread: {self.thread}, QApplication thread: {QCoreApplication.instance().thread()})")

    def __init__(self, view: MainWindow, model: Analysis):
        super().__init__()
        self.view = view
        self.model = model

        self.thread: QThread | None = None
        self.worker: AnalysisWorker | None = None

        self.current_city: City | None = None
        self.current_bearing: int | None = None
        self.current_month: int | None = None
        self.current_selected_data_route: MonthlyDataRoute | None = None

        self._connect_view_signals()

        first_city = next(iter(config.CITIES.values()), None)
        if first_city:
            self.on_city_selected(first_city)

        first_bearing = list(config.BEARINGS.keys())[0]
        if first_bearing is not None:
            self.on_bearing_selected(first_bearing)

        first_month = list(config.MONTHS.keys())[0]
        if first_month is not None:
            self.on_month_changed(first_month)

        print(
            f"MainPresenter initialized in thread: {threading.current_thread().name} (QObject thread: {self.thread}, QApplication thread: {QCoreApplication.instance().thread()})")

    def _connect_view_signals(self):
        self.view.start_analysis_signal.connect(self.run_analysis)
        self.view.city_selected_signal.connect(self.on_city_selected)
        self.view.bearing_selected_signal.connect(self.on_bearing_selected)
        self.view.month_selected_signal.connect(self.on_month_changed)
        self.view.data_route_selected_signal.connect(self.on_data_route_selected)

        # --- Подключение нового сигнала клика по графику ---
        self.view.plot_clicked_signal.connect(self.on_plot_clicked)
        print("View signals connected.")

    def on_city_selected(self, city: City):
        self.current_city = city
        print(f"City selected: {city.name}")

    def on_bearing_selected(self, bearing: int):
        self.current_bearing = bearing
        print(f"Bearing selected: {bearing}")

    def on_month_changed(self, month: int):
        self.current_month = month
        print(f"Month selected: {month}")

    @Slot(MonthlyDataRoute)
    def on_data_route_selected(self, route: MonthlyDataRoute):
        """Слот для обработки выбора MonthlyDataRoute из дерева данных."""
        self.current_selected_data_route = route
        print(
            f"Selected data route in presenter: Bearing={route.bearing}, Month={route.month}, Year={route.year}. Densities: {route.densities}")
        self.view.plot_data(route)  # Отрисовываем базовый график
        # Сбрасываем выбранные точки и модель при смене маршрута
        self._selected_point1 = None
        self._selected_point2 = None
        self._calculated_theta1 = None
        self._calculated_theta2 = None
        self.view.set_status_message("Выберите опорную точку на графике (ЛКМ).")

    @Slot()
    def on_analysis_finished_in_model(self):
        """
        Этот слот вызывается, когда анализ ЗАВЕРШЕН и данные в модели обновлены.
        Он должен выполняться в главном потоке.
        """
        print(
            f"on_analysis_finished_in_model called. Current thread: {threading.current_thread().name} (QObject thread: {self.thread}, QApplication thread: {QCoreApplication.instance().thread()})")

        self.view.update_data_tree(self.model.cities)
        self.view.set_ui_enabled(True)
        self.view.set_status_message("Анализ завершен! Выберите данные для отображения или начните новый анализ.")
        print("UI unlocked and data tree updated.")

    def on_thread_finished(self):
        """
        Этот слот вызывается, когда QThread полностью завершил свою работу.
        Он будет вызван в главном потоке.
        Здесь безопасно сбрасывать ссылки на поток и воркер.
        """
        print(
            f"Thread finished signal received in MainPresenter. Cleaning up. Current thread: {threading.current_thread().name} (QObject thread: {self.thread}, QApplication thread: {QCoreApplication.instance().thread()})")
        self.thread = None
        self.worker = None
        print("Thread and worker references reset.")

    def run_analysis(self):
        print("run_analysis called.")
        distance_params = self.view.get_distance_parameters()
        if not self.current_city or self.current_bearing is None or self.current_month is None or not distance_params:
            print("Missing parameters for analysis. Aborting.")
            self.view.set_status_message("Отсутствуют параметры для анализа.")
            return
        distances = list(range(
            distance_params['step'],
            distance_params['max'] + 1,
            distance_params['step']
        ))
        print(
            f"Analysis parameters: City={self.current_city.name}, Bearing={self.current_bearing}, Month={self.current_month}, Distances={distances}")

        self.view.set_ui_enabled(False)
        self.view.set_status_message("Начинаем анализ...")

        if self.thread and self.thread.isRunning():
            print("Worker thread is already running, not starting a new one.")
            self.view.set_status_message("Анализ уже запущен.")
            self.view.set_ui_enabled(True)
            return

        self.thread = QThread()
        self.worker = AnalysisWorker(
            analysis_model=self.model,
            city=self.current_city,
            bearings=[self.current_bearing],
            month=self.current_month,
            distances=distances
        )
        self.worker.moveToThread(self.thread)
        print("Worker moved to thread.")
        print(
            f"Worker's thread affinity after moveToThread: {threading.current_thread().name} (QObject thread: {self.worker.thread()}, QApplication thread: {QCoreApplication.instance().thread()})")

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.on_thread_finished)

        self.worker.progress.connect(self.on_progress_update, Qt.QueuedConnection)
        self.worker.analysis_finished_signal.connect(self.on_analysis_finished_in_model, Qt.QueuedConnection)

        print("Worker/Thread signals connected (inside run_analysis).")

        self.thread.start()
        print("Thread started.")

    # --- Новый слот для обработки кликов по графику ---
    @Slot(float, float, int)  # x, y, button
    def on_plot_clicked(self, clicked_x: float, clicked_y: float, button: int):
        if not self.current_selected_data_route:
            self.view.set_status_message("Выберите данные для анализа на графике, чтобы построить модель.")
            return

        # Фильтруем данные, чтобы исключить NaN
        valid_data_points = [(d, q) for d, q in self.current_selected_data_route.densities.items() if not math.isnan(q)]

        if not valid_data_points:
            self.view.set_status_message("В выбранном маршруте нет действительных данных для построения модели.")
            return

        distances_only = [p[0] for p in valid_data_points]
        densities_only = [p[1] for p in valid_data_points]

        # Определяем диапазон для модельной функции
        r_min_model = min(distances_only) if min(distances_only) > 0 else 1  # Начинаем с 1, если 0 - минимальное
        r_max_model = max(distances_only) + 10  # Немного больше, чтобы показать тренд
        model_generation_distances = np.linspace(r_min_model, r_max_model, 100).tolist()  # 100 точек для гладкой кривой

        if button == 1:  # Левая кнопка мыши: выбор опорной точки
            # Находим ближайшую точку данных к координате x клика
            nearest_dist_index = np.argmin(np.abs(np.array(distances_only) - clicked_x))
            nearest_dist = distances_only[nearest_dist_index]
            nearest_density = densities_only[nearest_dist_index]

            # Проверка на r=0 для первой точки (Theta1/r)
            if nearest_dist == 0:
                self.view.set_status_message(
                    "Ошибка: Точка находится в центре города (r=0), невозможно рассчитать модель Q = Theta/r.")
                return

            if self._selected_point1 is None:
                # Первый клик
                self._selected_point1 = (nearest_dist, nearest_density)
                self._selected_point2 = None  # Сбросим вторую точку, если она была

                # Рассчитываем Theta1 для модели q = Theta1/r
                self._calculated_theta1 = nearest_density * nearest_dist
                self._calculated_theta2 = 0.0  # Для простой модели фон равен 0

                model_densities_single = [self._calculated_theta1 / r for r in model_generation_distances if r > 0]
                self.view.plot_single_point_model(self._selected_point1, model_generation_distances,
                                                  model_densities_single)
                self.view.set_status_message(
                    f"Первая опорная точка выбрана (r={nearest_dist:.0f}км, q={nearest_density:.2f}). Нажмите еще раз для второй точки или ПКМ для отмены.")

            else:
                # Второй клик
                if nearest_dist == self._selected_point1[0]:
                    self.view.set_status_message("Выберите вторую точку на другом расстоянии.")
                    return

                self._selected_point2 = (nearest_dist, nearest_density)

                r1, q1 = self._selected_point1
                r2, q2 = self._selected_point2

                # Решаем систему уравнений:
                # q1 = Theta1/r1 + Theta2
                # q2 = Theta1/r2 + Theta2

                # Theta1 = (q1 - q2) / (1/r1 - 1/r2)
                # Theta2 = q1 - Theta1/r1

                denominator = (1 / r1) - (1 / r2)
                if abs(denominator) < 1e-9:  # Проверка на слишком близкие r1, r2, чтобы избежать деления на ~ноль
                    self.view.set_status_message(
                        "Ошибка: Вторая опорная точка слишком близка к первой по расстоянию, невозможно решить систему.")
                    self._selected_point2 = None  # Сбросить некорректный выбор
                    return

                try:
                    self._calculated_theta1 = (q1 - q2) / denominator
                    self._calculated_theta2 = q1 - (self._calculated_theta1 / r1)

                    print(
                        f"Рассчитанная Theta1 (θ1): {self._calculated_theta1:.2f}, Theta2 (θ2, Фон): {self._calculated_theta2:.2f}")

                    # Генерируем точки для модели Q = Theta1/r + Theta2
                    model_densities_double = []
                    for r_val in model_generation_distances:
                        if r_val > 0:
                            model_densities_double.append((self._calculated_theta1 / r_val) + self._calculated_theta2)
                        else:
                            model_densities_double.append(np.nan)  # Деление на ноль, если r = 0

                    self.view.plot_double_point_model(self._selected_point1, self._selected_point2,
                                                      model_generation_distances, model_densities_double)
                    self.view.set_status_message(
                        f"Модель построена. $\\Theta_1$ = {self._calculated_theta1:.2f}, Фон ($\\Theta_2$) = {self._calculated_theta2:.2f}")

                except Exception as e:
                    self.view.set_status_message(f"Ошибка при расчете модели: {e}")
                    self._selected_point2 = None  # Сбросить некорректный выбор

        elif button == 3:  # Правая кнопка мыши: отмена
            if self._selected_point2:
                # Отмена второй точки
                self._selected_point2 = None
                self._calculated_theta2 = None

                # Перерисовываем модель по одной точке
                r1, q1 = self._selected_point1
                self._calculated_theta1 = q1 * r1
                self._calculated_theta2 = 0.0  # Возвращаем фон к 0 для простой модели

                model_densities_single = [self._calculated_theta1 / r for r in model_generation_distances if r > 0]
                self.view.plot_single_point_model(self._selected_point1, model_generation_distances,
                                                  model_densities_single)
                self.view.set_status_message("Вторая опорная точка отменена. Построена модель по первой точке.")
            elif self._selected_point1:
                # Отмена первой точки (и, следовательно, второй, если она была, но мы уже ее обнулили выше)
                self._selected_point1 = None
                self._calculated_theta1 = None
                self._calculated_theta2 = None
                self.view.clear_model_elements()  # Очищаем все модельные элементы
                self.view.set_status_message("Выбор точек отменен. График сброшен.")
            else:
                self.view.set_status_message("Нет выбранных точек для отмены.")

