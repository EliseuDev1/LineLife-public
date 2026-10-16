"""Suíte de Testes Automatizados da Fase 3.

Valida os requisitos de modelo de projeto, tipos de instalação, pendências estruturais,
invalidação automática de resultados e persistência em arquivo .lvd.
"""

import json
import os
import tempfile
import unittest
import sys
from unittest.mock import Mock

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.application.project_service import ProjectService
from src.catalogs.cable_catalog import CableCatalog
from src.core.license_models import LicenseData, LicenseTier
from src.domain.installation_types import (
    IndustrialInstallation,
    InstallationCategory,
    MunckInstallation,
    RoofInstallation,
    SlabInstallation,
)
from src.domain.models import SpanGeometry, UserLoadConfig
from src.domain.project import Project, ProjectStatus
from src.persistence.project_serializer import ProjectSerializer


class TestFase3Project(unittest.TestCase):
    """Testes de modelo de projeto, ciclo de vida e persistência .lvd."""

    def test_unknown_lvd_schema_preserves_original_bytes(self):
        """Um esquema desconhecido não pode ser reinterpretado e salvo como atual."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "futuro.lvd")
            content = json.dumps({
                "format": "LINHA_DE_VIDA_DOCUMENT",
                "version": "9.0.0",
                "data": {"future_field": "preservar"},
            }).encode("utf-8")
            with open(path, "wb") as file:
                file.write(content)

            with self.assertRaisesRegex(ValueError, "Versão .lvd incompatível"):
                ProjectSerializer.load_from_file(path)
            with open(path, "rb") as file:
                self.assertEqual(file.read(), content)

    @classmethod
    def setUpClass(cls):
        cls.catalog = CableCatalog()
        # Este módulo valida persistência multi-vão; fixa explicitamente local review
        # para que o tier Free atual não torne o cenário de cálculo ambíguo.
        license_manager = Mock(get_license=lambda: LicenseData(tier=LicenseTier.LOCAL))
        cls.service = ProjectService(cls.catalog, license_manager=license_manager)

    def test_installation_types_structural_gaps_handling(self):
        """Valida que campos estruturais essenciais faltantes são marcados como pendências e impedem aprovação."""
        # 1. Laje sem espessura e sem ART
        slab = SlabInstallation(
            thickness_mm=None,
            concrete_fck_mpa=None,
            is_structure_validated_by_engineer=False,
        )
        gaps = slab.get_structural_gaps()
        self.assertFalse(slab.can_approve_structurally())
        self.assertTrue(any("Espessura da laje" in g for g in gaps))
        self.assertTrue(any("ART" in g for g in gaps))

        # Laje completa e validada por engenheiro
        slab_ok = SlabInstallation(
            thickness_mm=150.0,
            concrete_fck_mpa=25.0,
            anchor_edge_distance_mm=200.0,
            is_structure_validated_by_engineer=True,
            responsible_engineer_art="ART-2026-998877",
        )
        self.assertTrue(slab_ok.can_approve_structurally())
        self.assertEqual(len(slab_ok.get_structural_gaps()), 0)

        # 2. Telhado com fibrocimento
        roof_fibro = RoofInstallation(tile_type="Fibrocimento ondulada")
        roof_gaps = roof_fibro.get_structural_gaps()
        self.assertTrue(any("fibrocimento são frágeis" in g for g in roof_gaps))

        # 3. Caminhão Munck com restrição obrigatória
        munck = MunckInstallation(allows_vehicle_motion=True)
        munck_gaps = munck.get_structural_gaps()
        self.assertTrue(any("RESTRIÇÃO DE SEGURANÇA MUNCK" in g for g in munck_gaps))
        self.assertTrue(any("movimento" in g for g in munck_gaps))

    def test_project_lifecycle_and_automatic_invalidation(self):
        """Valida que alterar qualquer entrada relevante invalida imediatamente o cálculo prévio."""
        project = self.service.create_project(title="Projeto Invalidação")
        self.assertEqual(project.status, ProjectStatus.DRAFT)
        self.assertFalse(project.can_generate_bom)

        # Configura laje validada para permitir aprovação
        project.installation = SlabInstallation(
            thickness_mm=150.0,
            concrete_fck_mpa=25.0,
            anchor_edge_distance_mm=200.0,
            is_structure_validated_by_engineer=True,
            responsible_engineer_art="ART-12345",
        )

        # Executa o cálculo
        self.service.calculate_project(project)
        self.assertEqual(project.status, ProjectStatus.CALCULATED_VALID)
        self.assertIsNotNone(project.calculation_result)
        self.assertTrue(project.can_generate_bom)

        # Teste de Invalidação 1: Alterar vão
        project.update_spans([SpanGeometry(span_index=1, span_mm=8000.0, initial_sag_percent=3.0)])
        self.assertEqual(project.status, ProjectStatus.INVALIDATED)
        self.assertIsNone(project.calculation_result)
        self.assertFalse(project.can_generate_bom)

        # Recalcula
        self.service.calculate_project(project)
        self.assertEqual(project.status, ProjectStatus.CALCULATED_VALID)
        self.assertTrue(project.can_generate_bom)

        # Teste de Invalidação 2: Alterar cabo
        cabo_alt = self.catalog.get_by_specification("Ø3/8 - 6X19 SEALE EIPS - AF")
        project.update_cable(cabo_alt)
        self.assertEqual(project.status, ProjectStatus.INVALIDATED)
        self.assertIsNone(project.calculation_result)
        self.assertFalse(project.can_generate_bom)

        # Teste de Invalidação 3: Alterar usuários
        self.service.calculate_project(project)
        self.assertEqual(project.status, ProjectStatus.CALCULATED_VALID)
        project.update_user_config(UserLoadConfig(total_users=2, simultaneous_users=2))
        self.assertEqual(project.status, ProjectStatus.INVALIDATED)
        self.assertFalse(project.can_generate_bom)

    def test_lvd_file_save_and_load_persistence(self):
        """Valida que o projeto é serializado e recuperado fielmente em arquivo .lvd."""
        project = self.service.create_project(
            title="Projeto Linha Galpão Norte",
            client="Indústrias Metalúrgicas S/A",
            location="Galpão 03 - Vão Central",
            responsible_engineer="Eng. Carlos Silva - CREA 12345/D",
            installation=RoofInstallation(
                roof_type="Duas Águas",
                tile_type="Metálica Trapezoidal",
                support_element="Terça Metálica Z200",
                support_spacing_mm=1500.0,
                is_structure_validated_by_engineer=True,
                responsible_engineer_art="ART-MG-992211",
            ),
        )
        project.spans = [
            SpanGeometry(span_index=1, span_mm=6000.0, initial_sag_percent=3.0),
            SpanGeometry(span_index=2, span_mm=7500.0, initial_sag_percent=3.0),
        ]
        project.user_config = UserLoadConfig(total_users=2, simultaneous_users=2)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "projeto_teste.lvd")

            # Salva
            self.service.save_project(project, file_path)
            self.assertTrue(os.path.exists(file_path))

            # Carrega
            loaded = self.service.load_project(file_path)

            self.assertEqual(loaded.title, "Projeto Linha Galpão Norte")
            self.assertEqual(loaded.client, "Indústrias Metalúrgicas S/A")
            self.assertEqual(loaded.location, "Galpão 03 - Vão Central")
            self.assertEqual(loaded.responsible_engineer, "Eng. Carlos Silva - CREA 12345/D")
            self.assertEqual(loaded.installation.category, InstallationCategory.ROOF)
            self.assertIsInstance(loaded.installation, RoofInstallation)
            self.assertEqual(loaded.installation.tile_type, "Metálica Trapezoidal")
            self.assertEqual(loaded.installation.responsible_engineer_art, "ART-MG-992211")
            self.assertEqual(len(loaded.spans), 2)
            self.assertEqual(loaded.spans[0].span_mm, 6000.0)
            self.assertEqual(loaded.spans[1].span_mm, 7500.0)
            self.assertEqual(loaded.user_config.simultaneous_users, 2)
            self.assertIsNotNone(loaded.cable)
            self.assertEqual(loaded.cable.specification, "Ø5/16 - 6X19 SEALE EIPS - AF")

            # Recalcula o projeto carregado
            self.service.calculate_project(loaded)
            self.assertEqual(loaded.status, ProjectStatus.CALCULATED_VALID)
            self.assertTrue(loaded.can_generate_bom)

    def test_clone_project(self):
        """Valida que clonar um projeto cria uma nova cópia independente em modo rascunho."""
        original = self.service.create_project(title="Projeto Original")
        self.service.calculate_project(original)

        cloned = self.service.clone_project(original, new_title="Projeto Clonado")
        self.assertNotEqual(cloned.project_id, original.project_id)
        self.assertEqual(cloned.title, "Projeto Clonado")
        self.assertEqual(cloned.status, ProjectStatus.DRAFT)
        self.assertIsNone(cloned.calculation_result)
        self.assertFalse(cloned.can_generate_bom)


if __name__ == "__main__":
    unittest.main()
