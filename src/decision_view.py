"""Centro de Decisiones V4.3; sesión local sin escritura de resultados."""
import hashlib
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from decision_simulator import BLOCKERS, PERIODS, baseline, scenario_for, validate_transfer
from monthly_source import load_validated_monthly


def render_decisions(filtered, source_signature):
    period = st.selectbox("Período del escenario", list(PERIODS), key="decision_period")
    records = filtered.to_dict("records")
    monthly_path = Path(__file__).resolve().parents[1] / "data/output/planificacion_horas_mensuales.csv"
    monthly, monthly_hash = None, None
    if monthly_path.exists():
        try:
            monthly = load_validated_monthly(monthly_path)
            monthly_hash = hashlib.sha256(monthly_path.read_bytes()).hexdigest()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            st.warning(f"Línea base mensual no validada; no se utilizará: {exc}")
    try:
        base = baseline(records, period, monthly)
    except (ValueError, KeyError, TypeError) as exc:
        st.warning(f"Línea base mensual no compatible con los filtros: {exc}")
        base = baseline(records, period)
    has_hours = base["available_hours"] is not None
    if "source_coverage" in base:
        coverage = base["source_coverage"]
        global_coverage = coverage["global"]
        st.info(f"Fuente parcial · {period}: {coverage['observed_rows']} jornadas semanales observadas de {coverage['expected_professional_periods']} combinaciones profesional/mes del filtro. No es capacidad nacional completa ni cobertura de demanda.")
        st.caption("Períodos observados en el filtro: " + (", ".join(coverage["periods"]) or "ninguno"))
        st.caption(f"Conjunto fuente global, sin filtrar: {global_coverage.get('classifications', {}).get('DERIVED_FROM_BASE', 0)} proyecciones excluidas de observados; {global_coverage.get('classifications', {}).get('NOT_VERIFIED', 0)} combinaciones no verificadas. Jornadas observadas no certifican vigencia mensual ni horas efectivas.")
    scope = [st.session_state.get(f"filter_{field}") for field in ["Instituto", "Especialidad", "Cargo"]]
    source_hash = hashlib.sha256(source_signature).hexdigest()
    context = hashlib.sha256(json.dumps([source_hash, monthly_hash, scope, period, records], sort_keys=True, default=str).encode()).hexdigest()
    scenario = scenario_for(st.session_state, context, base)

    st.markdown('<div class="decision-diagnosis"><div class="eyebrow accent">V4.3 · DIAGNÓSTICO DE BRECHA</div><h2>Brecha asistencial: No disponible</h2><p>No existe demanda clínica en horas para el mismo período y alcance. Las atenciones planificadas y la meta de gestión no son demanda.</p></div>', unsafe_allow_html=True)
    st.warning("Redistribución bloqueada · No se ha calculado un escenario simulado.")
    left, right = st.columns([2, 3])
    with left, st.container(border=True):
        st.markdown('<div class="eyebrow">PASO 1 · AJUSTE CONTROLADO</div>', unsafe_allow_html=True)
        st.subheader("Redistribución de jornada")
        st.number_input("Horas indirectas a atención directa", min_value=0.0, max_value=0.0, value=0.0, disabled=True)
        st.caption("Transferencia deshabilitada. Las horas elegibles son desconocidas; no equivalen a cero horas disponibles.")
        for reason in (BLOCKERS[1:] if has_hours else BLOCKERS):
            st.write(f"• {reason}")
        st.button("Calcular escenario", disabled=True, use_container_width=True)
        if st.button("Restablecer escenario", use_container_width=True):
            scenario = scenario_for(st.session_state, context, base, reset=True)
            st.success("Escenario restablecido: sin ajuste y sin resultados simulados.")
        st.caption("El escenario vive únicamente en esta sesión. Cambiar filtros, período o archivo fuente descarta el alcance anterior.")

    with right:
        basal, simulated = st.columns(2)
        with basal, st.container(border=True):
            st.markdown('<div class="eyebrow">ESCENARIO BASAL · FUENTE CSV</div>', unsafe_allow_html=True)
            st.subheader(period)
            direct = base["direct_appointments"]
            st.metric("Atenciones directas planificadas", _format(direct))
            st.metric("Atenciones totales planificadas", _format(base["total_appointments"]))
            st.caption("Atenciones del CSV oficial para el filtro completo; no son totales exclusivos del subconjunto observado ni actividad ejecutada.")
            st.caption(f"{base['professionals']} registros profesionales en el alcance")
            st.metric("Horas directas basales", _hours(base["direct_hours"]))
            st.metric("Horas indirectas totales", _hours(base["indirect_hours"]))
            st.caption("Las horas indirectas totales no equivalen a horas elegibles para reasignación.")
            st.metric("FOJA anual medio", f"{base['foja_mean']:.1%}" if base["foja_mean"] is not None else "No disponible")
            st.caption("Media simple de FOJA por profesional; no es cobertura de demanda. No se dispone de FOJA mensual.")
        with simulated, st.container(border=True):
            st.markdown('<div class="eyebrow accent">ESCENARIO SIMULADO · BLOQUEADO</div>', unsafe_allow_html=True)
            st.subheader("Sin cálculo aplicado")
            st.metric("Horas directas simuladas", "No disponible")
            st.metric("Variación de horas directas", "No disponible")
            st.caption("No se estiman atenciones adicionales ni horas recuperadas por Blue Prism.")

    st.subheader("Comparación antes / después")
    st.dataframe(pd.DataFrame({
        "Indicador": ["Horas contratadas brutas", "Horas disponibles efectivas", "Horas directas", "Horas indirectas totales", "Horas no asistenciales", "Horas indirectas elegibles", "Brecha de demanda (horas)", "Cobertura de demanda"],
        "Basal": [_hours(base[k]) for k in ["contract_hours", "available_hours", "direct_hours", "indirect_hours", "nonclinical_hours"]] + ["No disponible"] * 3,
        "Simulado": ["No disponible"] * 8,
        "Motivo": ["Salida mensual validada" if has_hours else "Salida mensual no disponible o no validada"] * 5 + ["Sin regla de elegibilidad", "Sin demanda válida en horas", "Sin denominador de demanda"],
    }), hide_index=True, use_container_width=True)
    st.subheader("Resumen del impacto")
    status = "verificada en la línea base" if has_hours else "no verificable sin salida mensual validada"
    st.markdown(f'<div class="ribbon">Sin ajuste aplicado · Conservación de horas disponibles: {status} · Sin cambios en archivos oficiales</div>', unsafe_allow_html=True)
    if base.get("monthly_detail"):
        with st.expander("Desglose mensual por profesional · horas y procedencia contractual"):
            st.dataframe(pd.DataFrame(base["monthly_detail"]), hide_index=True, use_container_width=True)
            st.caption("Misma entrada que el cálculo oficial: el importador no transmite ausencias ni asignaciones especiales. Horas efectivas según ese payload; no acredita ausencia real igual a cero. Precisión íntegra en CSV; presentación en horas con decimales.")
    # Guardia independiente de los controles visuales y de posibles estados previos.
    validate_transfer(scenario["transfer_hours"])
    with st.expander("Trazabilidad de datos, fórmulas y requisitos pendientes"):
        st.write("Fuente: data/output/planificacion_calculada.csv, filtrada por instituto, especialidad y cargo. No se ejecuta el motor.")
        column = f"Ate_Dir_{PERIODS[period]}" if PERIODS[period] else "Atencion_Anual_Directa"
        st.code(f"Atenciones directas basales = suma({column})\nD_sim = D_base + Δ\nI_sim = I_base − Δ\nH_disponibles = D + I + N\nH_brutas = jornada_semanal × semanas_base\n0 ≤ Δ ≤ horas indirectas elegibles verificadas")
        st.caption("Las transferencias siguen sin habilitarse. La validación de horas basales no autoriza reasignación. No se adopta el mínimo ilustrativo de 15% de Stitch.")
        st.write("El motor redondea atenciones y aplica factores grupales; multiplicar atenciones por minutos estándar no recupera las horas basales exactas. Horas_Semanales_Prom es un promedio anual redondeado, no horas mensuales contratadas.")
        st.write("Para habilitar: exportación trazable de horas por período y profesional, clasificación de horas indirectas elegibles y límites aprobados. Para brechas y cobertura: demanda validada en las mismas unidades, período y filtros.")
        st.code("Brecha = demanda_h − horas_directas\nCobertura = horas_directas / demanda_h (solo con demanda_h > 0)")


def _format(value):
    return f"{value:,.0f}".replace(",", ".") if value is not None else "No disponible"


def _hours(value):
    return f"{value:,.2f} h" if value is not None else "No disponible"
