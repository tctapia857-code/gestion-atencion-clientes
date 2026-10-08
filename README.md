# Gestión de Atención a Clientes

Aplicación web en español con **Flask + SQLite** y **Angular**. Registra clientes, genera turnos A-001, A-002… y administra cuatro mesas. Cada mesa llama al primer cliente en espera, marca su atención como finalizada y vuelve a estar disponible.

## Requisitos

- Python 3.12 o posterior, con pip.
- Node.js 24 LTS y npm.
- Git, para publicar el repositorio.

## Desarrollo local

Abre dos terminales en esta carpeta.

### 1. Backend (PowerShell en Windows)

~~~powershell
cd backend
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
~~~

Si usas el comando python en lugar de py, reemplázalo en la primera línea de instalación. No necesitas activar el entorno virtual.

En macOS/Linux:

~~~bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
~~~

La API se ejecuta en http://127.0.0.1:5000.

### 2. Frontend

~~~bash
cd frontend
npm ci
npm start
~~~

Abre http://127.0.0.1:4200. En PowerShell puedes usar npm.cmd si la política de ejecución bloquea npm.ps1. El proxy Angular envía /api al backend, sin necesitar CORS.

## Uso

1. Ingresa el nombre del cliente y pulsa **Generar turno**.
2. En una mesa disponible, pulsa **Llamar siguiente**.
3. Al finalizar, pulsa **Marcar como atendido**.
4. La mesa vuelve a estar disponible y la atención aparece en el historial.

Las otras pantallas consultan el estado cada tres segundos. Los turnos son consecutivos durante toda la vida de la base de datos, sin reinicio diario. El número puede superar tres dígitos. El resumen muestra totales acumulados y el historial muestra las ocho últimas atenciones.

## Compilar y servir desde Flask

~~~bash
cd frontend
npm ci
npm run build
cd ../backend
~~~

En Windows, desde backend:

~~~powershell
.venv\Scripts\waitress-serve.exe --host=127.0.0.1 --port=5000 --call app:create_app
~~~

En macOS/Linux:

~~~bash
.venv/bin/waitress-serve --host=127.0.0.1 --port=5000 --call app:create_app
~~~

Abre http://127.0.0.1:5000. Flask sirve el Angular compilado y la API en el mismo origen. Para desarrollo, el servidor integrado se inicia sin depuración.

## Datos y concurrencia

La base se crea automáticamente en backend/instance/atencion.sqlite3. Puedes cambiar su ubicación con la variable de entorno DATABASE_PATH. Para respaldar, detén el servidor y copia la base. No se incluye la base en Git.

Las llamadas usan transacciones SQLite BEGIN IMMEDIATE y un índice único por mesa ocupada. Esto evita asignaciones duplicadas. El cierre exige el ID del turno actual para que una pantalla desactualizada no cierre una atención diferente. Este proyecto funciona en una instancia del servidor con almacenamiento local persistente; para escalar a múltiples servidores, migra a una base compartida.

## API

| Método | Ruta | Operación |
| --- | --- | --- |
| GET | /api/state | Fila, cuatro mesas, total atendido e historial |
| POST | /api/tickets | Crear turno; JSON: {"name":"Ana"} |
| POST | /api/desks/1/call | Llamar siguiente (mesa 1 a 4) |
| POST | /api/desks/1/complete | Finalizar; JSON: {"ticket_id":1} |

Errores: 400 para datos inválidos, 404 para mesa/ruta inexistente y 409 para conflictos de estado. Los mensajes están en español.

## Pruebas

Desde backend, usando el Python del entorno virtual:

~~~powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
~~~

Cubren flujo completo, persistencia, validación, cierre obsoleto y llamadas simultáneas. En frontend ejecuta npm run build para validar TypeScript y las plantillas.

## GitHub

Se incluyen .gitignore, .editorconfig, archivo de bloqueo npm y un workflow de GitHub Actions para pruebas y compilación. Desde la raíz del proyecto:

~~~bash
git init -b main
git add .
git commit -m "Aplicación inicial de atención a clientes"
~~~

Crea en GitHub un repositorio vacío llamado gestion-atencion-clientes; después ejecuta (reemplaza TU_USUARIO):

~~~bash
git remote add origin https://github.com/TU_USUARIO/gestion-atencion-clientes.git
git push -u origin main
~~~

No se publica automáticamente en una cuenta de GitHub. Antes de exponer la aplicación en Internet, incorpora autenticación, permisos y HTTPS: esta versión está preparada para operación local en un entorno de confianza.

## Estructura

~~~text
backend/
  app.py                API, persistencia y servidor del frontend compilado
  requirements.txt      Dependencias Python
  tests/test_app.py     Pruebas funcionales y de concurrencia
frontend/
  src/                  Interfaz Angular, estilos y componentes
  angular.json          Configuración de compilación
  proxy.conf.json       Proxy de desarrollo
.github/workflows/ci.yml
~~~
