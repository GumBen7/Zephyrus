from PySide6.QtCore import QObject, Signal

from models import City, Fetcher, Exporter
from models.analysis import Analysis


class AnalysisWorker(QObject):
    finished = Signal()
    progress = Signal(int, str)
    data_ready_for_export = Signal(list)

    def __init__(self, analysis_model: Analysis, city: City, bearings: list[int], month: int,
                 distances: list[int], fetcher: Fetcher, exporter: Exporter):
        super().__init__()
        self.analysis_model = analysis_model
        self.city = city
        self.bearings = bearings
        self.month = month
        self.distances = distances
        self.fetcher = fetcher
        self.exporter = exporter

    def run(self):
        try:
            self.progress.emit(10, "Started analysis")
            all_flat_data = self.analysis_model.run(
                city=self.city,
                bearings=self.bearings,
                distances=self.distances,
                month=self.month,
                fetcher=self.fetcher,
                exporter=self.exporter
            )

            self.progress.emit(100, "Finished")
            self.data_ready_for_export.emit(all_flat_data)

        except Exception as e:
            self.progress.emit(0, f"Error: {e}")
        finally:
            self.finished.emit()