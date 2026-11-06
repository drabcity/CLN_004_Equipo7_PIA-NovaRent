"""Ejecuta las 46 pruebas originales de Unidad 3 sin instalar dependencias.

Para ejecutar tambien pruebas SQL/API instala el proyecto y usa: pytest -q
"""
import os
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path[:0] = [str(RAIZ / "src"), str(RAIZ / "tests")]
loader = unittest.defaultTestLoader
suite = unittest.TestSuite()
for archivo in sorted((RAIZ / "tests").glob("test_*.py")):
    if archivo.name.startswith("test_integracion_"):
        continue  # requiere pytest/FastAPI/SQLAlchemy; se valida en CI con pytest
    suite.addTests(loader.discover(str(RAIZ / "tests"), pattern=archivo.name))
resultado = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if resultado.wasSuccessful() else 1)
