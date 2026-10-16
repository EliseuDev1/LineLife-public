"""Serviço de aplicação para orquestração de projetos de linha de vida."""

import os
import tempfile
from typing import Any, Callable, List, Optional
from src.calculations.engine import CalculationEngine
from src.catalogs.cable_catalog import CableCatalog
from src.core.license_models import LicenseData
from src.domain.installation_types import IndustrialInstallation, InstallationBase
from src.domain.models import CableProperties, FallClearanceInput, SpanGeometry, UserLoadConfig
from src.domain.project import Project, ProjectStatus
from src.persistence.project_serializer import ProjectSerializer


class ProjectService:
    """Orquestrador de casos de uso de projeto."""

    def __init__(
        self,
        catalog: Optional[CableCatalog] = None,
        license_manager: Optional[Any] = None,
    ):
        self.catalog = catalog or CableCatalog()
        self.engine = CalculationEngine()
        self.serializer = ProjectSerializer()
        self.license_manager = license_manager

    def get_license(self) -> LicenseData:
        """Obtém a licença ativa através do license_manager ou do singleton local."""
        if self.license_manager is not None:
            return self.license_manager.get_license()
        try:
            from src.core.license_manager import LicenseManager
            return LicenseManager().get_license()
        except Exception:
            return LicenseData()

    def create_project(
        self,
        title: str = "Novo Projeto",
        client: str = "Cliente",
        location: str = "Área Operacional",
        responsible_engineer: str = "Engenheiro Responsável",
        installation: Optional[InstallationBase] = None,
        default_cable_spec: str = "Ø5/16 - 6X19 SEALE EIPS - AF",
    ) -> Project:
        """Cria um novo projeto com valores padrão de fábrica homologados."""
        cabo = self.catalog.get_by_specification(default_cable_spec)
        inst = installation or IndustrialInstallation(
            is_structure_validated_by_engineer=True,
            responsible_engineer_art="ART-2026-PADRAO",
        )
        project = Project(
            title=title,
            client=client,
            location=location,
            responsible_engineer=responsible_engineer,
            cable=cabo,
            installation=inst,
        )
        return project

    def calculate_project(self, project: Project) -> Project:
        """Executa o cálculo estrutural completo e atualiza o estado do projeto."""
        if project.is_read_only:
            raise PermissionError("Projetos em modo somente leitura não podem ser recalculados.")

        lic = self.get_license()
        lic.assert_can_calculate(len(project.spans))

        if project.cable is None:
            raise ValueError("Não é possível calcular o projeto sem selecionar um cabo de aço.")

        if not project.spans:
            raise ValueError("O projeto deve possuir ao menos 1 vão configurado.")

        multi_result = self.engine.calculate_multi_span(
            spans=project.spans,
            cable=project.cable,
            user_config=project.user_config,
            min_safety_factor=project.min_safety_factor,
            clearance_input=project.clearance_input,
        )

        project.set_calculation_result(multi_result)
        return project

    def update_project_spans(self, project: Project, spans: List[SpanGeometry]) -> None:
        """Atualiza a geometria depois de validar o limite do tier ativo."""
        if project.is_read_only:
            raise PermissionError("Projetos em modo somente leitura não podem ser alterados.")
        self.get_license().assert_can_calculate(len(spans))
        project.update_spans(spans)

    def save_project(self, project: Project, filepath: str) -> None:
        """Salva o projeto em disco no formato .lvd com validação de modo somente leitura."""
        if project.is_read_only:
            raise PermissionError("Projetos em modo somente leitura não podem ser salvos.")
        self.get_license().assert_can_calculate(len(project.spans))

        self.serializer.save_to_file(project, filepath)

    def load_project(self, filepath: str, license_data: Optional[LicenseData] = None) -> Project:
        """Carrega o projeto a partir do disco no formato .lvd e aplica regras de licença."""
        project = self.serializer.load_from_file(filepath)
        lic = license_data if license_data is not None else (
            self.license_manager.get_license() if self.license_manager is not None else None
        )
        if lic is not None and not lic.has_full_functional_access and len(project.spans) > 1:
            project.is_read_only = True
        return project

    def clone_project(self, project: Project, new_title: Optional[str] = None) -> Project:
        """Clona um projeto existente garantindo bloqueio se em modo somente leitura."""
        if project.is_read_only:
            raise PermissionError("Projetos em modo somente leitura não podem ser duplicados ou clonados.")
        self.get_license().assert_can_calculate(len(project.spans))
        return self.serializer.clone(project, new_title)

    def export_pdf(self, project: Project, filepath: str) -> str:
        """Exporta o relatório técnico de memória de cálculo em PDF validando licença."""
        lic = self.get_license()
        lic.assert_can_export_pdf()
        from src.reports.pdf_generator import CalculationReportGenerator
        generator = CalculationReportGenerator()
        return generator.generate_pdf(project, filepath, license_data=lic)

    def generate_bom(self, project: Project) -> Any:
        """Gera a Lista de Materiais (BOM) do projeto validando licença."""
        lic = self.get_license()
        lic.assert_can_access_bom()
        return project.generate_bom(license_data=lic)

    def export_bom_excel(self, project: Project, filepath: str) -> str:
        """Exporta a Lista de Materiais em planilha Excel validando licença."""
        lic = self.get_license()
        lic.assert_can_access_bom()
        lic.assert_can_export_bom()
        from src.catalogs.material_rules import BOMGenerator
        bom = self.generate_bom(project)
        return BOMGenerator.export_to_excel(bom, filepath, license_data=lic)

    def get_detailed_memory(self, project: Project) -> Any:
        """Retorna os dados detalhados da memória de cálculo validando licença."""
        lic = self.get_license()
        lic.assert_can_access_memory()
        return project.get_detailed_memory(license_data=lic)

    def print_report(self, project: Project, submit_to_printer: Callable[[str], Any]) -> Any:
        """Gera o relatório temporário e o entrega ao backend de impressão selecionado."""
        lic = self.get_license()
        lic.assert_can_print()
        project.assert_can_print(license_data=lic)

        from src.reports.pdf_generator import CalculationReportGenerator

        with tempfile.TemporaryDirectory(prefix="linelife-print-") as temp_dir:
            pdf_path = os.path.join(temp_dir, "relatorio.pdf")
            CalculationReportGenerator().generate_pdf(project, pdf_path, license_data=lic)
            return submit_to_printer(pdf_path)
