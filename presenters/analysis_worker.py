import threading
import traceback

from PySide6.QtCore import QObject, Signal, Slot

from models import City
from models.analysis import Analysis
from models.exporters import CsvExporter
from models.fetchers import GeeFetcher


class AnalysisWorker(QObject):
    analysis_finished_signal = Signal()
    finished = Signal()
    progress = Signal(int, str)

    def __init__(self, analysis_model: Analysis, city: City, bearings: list[int], month: int,
                 distances: list[int]):
        super().__init__()
        self.analysis_model = analysis_model
        self.bearings = bearings
        self.city = city
        self.distances = distances
        self.exporter = CsvExporter()
        self.fetcher = GeeFetcher()
        self.month = month

        print("AnalysisWorker initialized.")

    @Slot()
    def run(self):
        print("AnalysisWorker run method started.")
        print("Current thread:", threading.current_thread().name)
        try:
            self.progress.emit(10, "Анализ запущен")
            print("Analysis model run method about to be called.")
            self.analysis_model.run(
                city=self.city,
                bearings=self.bearings,
                distances=self.distances,
                month=self.month,
                fetcher=self.fetcher,
                exporter=self.exporter
            )
            print("Analysis model run method finished.")

            self.progress.emit(100, "Finished")
            print(f"Progress update: 100%, Finished (Thread: {threading.current_thread().name})")

            self.analysis_finished_signal.emit()
            print(f"AnalysisWorker finished signal emitted (for UI update). Thread: {threading.current_thread().name}")

        except Exception as e:
            error_message = f"Error in AnalysisWorker: {e}"
            print(error_message)
            traceback.print_exc()
            self.progress.emit(0, error_message)
            self.analysis_finished_signal.emit()
            print(
                f"AnalysisWorker finished signal emitted due to error (for UI update). Thread: {threading.current_thread().name}")
        finally:
            self.finished.emit()
            print("Worker finished signal (for thread cleanup) emitted.")
