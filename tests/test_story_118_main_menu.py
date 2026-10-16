"""Testes headless da Story 1.18: menu e shell da Linha de Vida."""

import os
import sys
import unittest
from unittest.mock import Mock

os.environ["QT_QPA_PLATFORM"] = "offscreen"

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication, QHBoxLayout

from src.application.project_service import ProjectService
from src.catalogs.cable_catalog import CableCatalog
from src.core.license_models import LicenseData, LicenseTier
from src.ui.main_window import MainWindow


class TestStory118MainMenu(unittest.TestCase):
    """Valida somente a navegação autorizada pela Story 1.18."""

    MENU_LABELS = [
        "Linha de Vida",
        "Dimensionamento de Bombas",
        "Dimensionamento de Tubulações",
        "Gestão de Projetos",
    ]
    STAGE_LABELS = ["Identificação", "Geometria", "Cargas/ZLQ", "Cabo", "Resultados"]

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["--platform", "offscreen"])
        cls.license_data = LicenseData(tier=LicenseTier.LOCAL)
        cls.license_manager = Mock(get_license=lambda: cls.license_data)
        cls.service = ProjectService(CableCatalog(), license_manager=cls.license_manager)

    def setUp(self):
        self.window = MainWindow(self.service, self.license_manager)

    def tearDown(self):
        self.window.close()
        self.app.processEvents()

    def test_menu_has_exactly_the_approved_four_blocks(self):
        self.assertEqual(len(self.window.menu_blocks), 4)
        self.assertEqual(
            [block.title_label.text() for block in self.window.menu_blocks],
            self.MENU_LABELS,
        )

    def test_launcher_hides_shell_chrome(self):
        self.window.show()
        self.app.processEvents()

        self.assertTrue(self.window.menuBar().isHidden())
        self.assertTrue(self.window.toolbar.isHidden())
        self.assertTrue(self.window.statusBar().isHidden())

    def test_launcher_has_title_subtitle_and_informative_footer(self):
        self.assertEqual(self.window.launcher_title.text(), "Escolha um sistema")
        self.assertEqual(
            self.window.launcher_subtitle.text(),
            "Selecione um sistema para começar",
        )
        self.assertEqual(
            self.window.launcher_footer.text(),
            "Mais sistemas serão disponibilizados em breve.",
        )

    def test_every_launcher_card_has_icon_description_badge_and_button(self):
        for card in self.window.menu_blocks:
            self.assertTrue(card.icon_label.text())
            self.assertTrue(card.description_label.text())
            self.assertTrue(card.status_label.text())
            self.assertTrue(card.action_button.text())

    def test_launcher_buttons_reflect_available_and_future_systems(self):
        active_card, *future_cards = self.window.menu_blocks

        self.assertEqual(active_card.status_label.text(), "DISPONÍVEL")
        self.assertEqual(active_card.action_button.text(), "Abrir sistema")
        self.assertTrue(active_card.action_button.isEnabled())

        for card in future_cards:
            self.assertEqual(card.status_label.text(), "EM BREVE")
            self.assertEqual(card.action_button.text(), "Em desenvolvimento")
            self.assertFalse(card.action_button.isEnabled())

    def test_only_lifeline_is_enabled_and_future_blocks_are_coming_soon(self):
        self.assertTrue(self.window.menu_blocks[0].isEnabled())
        for block in self.window.menu_blocks[1:]:
            self.assertFalse(block.isEnabled())
            self.assertEqual(block.status_label.text(), "EM BREVE")

    def test_lifeline_block_opens_the_existing_shell(self):
        self.assertTrue(self.window.is_main_menu_visible)
        self.window.menu_blocks[0].activate()
        self.assertFalse(self.window.is_main_menu_visible)
        self.assertIs(self.window.centralWidget().currentWidget(), self.window.shell_widget)

    def test_shell_restores_chrome_and_existing_actions(self):
        self.window.show()
        self.window.open_lifeline_shell()
        self.app.processEvents()

        self.assertFalse(self.window.menuBar().isHidden())
        self.assertFalse(self.window.toolbar.isHidden())
        self.assertFalse(self.window.statusBar().isHidden())
        toolbar_action_texts = [action.text() for action in self.window.toolbar.actions()]
        self.assertIn("&Novo Projeto", toolbar_action_texts)
        self.assertIn("⚡ &Calcular Linha de Vida", toolbar_action_texts)
        self.assertIn("📄 &Gerar Memória de Cálculo (PDF)...", toolbar_action_texts)
        self.assertIn("📊 &Exportar Lista de Materiais (Excel)...", toolbar_action_texts)
        self.assertTrue(self.window.act_calc.isVisible())
        self.assertTrue(self.window.act_pdf.isVisible())
        self.assertTrue(self.window.act_bom.isVisible())
        self.assertEqual(self.window.tabs.tabText(5), "6. Lista de Materiais (BOM)")
        self.assertEqual(self.window.btn_back_to_menu.text(), "Voltar ao menu")

    def test_shell_keeps_the_five_existing_stages_in_order(self):
        self.window.open_lifeline_shell()
        self.assertEqual(self.window.line_life_stage_labels, self.STAGE_LABELS)
        stage_tabs = [self.window.tabs.tabText(index) for index in range(5)]
        self.assertEqual(
            stage_tabs,
            [
                "1. Identificação & Instalação",
                "2. Postes & Vãos (Geometria)",
                "3. Usuários, Cargas & ZLQ",
                "4. Cabo de Aço",
                "5. Resultados & Auditoria",
            ],
        )
        self.assertEqual(self.window.tabs.count(), 6)
        self.assertEqual(self.window.tabs.tabText(5), "6. Lista de Materiais (BOM)")

    def test_back_to_menu_returns_without_changing_project_or_license_state(self):
        self.window.open_lifeline_shell()
        project = self.window.current_project
        project_id = id(project)
        self.window.txt_title.setText("Projeto preservado")
        self.app.processEvents()
        title_before_back = project.title
        license_before_back = self.license_manager.get_license()

        self.assertEqual(self.window.btn_back_to_menu.text(), "Voltar ao menu")
        self.window.btn_back_to_menu.click()
        self.assertTrue(self.window.is_main_menu_visible)
        self.assertIs(self.window.current_project, project)
        self.assertEqual(id(self.window.current_project), project_id)
        self.assertEqual(self.window.current_project.title, title_before_back)
        self.assertIs(self.license_manager.get_license(), license_before_back)

        self.window.open_lifeline_shell()
        self.assertIs(self.window.current_project, project)
        self.assertEqual(self.window.txt_title.text(), "Projeto preservado")
    def test_every_action_button_is_fixed_width_and_centered_in_one_row(self):
        self.window.show()
        self.app.processEvents()

        for card in self.window.menu_blocks:
            button = card.action_button
            self.assertEqual(button.minimumWidth(), 210)
            self.assertEqual(button.maximumWidth(), 210)

            button_row = next(
                (
                    card.layout().itemAt(index).layout()
                    for index in range(card.layout().count())
                    if card.layout().itemAt(index).layout()
                    and any(
                        card.layout().itemAt(index).layout().itemAt(child_index).widget()
                        is button
                        for child_index in range(card.layout().itemAt(index).layout().count())
                    )
                ),
                None,
            )
            self.assertIsInstance(button_row, QHBoxLayout)
            self.assertEqual(button_row.count(), 3)
            self.assertIsNotNone(button_row.itemAt(0).spacerItem())
            self.assertIsNotNone(button_row.itemAt(2).spacerItem())
            self.assertAlmostEqual(
                button.geometry().center().x(),
                card.rect().center().x(),
                delta=2,
            )

    def test_active_card_keeps_system_active_and_available_labels(self):
        active_card = self.window.menu_blocks[0]

        self.assertIs(active_card.property("systemActive"), True)
        self.assertTrue(active_card.title_label.text())
        self.assertTrue(active_card.status_label.text())
        self.assertTrue(active_card.description_label.text())
        self.assertTrue(active_card.action_button.text())
        self.assertTrue(active_card.action_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
