"""CAPACIDAD 360 — visualización de planificación existente, sin escrituras."""

import base64
import json
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
import altair as alt
from decision_view import render_decisions

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
st.set_page_config(page_title="CAPACIDAD 360 · Teletón", page_icon="❤️", layout="wide")
st.markdown(f"<style>{Path(__file__).with_name('app.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        st.warning(f"No se pudo leer {path.name}: {exc}")
        return None


def metric_card(label, value, note):
    symbols = {"Dotación asistencial": "people", "Atenciones planificadas": "calendar", "Meta de gestión": "target", "FOJA promedio": "chart"}
    st.markdown(
        f'<div class="metric-card"><div class="metric-heading"><div class="eyebrow">{escape(label)}</div><span class="kpi-icon">{ui_icon(symbols[label])}</span></div>'
        f'<div class="metric-value">{escape(value)}</div><div class="muted">{escape(note)}</div></div>',
        unsafe_allow_html=True,
    )


def ui_icon(name):
    paths = {"people": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.87M15 3.13a4 4 0 0 1 0 7.75"/><circle cx="9" cy="7" r="4"/>',
             "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18m-12 5h6"/>',
             "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
             "chart": '<path d="M4 3v17h17M8 15l4-4 4 2 5-7"/>'}
    return f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths[name]}</svg>'


def chart_style(chart):
    return chart.properties(height=245).configure_view(strokeWidth=0).configure_axis(
        labelFont="Segoe UI", titleFont="Segoe UI", labelFontSize=11,
        labelColor="#64748b", titleColor="#64748b", domain=False,
        gridColor="#edf1f6", tickSize=0, labelPadding=8,
    ).configure_legend(labelFont="Segoe UI", labelFontSize=11, labelColor="#475569", title=None, orient="top", symbolType="circle").configure(background="transparent")


def number(value):
    return f"{value:,.0f}".replace(",", ".")


def table(frame):
    st.dataframe(frame, hide_index=True, use_container_width=True,
                 column_config={"FOJA": st.column_config.NumberColumn("FOJA", format="%.3f"),
                                "Dotacion_Profesionales": "Profesionales", "Horas_Semanales_Prom": st.column_config.NumberColumn("Jornada semanal · h", format="%.1f"),
                                "Atencion_Anual_Directa": "Atenciones directas", "Atencion_Anual_Indirecta": "Atenciones indirectas",
                                "Total_Atenciones": "Atenciones totales", "Meta_Gestion_90": "Meta de gestión · 90%"})


with st.sidebar:
    logo = base64.b64encode(Path(__file__).with_name("assets").joinpath("teleton-chile-logo.svg").read_bytes()).decode("ascii")
    st.markdown(f'<div class="brand-lockup"><div class="logo-slot"><img src="data:image/svg+xml;base64,{logo}" alt="Teletón Chile" /></div><div><div class="brand">CAPACIDAD <b>360</b></div><div class="sidebar-caption">CADA HORA CUENTA</div></div></div><div class="sidebar-edition">BOTATHON 2026 · PLANIFICACIÓN ASISTENCIAL</div>', unsafe_allow_html=True)
    st.divider()
    page = st.radio("Navegación", ["Centro de control", "Planificación profesional", "Centro de decisiones", "Automatización", "Reglas de planificación", "Reportes"], label_visibility="collapsed", key="main_navigation")
    st.divider()
    st.caption("PLANIFICACIÓN ASISTENCIAL · 2026")
    st.caption("Fuente: archivos locales BUK / planificación calculada. Sin conexión al robot en vivo.")

try:
    df = pd.read_csv(DATA / "output/planificacion_calculada.csv")
except (OSError, ValueError) as exc:
    st.error(f"No se puede cargar la planificación calculada: {exc}")
    st.stop()

required = {"PersonaId", "Instituto", "Cargo", "Especialidad", "Horas_Semanales_Prom", "FOJA", "Atencion_Anual_Directa", "Atencion_Anual_Indirecta", "Total_Atenciones", "Meta_Gestion_90"}
if missing := required.difference(df.columns):
    st.error(f"Faltan columnas en la planificación: {', '.join(sorted(missing))}")
    st.stop()

titles = {"Centro de control": "Centro de Control Nacional", "Planificación profesional": "Planificación Profesional", "Centro de decisiones": "Centro de Decisiones", "Automatización": "Automatización y Trazabilidad", "Reglas de planificación": "Reglas de Planificación", "Reportes": "Reportes"}
with st.container(key="dashboard_header"):
    st.markdown('<div class="topbar"><div class="institution">TELETÓN CHILE <span>CAPACIDAD 360</span></div><div class="source-label">Planificación 2026 · Fuente local</div></div>', unsafe_allow_html=True)
    st.title(titles[page])
    st.markdown('<p class="page-subtitle">Cada hora cuenta. <span>Planificación de capacidad asistencial para la red Teletón.</span></p>', unsafe_allow_html=True)

with st.container(border=True, key="dashboard_filters"):
    filters = st.columns(3)
    filtered = df.copy()
    for col, field, label in zip(filters, ["Instituto", "Especialidad", "Cargo"], ["Instituto", "Especialidad", "Cargo"]):
        options = sorted(filtered[field].dropna().astype(str).unique())
        selected = col.selectbox(label, ["Todos"] + options, key=f"filter_{field}")
        if selected != "Todos":
            filtered = filtered[filtered[field].astype(str) == selected]

if filtered.empty:
    st.info("No hay profesionales para esta combinación de filtros.")
    st.stop()

summary = filtered.groupby("Instituto", as_index=False).agg(
    Dotacion_Profesionales=("PersonaId", "size"),
    Horas_Semanales_Prom=("Horas_Semanales_Prom", "sum"),
    Atencion_Anual_Directa=("Atencion_Anual_Directa", "sum"),
    Atencion_Anual_Indirecta=("Atencion_Anual_Indirecta", "sum"),
    Total_Atenciones=("Total_Atenciones", "sum"),
    Meta_Gestion_90=("Meta_Gestion_90", "sum"), FOJA=("FOJA", "mean"))

if page == "Centro de control":
    with st.container(border=True, key="planning_notice"):
        st.markdown('<div class="source-note"><span class="source-note-label">FUENTE LOCAL</span> Planificación anual calculada · No representa actividad ejecutada, demanda clínica ni supervisión en tiempo real.</div>', unsafe_allow_html=True)
    cards = st.container(key="dashboard_kpis").columns(4)
    for col, args in zip(cards, [
        ("Dotación asistencial", number(len(filtered)), "registros profesionales en el alcance"),
        ("Atenciones planificadas", number(filtered.Total_Atenciones.sum()), "proyección anual · directas e indirectas"),
        ("Meta de gestión", number(filtered.Meta_Gestion_90.sum()), "meta anual al 90% · calculada por profesional"),
        ("FOJA promedio", f"{filtered.FOJA.mean():.1%}", "media simple del factor por profesional"),
    ]):
        with col:
            metric_card(*args)
    st.markdown(f'<div class="ribbon">{len(summary)} institutos en el alcance &nbsp; · &nbsp; {number(filtered.Horas_Semanales_Prom.sum())} horas semanales promedio acumuladas</div>', unsafe_allow_html=True)
    with st.container(key="priority_panel"):
        st.markdown('<div class="section-kicker">CENTRO DE DECISIONES <span>REVISIÓN COMPARATIVA</span></div>', unsafe_allow_html=True)
        st.subheader("Dónde actuar ahora")
        st.caption("Tres institutos con menor FOJA medio dentro del filtro. Puntos de revisión, no una clasificación de riesgo ni una brecha de demanda.")
        priorities = summary.nsmallest(3, "FOJA")
        for rank, (col, (_, row)) in enumerate(zip(st.columns(3), priorities.iterrows()), 1):
            with col:
                st.markdown(f'<article class="priority-card"><div class="priority-top"><span class="priority-rank">{rank:02d}</span><span class="eyebrow">REVISIÓN DE PLANIFICACIÓN</span>{ui_icon("target")}</div><h3>Instituto {escape(str(row.Instituto))}</h3><div class="priority-foja"><span>FOJA medio</span><strong>{row.FOJA:.1%}</strong></div><div class="foja-track" aria-hidden="true"><span style="width:{max(0, min(100, row.FOJA * 100))}%"></span></div><div class="priority-facts"><div><strong>{number(row.Dotacion_Profesionales)}</strong><span>profesionales</span></div><div><strong>{number(row.Total_Atenciones)}</strong><span>atenciones / año</span></div></div><p>Revisar distribución de jornada y detalle profesional antes de decidir ajustes.</p></article>', unsafe_allow_html=True)
    with st.container(key="summary_header"):
        st.subheader("Resumen nacional y comparativa por instituto")
        st.caption("Todos los gráficos y tablas respetan los filtros seleccionados.")
    left, right = st.columns([3, 2])
    with left, st.container(border=True, key="attentions_chart"):
        st.markdown("**Atenciones anuales planificadas**")
        chart_data = summary[["Instituto", "Atencion_Anual_Directa", "Atencion_Anual_Indirecta"]].rename(columns={"Atencion_Anual_Directa": "Directas", "Atencion_Anual_Indirecta": "Indirectas"}).melt("Instituto", var_name="Tipo", value_name="Atenciones")
        st.altair_chart(chart_style(alt.Chart(chart_data).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, size=24).encode(
            x=alt.X("Instituto:N", title=None, axis=alt.Axis(labelAngle=0, grid=False)), y=alt.Y("Atenciones:Q", title=None, axis=alt.Axis(format="~s")),
            color=alt.Color("Tipo:N", scale=alt.Scale(domain=["Directas", "Indirectas"], range=["#29415f", "#c93450"]), legend=alt.Legend(title=None, orient="top", direction="horizontal")),
            tooltip=["Instituto:N", "Tipo:N", alt.Tooltip("Atenciones:Q", format=",")],
        )), use_container_width=True)
    with right, st.container(border=True, key="foja_chart"):
        st.markdown("**FOJA medio por instituto (%)**")
        foja_data = summary[["Instituto", "FOJA"]].assign(FOJA=lambda frame: frame.FOJA * 100)
        st.altair_chart(chart_style(alt.Chart(foja_data).mark_bar(color="#c93450", cornerRadiusTopLeft=3, cornerRadiusTopRight=3, size=18).encode(
            x=alt.X("Instituto:N", title=None, axis=alt.Axis(labelAngle=0, grid=False)),
            y=alt.Y("FOJA:Q", title=None, scale=alt.Scale(domain=[0, 100]), axis=alt.Axis(labelExpr="datum.value + '%'")),
            tooltip=["Instituto:N", alt.Tooltip("FOJA:Q", format=".1f", title="FOJA (%)")],
        )), use_container_width=True)
    with st.container(key="institutes_table"):
        st.markdown("### Resumen de institutos")
        table(summary)
        st.caption("Consolidado de los registros filtrados. Horas_Semanales_Prom es la suma de promedios semanales; FOJA es una media simple.")

elif page == "Planificación profesional":
    st.subheader("Detalle por profesional")
    st.caption(f"{number(len(filtered))} registros · Identificación por PersonaId · Proyección anual 2026")
    table(filtered[["PersonaId", "Instituto", "Cargo", "Especialidad", "Horas_Semanales_Prom", "FOJA", "Atencion_Anual_Directa", "Total_Atenciones", "Meta_Gestion_90"]])
    with st.expander("Desglose mensual de atenciones directas", expanded=True):
        months = [f"Ate_Dir_{m}" for m in ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]]
        table(filtered[["PersonaId", "Instituto", "Cargo"] + [m for m in months if m in filtered]])

elif page == "Centro de decisiones":
    render_decisions(filtered, (DATA / "output/planificacion_calculada.csv").read_bytes())

elif page == "Automatización":
    st.info("Historial leído del archivo local. El dashboard no verifica el estado actual de Blue Prism ni certifica la ejecución del robot.")
    with st.container(border=True):
        st.subheader("Flujo de archivos")
        st.write("Recepción BUK → validación → cálculo de capacidad → registro de trazabilidad → archivo")
        st.caption("Entrada configurada en el script: data/input_buk/ · Historial: data/output/trazabilidad.json")
    st.subheader("Registro de trazabilidad disponible")
    audit_path = DATA / "output/trazabilidad.json"
    if audit_path.exists():
        events = read_json(audit_path)
        if isinstance(events, list) and all(isinstance(event, dict) for event in events):
            if events:
                table(pd.DataFrame(events))
            else:
                st.info("El archivo no contiene eventos.")
        elif events is not None:
            st.warning("Formato de trazabilidad no compatible: se esperaba una lista de eventos.")
    else:
        st.info("No hay archivo de trazabilidad disponible.")
    st.caption("El historial es global; los filtros de profesionales no se aplican a estos eventos.")

elif page == "Reglas de planificación":
    st.info("Consulta de parámetros en modo lectura. Esta fase no guarda cambios ni recalcula resultados.")
    for filename, label in [("distribucion_cargos.json", "Distribución por cargo"), ("factores_grupales.json", "Factores de atención grupal"), ("calendario_base_2026.json", "Calendario base 2026"), ("asignaciones_catalogo.json", "Catálogo de asignaciones")]:
        with st.expander(label):
            content = read_json(DATA / "parameters" / filename)
            if content is not None:
                st.json(content)

elif page == "Reportes":
    st.subheader("Exportar el alcance seleccionado")
    st.caption("Descargas de los datos existentes; no ejecutan el motor ni escriben archivos de resultados en el proyecto.")
    st.download_button("Descargar detalle profesional · CSV", filtered.to_csv(index=False).encode("utf-8-sig"), "capacidad360_profesionales.csv", "text/csv")
    st.download_button("Descargar resumen por instituto · CSV", summary.to_csv(index=False).encode("utf-8-sig"), "capacidad360_institutos.csv", "text/csv")
    with st.expander("Resumen nacional existente en disco"):
        st.caption("Archivo original global, sin aplicar filtros.")
        try:
            table(pd.read_csv(DATA / "output/resumen_nacional.csv"))
        except (OSError, ValueError) as exc:
            st.warning(f"Resumen no disponible: {exc}")

st.divider()
st.caption("CAPACIDAD 360 · Teletón Botathon 2026 · Cada hora cuenta · Planificación calculada, no actividad ejecutada.")
