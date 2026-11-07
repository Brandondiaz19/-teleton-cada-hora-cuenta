"""
Script de Procesamiento e Ingesta para Blue Prism RPA.
Es invocado por el bot de Blue Prism cuando detecta un nuevo archivo BUK en data/input_buk/.
Realiza:
1. Validación de integridad del archivo Excel.
2. Detección de novedades (Altas, Bajas, Cambios de Jornada).
3. Disparo del motor de cálculo de capacidad.
4. Registro de auditoría y trazabilidad en data/output/trazabilidad.json.
5. Archivado del reporte procesado en data/archive/.
"""

import os
import sys
import shutil
import glob
import json
from datetime import datetime
import pandas as pd
import openpyxl

from engine import TeletonCapacityEngine

INPUT_DIR = "data/input_buk"
ARCHIVE_DIR = "data/archive"
OUTPUT_DIR = "data/output"
AUDIT_FILE = os.path.join(OUTPUT_DIR, "trazabilidad.json")

def log_audit_event(evento, archivo, num_filas, num_prof, estado, detalles=""):
    """Registra eventos de auditoría para trazabilidad de Blue Prism."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    historial = []
    if os.path.exists(AUDIT_FILE):
        try:
            with open(AUDIT_FILE, "r", encoding="utf-8") as f:
                historial = json.load(f)
        except Exception:
            historial = []
            
    nuevo_evento = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Evento": evento,
        "Archivo": os.path.basename(archivo),
        "Registros": num_filas,
        "Profesionales": num_prof,
        "Estado": estado,
        "Detalles": detalles,
        "Agente": "Blue Prism Bot v7.5.1"
    }
    historial.insert(0, nuevo_evento)
    
    with open(AUDIT_FILE, "w", encoding="utf-8") as f:
        json.dump(historial, f, indent=2, ensure_ascii=False)
        
    print(f"[AUDITORIA BP] Evento registrado: {evento} - {estado}")

def validate_excel_integrity(file_path):
    """Valida que el archivo exista, no esté vacío y contenga las columnas obligatorias."""
    if not os.path.exists(file_path):
        return False, "El archivo no existe."
    if os.path.getsize(file_path) == 0:
        return False, "El archivo está vacío (0 bytes)."
        
    try:
        wb = openpyxl.load_workbook(file_path, read_only=True)
        ws = wb.worksheets[0]
        # Validar fila 2 (cabeceras de BUK)
        headers = [ws.cell(2, c).value for c in range(1, min(25, ws.max_column + 1))]
        required_cols = ["IT", "PersonaId", "Horas Semanales", "Cargo"]
        missing = [rc for rc in required_cols if not any(rc.lower() in str(h).lower() for h in headers if h)]
        
        if missing:
            return False, f"Faltan columnas requeridas en el reporte BUK: {missing}"
        return True, "Validación exitosa."
    except Exception as e:
        return False, f"Error al abrir Excel: {str(e)}"

def run_ingestion_pipeline():
    """Flujo principal ejecutado por Blue Prism."""
    print("=== INICIANDO TAREA ORQUESTADA POR BLUE PRISM ===")
    
    # 1. Buscar archivos .xlsx en la carpeta vigilada
    archivos_pendientes = glob.glob(os.path.join(INPUT_DIR, "*.xlsx"))
    
    if not archivos_pendientes:
        print(f"[INFO BP] No hay archivos pendientes en {INPUT_DIR}.")
        # Si la carpeta de entrada está vacía para pruebas, informar
        return {
            "status": "NO_FILES",
            "message": f"Carpeta vigilada {INPUT_DIR} sin archivos nuevos."
        }
        
    archivo_a_procesar = archivos_pendientes[0]
    nombre_archivo = os.path.basename(archivo_a_procesar)
    print(f"[BOT BP] Archivo detectado: {nombre_archivo}")
    
    # 2. Validar Integridad
    es_valido, msg_val = validate_excel_integrity(archivo_a_procesar)
    if not es_valido:
        log_audit_event("Error de Validación BUK", archivo_a_procesar, 0, 0, "Rechazado", msg_val)
        print(f"[ERROR BP] Archivo no superó las reglas de integridad: {msg_val}")
        return {"status": "ERROR_VALIDATION", "message": msg_val}
        
    print(f"[BOT BP] Archivo validado correctamente: {msg_val}")
    
    # 3. Disparar Motor de Cálculo
    try:
        engine = TeletonCapacityEngine()
        df_result = engine.process_buk_file(archivo_a_procesar)
        total_prof = len(df_result)
        
        # 4. Registrar Auditoría
        log_audit_event(
            evento="Recálculo Exitoso de Capacidad",
            archivo=archivo_a_procesar,
            num_filas=total_prof * 12,
            num_prof=total_prof,
            estado="Completado Exitoso",
            detalles=f"Metas 2026 recalculadas para {total_prof} profesionales. Dashboard actualizado."
        )
        
        # 5. Archivar archivo procesado
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        destino_archivo = os.path.join(ARCHIVE_DIR, f"{timestamp_str}_{nombre_archivo}")
        shutil.move(archivo_a_procesar, destino_archivo)
        print(f"[BOT BP] Archivo archivado en: {destino_archivo}")
        
        print("=== PROCESO BLUE PRISM COMPLETADO CON ÉXITO ===")
        return {
            "status": "SUCCESS",
            "profesionales": total_prof,
            "archivo_procesado": nombre_archivo
        }
        
    except Exception as e:
        error_msg = str(e)
        log_audit_event("Fallo en Motor de Cálculo", archivo_a_procesar, 0, 0, "Error de Ejecución", error_msg)
        print(f"[ERROR BP] Error durante el recálculo: {error_msg}")
        return {"status": "ERROR_ENGINE", "message": error_msg}

if __name__ == "__main__":
    run_ingestion_pipeline()
