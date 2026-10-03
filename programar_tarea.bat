@echo off
REM ============================================================
REM Programa el agente ASFI para ejecutarse automaticamente
REM al iniciar sesion en Windows (Task Scheduler).
REM El instalador Inno Setup configura esto automaticamente.
REM ============================================================

echo.
echo  Programando ASFI Monitor en el Programador de Tareas...
echo.

set "SCRIPT_DIR=%~dp0"
set "TAREA_NOMBRE=ASFI_SCIP_Monitor"
set "AGENTE=%SCRIPT_DIR%dist\ASFI_Monitor_Agent\ASFI_Monitor_Agent.exe"
set "COMANDO=\"%AGENTE%\""

if not exist "%AGENTE%" (
    set "COMANDO=pythonw \"%SCRIPT_DIR%asfi_monitor_agent.py\""
)

REM Eliminar tarea anterior si existe
schtasks /delete /tn "%TAREA_NOMBRE%" /f >nul 2>&1

REM Crear tarea al iniciar sesion con dos minutos de espera
schtasks /create ^
    /tn "%TAREA_NOMBRE%" ^
    /tr "%COMANDO%" ^
    /sc ONLOGON ^
    /delay 0002:00 ^
    /ru "%USERNAME%" ^
    /f

if errorlevel 1 (
    echo [ERROR] No se pudo crear la tarea programada.
    echo         Asegurarse de ejecutar como Administrador.
    pause
    exit /b 1
)

echo [OK] Tarea "%TAREA_NOMBRE%" creada exitosamente.
echo.
echo La tarea se ejecutara automaticamente al iniciar sesion.
echo Para administrar la tarea: Programador de Tareas ^> Biblioteca ^> %TAREA_NOMBRE%
echo Para eliminarla: schtasks /delete /tn "%TAREA_NOMBRE%" /f
echo.
pause
