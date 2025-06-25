# presenters/analysis_worker.py (без изменений)

import threading
import traceback

from PySide6.QtCore import QObject, Signal, QMetaObject, Qt

from models import City
from models.analysis import Analysis
from models.fetchers import GeeFetcher
from models.exporters import CsvExporter


class AnalysisWorker(QObject):
    finished = Signal()
    progress = Signal(int, str)
    analysis_finished_signal = Signal()

    def __init__(self, analysis_model: Analysis, city: City, bearings: list[int], month: int,
                 distances: list[int]):
        super().__init__()
        self.analysis_model = analysis_model
        self.city = city
        self.bearings = bearings
        self.month = month
        self.distances = distances

        self.fetcher = GeeFetcher()
        self.exporter = CsvExporter()

        print("AnalysisWorker initialized.")

    def run(self):
        print("AnalysisWorker run method started.")
        print("Current thread:", threading.current_thread().name)
        try:
            print(f"GeeFetcher thread affinity: {self.fetcher.thread() if hasattr(self.fetcher, 'thread') else 'N/A'}")

            self.progress.emit(10, "Started analysis")
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
            print(f"AnalysisWorker finished signal emitted due to error (for UI update). Thread: {threading.current_thread().name}")
        finally:
            self.finished.emit()
            print("Worker finished signal (for thread cleanup) emitted.")