"""Cálculo e verificação da Zona Livre de Queda (ZLQ) conforme NR-35 e NBR 16325-2.

A Zona Livre de Queda (ZLQ) é a distância vertical mínima livre necessária
entre o ponto de ancoragem / linha de vida e o obstáculo inferior mais próximo
(piso, mezanino ou maquinário), para que o trabalhador retenha a queda com segurança
sem sofrer colisão física.
"""

from typing import Optional
from src.domain.models import FallClearanceInput, FallClearanceResult


class FallClearanceCalculator:
    """Calculadora de Zona Livre de Queda (ZLQ)."""

    @staticmethod
    def calculate(
        dynamic_sag_mm: float,
        params: Optional[FallClearanceInput] = None
    ) -> FallClearanceResult:
        """Calcula a ZLQ necessária e confronta com a altura disponível.
        
        ZLQ_req = L_talabarte + Delta_L_absorvedor + h_trabalhador + f2 + Margem_Segurança
        """
        if params is None:
            params = FallClearanceInput()

        dynamic_sag_m = dynamic_sag_mm / 1000.0
        required_clearance_m = (
            params.lanyard_length_m
            + params.absorber_extension_m
            + params.worker_height_offset_m
            + dynamic_sag_m
            + params.safety_margin_m
        )

        available_m = params.available_clearance_m
        if available_m is not None:
            residual_margin_m = available_m - required_clearance_m
            collision_risk = residual_margin_m < 0.0
            clearance_approved = not collision_risk

            if collision_risk:
                warning_text = (
                    f"PERIGO: RISCO CRÍTICO DE COLISÃO! A Zona Livre de Queda necessária "
                    f"({required_clearance_m:.2f} m) excede a altura disponível no local "
                    f"({available_m:.2f} m) por {abs(residual_margin_m):.2f} m. "
                    f"O trabalhador atingirá o solo ou obstáculo antes da retenção total da queda."
                )
            else:
                warning_text = None
        else:
            residual_margin_m = None
            collision_risk = False
            clearance_approved = True
            warning_text = (
                f"NOTA DE PROJETO: ZLQ necessária calculada em {required_clearance_m:.2f} m. "
                "A altura livre disponível no local de trabalho não foi informada e deve ser "
                "obrigatoriamente validada em campo antes da liberação operacional."
            )

        return FallClearanceResult(
            required_clearance_m=required_clearance_m,
            dynamic_sag_m=dynamic_sag_m,
            available_clearance_m=available_m,
            residual_margin_m=residual_margin_m,
            collision_risk=collision_risk,
            clearance_approved=clearance_approved,
            warning_text=warning_text,
        )
