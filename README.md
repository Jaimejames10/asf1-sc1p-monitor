# ASFI Monitor

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-%E2%89%A51.40.0-green.svg)](https://playwright.dev/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011%20(64--bit)-lightgrey.svg)](https://www.microsoft.com/windows)
[![Database](https://img.shields.io/badge/Database-SQLite%203-orange.svg)](https://www.sqlite.org/)
[![Security](https://img.shields.io/badge/Security-Windows%20DPAPI-blueviolet.svg)](https://learn.microsoft.com/en-us/dotnet/standard/security/how-to-use-data-protection)

**ASFI Monitor** es una solución automatizada de escritorio y servicio en segundo plano diseñada para monitorear, validar y auditar el envío de reportes normativos a la plataforma estatal **ASFI / SCIP** (Autoridad de Supervisión del Sistema Financiero de Bolivia).

El sistema automatiza la autenticación y extracción de estados mediante Playwright, analiza las obligaciones según calendarios y feriados nacionales, alerta oportunamente ante fallos o retrasos mediante notificaciones nativas de Windows, y ofrece un panel de administración en Tkinter con generación de informes ejecutivos en PDF.

---

## 📋 Tabla de Contenidos

1. [Características Principales](#-características-principales)
2. [Arquitectura del Sistema](#-arquitectura-del-sistema)
3. [Estructura del Repositorio](#-estructura-del-repositorio)
4. [Requisitos del Entorno](#-requisitos-del-entorno)
5. [Instalación y Configuración Inicial](#-instalación-y-configuración-inicial)
6. [Guía de Uso](#-guía-de-uso)
   - [Panel Gráfico (GUI)](#panel-gráfico-gui)
   - [Monitoreo por Consola (CLI)](#monitoreo-por-consola-cli)
   - [Agente en Segundo Plano](#agente-en-segundo-plano)
7. [Motor de Reglas y Calendario Normativo](#-motor-de-reglas-y-calendario-normativo)
8. [Seguridad y Almacenamiento](#-seguridad-y-almacenamiento)
9. [Compilación y Empaquetado Windows](#-compilación-y-empaquetado-windows)
10. [Herramientas y Diagnóstico](#-herramientas-y-diagnóstico)
11. [Solución de Problemas Frecuentes](#-solución-de-problemas-frecuentes)

---

## 🚀 Características Principales

- 🤖 **Extracción Automatizada:** Conexión y navegación automatizada en SCIP mediante Playwright (Chromium headless o visible) con manejo de sesiones y reintentos.
- ⏱️ **Auditoría de Obligaciones Normativas:** Clasificación y control de reportes diarios, semanales y mensuales con soporte de plazos en días hábiles o calendario y horas límite configurables.
- 🇧🇴 **Gestión de Feriados Bolivianos:** Soporte nativo de feriados nacionales e inhábiles para cálculo exacto de vencimientos normativos.
- 🔔 **Notificaciones Nativas:** Alertas visuales de escritorio en tiempo real (Toast / Balloon de Windows) al detectar errores, rechazos o reportes pendientes.
- 📊 **Panel de Control Integral (GUI):** Dashboard visual desarrollado en Tkinter para ver métricas en tiempo real, filtrar historial, consultar logs y configurar reglas.
- 📄 **Informes Ejecutivos en PDF:** Generación y exportación de reportes resumidos listos para auditoría interna y gerencia.
- 🔒 **Almacenamiento Seguro:** Contraseñas y credenciales resguardadas mediante **Windows DPAPI** (Data Protection API) en base de datos SQLite local versionada.
- 🔄 **Bloqueo Serializado y Concurrencia:** Mecanismo de lock interproceso (`review.lock` / `instance_lock`) para evitar colisiones entre la GUI, la CLI y el agente de fondo.

---

## 🏗️ Arquitectura del Sistema

El proyecto sigue una arquitectura modular en capas desacopladas ubicada en [`asfi_monitor_app/`](file:///c:/Users/PA-CREDITO-02/Downloads/Reports_ASFI_monitor/asfi_monitor_app):

```
┌────────────────────────────────────────────────────────┐
│                   Puntos de Entrada                    │
│    GUI (Tkinter)  │  CLI (Consola)  │  Agente (Fondo)  │
└────────────┬──────────────┬──────────────────┬─────────┘
             │              │                  │
             └──────────────┼──────────────────┘
                            ▼
      ┌───────────────────────────────────────────┐
      │          Application & Runner             │
      │   - MonitorRunner (ejecución segura)      │
      │   - MonitorService (caso de uso central)  │
      │   - InstanceLock (exclusión mutua)        │
      └─────────────┬──────────────┬──────────────┘
                    │              │
        ┌───────────▼──┐        ┌──▼───────────┐
        │    Domain    │        │ Integrations │
        │  - Analysis  │        │ - Playwright │
        │  - Rules     │        │ - Plyer Win  │
        └───────────┬──┘        └──┬───────────┘
                    │              │
                    └───────┬──────┘
                            ▼
      ┌───────────────────────────────────────────┐
      │                  Storage                  │
      │   - SQLite (Esquema v8, Migraciones)      │
      │   - DPAPI Windows (Credenciales Seguras)  │
      │   - Cache JSON de Estado                  │
      └───────────────────────────────────────────┘
```

---

## 📁 Estructura del Repositorio

```
Reports_ASFI_monitor/
├── asfi_monitor_app/                # Implementación modular central
│   ├── application/                 # Servicios de aplicación, runner y scheduler
│   ├── domain/                      # Lógica de negocio, reglas normativas y análisis
│   ├── integrations/                # Conectores externos (Playwright SCIP, Plyer)
│   ├── storage/                     # SQLite, migraciones, DPAPI y estado JSON
│   ├── ui/                          # Vistas Tkinter, diálogos, PDF y dashboard
│   ├── tools/                       # Utilidades de mantenimiento y diagnóstico
│   ├── config.py                    # Configuración técnica por defecto
│   └── README.md                    # Documentación interna del módulo
├── assets/                          # Recursos gráficos (iconos .ico, .png)
├── tests/                           # Batería de pruebas automatizadas
├── tools/                           # Scripts auxiliares y backups
│   ├── diagnostico.bat              # Script de verificación del entorno
│   └── ejecutar.bat                 # Lanzador rápido
├── asfi_monitor.py                  # Fachada CLI y punto de entrada compatible
├── asfi_monitor_agent.py            # Entrada para el agente en segundo plano
├── gestionar_reportes.py            # Fachada GUI para la administración
├── reportes_db.py                   # Fachada compatible para acceso a SQLite
├── reportes_seed.json               # Catálogo inicial de reportes y reglas
├── debug_reportes.py                # Depuración interactiva de selectores
├── probar_notificaciones.py          # Verificación de notificaciones Windows
├── configurar.bat                   # Acceso rápido a la GUI de configuración
├── iniciar.bat                      # Acceso rápido para iniciar el monitor
├── instalar.bat                     # Instalador de dependencias en Windows
├── programar_tarea.bat              # Script para configurar tarea programada
├── build_windows.ps1                # Script PowerShell de empaquetado PyInstaller
├── asfi_monitor.iss                 # Script de compilación de instalador Inno Setup
├── requirements.txt                 # Dependencias de producción
├── requirements-build.txt           # Dependencias para compilación/build
└── README.md                        # Este documento
```

---

## 💻 Requisitos del Entorno

- **Sistema Operativo:** Windows 10 / Windows 11 (64-bit).
- **Python:** Versión 3.10 o superior (con soporte para `tkinter` y `sqlite3`).
- **Navegador:** Chromium para Playwright (se instala automáticamente).
- **Conectividad:** Acceso a la red institucional o VPN con conectividad al portal ASFI/SCIP (`https://appweb.asfi.gob.bo/SCIP`).

---

## ⚙️ Instalación y Configuración Inicial

### 1. Clonar el Repositorio
```powershell
git clone https://github.com/Jaimejames10/asf1-sc1p-monitor.git
cd Reports_ASFI_monitor
```

### 2. Instalación Automática (Recomendado)
Ejecute el script por lotes:
```cmd
instalar.bat
```
Este script realiza las siguientes acciones:
1. Valida la instalación de Python en el `PATH`.
2. Instala los paquetes de [`requirements.txt`](file:///c:/Users/PA-CREDITO-02/Downloads/Reports_ASFI_monitor/requirements.txt).
3. Descarga el binario de Chromium necesario para Playwright.
4. Valida la importación de módulos y crea un acceso directo en el escritorio.

### 3. Instalación Manual por Terminal
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
```

### 4. Configurar Credenciales y Catálogo
Ejecute la interfaz de configuración:
```cmd
configurar.bat
```
O mediante Python:
```powershell
python gestionar_reportes.py
```
- Ingrese su **Usuario** y **Contraseña** de ASFI/SCIP (se cifrarán con DPAPI en la base local).
- Revise o ajuste el catálogo de reportes y las reglas de periodicidad.
- Verifique que la tabla de **Feriados** incluya los días no laborables correspondientes.

---

## 📖 Guía de Uso

### Panel Gráfico (GUI)
Para abrir el panel de control y administración:
```powershell
python gestionar_reportes.py
```
**Funcionalidades de la GUI:**
- **Dashboard:** Estado del último ciclo de revisión, reportes enviados, alertas y gráficos de estado.
- **Catálogo de Reportes:** Alta, baja y modificación de códigos de reporte, nombres, periodicidades y plazos.
- **Feriados y Calendario:** Gestión de feriados nacionales bolivianos y días inhábiles.
- **Informe PDF:** Generación visual de informe consolidado exportable a PDF.
- **Credenciales:** Actualización segura de credenciales de acceso.

---

### Monitoreo por Consola (CLI)

El monitor CLI permite ejecuciones continuas o tareas programadas:

```powershell
# Monitoreo continuo (intervalo por defecto: 15 minutos)
python asfi_monitor.py

# Monitoreo con intervalo personalizado (ej. cada 10 minutos)
python asfi_monitor.py --intervalo 10

# Ejecución única (revisa una vez y termina, ideal para cron o tareas de Windows)
python asfi_monitor.py --una-vez

# Modo visible (abre la ventana del navegador para depuración visual)
python asfi_monitor.py --visible

# Salida detallada en consola
python asfi_monitor.py --verbose

# Especificar credenciales por línea de comandos (opcional)
python asfi_monitor.py --usuario MI_USUARIO --password MI_PASSWORD
```

También puede utilizar variables de entorno para las credenciales:
```powershell
$env:ASFI_USUARIO = "usuario_scip"
$env:ASFI_PASSWORD = "password_scip"
python asfi_monitor.py
```

---

### Agente en Segundo Plano

Para ejecutar el agente silencioso sin consola interactiva:
```powershell
python asfi_monitor_agent.py
```
El agente ejecuta revisiones periódicas, evalúa cambios de estado, emite notificaciones de Windows y registra eventos en [`asfi_monitor.log`](file:///c:/Users/PA-CREDITO-02/Downloads/Reports_ASFI_monitor/asfi_monitor.log).

---

## 📅 Motor de Reglas y Calendario Normativo

El sistema incorpora un motor de reglas adaptado a la normativa financiera:

- **Periodicidad Diaria:** Controla envíos diarios con opción de tolerancia para fines de semana (envíos de viernes, sábado y domingo permitidos hasta el lunes a las 12:00).
- **Periodicidad Semanal:** Vencimientos programados en días específicos de la semana con hora límite configurable.
- **Periodicidad Mensual:** Calcula el último día del mes correspondiente y aplica plazos en **días hábiles** o **días calendario**.
- **Excepciones de Fin de Mes:** Soporte para omitir generación de obligaciones en el último día del mes cuando el reporte así lo requiera.
- **Feriados Nacionales:** Exclusión automática de feriados registrados en la base de datos al contabilizar días hábiles.

---

## 🔒 Seguridad y Almacenamiento

- **Base de Datos Local:** Archivo [`asfi_monitor.db`](file:///c:/Users/PA-CREDITO-02/Downloads/Reports_ASFI_monitor/asfi_monitor.db) estructurado bajo SQLite con soporte de migraciones automáticas.
- **Protección DPAPI:** Las contraseñas se cifran mediante las API nativas de protección de datos de Windows vinculadas al usuario del sistema operativo; nunca se guardan en texto plano.
- **Concurrencia Segura:** Se utiliza un archivo de bloqueo (`review.lock`) para evitar que múltiples procesos intenten interactuar con el portal ASFI simultáneamente.
- **Persistencia de Estado:** El archivo [`asfi_estado.json`](file:///c:/Users/PA-CREDITO-02/Downloads/Reports_ASFI_monitor/asfi_estado.json) almacena una instantánea del último análisis para detectar discrepancias y nuevos estados.

---

## 📦 Compilación y Empaquetado Windows

El proyecto puede empaquetarse como una suite nativa de ejecutables independientes sin requerir Python en los equipos cliente:

### 1. Construir Ejecutables con PyInstaller
Ejecute en PowerShell con privilegios adecuados:
```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```
Este script genera tres ejecutables en la carpeta `dist/`:
- `ASFI_Monitor_GUI.exe`: Panel de control de escritorio.
- `ASFI_Monitor_Agent.exe`: Agente silencioso de fondo.
- `ASFI_Monitor_CLI.exe`: Interfaz por línea de comandos.
- Incluye el runtime empaquetado de Chromium en `ms-playwright/`.

### 2. Generar el Instalador con Inno Setup
Abra y compile [`asfi_monitor.iss`](file:///c:/Users/PA-CREDITO-02/Downloads/Reports_ASFI_monitor/asfi_monitor.iss) con **Inno Setup 6+** para producir el instalador `ASFI-Monitor-Setup-1.0.1.exe`.

**Comportamiento en versión instalada:**
- Archivos de aplicación: `%LOCALAPPDATA%\Programs\ASFI Monitor\`
- Datos de usuario, base SQLite y logs: `%LOCALAPPDATA%\ASFI Monitor\`
- Tarea de inicio automático configurada para `ASFI_Monitor_Agent.exe`.

---

## 🛠️ Herramientas y Diagnóstico

| Herramienta | Comando | Descripción |
|---|---|---|
| **Diagnóstico del Sistema** | `tools\diagnostico.bat` | Inspecciona el entorno, versiones instaladas y conectividad. |
| **Prueba de Notificaciones** | `python probar_notificaciones.py` | Envía una notificación Toast de prueba para validar compatibilidad. |
| **Depurador de Selectores** | `python debug_reportes.py` | Ejecuta el scraping e inspecciona los elementos HTML sin alterar el estado. |
| **Lanzador Rápido** | `iniciar.bat` | Inicia el monitor buscando automáticamente el entorno Python configurado. |
| **Programador de Tareas** | `programar_tarea.bat` | Crea una tarea programada en el Programador de Tareas de Windows. |

---

## ❓ Solución de Problemas Frecuentes

### 1. Timeout al conectar con ASFI/SCIP
- **Causa:** Conectividad deficiente, VPN inactiva o servidor ASFI no disponible.
- **Solución:** Compruebe su conexión a internet/VPN, o intente ejecutar con `python asfi_monitor.py --visible` para observar la respuesta del portal.

### 2. Notificaciones no aparecen en Windows
- **Causa:** El Asistente de Concentración (Focus Assist) de Windows está activado o falta la librería Plyer.
- **Solución:** Ejecute `python probar_notificaciones.py`. Si no se visualiza, revise la configuración de notificaciones en Windows > Sistema > Notificaciones.

### 3. Error de Chromium no encontrado
- **Causa:** El navegador de Playwright no fue descargado.
- **Solución:** Ejecute `python -m playwright install chromium`.

### 4. Base de datos bloqueada (`database is locked`)
- **Causa:** Otro proceso del monitor o visor SQLite mantiene abierta una transacción.
- **Solución:** Cierre instancias concurrentes o verifique que el archivo `review.lock` no haya quedado huérfano.

---

## 📄 Licencia y Créditos

Desarrollado para la optimización de procesos regulatorios y auditoría de **Comarapa RL**.  
Distribuido bajo directrices internas de cumplimiento normativo y seguridad institucional.
