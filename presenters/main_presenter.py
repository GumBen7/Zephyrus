# presenters/main_presenter.py
import threading

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
        # Подключаем сигнал от View к слоту в Презентере
        self.view.data_route_selected_signal.connect(self.on_data_route_selected)
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

    @Slot(MonthlyDataRoute)  # Указываем тип аргумента для слота
    def on_data_route_selected(self, route: MonthlyDataRoute):
        """Слот для обработки выбора MonthlyDataRoute из дерева данных."""
        self.current_selected_data_route = route
        print(
            f"Selected data route in presenter: Bearing={route.bearing}, Month={route.month}, Year={route.year}. Densities: {route.densities}")
        # Вызываем метод отрисовки в View
        self.view.plot_data(route)

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
            f"Worker's thread affinity after moveToThread: {threading.current_thread().name} (QObject thread: {self.worker.thread}, QApplication thread: {QCoreApplication.instance().thread()})")

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