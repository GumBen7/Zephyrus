from PySide6.QtCore import QThread

import config
from models import City
from models.analysis import Analysis
from models.exporters import CsvExporter
from models.fetchers import GeeFetcher
from presenters.analysis_worker import AnalysisWorker
from views.main_window import MainWindow


class MainPresenter:
    def __init__(self, view: MainWindow, model: Analysis):
        self.view = view
        self.model = model
        self.fetcher = GeeFetcher()
        self.exporter = CsvExporter()

        self.thread: QThread | None = None
        self.worker: AnalysisWorker | None = None

        self.current_city : City | None = None
        self.current_bearing: int | None = None
        self.current_month: int | None = None

        self._connect_signals()

        first_city = next(iter(config.CITIES.values()), None)
        if first_city:
            self.on_city_selected(first_city)

        first_bearing = list(config.BEARINGS.keys())[0]
        if first_bearing is not None:
            self.on_bearing_selected(first_bearing)

        first_month = list(config.MONTHS.keys())[0]
        if first_month is not None:
            self.on_month_selected(first_month)

    def _connect_signals(self):
        self.view.start_analysis_signal.connect(self.run_analysis)
        self.view.city_selected_signal.connect(self.on_city_selected)
        self.view.bearing_selected_signal.connect(self.on_bearing_selected)
        self.view.month_selected_signal.connect(self.on_month_selected)
        print("Signals connected.")

    def on_city_selected(self, city: City):
        self.current_city = city
        print(f"City selected: {city.name}")

    def on_bearing_selected(self, bearing: int):
        self.current_bearing = bearing
        print(f"Bearing selected: {bearing}")

    def on_month_selected(self, month: int):
        self.current_month = month
        print(f"Month selected: {month}")

    def run_analysis(self):
        print("run_analysis called.")
        distance_params = self.view.get_distance_parameters()
        if not self.current_city or self.current_bearing is None or self.current_month is None or not distance_params:
            print("Missing parameters for analysis. Aborting.")
            return
        distances = list(range(
            distance_params['step'],
            distance_params['max'] + 1,
            distance_params['step']
        ))
        print(f"Analysis parameters: City={self.current_city.name}, Bearing={self.current_bearing}, Month={self.current_month}, Distances={distances}")

        #self.view.set_ui_enabled(False)
        #self.view.set_progress(5, "Starting analysis")

        if self.thread and self.thread.isRunning():
            print("Worker thread is already running, not starting a new one.")
            return

        self.thread = QThread()
        self.worker = AnalysisWorker(
            analysis_model=self.model,
            city=self.current_city,
            bearings=[self.current_bearing],
            month=self.current_month,
            distances=distances,
            fetcher=self.fetcher,
            exporter=self.exporter
        )
        self.worker.moveToThread(self.thread)
        print("Worker moved to thread.")
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        print("Worker/Thread signals connected.")
        # self.thread.finished.connect(lambda: self.view.set_ui_enabled(True))

        #self.worker.progress.connect(self.view.set_progress)
        # self.worker.data_ready_for_export.connect(self.on_data_ready)

        self.thread.start()
        print("Thread started.")