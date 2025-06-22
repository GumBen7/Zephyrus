import sys

from PySide6.QtWidgets import QApplication

from models.analysis import Analysis


def main():
    app = QApplication(sys.argv)
    analysis = Analysis()

if __name__ == "__main__":
    main()