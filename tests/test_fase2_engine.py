"""Suíte de Testes Automatizados da Fase 2.

Cobre os requisitos avançados de engenharia:
1. Regras de combinação de usuários múltiplos (ABNT NBR 16325-2 vs. Customizada com advertência);
2. Cálculo da Zona Livre de Queda (ZLQ conforme NR-35) e detecção de risco de colisão com o solo;
3. Dimensionamento de linhas contínuas com múltiplos postes e vãos (2 postes, 3 postes, 5 postes);
4. Fachada unificada CalculationEngine.
"""

import unittest
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.catalogs.cable_catalog import CableCatalog
from src.calculations.engine import CalculationEngine
from src.calculations.fall_clearance import FallClearanceCalculator
from src.domain.models import (
    FallClearanceInput,
    LoadRuleType,
    SpanGeometry,
    UserLoadConfig,
)


class TestFase2Engine(unittest.TestCase):
    """Testes dos recursos avançados do motor de cálculo da Fase 2."""

    @classmethod
    def setUpClass(cls):
        cls.catalog = CableCatalog()
        cls.engine = CalculationEngine()
        cls.cabo_base = cls.catalog.get_by_specification("Ø5/16 - 6X19 SEALE EIPS - AF")
        assert cls.cabo_base is not None

    def test_multi_user_load_rules_nbr16325_2(self):
        """Valida regra de combinação de usuários da NBR 16325-2:
        1º usuário dinâmico (600 kgf) + 100 kgf por usuário adicional.
        """
        # 1 usuário
        cfg_1 = UserLoadConfig(total_users=1, simultaneous_users=1)
        self.assertEqual(cfg_1.calculated_design_load_kgf, 600.0)
        self.assertTrue(cfg_1.is_normative_compliant)
        self.assertIsNone(cfg_1.warning_text)

        # 2 usuários simultâneos
        cfg_2 = UserLoadConfig(total_users=2, simultaneous_users=2)
        self.assertEqual(cfg_2.calculated_design_load_kgf, 700.0)  # 600 + 100
        self.assertTrue(cfg_2.is_normative_compliant)
        self.assertIsNone(cfg_2.warning_text)

        # 3 usuários simultâneos
        cfg_3 = UserLoadConfig(total_users=3, simultaneous_users=3)
        self.assertEqual(cfg_3.calculated_design_load_kgf, 800.0)  # 600 + 2*100
        self.assertTrue(cfg_3.is_normative_compliant)
        self.assertIsNone(cfg_3.warning_text)

    def test_multi_user_load_rules_custom_with_warning(self):
        """Valida regra customizada com emissão de alerta explícito de divergência da norma."""
        cfg_custom = UserLoadConfig(
            total_users=3,
            simultaneous_users=3,
            rule_type=LoadRuleType.CUSTOM,
            custom_total_load_kgf=1800.0,  # 3 * 600 kgf
        )
        self.assertEqual(cfg_custom.calculated_design_load_kgf, 1800.0)
        self.assertFalse(cfg_custom.is_normative_compliant)
        self.assertIsNotNone(cfg_custom.warning_text)
        self.assertIn("diverge do método padrão da ABNT NBR 16325-2", cfg_custom.warning_text)

    def test_fall_clearance_calculation_and_collision_detection(self):
        """Valida o cálculo da ZLQ e detecção de risco de colisão (NR-35)."""
        f2_mm = 515.17  # ~0.515 m
        
        # Cenário 1: Altura disponível suficiente (H_disp = 6.5 m)
        params_ok = FallClearanceInput(
            lanyard_length_m=1.5,
            absorber_extension_m=1.2,
            worker_height_offset_m=1.5,
            safety_margin_m=1.0,
            available_clearance_m=6.5,
        )
        res_ok = FallClearanceCalculator.calculate(f2_mm, params_ok)
        expected_zlq = 1.5 + 1.2 + 1.5 + 1.0 + (515.17 / 1000.0)  # 5.715 m
        self.assertAlmostEqual(res_ok.required_clearance_m, expected_zlq, places=3)
        self.assertFalse(res_ok.collision_risk)
        self.assertTrue(res_ok.clearance_approved)
        self.assertAlmostEqual(res_ok.residual_margin_m, 6.5 - expected_zlq, places=3)
        self.assertIsNone(res_ok.warning_text)

        # Cenário 2: Altura disponível insuficiente (H_disp = 5.0 m) -> RISCO DE COLISÃO
        params_fail = FallClearanceInput(
            lanyard_length_m=1.5,
            absorber_extension_m=1.2,
            worker_height_offset_m=1.5,
            safety_margin_m=1.0,
            available_clearance_m=5.0,
        )
        res_fail = FallClearanceCalculator.calculate(f2_mm, params_fail)
        self.assertTrue(res_fail.collision_risk)
        self.assertFalse(res_fail.clearance_approved)
        self.assertAlmostEqual(res_fail.residual_margin_m, 5.0 - expected_zlq, places=3)
        self.assertIn("RISCO CRÍTICO DE COLISÃO", res_fail.warning_text)

    def test_single_span_rejection_due_to_collision_risk(self):
        """Valida que o motor reprova o projeto se houver risco de colisão na ZLQ."""
        clearance_insufficient = FallClearanceInput(available_clearance_m=4.5)  # Necessário ~5.7 m
        res = self.engine.calculate_single_span(
            span_mm=6600.0,
            initial_sag_percent=3.0,
            cable=self.cabo_base,
            impact_load_kgf=600.0,
            clearance_input=clearance_insufficient,
        )
        self.assertTrue(res.converged)
        self.assertFalse(res.is_approved)
        self.assertEqual(res.status_text, "REPROVADO")
        self.assertIn("Risco de colisão detectado na Zona Livre de Queda", res.rejection_reason)

    def test_multi_span_two_posts_matches_single_span(self):
        """Valida que uma linha com 2 postes (1 vão) é matematicamente idêntica ao caso-base."""
        spans = [SpanGeometry(span_index=1, span_mm=6600.0, initial_sag_percent=3.0)]
        res_multi = self.engine.calculate_multi_span(spans=spans, cable=self.cabo_base)

        self.assertEqual(res_multi.number_of_posts, 2)
        self.assertEqual(res_multi.number_of_spans, 1)
        self.assertEqual(res_multi.critical_span_index, 1)
        self.assertAlmostEqual(res_multi.critical_span_result.tension_kgf, 1944.99, delta=0.05)
        self.assertAlmostEqual(res_multi.critical_span_result.dynamic_sag_mm, 515.17, delta=0.05)
        self.assertTrue(res_multi.is_approved)
        self.assertEqual(res_multi.status_text, "APROVADO")

    def test_multi_span_three_posts_two_spans(self):
        """Valida linha com 3 postes e 2 vãos contínuos (6 m e 8 m)."""
        spans = [
            SpanGeometry(span_index=1, span_mm=6000.0, initial_sag_percent=3.0),
            SpanGeometry(span_index=2, span_mm=8000.0, initial_sag_percent=3.0),
        ]
        res = self.engine.calculate_multi_span(spans=spans, cable=self.cabo_base)

        self.assertEqual(res.number_of_posts, 3)
        self.assertEqual(res.number_of_spans, 2)
        # O vão 2 (8000 mm) deve ser o vão crítico
        self.assertEqual(res.critical_span_index, 2)
        self.assertTrue(res.critical_span_result.converged)
        self.assertTrue(res.is_approved)

        # Cargas nas ancoragens
        self.assertGreater(res.end_anchor_load_kgf, 1000.0)
        self.assertGreater(res.intermediate_post_vertical_load_kgf, 100.0)
        self.assertGreater(res.intermediate_post_horizontal_load_kgf, 50.0)
        self.assertEqual(len(res.span_results), 2)

    def test_multi_span_five_posts_equal_spans(self):
        """Valida linha extensa com 5 postes e 4 vãos iguais de 6.000 mm (24 m de extensão total)."""
        spans = [
            SpanGeometry(span_index=i + 1, span_mm=6000.0, initial_sag_percent=3.0)
            for i in range(4)
        ]
        user_cfg = UserLoadConfig(total_users=2, simultaneous_users=2)  # 700 kgf
        res = self.engine.calculate_multi_span(
            spans=spans,
            cable=self.cabo_base,
            user_config=user_cfg,
        )

        self.assertEqual(res.number_of_posts, 5)
        self.assertEqual(res.number_of_spans, 4)
        self.assertTrue(res.critical_span_result.converged)
        self.assertTrue(res.is_approved)
        self.assertEqual(len(res.span_results), 4)


if __name__ == "__main__":
    unittest.main()
