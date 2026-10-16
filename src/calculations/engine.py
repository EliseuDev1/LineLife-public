"""Fachada unificada do motor de cálculo de engenharia para Linhas de Vida."""

from typing import List, Optional
from src.domain.models import (
    CableProperties,
    FallClearanceInput,
    MultiSpanInput,
    MultiSpanResult,
    SingleSpanInput,
    SingleSpanResult,
    SpanGeometry,
    UserLoadConfig,
)
from src.calculations.cable_solver import CableSolver
from src.calculations.multi_span_solver import MultiSpanSolver


class CalculationEngine:
    """Motor unificado de dimensionamento e verificação estrutural."""

    def __init__(self, tolerance_kgf: float = 1e-6, max_iterations: int = 100):
        self.single_solver = CableSolver(tolerance_kgf=tolerance_kgf, max_iterations=max_iterations)
        self.multi_solver = MultiSpanSolver(tolerance_kgf=tolerance_kgf, max_iterations=max_iterations)

    def calculate_single_span(
        self,
        span_mm: float,
        initial_sag_percent: float,
        cable: CableProperties,
        impact_load_kgf: float = 600.0,
        min_safety_factor: float = 2.0,
        clearance_input: Optional[FallClearanceInput] = None,
    ) -> SingleSpanResult:
        """Calcula uma linha de vida com vão único (2 postes)."""
        inp = SingleSpanInput(
            span_mm=span_mm,
            initial_sag_percent=initial_sag_percent,
            impact_load_kgf=impact_load_kgf,
            min_safety_factor=min_safety_factor,
            cable=cable,
            clearance_input=clearance_input,
        )
        return self.single_solver.solve(inp)

    def calculate_multi_span(
        self,
        spans: List[SpanGeometry],
        cable: CableProperties,
        user_config: Optional[UserLoadConfig] = None,
        min_safety_factor: float = 2.0,
        clearance_input: Optional[FallClearanceInput] = None,
    ) -> MultiSpanResult:
        """Calcula uma linha de vida com múltiplos postes e vãos contínuos."""
        if user_config is None:
            user_config = UserLoadConfig()

        inp = MultiSpanInput(
            spans=spans,
            cable=cable,
            user_config=user_config,
            min_safety_factor=min_safety_factor,
            clearance_input=clearance_input,
        )
        return self.multi_solver.solve(inp)
