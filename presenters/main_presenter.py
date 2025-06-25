# /home/gumben7/PycharmProjects/Zephyrus/presenters/main_presenter.py

import threading
import math # Для расчета ближайшей точки и Theta
import numpy as np # Для генерации точек модельной функции и работы с nan

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

        # --- НОВОЕ: Подключение сигнала клика по графику ---
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
        self.current_selected_data_route = route  # Сохраняем выбранный маршрут
        print(
            f"Selected data route in presenter: Bearing={route.bearing}, Month={route.month}, Year={route.year}. Densities: {route.densities}")
        self.view.plot_data(route)  # Отрисовываем базовый график

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
        self.view.set_status_message("Анализ завершен!")
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

    # --- НОВЫЙ СЛОТ: Обработка кликов по графику ---
    @Slot(float, float) # Указываем типы аргументов: x, y
    def on_plot_clicked(self, clicked_x: float, clicked_y: float):
        """
        Обрабатывает клик по графику, находит ближайшую точку данных,
        рассчитывает Theta и отображает модельную функцию.
        """
        if not self.current_selected_data_route:
            print("Нет выбранных данных для построения модели.")
            self.view.set_status_message("Выберите данные для анализа на графике, чтобы построить модель.")
            return

        # Фильтруем данные, чтобы исключить NaN перед поиском ближайшей точки
        valid_distances = []
        valid_densities = []
        for dist, density in self.current_selected_data_route.densities.items():
            if not math.isnan(density):
                valid_distances.append(dist)
                valid_densities.append(density)

        if not valid_distances:
            print("Нет действительных данных для построения модели в выбранном маршруте.")
            self.view.set_status_message("В выбранном маршруте нет действительных данных для построения модели.")
            return

        # 1. Находим ближайшую точку данных к координате x клика
        # Используем valid_distances для поиска ближайшей точки
        nearest_dist_index = np.argmin(np.abs(np.array(valid_distances) - clicked_x))
        nearest_dist = valid_distances[nearest_dist_index]
        nearest_density = valid_densities[nearest_dist_index] # Получаем соответствующую плотность

        print(f"Ближайшая точка данных: r={nearest_dist}, q={nearest_density:.2f}")

        # Используем эту точку как опорную для расчета Theta
        # Если nearest_dist очень близко к нулю, это может вызвать деление на ноль
        if nearest_dist == 0:
            print("Ошибка: Выбранная точка находится в центре города (r=0), невозможно рассчитать Theta.")
            self.view.set_status_message("Невозможно рассчитать модель: точка находится в центре города (r=0).")
            return

        # 2. Рассчитываем Theta: q = Theta / r => Theta = q * r
        calculated_theta = nearest_density * nearest_dist
        print(f"Рассчитанная Theta (θ): {calculated_theta:.2f}")

        # 3. Генерируем точки для новой гладкой функции q = Theta / r
        # Создаем диапазон расстояний для отрисовки модели
        # Избегаем деления на ноль, начиная с небольшого значения > 0.
        r_min = min(valid_distances) if min(valid_distances) > 0 else 1 # Начинаем с 1, если 0 - минимальное
        r_max = max(valid_distances) + 10 # Немного больше, чтобы показать тренд
        model_distances = np.linspace(r_min, r_max, 100) # 100 точек для гладкой кривой

        # Защита от деления на ноль для model_distances
        model_densities = []
        for r in model_distances:
            if r > 0:
                model_densities.append(calculated_theta / r)
            else:
                model_densities.append(np.nan) # Если r = 0, добавляем NaN, хотя по идее это уже отфильтровано

        # 4. Отрисовываем модельную функцию на графике
        self.view.plot_model_data(model_distances, model_densities, (nearest_dist, nearest_density))
        self.view.set_status_message(f"Модель построена. Theta (θ) = {calculated_theta:.2f}")