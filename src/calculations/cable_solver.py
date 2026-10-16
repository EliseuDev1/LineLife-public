"""Motor de cálculo analítico e solucionador numérico para linha de vida flexível.

Reproduz rigorosamente as equações de equilíbrio estático sob impacto e flecha
da planilha de referência, integrando verificação de Zona Livre de Queda (NR-35)
e solucionador numérico robusto com convergência garantida.
"""

import math
from typing import Tuple
from src.domain.models import SingleSpanInput, SingleSpanResult, CableProperties
from src.calculations.fall_clearance import FallClearanceCalculator


class CableSolver:
    """Solucionador numérico para vão único de linha de vida flexível."""

    def __init__(self, tolerance_kgf: float = 1e-6, max_iterations: int = 100):
        self.tolerance_kgf = tolerance_kgf
        self.max_iterations = max_iterations

    @staticmethod
    def calculate_initial_geometry(span_mm: float, sag_percent: float) -> Tuple[float, float]:
        """Calcula a flecha inicial f1 e o comprimento geométrico inicial L do cabo.
        
        Fórmulas da planilha:
        f1 = D * (%f1 / 100)
        L = D * [1 + 2/3 * (2*f1/D)² - 2/5 * (2*f1/D)⁴]
        """
        f1 = span_mm * (sag_percent / 100.0)
        ratio = (2.0 * f1) / span_mm
        L = span_mm * (1.0 + (2.0 / 3.0) * (ratio ** 2) - (2.0 / 5.0) * (ratio ** 4))
        return f1, L

    def residual(
        self,
        T_arb: float,
        span_mm: float,
        L_mm: float,
        impact_load_kgf: float,
        cable: CableProperties,
    ) -> Tuple[float, float, float, float]:
        """Calcula o resíduo R(T) = T_teor - T_arb e variáveis intermediárias.
        
        Retorna: (resíduo, Delta_L, f2, T_teor)
        """
        am = cable.metallic_area_mm2
        # Alongamento: Delta L = (L * T) / (E * Am)
        delta_L = (L_mm * T_arb) / (cable.elastic_modulus_kgf_mm2 * am)
        L_dynamic = L_mm + delta_L

        half_L = L_dynamic / 2.0
        half_D = span_mm / 2.0
        radicand = (half_L ** 2) - (half_D ** 2)

        if radicand < 0:
            radicand = 0.0

        f2 = math.sqrt(radicand)
        if f2 <= 1e-9:
            # Evita divisão por zero para flecha virtualmente nula
            T_teor = 1e9
        else:
            # Tração teórica de equilíbrio no ponto central: T = (P * (L + Delta L)) / (4 * f2)
            T_teor = (impact_load_kgf * L_dynamic) / (4.0 * f2)

        diff = T_teor - T_arb
        return diff, delta_L, f2, T_teor

    def solve(self, inp: SingleSpanInput) -> SingleSpanResult:
        """Resolve a tração de equilíbrio pelo método da bisseção com tolerância estrita."""
        f1, L = self.calculate_initial_geometry(inp.span_mm, inp.initial_sag_percent)

        # Intervalo de busca para a tração [T_low, T_high]
        T_low = 1.0  # Mínimo físico positivo
        T_high = max(inp.cable.min_breaking_load_kgf * 20.0, 50000.0)

        diff_low, _, _, _ = self.residual(T_low, inp.span_mm, L, inp.impact_load_kgf, inp.cable)
        diff_high, _, _, _ = self.residual(T_high, inp.span_mm, L, inp.impact_load_kgf, inp.cable)

        if diff_low < 0:
            T_low = 0.001
            diff_low, _, _, _ = self.residual(T_low, inp.span_mm, L, inp.impact_load_kgf, inp.cable)

        expand_count = 0
        while diff_high > 0 and expand_count < 20:
            T_high *= 2.0
            diff_high, _, _, _ = self.residual(T_high, inp.span_mm, L, inp.impact_load_kgf, inp.cable)
            expand_count += 1

        converged = False
        iterations = 0
        T_mid = (T_low + T_high) / 2.0
        final_diff = 0.0
        final_dL = 0.0
        final_f2 = 0.0

        for i in range(1, self.max_iterations + 1):
            iterations = i
            T_mid = (T_low + T_high) / 2.0
            diff_mid, dL_mid, f2_mid, _ = self.residual(
                T_mid, inp.span_mm, L, inp.impact_load_kgf, inp.cable
            )

            final_diff = diff_mid
            final_dL = dL_mid
            final_f2 = f2_mid

            if abs(diff_mid) <= self.tolerance_kgf or (T_high - T_low) / 2.0 <= self.tolerance_kgf:
                converged = True
                break

            if (diff_low > 0 and diff_mid > 0) or (diff_low < 0 and diff_mid < 0):
                T_low = T_mid
                diff_low = diff_mid
            else:
                T_high = T_mid

        safety_factor = inp.cable.min_breaking_load_kgf / T_mid if T_mid > 0 else 0.0
        is_approved = converged and (safety_factor >= inp.min_safety_factor)

        # Cálculo da Zona Livre de Queda (se solicitada ou padrão)
        clearance_res = None
        if inp.clearance_input is not None:
            clearance_res = FallClearanceCalculator.calculate(final_f2, inp.clearance_input)
            if clearance_res.collision_risk:
                is_approved = False

        if not converged:
            status_text = "NÃO CONVERGE"
            rejection = "O método numérico não convergiu dentro da tolerância configurada."
        elif safety_factor < inp.min_safety_factor:
            status_text = "REPROVADO"
            rejection = (
                f"Fator de Segurança ({safety_factor:.3f}) inferior ao limite mínimo "
                f"normativo ({inp.min_safety_factor:.2f})."
            )
        elif clearance_res and clearance_res.collision_risk:
            status_text = "REPROVADO"
            rejection = "Risco de colisão detectado na Zona Livre de Queda (ZLQ)."
        else:
            status_text = "APROVADO"
            rejection = None

        return SingleSpanResult(
            initial_sag_mm=f1,
            initial_length_mm=L,
            elongation_mm=final_dL,
            dynamic_sag_mm=final_f2,
            tension_kgf=T_mid,
            safety_factor=safety_factor,
            converged=converged,
            iterations=iterations,
            residual_error_kgf=abs(final_diff),
            tolerance_kgf=self.tolerance_kgf,
            initial_guess_kgf=1.0,
            is_approved=is_approved,
            status_text=status_text,
            rejection_reason=rejection,
            clearance_result=clearance_res,
        )
