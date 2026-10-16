"""Modelos de dados e entidades de domínio para cálculo de Linhas de Vida."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class LoadRuleType(str, Enum):
    """Regra de combinação de carregamento para múltiplos usuários."""
    NBR_16325_2 = "NBR_16325_2"    # 1º dinâmico (6 kN/600 kgf) + estático (1 kN/100 kgf) por usuário adicional
    CUSTOM = "CUSTOM"                # Carga customizada ou multiplicativa direta pelo número de usuários


@dataclass(frozen=True)
class CableProperties:
    """Propriedades mecânicas e geométricas do cabo de aço conforme NBR ISO 2408."""
    specification: str
    diameter_mm: float
    metallic_area_factor: float
    elastic_modulus_kgf_mm2: float
    min_breaking_load_kgf: float
    grade_n_mm2: Optional[float] = None
    core_type: str = "6 x 19 com alma de fibra"

    @property
    def metallic_area_mm2(self) -> float:
        """Área metálica resistente Am = F * d² [mm²]."""
        return self.metallic_area_factor * (self.diameter_mm ** 2)

    @property
    def elastic_modulus_mpa(self) -> float:
        """Módulo de elasticidade em MPa (N/mm²)."""
        return self.elastic_modulus_kgf_mm2 * 9.80665

    @property
    def min_breaking_load_kn(self) -> float:
        """Força mínima de ruptura em kN (SI)."""
        return (self.min_breaking_load_kgf * 9.80665) / 1000.0


@dataclass(frozen=True)
class UserLoadConfig:
    """Configuração de usuários e definição de carregamento de impacto."""
    total_users: int = 1
    simultaneous_users: int = 1
    rule_type: LoadRuleType = LoadRuleType.NBR_16325_2
    dynamic_load_first_user_kgf: float = 600.0   # Impacto máx. absorvedor (6 kN ~ 600 kgf)
    static_load_per_additional_kgf: float = 100.0 # Peso estático por usuário extra (1 kN ~ 100 kgf)
    custom_total_load_kgf: Optional[float] = None # Utilizado apenas se rule_type == CUSTOM

    @property
    def calculated_design_load_kgf(self) -> float:
        """Calcula a carga de projeto P resultante em kgf."""
        if self.rule_type == LoadRuleType.CUSTOM and self.custom_total_load_kgf is not None:
            return self.custom_total_load_kgf

        if self.simultaneous_users <= 1:
            return self.dynamic_load_first_user_kgf

        # Regra NBR 16325-2: 1º dinâmico + 100 kgf por usuário adicional
        additional_users = self.simultaneous_users - 1
        return self.dynamic_load_first_user_kgf + (additional_users * self.static_load_per_additional_kgf)

    @property
    def is_normative_compliant(self) -> bool:
        """Indica se a regra segue os critérios normativos da NBR 16325-2."""
        return self.rule_type == LoadRuleType.NBR_16325_2

    @property
    def warning_text(self) -> Optional[str]:
        """Aviso caso a regra divirja dos critérios recomendados da NBR 16325-2."""
        if not self.is_normative_compliant:
            return (
                "ATENÇÃO: A regra de carregamento configurada diverge do método padrão da ABNT NBR 16325-2. "
                "A carga foi definida manualmente pelo usuário sob sua responsabilidade técnica."
            )
        return None


@dataclass(frozen=True)
class FallClearanceInput:
    """Parâmetros para cálculo da Zona Livre de Queda (ZLQ) conforme NR-35."""
    lanyard_length_m: float = 1.5           # Comprimento do talabarte (m)
    absorber_extension_m: float = 1.2        # Desaceleração máxima do absorvedor de energia (m)
    worker_height_offset_m: float = 1.5      # Deslocamento do cinto / altura média do anel dorsal (m)
    safety_margin_m: float = 1.0             # Margem de segurança obrigatória NR-35 (m)
    available_clearance_m: Optional[float] = None # Altura disponível do plano de trabalho ao obstáculo/piso


@dataclass(frozen=True)
class FallClearanceResult:
    """Resultado da verificação de Zona Livre de Queda (ZLQ)."""
    required_clearance_m: float              # ZLQ necessária (m)
    dynamic_sag_m: float                     # Flecha dinâmica do cabo f2 convertida para metros
    available_clearance_m: Optional[float]   # Altura livre existente (m)
    residual_margin_m: Optional[float]       # Margem livre restante (H_disp - ZLQ_req)
    collision_risk: bool                     # True se ZLQ_req > H_disp
    clearance_approved: bool                 # True se não há colisão (ou se H_disp não foi informado)
    warning_text: Optional[str] = None


@dataclass(frozen=True)
class SingleSpanInput:
    """Parâmetros de entrada para dimensionamento de vão único."""
    span_mm: float
    initial_sag_percent: float
    impact_load_kgf: float
    min_safety_factor: float
    cable: CableProperties
    clearance_input: Optional[FallClearanceInput] = None


@dataclass(frozen=True)
class SingleSpanResult:
    """Resultados detalhados do cálculo com auditoria de convergência."""
    initial_sag_mm: float                 # f1 [mm]
    initial_length_mm: float              # L [mm]
    elongation_mm: float                  # Delta L [mm]
    dynamic_sag_mm: float                 # f2 [mm]
    tension_kgf: float                    # Tração convergente T [kgf]
    safety_factor: float                  # FS = Fu / T
    
    converged: bool                       # Se convergiu dentro da tolerância
    iterations: int                       # Número de iterações executadas
    residual_error_kgf: float             # |T_teor - T_arb| final
    tolerance_kgf: float                  # Tolerância adotada no cálculo
    initial_guess_kgf: float              # Ponto de partida do método
    
    is_approved: bool                     # Aprovado se converge e FS >= FS_min
    status_text: str                      # "APROVADO", "REPROVADO" ou "NÃO CONVERGE"
    rejection_reason: Optional[str] = None
    clearance_result: Optional[FallClearanceResult] = None


@dataclass(frozen=True)
class SpanGeometry:
    """Geometria individual de um vão."""
    span_index: int                       # 1-indexed (1, 2, ..., N-1)
    span_mm: float                        # Vão livre entre os dois postes adjacentes
    initial_sag_percent: float = 3.0      # Taxa de flecha inicial


@dataclass(frozen=True)
class MultiSpanInput:
    """Configuração completa de uma linha com múltiplos postes e vãos."""
    spans: List[SpanGeometry]
    cable: CableProperties
    user_config: UserLoadConfig = field(default_factory=UserLoadConfig)
    min_safety_factor: float = 2.0
    clearance_input: Optional[FallClearanceInput] = None

    @property
    def number_of_posts(self) -> int:
        """Quantidade total de postes (N = número de vãos + 1)."""
        return len(self.spans) + 1

    @property
    def total_length_mm(self) -> float:
        """Comprimento nominal total da linha de ancoragem a ancoragem."""
        return sum(s.span_mm for s in self.spans)


@dataclass(frozen=True)
class MultiSpanResult:
    """Resultados do dimensionamento de uma linha de vida contínua com múltiplos vãos."""
    number_of_posts: int
    number_of_spans: int
    critical_span_index: int              # Vão que apresenta a maior flecha / solicitação
    critical_span_result: SingleSpanResult
    span_results: List[SingleSpanResult]
    
    # Esforços nas estruturas
    end_anchor_load_kgf: float            # Força máxima nas ancoragens de extremidade (kgf)
    intermediate_post_vertical_load_kgf: float # Carga vertical nos postes intermediários (kgf)
    intermediate_post_horizontal_load_kgf: float # Carga horizontal transversal/longitudinal máxima (kgf)
    
    is_approved: bool
    status_text: str
    rejection_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
