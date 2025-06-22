import sys

from PySide6.QtWidgets import QApplication

from models.analysis import Analysis
from presenters.main_presenter import MainPresenter
from views.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    model = Analysis()
    view = MainWindow()
    MainPresenter(view, model)
    view.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()