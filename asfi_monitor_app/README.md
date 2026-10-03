# ASFI Monitor App

El paquete contiene la implementacion principal del monitor. Los archivos
Python de la raiz se mantienen como fachadas para no romper comandos, tareas
programadas ni imports existentes.

## Capas

- `application`: casos de uso, revision completa, CLI, agente y scheduler.
- `application/runner.py`: ciclo serializado compartido por la GUI, el agente y la CLI.
- `domain`: analisis de estados y reconciliacion de reintentos.
- `integrations`: cliente Playwright SCIP y notificaciones Windows.
- `storage`: SQLite, esquema, migraciones, credenciales y estado JSON.
- `ui`: dashboard Tkinter, dialogos, PDF y formateadores.
- `tools`: herramientas manuales de depuracion y diagnostico.

## Compatibilidad

Los puntos de entrada publicos siguen siendo:

```powershell
python asfi_monitor.py
python gestionar_reportes.py
python debug_reportes.py
python probar_notificaciones.py
```

## Instalacion de Windows

Para preparar una instalacion:

```powershell
.\build_windows.ps1
```

Despues se compila `asfi_monitor.iss` con Inno Setup. El instalador crea una
aplicacion GUI, un agente silencioso que inicia al iniciar sesion del usuario y
un ejecutable CLI. La base, el estado y los logs instalados se guardan en
`%LOCALAPPDATA%\ASFI Monitor`; los recursos semilla permanecen junto al programa.
