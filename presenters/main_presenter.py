import config
from models import City
from models.analysis import Analysis
from models.exporters import CsvExporter
from models.fetchers import GeeFetcher
from views.main_window import MainWindow


class MainPresenter:
    def __init__(self, view: MainWindow, model: Analysis):
        self.view = view
        self.model = model
        self.fetcher = GeeFetcher()
        self.exporter = CsvExporter()

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

    def on_city_selected(self, city: City):
        self.current_city = city

    def on_bearing_selected(self, bearing: int):
        self.current_bearing = bearing

    def on_month_selected(self, month: int):
        self.current_month = month

    def run_analysis(self):
        selected_distances = self.view.get_selected_distances()
        if not self.current_city or self.current_bearing is None or not selected_distances:
            return
        self.model.run(
            city=self.current_city,
            bearings=[self.current_bearing],
            month=self.current_month,
            distances=selected_distances,
            fetcher=self.fetcher,
            exporter=self.exporter
        )