"""Línea base de resultados exportados y bloqueo seguro de redistribución.

No se invierte el cálculo de atenciones: floor, round y factores grupales
impiden recuperar las horas exactas del motor desde los CSV actuales.
"""
from math import isfinite

PERIODS = {"Anual 2026": None, **dict(zip(
    [f"{month} 2026" for month in ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]],
    ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]))}

BLOCKERS = (
    "Faltan horas contratadas, directas, indirectas y no clínicas por profesional y período en los resultados exportados.",
    "No hay identificación de horas indirectas elegibles ni regla verificable que autorice su redistribución. Los porcentajes por cargo son distribución basal, no límites de reasignación.",
)


def _total(rows, column):
    try:
        values = [float(row[column]) for row in rows]
        if not values or any(not isfinite(v) or v < 0 for v in values):
            return None
        return sum(values)
    except (KeyError, TypeError, ValueError):
        return None


def baseline(rows, period, monthly_rows=None):
    """Suma exclusivamente columnas fuente del período; no estima horas."""
    if period not in PERIODS:
        raise ValueError("Período no disponible en los resultados.")
    month = PERIODS[period]
    result = {
        "period": period,
        "professionals": len(rows),
        "direct_appointments": _total(rows, f"Ate_Dir_{month}" if month else "Atencion_Anual_Directa"),
        "total_appointments": _total(rows, f"Ate_Tot_{month}" if month else "Total_Atenciones"),
        "foja_mean": (_total(rows, "FOJA") / len(rows)) if not month and rows and _total(rows, "FOJA") is not None else None,
        "direct_hours": None,
        "indirect_hours": None,
        "contract_hours": None,
        "available_hours": None,
        "nonclinical_hours": None,
        "eligible_hours": None,
        "demand_hours": None,
    }
    if monthly_rows is not None:
        # No se cruza solo por PersonaId: preserva instituto, cargo y especialidad.
        fields = ["PersonaId", "IT", "Instituto", "Cargo", "Especialidad"]
        keys = {tuple(str(row[k]) for k in fields) for row in rows}
        selected = [row for row in monthly_rows if tuple(str(row[k]) for k in fields) in keys]
        wanted = list(PERIODS.values())[1:] if month is None else [month]
        periods = {f"2026-{list(PERIODS.values())[1:].index(m) + 1:02d}" for m in wanted}
        selected = [row for row in selected if row["Periodo"] in periods]
        expected = {(key, p) for key in keys for p in periods}
        actual = {(tuple(str(row[k]) for k in fields), row["Periodo"]) for row in selected}
        if len(rows) != len(keys) or len(selected) != len(actual) or not actual.issubset(expected):
            raise ValueError("Atribución mensual ambigua o duplicada en el alcance seleccionado.")
        # Una jornada semanal observada no certifica horas de capacidad mensual.
        verified = [r for r in selected if r.get("Horas_Estado") == "VERIFIED"]
        if selected and len(verified) == len(selected):
            for key, column in [("contract_hours", "horas_contratadas_brutas"), ("available_hours", "horas_disponibles"), ("direct_hours", "horas_directas"), ("indirect_hours", "horas_indirectas"), ("nonclinical_hours", "horas_no_asistenciales")]:
                result[key] = _total(verified, column)
        result["monthly_detail"] = selected
        result["source_coverage"] = {
            "observed_rows": len(selected), "expected_professional_periods": len(expected),
            "observed_fraction": len(selected) / len(expected) if expected else None,
            "periods": sorted({r["Periodo"] for r in selected}),
            "global": getattr(monthly_rows, "coverage", {}),
        }
    return result


def validate_transfer(hours):
    """Cero significa sin ajuste; ninguna transferencia está autorizada."""
    if not isfinite(hours) or hours < 0:
        raise ValueError("La transferencia debe ser finita y no negativa.")
    if hours != 0:
        raise ValueError("Simulación bloqueada: faltan horas basales y elegibilidad verificable.")
    return 0.0


def scenario_for(state, context, base, reset=False):
    """Descarta escenarios de otro alcance, otra fuente o estado inválido."""
    current = state.get("decision_scenario")
    if reset or not current or current.get("context") != context or current.get("transfer_hours") != 0:
        current = {"context": context, "baseline": base, "transfer_hours": validate_transfer(0), "status": "blocked"}
        state["decision_scenario"] = current
    return current
