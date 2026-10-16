"""Suíte de Testes de Regressão Obrigatória - Fase 1.

Valida a reprodução exata dos cálculos da planilha Excel 'Linha de Vida Horizontal - Cálculo.xlsm'
sem executar macros ou depender do Excel, cobrindo:
1. Caso-base especificado com tolerâncias numéricas rigorosas;
2. Todos os 46 cabos de aço da planilha de referência comparados contra as colunas H a L da aba PRINCIPAL;
3. Robustez do solver numérico contra divergências e reprovações;
4. Rastreabilidade das conversões de unidades físicas.
"""

import unittest
import sys
import os

# Adiciona o diretório raiz do projeto ao path de importação
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.catalogs.cable_catalog import CableCatalog
from src.calculations.cable_solver import CableSolver
from src.domain.models import SingleSpanInput, CableProperties
from src.core import units


class TestRegressionExcel(unittest.TestCase):
    """Testes de regressão confrontando o motor Python com o Excel de referência."""

    @classmethod
    def setUpClass(cls):
        cls.catalog = CableCatalog()
        cls.solver = CableSolver(tolerance_kgf=1e-6, max_iterations=100)

    def test_base_case_excel_exact(self):
        """Teste do Caso-Base da especificação técnica (Item 13):
        
        Entradas:
        - Vão D = 6600 mm
        - Flecha inicial %f1 = 3%
        - Carga P = 600 kgf
        - FS mínimo = 2.0
        - Cabo = Ø5/16 - 6X19 SEALE EIPS - AF (d = 8 mm, F = 0.33, E = 9500 kgf/mm², Fu = 4139.52 kgf)
        
        Valores esperados da planilha:
        - f1 = 198 mm
        - L = 6615.81 mm
        - Alongamento Delta L = 64.13 mm
        - Flecha dinâmica f2 = 515.17 mm
        - Tração T = 1944.99 kgf
        - FS = 2.1283
        - Convergência: True
        - Status: APROVADO
        """
        cabo = self.catalog.get_by_specification("Ø5/16 - 6X19 SEALE EIPS - AF")
        self.assertIsNotNone(cabo, "Cabo Ø5/16 - 6X19 SEALE EIPS - AF deve constar no catálogo")
        
        # Validação das propriedades do cabo extraídas
        self.assertEqual(cabo.diameter_mm, 8.0)
        self.assertEqual(cabo.metallic_area_factor, 0.33)
        self.assertEqual(cabo.elastic_modulus_kgf_mm2, 9500.0)
        self.assertEqual(cabo.min_breaking_load_kgf, 4139.52)
        self.assertAlmostEqual(cabo.metallic_area_mm2, 21.12, places=2)

        inp = SingleSpanInput(
            span_mm=6600.0,
            initial_sag_percent=3.0,
            impact_load_kgf=600.0,
            min_safety_factor=2.0,
            cable=cabo,
        )

        res = self.solver.solve(inp)

        # 1. Flecha inicial f1: 198 mm
        self.assertAlmostEqual(res.initial_sag_mm, 198.0, delta=0.01)

        # 2. Comprimento inicial L: 6615.8058 mm (~6615.81 mm)
        self.assertAlmostEqual(res.initial_length_mm, 6615.81, delta=0.02)

        # 3. Alongamento Delta L: 64.133 mm (~64.13 mm)
        self.assertAlmostEqual(res.elongation_mm, 64.13, delta=0.02)

        # 4. Flecha dinâmica f2: 515.166 mm (~515.17 mm)
        self.assertAlmostEqual(res.dynamic_sag_mm, 515.17, delta=0.02)

        # 5. Tração convergente T: 1944.987 kgf (~1944.99 kgf)
        self.assertAlmostEqual(res.tension_kgf, 1944.99, delta=0.02)

        # 6. Fator de segurança FS: 2.1283
        self.assertAlmostEqual(res.safety_factor, 2.1283, delta=0.0005)

        # 7. Auditoria numérica
        self.assertTrue(res.converged)
        self.assertLess(res.residual_error_kgf, 1e-6)
        self.assertTrue(res.is_approved)
        self.assertEqual(res.status_text, "APROVADO")

    def test_all_46_catalog_cables_against_excel_baseline(self):
        """Validação sistemática de todos os 46 cabos comparando com as colunas H a L do Excel.
        
        Para cada um dos 46 cabos no vão de 6600 mm e carga de 600 kgf:
        - f2_calc vs f2_excel (tolerância <= 0.05 mm)
        - T_calc vs T_excel (tolerância <= 0.05 kgf)
        - FS_calc vs FS_excel (tolerância <= 0.005)
        - status_calc vs status_excel ('APROVADO' ou 'REPROVADO')
        """
        baseline_cases = self.catalog.get_baseline_cases()
        self.assertEqual(len(baseline_cases), 46, "Devem existir 46 casos de referência extraídos")

        divergencias = []

        for case in baseline_cases:
            spec = case["specification"]
            expected_f2 = case["excel_f2_mm"]
            expected_T = case["excel_T_kgf"]
            expected_status = case["excel_status"]
            expected_fs = case["excel_FS"]

            cabo = self.catalog.get_by_specification(spec)
            self.assertIsNotNone(cabo, f"Cabo {spec} não encontrado no catálogo")

            inp = SingleSpanInput(
                span_mm=6600.0,
                initial_sag_percent=3.0,
                impact_load_kgf=600.0,
                min_safety_factor=2.0,
                cable=cabo,
            )

            res = self.solver.solve(inp)

            # Verifica tolerâncias numéricas
            diff_f2 = abs(res.dynamic_sag_mm - expected_f2)
            diff_T = abs(res.tension_kgf - expected_T)
            diff_fs = abs(res.safety_factor - expected_fs)
            status_match = (res.status_text == expected_status)

            if diff_f2 > 0.05 or diff_T > 0.05 or diff_fs > 0.005 or not status_match:
                divergencias.append(
                    f"{spec}: "
                    f"f2[calc={res.dynamic_sag_mm:.2f}, exp={expected_f2:.2f}, diff={diff_f2:.3f}] | "
                    f"T[calc={res.tension_kgf:.2f}, exp={expected_T:.2f}, diff={diff_T:.3f}] | "
                    f"FS[calc={res.safety_factor:.4f}, exp={expected_fs:.4f}, diff={diff_fs:.4f}] | "
                    f"Status[calc={res.status_text}, exp={expected_status}]"
                )

        self.assertEqual(
            len(divergencias),
            0,
            f"Divergências encontradas em {len(divergencias)} dos 46 cabos:\n" + "\n".join(divergencias),
        )

    def test_rejection_when_safety_factor_insufficient(self):
        """Valida que cabos subdimensionados são reprovados com justificativa explícita."""
        # Cabo fino Ø1/8 (Fu = 598.12 kgf) para carga de 600 kgf
        cabo = self.catalog.get_by_specification("Ø1/8 - 6X19 SEALE IPS - AF")
        inp = SingleSpanInput(
            span_mm=6600.0,
            initial_sag_percent=3.0,
            impact_load_kgf=600.0,
            min_safety_factor=2.0,
            cable=cabo,
        )
        res = self.solver.solve(inp)
        self.assertTrue(res.converged)
        self.assertFalse(res.is_approved)
        self.assertEqual(res.status_text, "REPROVADO")
        self.assertLess(res.safety_factor, 2.0)
        self.assertIn("inferior ao limite mínimo", res.rejection_reason)

    def test_units_traceability(self):
        """Valida funções de conversão e rastreabilidade entre SI e kgf."""
        # 1 kgf em SI padrão
        self.assertAlmostEqual(units.kgf_to_n(1.0), 9.80665, places=5)
        self.assertAlmostEqual(units.n_to_kgf(9.80665), 1.0, places=5)

        # 600 kgf em kN
        kn = units.kgf_to_kn(600.0)
        self.assertAlmostEqual(kn, (600.0 * 9.80665) / 1000.0, places=4)

        # Verificação da aproximação legada de g = 10 m/s² da planilha
        fu_n = 1960.0 * 21.12  # 41395.2 N
        fu_kgf_approx = fu_n / units.G_APPROX_EXCEL
        self.assertEqual(fu_kgf_approx, 4139.52)


if __name__ == "__main__":
    unittest.main()
