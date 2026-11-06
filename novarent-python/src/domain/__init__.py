"""Alias de compatibilidad con la estructura de carpetas del PIA.

Los Aggregates originales de U3 permanecen en novarent.dominio para no romper
la trazabilidad ni las importaciones del proyecto original.
"""
from novarent.dominio import *  # noqa: F401,F403
