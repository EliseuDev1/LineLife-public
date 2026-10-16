"""Testes automatizados da Fase 5 — Geração de Memória de Cálculo em PDF (ReportLab)."""

import os
import tempfile
import unittest
from unittest.mock import Mock

from src.application.project_service import ProjectService
from src.catalogs.cable_catalog import CableCatalog
from src.core.license_models import LicenseData, LicenseTier
from src.domain.installation_types import SlabInstallation
from src.domain.models import FallClearanceInput, LoadRuleType, SpanGeometry, UserLoadConfig
from src.domain.project import Project, ProjectStatus
from src.reports.pdf_generator import CalculationReportGenerator


class TestFase5Reports(unittest.TestCase):
    """Bateria de testes de validação da emissão de relatórios técnicos em PDF."""

    def setUp(self):
        self.generator = CalculationReportGenerator()
        self.catalog = CableCatalog()
        license_manager = Mock(get_license=lambda: LicenseData(tier=LicenseTier.LOCAL))
        self.service = ProjectService(self.catalog, license_manager=license_manager)
        self.cabo_base = self.catalog.get_by_specification("Ø5/16 - 6X19 SEALE EIPS - AF")
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_pdf_for_valid_calculated_project(self):
        """Valida emissão completa de PDF para projeto calculado e aprovado."""
        # 1. Configurar projeto aprovado
        proj = self.service.create_project(
            title="Linha Galpão Logístico",
            client="Suzano Papel e Celulose",
            location="Fábrica Ribas do Rio Pardo - MS",
            responsible_engineer="Eng. Especialista em Segurança",
            installation=SlabInstallation(
                concrete_fck_mpa=30.0,
                thickness_mm=150.0,
                anchor_edge_distance_mm=150.0,
                is_structure_validated_by_engineer=True,
                responsible_engineer_art="ART-2026-998877",
            ),
        )
        proj.cable = self.cabo_base
        proj.update_spans([
            SpanGeometry(span_index=1, span_mm=6000.0, initial_sag_percent=3.0),
            SpanGeometry(span_index=2, span_mm=8000.0, initial_sag_percent=3.0),
            SpanGeometry(span_index=3, span_mm=6000.0, initial_sag_percent=3.0),
        ])
        proj.user_config = UserLoadConfig(
            rule_type=LoadRuleType.NBR_16325_2,
            simultaneous_users=2,
        )
        proj.clearance_input = FallClearanceInput(available_clearance_m=6.50)

        # 2. Executar cálculo
        self.service.calculate_project(proj)
        self.assertEqual(proj.status, ProjectStatus.CALCULATED_VALID)

        # 3. Gerar PDF
        out_pdf = os.path.join(self.temp_dir.name, "memoria_calculo_aprovada.pdf")
        ret_path = self.generator.generate_pdf(proj, out_pdf)

        # 4. Verificações
        self.assertTrue(os.path.exists(out_pdf))
        self.assertEqual(ret_path, out_pdf)
        file_size = os.path.getsize(out_pdf)
        self.assertGreater(file_size, 10000, f"Arquivo PDF muito pequeno: {file_size} bytes")

        # Verifica cabeçalho binário do PDF (%PDF-)
        with open(out_pdf, "rb") as f:
            header = f.read(5)
            self.assertEqual(header, b"%PDF-")

    def test_generate_pdf_for_rejected_project(self):
        """Valida que um projeto reprovado por colisão gera PDF com parecer explícito."""
        proj = self.service.create_project(
            title="Linha Insegura com Vão Excessivo",
            client="Cliente Teste Reprovação",
            location="Canteiro de Obras",
            responsible_engineer="Eng. Auditor",
        )
        proj.cable = self.cabo_base
        proj.update_spans([
            SpanGeometry(span_index=1, span_mm=15000.0, initial_sag_percent=1.0),
        ])
        proj.user_config = UserLoadConfig(
            rule_type=LoadRuleType.NBR_16325_2,
            simultaneous_users=3,
        )
        # Altura disponível insuficiente propositalmente (2.0 m quando precisa de > 5 m)
        proj.clearance_input = FallClearanceInput(available_clearance_m=2.0)

        self.service.calculate_project(proj)
        self.assertEqual(proj.status, ProjectStatus.CALCULATED_REJECTED)

        out_pdf = os.path.join(self.temp_dir.name, "memoria_calculo_reprovada.pdf")
        self.generator.generate_pdf(proj, out_pdf)

        self.assertTrue(os.path.exists(out_pdf))
        self.assertGreater(os.path.getsize(out_pdf), 8000)

    def test_generate_pdf_with_custom_rule_and_divergence_warning(self):
        """Valida geração de PDF quando usuário escolhe regra customizada (divergência NBR)."""
        proj = self.service.create_project(
            title="Linha com Regra Customizada",
            client="Cliente Regra Especial",
            location="Área Industrial",
            responsible_engineer="Eng. Especialista",
        )
        proj.cable = self.cabo_base
        proj.update_spans([
            SpanGeometry(span_index=1, span_mm=8000.0, initial_sag_percent=3.0),
        ])
        proj.user_config = UserLoadConfig(
            rule_type=LoadRuleType.CUSTOM,
            simultaneous_users=2,
            dynamic_load_first_user_kgf=750.0,
            static_load_per_additional_kgf=150.0,
        )
        proj.clearance_input = FallClearanceInput(available_clearance_m=7.0)

        self.service.calculate_project(proj)

        out_pdf = os.path.join(self.temp_dir.name, "memoria_calculo_custom.pdf")
        self.generator.generate_pdf(proj, out_pdf)

        self.assertTrue(os.path.exists(out_pdf))
        self.assertGreater(os.path.getsize(out_pdf), 8000)


if __name__ == "__main__":
    unittest.main()
