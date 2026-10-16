"""Módulo de conversão e rastreabilidade de unidades físicas.

Permite conversão transparente entre o Sistema Internacional (SI) e o sistema
adotado na planilha de referência (kgf, mm, kgf/mm²), registrando a aceleração
gravitacional adotada para fins de auditoria de engenharia.
"""

# Aceleração da gravidade padrão internacional (SI / ISO 80000-3)
G_STANDARD = 9.80665  # m/s²

# Aceleração da gravidade aproximada implicitamente adotada na planilha de referência
G_APPROX_EXCEL = 10.0  # m/s²


def kgf_to_n(force_kgf: float, g: float = G_STANDARD) -> float:
    """Converte força em kgf para Newtons (N)."""
    return force_kgf * g


def n_to_kgf(force_n: float, g: float = G_STANDARD) -> float:
    """Converte força em Newtons (N) para kgf."""
    return force_n / g


def kgf_to_kn(force_kgf: float, g: float = G_STANDARD) -> float:
    """Converte força em kgf para quilonewtons (kN)."""
    return (force_kgf * g) / 1000.0


def kn_to_kgf(force_kn: float, g: float = G_STANDARD) -> float:
    """Converte força em quilonewtons (kN) para kgf."""
    return (force_kn * 1000.0) / g


def mm_to_m(length_mm: float) -> float:
    """Converte milímetros para metros."""
    return length_mm / 1000.0


def m_to_mm(length_m: float) -> float:
    """Converte metros para milímetros."""
    return length_m * 1000.0


def kgf_per_mm2_to_mpa(modulus_kgf_mm2: float, g: float = G_STANDARD) -> float:
    """Converte módulo de elasticidade ou tensão de kgf/mm² para MPa (N/mm²)."""
    return modulus_kgf_mm2 * g


def mpa_to_kgf_per_mm2(stress_mpa: float, g: float = G_STANDARD) -> float:
    """Converte MPa (N/mm²) para kgf/mm²."""
    return stress_mpa / g
