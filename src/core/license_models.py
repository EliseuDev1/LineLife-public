"""Entitlements locais usados apenas pelo snapshot público de revisão."""
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class LicenseTier(str, Enum):
    LOCAL = "local"


class LicenseMode(str, Enum):
    LOCAL = "local"


class LicenseStatus(str, Enum):
    LOCAL = "local"


@dataclass
class LicenseData:
    tier: LicenseTier = LicenseTier.LOCAL
    mode: LicenseMode = LicenseMode.LOCAL
    licensee_name: str = "Local code review"
    licensee_email: str = ""
    company_name: str = ""
    license_key: str = "LOCAL-REVIEW"
    expiration_date: str | None = None

    @property
    def is_active(self) -> bool:
        return True

    @property
    def is_pro(self) -> bool:
        return True

    @property
    def has_functional_access(self) -> bool:
        return True

    @property
    def has_full_functional_access(self) -> bool:
        return True

    @property
    def max_allowed_spans(self) -> int:
        return 30

    def can_support_spans(self, span_count: int) -> bool:
        return span_count <= self.max_allowed_spans

    @property
    def is_calculation_allowed(self) -> bool:
        return True

    @property
    def is_screen_verdict_allowed(self) -> bool:
        return True

    @property
    def is_pdf_allowed(self) -> bool:
        return True

    @property
    def is_bom_allowed(self) -> bool:
        return True

    @property
    def is_bom_export_allowed(self) -> bool:
        return True

    @property
    def is_memory_allowed(self) -> bool:
        return True

    @property
    def is_print_allowed(self) -> bool:
        return True

    @property
    def is_custom_logo_allowed(self) -> bool:
        return True

    @property
    def watermark_text(self) -> str | None:
        return None

    @property
    def status(self) -> LicenseStatus:
        return LicenseStatus.LOCAL

    @property
    def display_name(self) -> str:
        return "Local review"

    def assert_can_calculate(self, span_count: int) -> None:
        return None

    def assert_can_access_bom(self) -> None:
        return None

    def assert_can_export_bom(self) -> None:
        return None

    def assert_can_export_pdf(self) -> None:
        return None

    def assert_can_access_memory(self) -> None:
        return None

    def assert_can_print(self) -> None:
        return None


def canonical_entitlement(entitlements: Iterable[LicenseData]) -> LicenseData:
    return next(iter(entitlements), LicenseData())
