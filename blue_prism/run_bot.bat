@echo off
chcp 65001 > nul
cd /d "C:\Users\nicol\OneDrive\Escritorio\Proyecto Botathon"
echo ========================================================
echo   BOT BLUE PRISM - TELETÓN 2026 "CADA HORA CUENTA"
echo ========================================================
python src/process_incoming_file.py
echo ========================================================
