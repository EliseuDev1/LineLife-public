"""Suíte de Testes Automatizados da Interface Gráfica (Fase 4).

Executa testes automatizados de GUI em modo headless (offscreen) validando:
1. Inicialização limpa da MainWindow e abas guiadas;
2. Alternância dinâmica de tipos de instalação física (Laje, Telhado, Industrial, Munck);
3. Sincronização entre tabela de vãos e o canvas esquemático 2D;
4. Disparo do cálculo via interface e preenchimento dos cards e tabelas de resultados;
5. Invalidação automática dos badges e resultados ao alterar parâmetros.
"""

import os
import sys
import unittest
from unittest.mock import Mock

os.environ["QT_QPA_PLATFORM"] = "offscreen"

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication, QLabel
from src.application.project_service import ProjectService
from src.catalogs.cable_catalog import CableCatalog
from src.core.license_models import LicenseData, LicenseTier
from src.domain.installation_types import InstallationCategory, SlabInstallation
from src.domain.project import ProjectStatus
from src.ui.main_window import MainWindow


class TestFase4UI(unittest.TestCase):
    """Testes automatizados da camada visual (PySide6)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication(["--platform", "offscreen"])

        cls.catalog = CableCatalog()
        cls.license_manager = Mock(get_license=lambda: LicenseData(tier=LicenseTier.LOCAL))
        cls.service = ProjectService(cls.catalog, license_manager=cls.license_manager)

    def setUp(self):
        self.window = MainWindow(self.service, self.license_manager)

    def tearDown(self):
        self.window.close()

    def test_ui_initialization_and_default_state(self):
        """Valida inicialização correta das abas, título e estado inicial."""
        self.assertEqual(self.window.tabs.count(), 6)
        self.assertEqual(self.window.windowTitle(), "LineLife — Public Review")
        self.assertFalse(self.window.windowIcon().isNull())
        self.assertEqual(self.window.tabs.tabText(0), "1. Identificação & Instalação")
        self.assertEqual(self.window.tabs.tabText(1), "2. Postes & Vãos (Geometria)")
        self.assertEqual(self.window.tabs.tabText(2), "3. Usuários, Cargas & ZLQ")
        self.assertEqual(self.window.tabs.tabText(3), "4. Cabo de Aço")
        self.assertEqual(self.window.tabs.tabText(4), "5. Resultados & Auditoria")
        self.assertEqual(self.window.tabs.tabText(5), "6. Lista de Materiais (BOM)")

        self.assertEqual(self.window.spn_num_posts.value(), 2)
        self.assertEqual(self.window.table_spans.rowCount(), 1)
        self.assertEqual(self.window.lbl_status_badge.text(), "RASCUNHO")

    def test_ui_switch_installation_types(self):
        """Valida alternância entre os formulários especializados de instalação."""
        self.window.installation_widget.cmb_category.setCurrentIndex(1)
        inst_slab = self.window.installation_widget.get_installation()
        self.assertEqual(inst_slab.category, InstallationCategory.SLAB)

        self.window.installation_widget.cmb_category.setCurrentIndex(2)
        inst_roof = self.window.installation_widget.get_installation()
        self.assertEqual(inst_roof.category, InstallationCategory.ROOF)

        self.window.installation_widget.cmb_category.setCurrentIndex(3)
        inst_munck = self.window.installation_widget.get_installation()
        self.assertEqual(inst_munck.category, InstallationCategory.MUNCK)

    def test_ui_multi_span_sync_with_canvas(self):
        """Valida que alterar a quantidade de postes atualiza a tabela de vãos e o canvas 2D."""
        self.window.spn_num_posts.setValue(4)
        self.assertEqual(len(self.window.current_project.spans), 3)
        self.assertEqual(self.window.table_spans.rowCount(), 3)
        self.assertEqual(len(self.window.canvas_2d._spans), 3)

    def test_ui_calculation_trigger_and_results(self):
        """Valida execução do cálculo via interface, exibição de resultados e badge aprovado."""
        self.window.installation_widget.set_installation(
            SlabInstallation(
                thickness_mm=150.0,
                concrete_fck_mpa=25.0,
                anchor_edge_distance_mm=200.0,
                is_structure_validated_by_engineer=True,
                responsible_engineer_art="ART-TESTE-GUI",
            )
        )

        self.window._on_action_calculate()

        self.assertEqual(self.window.current_project.status, ProjectStatus.CALCULATED_VALID)
        self.assertEqual(self.window.lbl_status_badge.text(), "✓ APROVADO")

        res = self.window.current_project.calculation_result
        self.assertIsNotNone(res)
        self.assertEqual(self.window.table_results.rowCount(), 1)

        lbl_t = self.window.card_tension.findChild(QLabel, "val")
        self.assertIsNotNone(lbl_t)
        self.assertIn("kgf", lbl_t.text())

    def test_ui_automatic_invalidation_on_parameter_change(self):
        """Valida que alterar parâmetros na UI invalida o resultado prévio e atualiza o badge."""
        self.window._on_action_calculate()
        self.assertIn("APROVADO", self.window.lbl_status_badge.text())

        self.window.spn_equal_span.setValue(8500.0)
        self.window._on_apply_equal_spans()

        self.assertEqual(self.window.current_project.status, ProjectStatus.INVALIDATED)
        self.assertIn("ALTERADO", self.window.lbl_status_badge.text())


if __name__ == "__main__":
    unittest.main()
