"""Gerenciador sem rede para o snapshot público de revisão."""
from src.core.license_models import LicenseData


class LicenseManager:
    def __init__(self, *args, **kwargs):
        self._license = LicenseData()

    def get_license(self) -> LicenseData:
        return self._license

    @staticmethod
    def post_heartbeat(*args, **kwargs):
        return ("disabled", None, "Local public review mode")
