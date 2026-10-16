"""Módulo de tipos de instalação física e interfaces estruturais."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class InstallationCategory(str, Enum):
    """Categorias homologadas de instalação de linha de vida."""
    SLAB = "SLAB"                  # Laje de concreto
    ROOF = "ROOF"                  # Telhado (telhas e terças estruturais)
    INDUSTRIAL = "INDUSTRIAL"      # Área industrial (perfis metálicos/tubulações)
    MUNCK = "MUNCK"                # Veículo / Caminhão Munck


@dataclass
class InstallationBase:
    """Classe base para tipos de instalação física."""
    category: InstallationCategory
    structure_description: str = ""
    technical_notes: str = ""
    is_structure_validated_by_engineer: bool = False
    responsible_engineer_art: Optional[str] = None

    def get_structural_gaps(self) -> List[str]:
        """Retorna a lista de dados essenciais faltantes ou pendências estruturais."""
        gaps = []
        if not self.is_structure_validated_by_engineer:
            gaps.append(
                "A capacidade resistente da estrutura de suporte não foi formalmente validada por profissional habilitado com ART."
            )
        return gaps

    def can_approve_structurally(self) -> bool:
        """Indica se a instalação possui todos os dados estruturais validados para aprovação."""
        return len(self.get_structural_gaps()) == 0


@dataclass
class SlabInstallation(InstallationBase):
    """Instalação em Laje de concreto armado."""
    slab_type: str = "Concreto Armado Maciço"   # Maciça, nervurada, protendida
    thickness_mm: Optional[float] = None        # Espessura da laje (mm)
    concrete_fck_mpa: Optional[float] = None    # Resistência característica fck (MPa)
    anchor_type: str = "Chumbador Químico"      # Químico, expansão, transpassante
    anchor_edge_distance_mm: Optional[float] = None # Distância da borda da laje (mm)

    def __init__(
        self,
        slab_type: str = "Concreto Armado Maciço",
        thickness_mm: Optional[float] = None,
        concrete_fck_mpa: Optional[float] = None,
        anchor_type: str = "Chumbador Químico",
        anchor_edge_distance_mm: Optional[float] = None,
        structure_description: str = "",
        technical_notes: str = "",
        is_structure_validated_by_engineer: bool = False,
        responsible_engineer_art: Optional[str] = None,
    ):
        super().__init__(
            category=InstallationCategory.SLAB,
            structure_description=structure_description,
            technical_notes=technical_notes,
            is_structure_validated_by_engineer=is_structure_validated_by_engineer,
            responsible_engineer_art=responsible_engineer_art,
        )
        self.slab_type = slab_type
        self.thickness_mm = thickness_mm
        self.concrete_fck_mpa = concrete_fck_mpa
        self.anchor_type = anchor_type
        self.anchor_edge_distance_mm = anchor_edge_distance_mm

    def get_structural_gaps(self) -> List[str]:
        gaps = super().get_structural_gaps()
        if self.thickness_mm is None or self.thickness_mm <= 0:
            gaps.append("Espessura da laje não informada.")
        if self.concrete_fck_mpa is None or self.concrete_fck_mpa < 15:
            gaps.append("Resistência do concreto (fck) não informada ou inferior a 15 MPa.")
        if self.anchor_edge_distance_mm is None or self.anchor_edge_distance_mm <= 0:
            gaps.append("Distância do chumbador até a borda da laje não informada.")
        return gaps


@dataclass
class RoofInstallation(InstallationBase):
    """Instalação em Telhado."""
    roof_type: str = "Duas Águas"               # Shed, duas águas, arco
    tile_type: str = "Metálica Trapezoidal"     # Trapezoidal, fibrocimento, zipada
    support_element: str = "Terça Metálica"     # Terça metálica, tesoura, viga de concreto
    support_spacing_mm: Optional[float] = None  # Espaçamento entre terças (mm)
    roof_slope_percent: float = 10.0            # Inclinação do telhado (%)
    environment_corrosivity: str = "Média"      # Baixa, Média, Severa

    def __init__(
        self,
        roof_type: str = "Duas Águas",
        tile_type: str = "Metálica Trapezoidal",
        support_element: str = "Terça Metálica",
        support_spacing_mm: Optional[float] = None,
        roof_slope_percent: float = 10.0,
        environment_corrosivity: str = "Média",
        structure_description: str = "",
        technical_notes: str = "",
        is_structure_validated_by_engineer: bool = False,
        responsible_engineer_art: Optional[str] = None,
    ):
        super().__init__(
            category=InstallationCategory.ROOF,
            structure_description=structure_description,
            technical_notes=technical_notes,
            is_structure_validated_by_engineer=is_structure_validated_by_engineer,
            responsible_engineer_art=responsible_engineer_art,
        )
        self.roof_type = roof_type
        self.tile_type = tile_type
        self.support_element = support_element
        self.support_spacing_mm = support_spacing_mm
        self.roof_slope_percent = roof_slope_percent
        self.environment_corrosivity = environment_corrosivity

    def get_structural_gaps(self) -> List[str]:
        gaps = super().get_structural_gaps()
        if "fibrocimento" in self.tile_type.lower():
            gaps.append(
                "ADVERTÊNCIA: Telhas de fibrocimento são frágeis e NÃO podem ser utilizadas como suporte estrutural de ancoragem."
            )
        if self.support_spacing_mm is None or self.support_spacing_mm <= 0:
            gaps.append("Espaçamento entre elementos estruturais (terças) não informado.")
        return gaps


@dataclass
class IndustrialInstallation(InstallationBase):
    """Instalação em Área Industrial / Estrutura Metálica."""
    structure_type: str = "Perfil I / H Laminado" # Perfil metálico, tubular, treliça
    steel_grade: str = "ASTM A36"                  # ASTM A36, ASTM A572 Gr50
    post_attachment_method: str = "Abraçadeira Grampo / Bocal Parafusado" # Solda, parafuso, grampo
    working_height_m: float = 6.0
    is_indoor: bool = True
    corrosive_agents: str = "Nenhum"

    def __init__(
        self,
        structure_type: str = "Perfil I / H Laminado",
        steel_grade: str = "ASTM A36",
        post_attachment_method: str = "Abraçadeira Grampo / Bocal Parafusado",
        working_height_m: float = 6.0,
        is_indoor: bool = True,
        corrosive_agents: str = "Nenhum",
        structure_description: str = "",
        technical_notes: str = "",
        is_structure_validated_by_engineer: bool = False,
        responsible_engineer_art: Optional[str] = None,
    ):
        super().__init__(
            category=InstallationCategory.INDUSTRIAL,
            structure_description=structure_description,
            technical_notes=technical_notes,
            is_structure_validated_by_engineer=is_structure_validated_by_engineer,
            responsible_engineer_art=responsible_engineer_art,
        )
        self.structure_type = structure_type
        self.steel_grade = steel_grade
        self.post_attachment_method = post_attachment_method
        self.working_height_m = working_height_m
        self.is_indoor = is_indoor
        self.corrosive_agents = corrosive_agents

    def get_structural_gaps(self) -> List[str]:
        gaps = super().get_structural_gaps()
        if self.working_height_m <= 0:
            gaps.append("Altura de trabalho deve ser superior a zero.")
        return gaps


@dataclass
class MunckInstallation(InstallationBase):
    """Instalação em Veículo / Caminhão Munck."""
    vehicle_model: str = "Caminhão Munck Padrão"
    chassis_region: str = "Sobre a Carroceria / Patolas"
    attachment_support: str = "Suporte Tubular Fixado no Chassi"
    max_boom_height_m: float = 12.0
    allows_vehicle_motion: bool = False

    def __init__(
        self,
        vehicle_model: str = "Caminhão Munck Padrão",
        chassis_region: str = "Sobre a Carroceria / Patolas",
        attachment_support: str = "Suporte Tubular Fixado no Chassi",
        max_boom_height_m: float = 12.0,
        allows_vehicle_motion: bool = False,
        structure_description: str = "",
        technical_notes: str = "",
        is_structure_validated_by_engineer: bool = False,
        responsible_engineer_art: Optional[str] = None,
    ):
        super().__init__(
            category=InstallationCategory.MUNCK,
            structure_description=structure_description,
            technical_notes=technical_notes,
            is_structure_validated_by_engineer=is_structure_validated_by_engineer,
            responsible_engineer_art=responsible_engineer_art,
        )
        self.vehicle_model = vehicle_model
        self.chassis_region = chassis_region
        self.attachment_support = attachment_support
        self.max_boom_height_m = max_boom_height_m
        self.allows_vehicle_motion = allows_vehicle_motion

    def get_structural_gaps(self) -> List[str]:
        gaps = super().get_structural_gaps()
        if not self.is_structure_validated_by_engineer or not self.responsible_engineer_art:
            gaps.append(
                "RESTRIÇÃO DE SEGURANÇA MUNCK: É terminantemente proibido assumir que a carroceria ou o chassi "
                "suportam as cargas de impacto sem projeto de reforço estrutural específico validado por Engenheiro Mecânico com ART."
            )
        if self.allows_vehicle_motion:
            gaps.append(
                "ADVERTÊNCIA: Linha de vida não pode ser utilizada com o veículo em movimento sob nenhuma hipótese."
            )
        return gaps
