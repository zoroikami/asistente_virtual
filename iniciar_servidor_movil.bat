@echo off
chcp 65001 >nul
title Yize — Servidor Móvil para Celular
color 0D

cd /d "%~dp0"

echo ======================================================================
echo          ✦  YIZE — SERVIDOR MÓVIL Y CONTROL REMOTO DESDE EL CELULAR  ✦
echo ======================================================================
echo.
echo   ¿Cómo vas a conectarte desde tu celular?
echo.
echo   [1] En mi casa (Misma red Wi-Fi que la PC) — Super rápido y directo
echo   [2] Desde fuera de casa (Con datos móviles 4G/5G usando túnel HTTPS)
echo.
echo ======================================================================
echo.

set "modo=1"
set /p modo="Elige una opción [1 o 2, Enter para 1]: "

if "%modo%"=="2" (
    cls
    echo ======================================================================
    echo   INICIANDO MODO REMOTO (TÚNEL HTTPS CLOUDFLARE PARA 4G/5G)
    echo ======================================================================
    echo [*] Generando enlace público seguro...
    python mobile_server.py --tunnel
) else (
    cls
    echo ======================================================================
    echo   INICIANDO MODO LOCAL (WI-FI DE CASA)
    echo ======================================================================
    python mobile_server.py
)

pause