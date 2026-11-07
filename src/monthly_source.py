"""Lector opcional de resultados mensuales para el frontend, sin motor ni escrituras.

Comprueba el contrato schema=2 del productor. Si sus fuentes no existen en otro
equipo o cambiaron, la vista muestra el aviso y conserva el dashboard CSV habitual.
"""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOURS = ("horas_contratadas_brutas", "horas_disponibles", "horas_directas", "horas_indirectas", "horas_no_asistenciales")


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _number(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError("Horas o semanas inválidas.")
    return number


def _close(a, b):
    return math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-9)


def _validate_rows(rows):
    seen = set()
    periods = {f"2026-{month:02d}" for month in range(1, 13)}
    for row in rows:
        key = (row["PersonaId"], row["Periodo"])
        if key in seen or key[1] not in periods:
            raise ValueError("Duplicado o período mensual inválido.")
        seen.add(key)
        if row["Procedencia"] != "EXPLICIT_CONTRACT" or not row["Fila_Contrato"]:
            raise ValueError("Registro observado sin procedencia válida.")
        _number(row["horas_semanales"])
        if row["Horas_Estado"] == "NOT_VERIFIED":
            if any(row.get(key) not in (None, "") for key in HOURS) or not row["Horas_Motivo"]:
                raise ValueError("Horas no verificadas no pueden tener cifras certificadas.")
            continue
        if row["Horas_Estado"] != "VERIFIED":
            raise ValueError("Estado de horas mensual no compatible.")
        for key in HOURS:
            _number(row[key])
        h, sb, se = (_number(row[key]) for key in ["horas_semanales", "semanas_base", "semanas_efectivas"])
        if se > sb or not _close(row["horas_contratadas_brutas"], h * sb) or not _close(row["horas_disponibles"], h * se):
            raise ValueError("Horas brutas/efectivas inconsistentes.")
        if not _close(row["horas_disponibles"], sum(float(row[key]) for key in HOURS[2:])):
            raise ValueError("No se conserva la distribución de horas disponibles.")


class MonthlyRows(list):
    def __init__(self, rows, coverage):
        super().__init__(rows)
        self.coverage = coverage


def load_validated_monthly(path):
    """Lectura y validación únicamente; no importa ni ejecuta el exportador."""
    path = Path(path)
    coverage = json.loads(path.with_name("planificacion_cobertura.json").read_text(encoding="utf-8"))
    if coverage.get("schema") != 2:
        raise ValueError("Esquema de cobertura no compatible.")
    # Son referencias de procedencia, no dependencias Python del frontend.
    required = {str((ROOT / name).resolve()) for name in [
        "src/engine.py", "src/export_monthly_hours.py",
        "data/output/planificacion_calculada.csv", "data/output/resumen_nacional.csv",
    ]}
    required.update(str(p.resolve()) for p in (ROOT / "data/parameters").glob("*.json"))
    if not required.issubset(coverage["dependencies"]):
        raise ValueError("Falta trazabilidad de fuentes oficiales.")
    for dependency, expected in coverage["dependencies"].items():
        if _digest(dependency) != expected:
            raise ValueError("Salida mensual obsoleta: cambió una fuente o el motor.")
    for name in [path.name, "planificacion_exclusiones.csv"]:
        if coverage["files"].get(name) != _digest(path.with_name(name)):
            raise ValueError("Salida mensual alterada o parcial.")
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    _validate_rows(rows)
    if len(rows) != coverage["observed_rows"]:
        raise ValueError("Cantidad de filas mensual no validada.")
    return MonthlyRows(rows, coverage)
