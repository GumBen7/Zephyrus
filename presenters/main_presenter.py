from models.analysis import Analysis
from views.main_window import MainWindow


class MainPresenter:
    def __init__(self, view: MainWindow, model: Analysis):
        self.view = view
        self.model = model
        self._connect_signals()

    def _connect_signals(self):
        self.view.start_analysis_signal.connect(self.run_analysis)

    def run_analysis(self):
        self.model.run()