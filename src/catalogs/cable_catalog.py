"""Catálogo de cabos de aço conforme NBR ISO 2408 e dados da planilha de referência."""

import json
import os
from typing import List, Optional, Dict
from src.domain.models import CableProperties


class CableCatalog:
    """Gerenciador de catálogo de cabos de aço."""

    def __init__(self, json_path: Optional[str] = None):
        if json_path is None:
            # Caminho padrão relativo ao arquivo do módulo
            base_dir = os.path.dirname(__file__)
            json_path = os.path.join(base_dir, "data", "cables_iso2408.json")
        self.json_path = json_path
        self._cables: Dict[str, CableProperties] = {}
        self._baseline_cases: List[dict] = []
        self._load_catalog()

    def _load_catalog(self) -> None:
        """Carrega os cabos a partir do arquivo JSON estruturado."""
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(f"Arquivo de catálogo não encontrado: {self.json_path}")

        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data.get("cables", []):
            cable = CableProperties(
                specification=item["specification"],
                diameter_mm=float(item["diameter_mm"]),
                metallic_area_factor=float(item["metallic_area_factor"]),
                elastic_modulus_kgf_mm2=float(item["elastic_modulus_kgf_mm2"]),
                min_breaking_load_kgf=float(item["min_breaking_load_kgf"]),
                grade_n_mm2=float(item["grade_n_mm2"]) if item.get("grade_n_mm2") else None,
                core_type=item.get("core_type", "6 x 19 com alma de fibra")
            )
            self._cables[cable.specification] = cable

        self._baseline_cases = data.get("excel_summary_baseline", [])

    def get_by_specification(self, spec: str) -> Optional[CableProperties]:
        """Obtém as propriedades de um cabo por sua especificação textual exata."""
        return self._cables.get(spec.strip())

    def list_all(self) -> List[CableProperties]:
        """Retorna todos os cabos cadastrados no catálogo."""
        return list(self._cables.values())

    def get_baseline_cases(self) -> List[dict]:
        """Retorna os casos resumo gravados da planilha Excel para testes de regressão."""
        return self._baseline_cases
