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

        self._selected_point1: tuple[float, float] | None = None  # (r, q)
        self._selected_point2: tuple[float, float] | None = None  # (r, q)
        self._calculated_theta1: float | None = None
        self._calculated_theta2: float | None = None

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
        self.view.export_data_signal.connect(self.export_all_data)  # НОВОЕ: Подключаем сигнал экспорта
        self.view.city_selected_signal.connect(self.on_city_selected)
        self.view.bearing_selected_signal.connect(self.on_bearing_selected)
        self.view.month_selected_signal.connect(self.on_month_changed)
        self.view.data_route_selected_signal.connect(self.on_data_route_selected)

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
        self.view.plot_data(route)
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

    @Slot()  # НОВОЕ: Слот для экспорта всех загруженных данных
    def export_all_data(self):
        if not self.model.cities:
            self.view.set_status_message("Нет загруженных данных для экспорта.")
            return

        self.view.set_ui_enabled(False)
        self.view.set_status_message("Начинаем экспорт данных...")

        # Экспорт может занять время, возможно, его тоже стоит вынести в отдельный поток
        # Но для начала сделаем просто в основном потоке, если не будет зависаний UI
        try:
            self.model.export_all_loaded_data(self.model.exporter)  # НОВОЕ: Вызов метода экспорта из модели
            self.view.set_status_message(f"Данные успешно экспортированы в папку '{config.EXPORTS_FOLDER}'.")
        except Exception as e:
            self.view.set_status_message(f"Ошибка при экспорте данных: {e}")
            print(f"Error during export: {e}")
        finally:
            self.view.set_ui_enabled(True)
            self.view.update_data_tree(
                self.model.cities)  # Обновляем дерево, чтобы включить кнопку экспорта, если она была отключена

    @Slot(float, float, int)
    def on_plot_clicked(self, clicked_x: float, clicked_y: float, button: int):
        if not self.current_selected_data_route:
            self.view.set_status_message("Выберите данные для анализа на графике, чтобы построить модель.")
            return

        valid_data_points = [(d, q) for d, q in self.current_selected_data_route.densities.items() if not math.isnan(q)]

        if not valid_data_points:
            self.view.set_status_message("В выбранном маршруте нет действительных данных для построения модели.")
            return

        distances_only = [p[0] for p in valid_data_points]
        densities_only = [p[1] for p in valid_data_points]

        r_min_model = min(distances_only) if min(distances_only) > 0 else 1
        r_max_model = max(distances_only) + 10
        model_generation_distances = np.linspace(r_min_model, r_max_model, 100).tolist()

        if button == 1:
            nearest_dist_index = np.argmin(np.abs(np.array(distances_only) - clicked_x))
            nearest_dist = distances_only[nearest_dist_index]
            nearest_density = densities_only[nearest_dist_index]

            if nearest_dist == 0:
                self.view.set_status_message(
                    "Ошибка: Точка находится в центре города (r=0), невозможно рассчитать модель Q = Theta/r.")
                return

            if self._selected_point1 is None:
                self._selected_point1 = (nearest_dist, nearest_density)
                self._selected_point2 = None

                self._calculated_theta1 = nearest_density * nearest_dist
                self._calculated_theta2 = 0.0

                model_densities_single = [self._calculated_theta1 / r for r in model_generation_distances if r > 0]
                self.view.plot_single_point_model(self._selected_point1, model_generation_distances,
                                                  model_densities_single)
                self.view.set_status_message(
                    f"Первая опорная точка выбрана (r={nearest_dist:.0f}км, q={nearest_density:.2f}). Нажмите еще раз для второй точки или ПКМ для отмены.")

            else:
                if nearest_dist == self._selected_point1[0]:
                    self.view.set_status_message("Выберите вторую точку на другом расстоянии.")
                    return

                self._selected_point2 = (nearest_dist, nearest_density)

                r1, q1 = self._selected_point1
                r2, q2 = self._selected_point2

                denominator = (1 / r1) - (1 / r2)
                if abs(denominator) < 1e-9:
                    self.view.set_status_message(
                        "Ошибка: Вторая опорная точка слишком близка к первой по расстоянию, невозможно решить систему.")
                    self._selected_point2 = None
                    return

                try:
                    self._calculated_theta1 = (q1 - q2) / denominator
                    self._calculated_theta2 = q1 - (self._calculated_theta1 / r1)

                    print(
                        f"Рассчитанная Theta1 (θ1): {self._calculated_theta1:.2f}, Theta2 (θ2, Фон): {self._calculated_theta2:.2f}")

                    model_densities_double = []
                    for r_val in model_generation_distances:
                        if r_val > 0:
                            model_densities_double.append((self._calculated_theta1 / r_val) + self._calculated_theta2)
                        else:
                            model_densities_double.append(np.nan)

                    self.view.plot_double_point_model(self._selected_point1, self._selected_point2,
                                                      model_generation_distances, model_densities_double,
                                                      self._calculated_theta2)

                    self.view.set_status_message(
                        f"Модель построена. $\\Theta_1$ = {self._calculated_theta1:.2f}, Фон ($\\Theta_2$) = {self._calculated_theta2:.2f}")

                except Exception as e:
                    self.view.set_status_message(f"Ошибка при расчете модели: {e}")
                    self._selected_point2 = None

        elif button == 3:
            if self._selected_point2:
                self._selected_point2 = None
                self._calculated_theta2 = None

                r1, q1 = self._selected_point1
                self._calculated_theta1 = q1 * r1
                self._calculated_theta2 = 0.0

                model_densities_single = [self._calculated_theta1 / r for r in model_generation_distances if r > 0]
                self.view.plot_single_point_model(self._selected_point1, model_generation_distances,
                                                  model_densities_single)
                self.view.set_status_message("Вторая опорная точка отменена. Построена модель по первой точке.")
            elif self._selected_point1:
                self._selected_point1 = None
                self._calculated_theta1 = None
                self._calculated_theta2 = None
                self.view.clear_model_elements()
                self.view.set_status_message("Выбор точек отменен. График сброшен.")
            else:
                self.view.set_status_message("Нет выбранных точек для отмены.")
