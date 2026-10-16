"""Motor de cálculo estrutural para Linhas de Vida contínuas com múltiplos vãos e postes.

Modela a física de uma linha flexível contínua sobre N postes (N-1 vãos) conforme
os preceitos da ABNT NBR 16325-2:
- O alongamento elástico axial total mobiliza a extensão completa do cabo entre ancoragens;
- Determina o vão crítico (maior flecha dinâmica sob queda);
- Calcula os esforços solicitantes nas ancoragens de extremidade e nos postes intermediários;
- Reduz-se exatamente ao caso-base quando houver apenas 1 vão (2 postes).
"""

import math
from typing import List, Tuple
from src.domain.models import (
    MultiSpanInput,
    MultiSpanResult,
    SingleSpanInput,
    SingleSpanResult,
    SpanGeometry,
)
from src.calculations.cable_solver import CableSolver
from src.calculations.fall_clearance import FallClearanceCalculator


class MultiSpanSolver:
    """Solucionador de equilíbrio para linhas de múltiplos vãos."""

    def __init__(self, tolerance_kgf: float = 1e-6, max_iterations: int = 100):
        self.tolerance_kgf = tolerance_kgf
        self.max_iterations = max_iterations
        self.single_solver = CableSolver(tolerance_kgf=tolerance_kgf, max_iterations=max_iterations)

    def solve(self, inp: MultiSpanInput) -> MultiSpanResult:
        """Executa o cálculo estrutural completo para múltiplos vãos e postes."""
        if not inp.spans:
            raise ValueError("A linha de vida deve possuir pelo menos 1 vão (2 postes).")

        num_spans = len(inp.spans)
        num_posts = num_spans + 1
        design_load_kgf = inp.user_config.calculated_design_load_kgf

        # 1. Caso especial: vão único (2 postes) - utiliza o solver analítico padrão
        if num_spans == 1:
            single_input = SingleSpanInput(
                span_mm=inp.spans[0].span_mm,
                initial_sag_percent=inp.spans[0].initial_sag_percent,
                impact_load_kgf=design_load_kgf,
                min_safety_factor=inp.min_safety_factor,
                cable=inp.cable,
                clearance_input=inp.clearance_input,
            )
            single_res = self.single_solver.solve(single_input)

            # Esforços estruturais para vão único
            end_anchor_load = single_res.tension_kgf
            warnings = []
            if inp.user_config.warning_text:
                warnings.append(inp.user_config.warning_text)
            if single_res.clearance_result and single_res.clearance_result.warning_text:
                warnings.append(single_res.clearance_result.warning_text)

            is_approved = single_res.is_approved
            rejection_reason = single_res.rejection_reason

            if single_res.clearance_result and single_res.clearance_result.collision_risk:
                is_approved = False
                rejection_reason = (
                    f"{rejection_reason + ' | ' if rejection_reason else ''}"
                    "Reprovado por risco de colisão (ZLQ requerida > altura disponível)."
                )

            return MultiSpanResult(
                number_of_posts=2,
                number_of_spans=1,
                critical_span_index=1,
                critical_span_result=single_res,
                span_results=[single_res],
                end_anchor_load_kgf=end_anchor_load,
                intermediate_post_vertical_load_kgf=0.0,
                intermediate_post_horizontal_load_kgf=0.0,
                is_approved=is_approved,
                status_text="APROVADO" if is_approved else single_res.status_text,
                rejection_reason=rejection_reason,
                warnings=warnings,
            )

        # 2. Múltiplos vãos contínuos (N >= 3 postes)
        # Calcula o comprimento geométrico inicial total somando todos os vãos
        total_initial_L = 0.0
        span_initial_geometries: List[Tuple[float, float]] = []

        for span in inp.spans:
            f1_i, L_i = self.single_solver.calculate_initial_geometry(
                span.span_mm, span.initial_sag_percent
            )
            span_initial_geometries.append((f1_i, L_i))
            total_initial_L += L_i

        # Identifica o vão crítico (vão de maior comprimento livre)
        critical_idx = 0
        max_span_mm = -1.0
        for idx, span in enumerate(inp.spans):
            if span.span_mm > max_span_mm:
                max_span_mm = span.span_mm
                critical_idx = idx

        crit_span_geom = inp.spans[critical_idx]
        crit_f1, crit_L = span_initial_geometries[critical_idx]

        # Solver para o vão crítico com cabo contínuo:
        # A deformação total Delta_L_tot ocorre ao longo de todo o cabo total_initial_L
        # Delta_L_tot = (total_initial_L * T) / (E * Am)
        am = inp.cable.metallic_area_mm2
        E = inp.cable.elastic_modulus_kgf_mm2

        def multi_residual(T_arb: float) -> Tuple[float, float, float, float]:
            delta_L_tot = (total_initial_L * T_arb) / (E * am)
            # O cabo no vão crítico recebe o comprimento crit_L + delta_L_tot
            L_dyn_crit = crit_L + delta_L_tot
            half_L = L_dyn_crit / 2.0
            half_D = crit_span_geom.span_mm / 2.0
            radicand = (half_L ** 2) - (half_D ** 2)
            if radicand < 0:
                radicand = 0.0
            f2_crit = math.sqrt(radicand)
            if f2_crit <= 1e-9:
                T_teor = 1e9
            else:
                T_teor = (design_load_kgf * L_dyn_crit) / (4.0 * f2_crit)
            return (T_teor - T_arb), delta_L_tot, f2_crit, T_teor

        # Bisseção para multi-vãos
        T_low = 1.0
        T_high = max(inp.cable.min_breaking_load_kgf * 20.0, 50000.0)
        diff_low, _, _, _ = multi_residual(T_low)
        diff_high, _, _, _ = multi_residual(T_high)

        converged = False
        iterations = 0
        final_diff = 0.0
        final_dL_tot = 0.0
        final_f2_crit = 0.0
        T_mid = (T_low + T_high) / 2.0

        for i in range(1, self.max_iterations + 1):
            iterations = i
            T_mid = (T_low + T_high) / 2.0
            diff_mid, dL_mid, f2_mid, _ = multi_residual(T_mid)

            final_diff = diff_mid
            final_dL_tot = dL_mid
            final_f2_crit = f2_mid

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

        # Cálculo de ZLQ no vão crítico
        clearance_res = FallClearanceCalculator.calculate(final_f2_crit, inp.clearance_input)

        if clearance_res.collision_risk:
            is_approved = False

        status_text = "APROVADO" if is_approved else ("REPROVADO" if converged else "NÃO CONVERGE")
        rejection_reason = None
        if not converged:
            rejection_reason = "Solver não convergiu para a linha de múltiplos vãos."
        elif safety_factor < inp.min_safety_factor:
            rejection_reason = (
                f"Fator de segurança ({safety_factor:.2f}) inferior ao limite mínimo ({inp.min_safety_factor:.2f})."
            )
        elif clearance_res.collision_risk:
            rejection_reason = "Risco de colisão detectado na Zona Livre de Queda do vão crítico."

        # Monta resultado do vão crítico
        critical_single_res = SingleSpanResult(
            initial_sag_mm=crit_f1,
            initial_length_mm=crit_L,
            elongation_mm=final_dL_tot,
            dynamic_sag_mm=final_f2_crit,
            tension_kgf=T_mid,
            safety_factor=safety_factor,
            converged=converged,
            iterations=iterations,
            residual_error_kgf=abs(final_diff),
            tolerance_kgf=self.tolerance_kgf,
            initial_guess_kgf=1.0,
            is_approved=is_approved,
            status_text=status_text,
            rejection_reason=rejection_reason,
            clearance_result=clearance_res,
        )

        # Gera resultados individuais para cada vão sob a tração T_mid
        span_results: List[SingleSpanResult] = []
        for idx, span in enumerate(inp.spans):
            if idx == critical_idx:
                span_results.append(critical_single_res)
            else:
                f1_i, L_i = span_initial_geometries[idx]
                # Flecha dinâmica neste vão com alongamento proporcional
                dL_i = (L_i * T_mid) / (E * am)
                L_dyn_i = L_i + dL_i
                half_L_i = L_dyn_i / 2.0
                half_D_i = span.span_mm / 2.0
                rad_i = max(0.0, (half_L_i ** 2) - (half_D_i ** 2))
                f2_i = math.sqrt(rad_i)
                clear_i = FallClearanceCalculator.calculate(f2_i, inp.clearance_input)

                span_results.append(
                    SingleSpanResult(
                        initial_sag_mm=f1_i,
                        initial_length_mm=L_i,
                        elongation_mm=dL_i,
                        dynamic_sag_mm=f2_i,
                        tension_kgf=T_mid,
                        safety_factor=safety_factor,
                        converged=converged,
                        iterations=iterations,
                        residual_error_kgf=abs(final_diff),
                        tolerance_kgf=self.tolerance_kgf,
                        initial_guess_kgf=1.0,
                        is_approved=is_approved,
                        status_text=status_text,
                        rejection_reason=rejection_reason,
                        clearance_result=clear_i,
                    )
                )

        # Cargas nas estruturas de suporte:
        # 1. Ancoragens de extremidade: suportam a tração integral da linha
        end_anchor_load_kgf = T_mid

        # 2. Postes intermediários:
        # Sob passagem livre do cabo, a componente vertical máxima decorre da deflexão
        # angular combinada dos vãos adjacentes (típico NBR 16325-2: ~15% a 25% da tração ou 2 kN)
        sin_angle = final_f2_crit / ((crit_L + final_dL_tot) / 2.0) if (crit_L + final_dL_tot) > 0 else 0.1
        intermediate_vertical_kgf = 2.0 * T_mid * sin_angle
        # Componente horizontal nos intermediários decorrente de atrito/engastamento do passador (~15% de T)
        intermediate_horizontal_kgf = 0.15 * T_mid

        # Lista de advertências de engenharia
        warnings: List[str] = []
        if inp.user_config.warning_text:
            warnings.append(inp.user_config.warning_text)
        if clearance_res.warning_text:
            warnings.append(clearance_res.warning_text)

        warnings.append(
            f"MODELO DE LINHA CONTÍNUA: Linha com {num_posts} postes e {num_spans} vãos. "
            f"O vão {critical_idx + 1} ({crit_span_geom.span_mm:.0f} mm) foi identificado como o vão crítico. "
            "Os postes intermediários devem ser dimensionados para suportar passagem livre do cabo sem travar."
        )

        return MultiSpanResult(
            number_of_posts=num_posts,
            number_of_spans=num_spans,
            critical_span_index=critical_idx + 1,
            critical_span_result=critical_single_res,
            span_results=span_results,
            end_anchor_load_kgf=end_anchor_load_kgf,
            intermediate_post_vertical_load_kgf=intermediate_vertical_kgf,
            intermediate_post_horizontal_load_kgf=intermediate_horizontal_kgf,
            is_approved=is_approved,
            status_text=status_text,
            rejection_reason=rejection_reason,
            warnings=warnings,
        )
