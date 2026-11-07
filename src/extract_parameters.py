"""
Extractor de Parámetros desde el Excel de Referencia de Teletón.
Desacopla las reglas de negocio a archivos JSON editables en data/parameters/.
"""
import json
import os
import openpyxl

def extract_parameters():
    excel_path = "data/raw/Nac - Planificacion Asistencial x mes.xlsx"
    os.makedirs("data/parameters", exist_ok=True)
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    
    # 1. Factores Grupales (de la primera hoja 'Parámetros')
    ws_param = wb.worksheets[0]
    factores_grupales = {}
    for r in range(4, 9):
        esp = ws_param.cell(r, 6).value
        pct = float(ws_param.cell(r, 7).value or 0)
        pac_san_con = float(ws_param.cell(r, 8).value or 0)
        pac_otros = float(ws_param.cell(r, 9).value or 0)
        if esp:
            factores_grupales[esp] = {
                "pct_grupal": pct,
                "pacientes_san_con": pac_san_con,
                "pacientes_otros": pac_otros
            }
            
    with open("data/parameters/factores_grupales.json", "w", encoding="utf-8") as f:
        json.dump(factores_grupales, f, indent=2, ensure_ascii=False)
    print("[OK] Factores grupales exportados:", len(factores_grupales))
    
    # 2. Asignaciones Especiales Catálogo (de 'Distribucion_NAC' cols 18-19)
    ws_dist = wb["Distribucion_NAC"]
    asignaciones = {}
    for r in range(7, 36):
        tipo = ws_dist.cell(r, 18).value
        horas = ws_dist.cell(r, 19).value
        if tipo:
            tipo_clean = str(tipo).strip()
            hrs_val = float(horas) if horas is not None and str(horas).strip() != '' else 0.0
            asignaciones[tipo_clean] = hrs_val
            
    with open("data/parameters/asignaciones_catalogo.json", "w", encoding="utf-8") as f:
        json.dump(asignaciones, f, indent=2, ensure_ascii=False)
    print("[OK] Catálogo de Asignaciones exportado:", len(asignaciones))
    
    # 3. Distribución por Cargo y Tramo (de 'Distribucion_NAC' cols 1-14)
    cargos = {}
    for r in range(7, ws_dist.max_row + 1):
        cargo = ws_dist.cell(r, 2).value
        # Si la fila no tiene cargo, o es un encabezado intermedio, ignorar
        if not cargo or "cargo" in str(cargo).lower() or "matriz" in str(cargo).lower():
            continue
            
        esp = ws_dist.cell(r, 1).value
        unidad = ws_dist.cell(r, 3).value
        std_dir = ws_dist.cell(r, 4).value
        std_ind = ws_dist.cell(r, 5).value
        
        # Validar que los minutos sean números
        try:
            min_dir = int(float(std_dir)) if std_dir is not None else 40
        except (ValueError, TypeError):
            min_dir = 40
            
        try:
            min_ind = int(float(std_ind)) if std_ind is not None else 30
        except (ValueError, TypeError):
            min_ind = 30
            
        def safe_float(cell_val):
            try:
                return float(cell_val) if cell_val is not None else 0.0
            except (ValueError, TypeError):
                return 0.0
                
        cargo_clean = str(cargo).strip()
        cargos[cargo_clean] = {
            "especialidad": str(esp).strip() if esp else "",
            "unidad": str(unidad).strip() if unidad else "",
            "minutos_std_directa": min_dir,
            "minutos_std_indirecta": min_ind,
            "tramo_gte_40": {
                "pct_dir": safe_float(ws_dist.cell(r, 6).value),
                "pct_ind": safe_float(ws_dist.cell(r, 7).value),
                "pct_nas": safe_float(ws_dist.cell(r, 8).value)
            },
            "tramo_22_40": {
                "pct_dir": safe_float(ws_dist.cell(r, 9).value),
                "pct_ind": safe_float(ws_dist.cell(r, 10).value),
                "pct_nas": safe_float(ws_dist.cell(r, 11).value)
            },
            "tramo_lt_22": {
                "pct_dir": safe_float(ws_dist.cell(r, 12).value),
                "pct_ind": safe_float(ws_dist.cell(r, 13).value),
                "pct_nas": safe_float(ws_dist.cell(r, 14).value)
            }
        }
            
    with open("data/parameters/distribucion_cargos.json", "w", encoding="utf-8") as f:
        json.dump(cargos, f, indent=2, ensure_ascii=False)
    print("[OK] Matriz de Cargos exportada:", len(cargos))
    
    # 4. Calendario Base de Semanas Hábiles por Mes 2026
    calendario_meses = {
        "ene": 4.2, "feb": 4.0, "mar": 4.4, "abr": 4.2,
        "may": 3.8, "jun": 4.2, "jul": 4.4, "ago": 4.2,
        "sep": 4.2, "oct": 4.2, "nov": 4.2, "dic": 4.2
    }
    with open("data/parameters/calendario_base_2026.json", "w", encoding="utf-8") as f:
        json.dump(calendario_meses, f, indent=2, ensure_ascii=False)
    print("[OK] Calendario base 2026 exportado (Total semanas:", sum(calendario_meses.values()), ")")

if __name__ == "__main__":
    extract_parameters()
