"""Modelo de Projeto completo com rastreabilidade, ciclo de vida e invalidação."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from src.domain.installation_types import (
    IndustrialInstallation,
    InstallationBase,
    InstallationCategory,
    MunckInstallation,
    RoofInstallation,
    SlabInstallation,
)
from src.domain.models import (
    CableProperties,
    FallClearanceInput,
    FallClearanceResult,
    LoadRuleType,
    MultiSpanResult,
    SingleSpanResult,
    SpanGeometry,
    UserLoadConfig,
)


class ProjectStatus(str, Enum):
    """Status do ciclo de vida do projeto."""
    DRAFT = "DRAFT"                          # Rascunho / em preenchimento
    CALCULATED_VALID = "CALCULATED_VALID"    # Calculado e aprovado com sucesso
    CALCULATED_REJECTED = "CALCULATED_REJECTED" # Calculado, porém reprovado por critérios técnicos
    INVALIDATED = "INVALIDATED"              # Entradas alteradas após cálculo prévio


@dataclass
class Project:
    """Entidade agregada representando o projeto completo de linha de vida."""
    title: str = "Novo Projeto de Linha de Vida"
    client: str = "Cliente Padrão"
    location: str = "Área Operacional"
    responsible_engineer: str = "Engenheiro Responsável"
    project_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    schema_version: str = "1.0.0"

    # Configurações de engenharia
    installation: InstallationBase = field(default_factory=lambda: IndustrialInstallation())
    user_config: UserLoadConfig = field(default_factory=UserLoadConfig)
    spans: List[SpanGeometry] = field(
        default_factory=lambda: [SpanGeometry(span_index=1, span_mm=6600.0, initial_sag_percent=3.0)]
    )
    cable: Optional[CableProperties] = None
    clearance_input: FallClearanceInput = field(default_factory=FallClearanceInput)
    min_safety_factor: float = 2.0

    # Estado e resultados
    status: ProjectStatus = ProjectStatus.DRAFT
    calculation_result: Optional[MultiSpanResult] = None
    is_dirty: bool = False
    is_read_only: bool = False

    def touch(self) -> None:
        """Marca o projeto como modificado."""
        if self.is_read_only:
            raise PermissionError("Projetos em modo somente leitura não podem ser alterados.")
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.is_dirty = True

    def invalidate_calculation(self) -> None:
        """Invalida o cálculo atual quando qualquer entrada relevante for alterada.
        
        Garante que um projeto aprovado nunca seja modificado silenciosamente.
        """
        if self.is_read_only:
            raise PermissionError("Projetos em modo somente leitura não podem ser alterados.")
        if self.status != ProjectStatus.DRAFT:
            self.status = ProjectStatus.INVALIDATED
        self.calculation_result = None
        self.touch()

    def update_spans(self, spans: List[SpanGeometry]) -> None:
        """Atualiza os vãos da linha e invalida cálculos anteriores."""
        if self.is_read_only:
            raise PermissionError("Projetos em modo somente leitura não podem ser alterados.")
        self.spans = spans
        self.invalidate_calculation()

    def update_cable(self, cable: CableProperties) -> None:
        """Atualiza o cabo selecionado e invalida cálculos anteriores."""
        if self.is_read_only:
            raise PermissionError("Projetos em modo somente leitura não podem ser alterados.")
        self.cable = cable
        self.invalidate_calculation()

    def update_user_config(self, user_config: UserLoadConfig) -> None:
        """Atualiza a configuração de usuários e invalida cálculos anteriores."""
        if self.is_read_only:
            raise PermissionError("Projetos em modo somente leitura não podem ser alterados.")
        self.user_config = user_config
        self.invalidate_calculation()

    def update_clearance_input(self, clearance_input: FallClearanceInput) -> None:
        """Atualiza a verificação de ZLQ e invalida cálculos anteriores."""
        if self.is_read_only:
            raise PermissionError("Projetos em modo somente leitura não podem ser alterados.")
        self.clearance_input = clearance_input
        self.invalidate_calculation()

    def update_installation(self, installation: InstallationBase) -> None:
        """Atualiza os dados da instalação física e invalida cálculos anteriores."""
        if self.is_read_only:
            raise PermissionError("Projetos em modo somente leitura não podem ser alterados.")
        self.installation = installation
        self.invalidate_calculation()

    def set_calculation_result(self, result: MultiSpanResult) -> None:
        """Registra o resultado do cálculo e atualiza o status de homologação."""
        if self.is_read_only:
            raise PermissionError("Projetos em modo somente leitura não podem ser recalculados.")
        self.calculation_result = result
        if result.is_approved and self.installation.can_approve_structurally():
            self.status = ProjectStatus.CALCULATED_VALID
        else:
            self.status = ProjectStatus.CALCULATED_REJECTED
        self.touch()

    @property
    def can_generate_bom(self) -> bool:
        """A lista de materiais somente pode ser gerada após uma memória de cálculo válida e aprovada e sem pendências estruturais."""
        return (
            self.status == ProjectStatus.CALCULATED_VALID
            and self.calculation_result is not None
            and self.calculation_result.is_approved
            and self.installation.can_approve_structurally()
        )

    def generate_bom(self, license_data: Optional[Any] = None):
        """Gera a lista de materiais estruturada através do motor de regras BOMGenerator."""
        if self.is_read_only:
            raise PermissionError("Projetos em modo somente leitura não podem gerar Lista de Materiais.")
        if license_data is not None:
            license_data.assert_can_access_bom()
        from src.catalogs.material_rules import BOMGenerator
        return BOMGenerator.generate(self, license_data=license_data)

    def get_detailed_memory(self, license_data: Optional[Any] = None) -> Dict[str, Any]:
        """Retorna os dados detalhados da memória de cálculo auditada."""
        if license_data is not None:
            license_data.assert_can_access_memory()
        if not self.calculation_result:
            raise ValueError("O projeto não possui cálculo realizado para emissão da memória detalhada.")
        crit = self.calculation_result.critical_span_result
        return {
            "critical_span_index": self.calculation_result.critical_span_index,
            "end_anchor_load_kgf": self.calculation_result.end_anchor_load_kgf,
            "intermediate_post_vertical_load_kgf": self.calculation_result.intermediate_post_vertical_load_kgf,
            "is_approved": self.calculation_result.is_approved,
            "iterations": crit.iterations,
            "residual_error_kgf": crit.residual_error_kgf,
            "safety_factor": crit.safety_factor,
            "dynamic_sag_mm": crit.dynamic_sag_mm,
            "span_results": [
                {
                    "span_index": i + 1,
                    "span_mm": s.span_mm,
                    "tension_kgf": r.tension_kgf,
                    "safety_factor": r.safety_factor,
                    "dynamic_sag_mm": r.dynamic_sag_mm,
                    "elongation_mm": r.elongation_mm,
                    "is_approved": r.is_approved,
                }
                for i, (s, r) in enumerate(zip(self.spans, self.calculation_result.span_results))
            ],
        }

    def assert_can_print(self, license_data: Optional[Any] = None) -> None:
        """Valida se a licença e o estado do projeto autorizam impressão direta."""
        if self.is_read_only:
            raise PermissionError("Projetos em modo somente leitura não podem ser impressos.")
        if license_data is not None:
            license_data.assert_can_print()

    def to_dict(self) -> Dict[str, Any]:
        """Serializa o projeto completo para um dicionário compatível com JSON."""
        inst_dict = {
            "category": self.installation.category.value,
            "structure_description": self.installation.structure_description,
            "technical_notes": self.installation.technical_notes,
            "is_structure_validated_by_engineer": self.installation.is_structure_validated_by_engineer,
            "responsible_engineer_art": self.installation.responsible_engineer_art,
        }
        if isinstance(self.installation, SlabInstallation):
            inst_dict.update({
                "slab_type": self.installation.slab_type,
                "thickness_mm": self.installation.thickness_mm,
                "concrete_fck_mpa": self.installation.concrete_fck_mpa,
                "anchor_type": self.installation.anchor_type,
                "anchor_edge_distance_mm": self.installation.anchor_edge_distance_mm,
            })
        elif isinstance(self.installation, RoofInstallation):
            inst_dict.update({
                "roof_type": self.installation.roof_type,
                "tile_type": self.installation.tile_type,
                "support_element": self.installation.support_element,
                "support_spacing_mm": self.installation.support_spacing_mm,
                "roof_slope_percent": self.installation.roof_slope_percent,
                "environment_corrosivity": self.installation.environment_corrosivity,
            })
        elif isinstance(self.installation, IndustrialInstallation):
            inst_dict.update({
                "structure_type": self.installation.structure_type,
                "steel_grade": self.installation.steel_grade,
                "post_attachment_method": self.installation.post_attachment_method,
                "working_height_m": self.installation.working_height_m,
                "is_indoor": self.installation.is_indoor,
                "corrosive_agents": self.installation.corrosive_agents,
            })
        elif isinstance(self.installation, MunckInstallation):
            inst_dict.update({
                "vehicle_model": self.installation.vehicle_model,
                "chassis_region": self.installation.chassis_region,
                "attachment_support": self.installation.attachment_support,
                "max_boom_height_m": self.installation.max_boom_height_m,
                "allows_vehicle_motion": self.installation.allows_vehicle_motion,
            })

        cable_dict = None
        if self.cable:
            cable_dict = {
                "specification": self.cable.specification,
                "diameter_mm": self.cable.diameter_mm,
                "metallic_area_factor": self.cable.metallic_area_factor,
                "elastic_modulus_kgf_mm2": self.cable.elastic_modulus_kgf_mm2,
                "min_breaking_load_kgf": self.cable.min_breaking_load_kgf,
                "grade_n_mm2": self.cable.grade_n_mm2,
                "core_type": self.cable.core_type,
            }

        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "title": self.title,
            "client": self.client,
            "location": self.location,
            "responsible_engineer": self.responsible_engineer,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status.value,
            "installation": inst_dict,
            "user_config": {
                "total_users": self.user_config.total_users,
                "simultaneous_users": self.user_config.simultaneous_users,
                "rule_type": self.user_config.rule_type.value,
                "dynamic_load_first_user_kgf": self.user_config.dynamic_load_first_user_kgf,
                "static_load_per_additional_kgf": self.user_config.static_load_per_additional_kgf,
                "custom_total_load_kgf": self.user_config.custom_total_load_kgf,
            },
            "spans": [
                {
                    "span_index": s.span_index,
                    "span_mm": s.span_mm,
                    "initial_sag_percent": s.initial_sag_percent,
                }
                for s in self.spans
            ],
            "cable": cable_dict,
            "clearance_input": {
                "lanyard_length_m": self.clearance_input.lanyard_length_m,
                "absorber_extension_m": self.clearance_input.absorber_extension_m,
                "worker_height_offset_m": self.clearance_input.worker_height_offset_m,
                "safety_margin_m": self.clearance_input.safety_margin_m,
                "available_clearance_m": self.clearance_input.available_clearance_m,
            },
            "min_safety_factor": self.min_safety_factor,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        """Reconstrói um objeto Project a partir de um dicionário."""
        inst_data = data.get("installation", {})
        cat = inst_data.get("category", InstallationCategory.INDUSTRIAL.value)
        
        base_kwargs = {
            "structure_description": inst_data.get("structure_description", ""),
            "technical_notes": inst_data.get("technical_notes", ""),
            "is_structure_validated_by_engineer": inst_data.get("is_structure_validated_by_engineer", False),
            "responsible_engineer_art": inst_data.get("responsible_engineer_art"),
        }

        if cat == InstallationCategory.SLAB.value:
            installation = SlabInstallation(
                slab_type=inst_data.get("slab_type", "Concreto Armado Maciço"),
                thickness_mm=inst_data.get("thickness_mm"),
                concrete_fck_mpa=inst_data.get("concrete_fck_mpa"),
                anchor_type=inst_data.get("anchor_type", "Chumbador Químico"),
                anchor_edge_distance_mm=inst_data.get("anchor_edge_distance_mm"),
                **base_kwargs,
            )
        elif cat == InstallationCategory.ROOF.value:
            installation = RoofInstallation(
                roof_type=inst_data.get("roof_type", "Duas Águas"),
                tile_type=inst_data.get("tile_type", "Metálica Trapezoidal"),
                support_element=inst_data.get("support_element", "Terça Metálica"),
                support_spacing_mm=inst_data.get("support_spacing_mm"),
                roof_slope_percent=inst_data.get("roof_slope_percent", 10.0),
                environment_corrosivity=inst_data.get("environment_corrosivity", "Média"),
                **base_kwargs,
            )
        elif cat == InstallationCategory.MUNCK.value:
            installation = MunckInstallation(
                vehicle_model=inst_data.get("vehicle_model", "Caminhão Munck Padrão"),
                chassis_region=inst_data.get("chassis_region", "Sobre a Carroceria / Patolas"),
                attachment_support=inst_data.get("attachment_support", "Suporte Tubular"),
                max_boom_height_m=inst_data.get("max_boom_height_m", 12.0),
                allows_vehicle_motion=inst_data.get("allows_vehicle_motion", False),
                **base_kwargs,
            )
        else:
            installation = IndustrialInstallation(
                structure_type=inst_data.get("structure_type", "Perfil I / H"),
                steel_grade=inst_data.get("steel_grade", "ASTM A36"),
                post_attachment_method=inst_data.get("post_attachment_method", "Abraçadeira"),
                working_height_m=inst_data.get("working_height_m", 6.0),
                is_indoor=inst_data.get("is_indoor", True),
                corrosive_agents=inst_data.get("corrosive_agents", "Nenhum"),
                **base_kwargs,
            )

        u_data = data.get("user_config", {})
        user_config = UserLoadConfig(
            total_users=u_data.get("total_users", 1),
            simultaneous_users=u_data.get("simultaneous_users", 1),
            rule_type=LoadRuleType(u_data.get("rule_type", LoadRuleType.NBR_16325_2.value)),
            dynamic_load_first_user_kgf=u_data.get("dynamic_load_first_user_kgf", 600.0),
            static_load_per_additional_kgf=u_data.get("static_load_per_additional_kgf", 100.0),
            custom_total_load_kgf=u_data.get("custom_total_load_kgf"),
        )

        spans = [
            SpanGeometry(
                span_index=s["span_index"],
                span_mm=float(s["span_mm"]),
                initial_sag_percent=float(s.get("initial_sag_percent", 3.0)),
            )
            for s in data.get("spans", [])
        ]

        c_data = data.get("cable")
        cable = None
        if c_data:
            cable = CableProperties(
                specification=c_data["specification"],
                diameter_mm=float(c_data["diameter_mm"]),
                metallic_area_factor=float(c_data["metallic_area_factor"]),
                elastic_modulus_kgf_mm2=float(c_data["elastic_modulus_kgf_mm2"]),
                min_breaking_load_kgf=float(c_data["min_breaking_load_kgf"]),
                grade_n_mm2=float(c_data["grade_n_mm2"]) if c_data.get("grade_n_mm2") else None,
                core_type=c_data.get("core_type", "6 x 19 com alma de fibra"),
            )

        cl_data = data.get("clearance_input", {})
        clearance_input = FallClearanceInput(
            lanyard_length_m=float(cl_data.get("lanyard_length_m", 1.5)),
            absorber_extension_m=float(cl_data.get("absorber_extension_m", 1.2)),
            worker_height_offset_m=float(cl_data.get("worker_height_offset_m", 1.5)),
            safety_margin_m=float(cl_data.get("safety_margin_m", 1.0)),
            available_clearance_m=float(cl_data["available_clearance_m"]) if cl_data.get("available_clearance_m") is not None else None,
        )

        project = cls(
            title=data.get("title", "Novo Projeto"),
            client=data.get("client", "Cliente"),
            location=data.get("location", "Local"),
            responsible_engineer=data.get("responsible_engineer", "Engenheiro"),
            project_id=data.get("project_id", str(uuid.uuid4())[:8]),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
            schema_version=data.get("schema_version", "1.0.0"),
            installation=installation,
            user_config=user_config,
            spans=spans,
            cable=cable,
            clearance_input=clearance_input,
            min_safety_factor=float(data.get("min_safety_factor", 2.0)),
            status=ProjectStatus(data.get("status", ProjectStatus.DRAFT.value)),
        )
        return project
