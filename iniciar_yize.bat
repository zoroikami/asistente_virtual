@echo off
chcp 65001 >nul
title Yize 3D — Asistente Virtual de Escritorio
color 0D

cd /d "%~dp0"

echo ======================================================================
echo          ✦  YIZE 3D — ASISTENTE VIRTUAL Y VTUBER DE ESCRITORIO  ✦
echo ======================================================================
echo.

:: 1. Iniciar o verificar Overlay 3D de Electron en segundo plano
tasklist /FI "IMAGENAME eq electron.exe" 2>NUL | findstr /i "electron.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    echo [✓] Yize 3D Overlay ya está activa en tu escritorio.
) else (
    echo [*] Cargando a Yize 3D sobre tu pantalla...
    start "" "%~dp0yize_overlay\node_modules\electron\dist\electron.exe" "%~dp0yize_overlay\electron-main.cjs"
    ping -n 3 127.0.0.1 >nul
    echo [✓] Yize 3D cargada correctamente.
)

echo.
echo ======================================================================
echo   ¿Cómo prefieres interactuar con Yize?
echo.
echo   [1] Modo Texto / Consola (Escribir en teclado — Recomendado)
echo   [2] Modo Voz (Hablarle por micrófono continuamente)
echo   [3] Servidor Móvil (Controlar desde tu celular con código QR)
echo   [4] Iniciar Todo (Asistente en PC + Servidor Móvil para Celular)
echo ======================================================================
echo.

set "modo=1"
set /p modo="Presiona ENTER para iniciar (o escribe 1, 2, 3, 4): "

if "%modo%"=="4" (
    cls
    echo [*] Iniciando Servidor Móvil en segundo plano...
    start "Yize Servidor Movil" cmd /k "chcp 65001 >nul && python mobile_server.py"
    ping -n 3 127.0.0.1 >nul
    echo ======================================================================
    echo   INICIANDO MODO TEXTO EN PC — Escribe tus preguntas u órdenes
    echo ======================================================================
    python main.py --texto
) else if "%modo%"=="3" (
    cls
    echo ======================================================================
    echo   INICIANDO SERVIDOR MÓVIL — Escanea el QR con tu teléfono
    echo ======================================================================
    python mobile_server.py
) else if "%modo%"=="2" (
    cls
    echo ======================================================================
    echo   INICIANDO MODO VOZ — Háblale por micrófono a Yize
    echo ======================================================================
    python main.py
) else (
    cls
    echo ======================================================================
    echo   INICIANDO MODO TEXTO — Escribe tus preguntas u órdenes
    echo ======================================================================
    python main.py --texto
)

pause