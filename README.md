# Teletón — Planificación Asistencial 2026 ("Cada hora cuenta")
**Desafío Botathon 2026 — Modelo Híbrido: RPA Blue Prism + Motor Python + Dashboard Streamlit**

Este repositorio contiene la solución completa desarrollada para automatizar y reemplazar el Excel de planificación de capacidad técnica asistencial de los **15 Institutos Teletón de Chile**, con cumplimiento estricto de las reglas de negocio 2026 y la reducción legal de jornada de 44h a 42h a partir de mayo de 2026.

---

## 🚀 Arquitectura del Proyecto

```
-teleton-cada-hora-cuenta/
├── blue_prism/                  # Artefactos y procesos para Blue Prism v7.5
│   ├── Teleton_Ingesta_BUK_y_Recalculo.xml   # Proceso importable en Process Studio
│   └── run_bot.bat                          # Ejecutable de orquestación
├── data/
│   ├── raw/                     # Excels base originales (BUK y Planificación)
│   ├── input_buk/               # Carpeta vigilada por Blue Prism (nuevos reportes)
│   ├── parameters/              # Reglas desacopladas en JSON (editables sin tocar código)
│   │   ├── distribucion_cargos.json     # % Dir, Ind, NAS y minutos estándar
│   │   ├── asignaciones_catalogo.json   # Asignaciones especiales y horas
│   │   ├── factores_grupales.json       # Factores de atención grupal
│   │   └── calendario_base_2026.json    # Semanas hábiles por mes 2026
│   ├── output/                  # Resultados calculados y trazabilidad
│   │   ├── planificacion_calculada.csv  # Base 462 profesionales calculados
│   │   ├── resumen_nacional.csv         # Agregación por instituto
│   │   └── trazabilidad.json            # Bitácora de auditoría RPA
│   └── archive/                 # Archivos históricos procesados
├── src/
│   ├── app.py                   # Dashboard Web interactivo en Streamlit
│   ├── engine.py                # Motor vectorial de cálculo matemático Teletón 2026
│   ├── extract_parameters.py    # Extractor de reglas desde Excel hacia JSON
│   └── process_incoming_file.py # Pipeline de ingesta, validación y archivo
├── requirements.txt             # Dependencias del proyecto
└── README.md
```

---

## 🛠️ Cómo ejecutar el proyecto (Para el compañero de equipo)

### 1. Clonar e instalar dependencias
Asegurarse de tener Python 3.10 o superior instalado:
```bash
pip install -r requirements.txt
```

### 2. Levantar el Dashboard Ejecutivo
Para abrir la interfaz web con los KPIs, filtros multinivel y editor de parámetros:
```bash
streamlit run src/app.py
```
Se abrirá automáticamente en tu navegador en `http://localhost:8501`.

### 3. Ejecutar o Probar el Motor de Cálculo
Si deseas recalcular la dotación completa (462 profesionales en <2 segundos):
```bash
python src/engine.py
```

### 4. Simular la Ingesta de Blue Prism
Para probar la vigilancia automática de la carpeta de entrada:
```bash
python src/process_incoming_file.py
```

---

## 💡 Reglas de Negocio Implementadas

1. **Transición 44h a 42h:** A partir de mayo (mes 5), los contratos de 44 hrs bajan automáticamente a 42 hrs.
2. **Tramos de Jornada:** $\ge 40\text{ h}$, $22\text{ a }40\text{ h}$, y $< 22\text{ h}$, asignando los porcentajes correspondientes de atención Directa, Indirecta y No Asistencial (NAS).
3. **Tope de Asignaciones:** Máximo 2 asignaciones para profesionales con $>30\text{ h/sem}$.
4. **Atención Grupal:** Ponderación con ratios de pacientes diferenciados para Santiago/Concepción vs otras sedes.
5. **Indicadores:**
   * **% FOJA:** Horas Directas Disponibles / Horas Contratadas.
   * **Meta de Gestión:** 90% de las atenciones resultantes del cálculo.
