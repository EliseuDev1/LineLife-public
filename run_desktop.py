"""Ponto de entrada local do snapshot público de revisão."""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication
from src.application.project_service import ProjectService
from src.catalogs.cable_catalog import CableCatalog
from src.core.license_manager import LicenseManager
from src.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    license_manager = LicenseManager()
    service = ProjectService(CableCatalog(), license_manager=license_manager)
    window = MainWindow(service, license_manager)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
