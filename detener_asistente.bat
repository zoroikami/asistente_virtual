@echo off
chcp 65001 > nul
title Detener Yize — Asistente y Servidor Móvil
color 0C

echo =======================================================
echo          DETENIENDO YIZE (ASISTENTE Y OVERLAY 3D)
echo =======================================================
echo.

taskkill /F /FI "WINDOWTITLE eq Yize*" 2>nul
taskkill /F /IM electron.exe 2>nul
echo [OK] El asistente, overlay 3D y servidor móvil han sido detenidos.

echo.
pause
