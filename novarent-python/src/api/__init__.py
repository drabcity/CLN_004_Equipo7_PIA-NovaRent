"""Ruta esperada por el PIA, expone la API del paquete NovaRent."""
from novarent.api.main import app, crear_api
__all__ = ["app", "crear_api"]
