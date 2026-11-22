# Saturna

**Sistema inteligente de gestión, aviso IA y QR de seguridad para paqueterías.**

*«Entregas inteligentes, retiros en segundos».*

Proyecto de Emprendimiento e Innovación Tecnológica (INF-264) · Carrera de Informática, UMSA · Grupo JAVA-Son.

Los documentos originales están en `docs/`: el proyecto de emprendimiento y la guía de desarrollo técnico.

---

## 1. Contexto: qué problema resuelve

Muchas paqueterías de La Paz y El Alto administran su operación con cuadernos, hojas de cálculo y WhatsApp.

Eso dificulta localizar paquetes, controlar cuánto tiempo llevan en custodia, avisar su llegada y verificar quién los retira.

Saturna digitaliza **el registro, la custodia y la entrega segura** (no hace transporte). Es un SaaS **multi-tenant**: cada paquetería es un *tenant* aislado, con tres planes (Gratuito, Básico y Premium).

**Flujo completo (sección 3.2 del documento), ya implementado:**

```text
Registrar paquete → código único → aviso por WhatsApp → (consultas al agente IA)
   → QR de un solo uso → validar QR en ventanilla → operador confirma el cobro
   → entrega + token invalidado → inventario y panel actualizados
```

## 2. Qué incluye esta versión

| Módulo | Estado | Detalle |
|---|---|---|
| Autenticación y roles | ✅ | Registro de paquetería, login, JWT access + refresh, argon2, roles `owner` / `operator` |
| Paquetes | ✅ | Código único `SAT-XXXXXX`, máquina de estados, bitácora de auditoría, búsqueda, filtros |
| QR de un solo uso | ✅ | Token opaco, solo se guarda su hash SHA-256, expiración, invalidación atómica, rate limiting |
| Cobros | ✅ | Efectivo / QR confirmados manualmente por el operador, recargo por demora configurable |
| Notificaciones WhatsApp | ✅ | WhatsApp Cloud API, plantillas, webhook con verificación de firma, tarea en segundo plano, reintentos |
| Agente de IA | ✅ | Function calling con 6 herramientas; si no hay API key funciona un agente por reglas |
| Panel y análisis | ✅ | Indicadores, inventario por estado, gráfica diaria/semanal/mensual/anual según plan, export CSV (Premium) |
| Control de planes | ✅ | Límites aplicados en el servidor (paquetes, avisos, consultas IA, operadores, gráficas) |
| PWA | ✅ | Instalable en el celular, escáner de QR con cámara, diseño responsive |
| Pruebas | ✅ | 25 pruebas backend (incluye concurrencia del QR y aislamiento entre tenants) + pruebas del frontend |

**Fuera de alcance (igual que en el documento):** audios, autorización a terceros, sugerencia de horarios, cobro automático de suscripciones, modo offline con sincronización, visión artificial.

## 3. Arquitectura

```text
[Operador / Propietario] ──► PWA (React + Vite) ──► API FastAPI ──► PostgreSQL
                                                        │
                                                        ├─► BackgroundTasks
                                                        │       └─► WhatsApp Cloud API ──► [Comprador]
                                                        │
                                                        └─► Agente IA (LLM + herramientas)

[Comprador] ── WhatsApp ──► Webhook de Meta ──► API FastAPI (el agente responde)
```

**Monolito modular** (decisión de la guía): con 5 personas y un piloto de 5 paqueterías, los microservicios serían sobrecosto. Cada módulo puede separarse luego.

Dentro del backend, cada módulo sigue capas: `router` (HTTP) → `service` (reglas de negocio) → modelos SQLAlchemy.

Los routers no contienen reglas, así que éstas se prueban sin levantar HTTP.

### Decisiones clave de seguridad

1. **Aislamiento por tenant.** El `tenant_id` sale siempre del usuario autenticado (dependencia `CurrentTenant`), nunca de lo que envía el cliente. Pedir un recurso de otra paquetería devuelve el mismo `404` que uno inexistente.

2. **QR de un solo uso.** `secrets.token_urlsafe(32)` → la base guarda solo `sha256(token)` → expira (24 h, configurable) → al confirmar se ejecuta un `UPDATE ... WHERE used_at IS NULL ... RETURNING`. Si dos operadores escanean a la vez, solo uno gana. Token, estado del paquete, cobro y bitácora se guardan en la misma transacción.

3. **No existe `ENTREGADO` sin QR válido.** La máquina de estados lo prohíbe y la API manual no lo acepta.

4. **El modelo de IA no toca la base de datos.** Solo invoca herramientas predefinidas; el `tenant_id` y el teléfono vienen del servidor, no de los argumentos del modelo. Un texto del usuario no puede cambiar el tenant ni las herramientas permitidas.

5. **Los límites del plan se aplican en el backend**, no solo ocultando botones.

6. **Saturna no maneja dinero ni da por pagado un paquete con una captura**: el operador verifica y confirma.

7. Montos en `NUMERIC(10,2)`, contraseñas con argon2, JWT de vida corta, CORS restringido, firma `X-Hub-Signature-256` en el webhook.

## 4. Herramientas (stack)

| Capa | Tecnología |
|---|---|
| Frontend | React 18 + Vite + TypeScript, Tailwind CSS, TanStack Query, React Router, Recharts |
| PWA / QR | `vite-plugin-pwa` (service worker + manifest), `@yudiel/react-qr-scanner` |
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| Datos | SQLAlchemy 2, Alembic (migraciones), PostgreSQL 16 (SQLite solo para desarrollo rápido y pruebas) |
| Auth | JWT (PyJWT), argon2 (`pwdlib`) |
| QR (servidor) | `segno` |
| Mensajería | WhatsApp Business Platform (Cloud API de Meta) vía `httpx` |
| IA | API de mensajes con tool use (Claude u otro compatible) o agente por reglas sin costo |
| Pruebas | `pytest`, Vitest · Calidad: Ruff, ESLint, Prettier |
| DevOps | Docker + Docker Compose, GitHub Actions |

## 5. Estructura del repositorio

```text
saturna/
├── README.md
├── docker-compose.yml          # postgres + api + web
├── .env.example                # variables (copiar a .env)
├── .github/workflows/ci.yml    # lint + pruebas + build en cada PR
├── .vscode/                    # extensiones, formateo y depuración
├── docs/                       # documentos del proyecto y guía de WhatsApp/IA
├── backend/
│   ├── pyproject.toml · Dockerfile · alembic.ini
│   ├── alembic/versions/       # migración inicial
│   ├── scripts/seed.py         # datos de demostración
│   ├── app/
│   │   ├── main.py · models.py · schemas.py
│   │   ├── core/               # config, seguridad, planes, dependencias, rate limit
│   │   ├── db/                 # sesión y base declarativa
│   │   └── modules/            # auth · tenants · packages · qr · payments
│   │                           # notifications · ai_agent · analytics
│   └── tests/
└── frontend/
    ├── package.json · vite.config.ts · Dockerfile · nginx.conf
    └── src/
        ├── app/                # rutas
        ├── features/            # auth · dashboard · packages · scanner · team · settings · agent
        ├── components/         # layout y piezas reutilizables
        └── lib/                # cliente API, formato, tipos
```

## 6. Cómo ejecutarlo

### Requisitos

- Docker Desktop instalado y funcionando.
- Git (si se clona el repositorio).
- Computadora con Windows, Linux o macOS.
- Para pruebas móviles: teléfono Android con Chrome y conexión a la misma red Wi-Fi que la computadora.

### Opción A — Todo con Docker (la más simple)

1. Abrir Docker Desktop.
2. Abrir PowerShell o una terminal en la carpeta raíz del proyecto.
3. Crear el archivo de variables de entorno:

```powershell
Copy-Item .env.example .env
```

4. Construir e iniciar los contenedores:

```powershell
docker compose up --build -d
```

5. Comprobar que los servicios estén funcionando:

```powershell
docker compose ps
```

Los servicios disponibles son:

| Servicio | Dirección |
|---|---|
| Aplicación web (PWA) | `http://localhost:8080` |
| API y documentación interactiva | `http://localhost:8000/docs` |
| PostgreSQL | Puerto `5432` |

Las migraciones se aplican automáticamente al arrancar la API.

Para cargar los datos de demostración:

```powershell
docker compose exec api python -m scripts.seed
```

### Opción B — Desarrollo local (VS Code)

Requisitos: Git, Python 3.12, Node.js 20 o superior y (opcional) Docker para PostgreSQL.

```bash
# Crear archivo de configuración
cp .env.example .env

# 1) Base de datos: PostgreSQL de Docker
docker compose up -d db

# O sin Docker: en .env usa:
# DATABASE_URL=sqlite:///./saturna.db

# 2) Backend
cd backend

python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows PowerShell:
# .venv\Scripts\Activate.ps1

pip install -e ".[dev]"

alembic upgrade head

python -m scripts.seed

uvicorn app.main:app --reload

# API: http://localhost:8000/docs

# 3) Frontend (abrir otra terminal)
cd frontend

cp .env.example .env

npm install

npm run dev

# PWA: http://localhost:5173
```

### Usuarios de demostración (tras ejecutar el seed)

| Rol | Correo | Contraseña | Celular (para el agente) |
|---|---|---|---|
| Propietario (plan Premium) | `dueno@saturna.com` | `saturna123` | `70000001` |
| Operador | `operador@saturna.com` | `saturna123` | `70000002` |

También puedes crear tu propia paquetería desde la pantalla de inicio (**Registra tu paquetería**); empieza en el plan Gratuito.

### 6.1. Acceso desde dispositivos móviles y configuración de cámara (HTTP local)

Saturna permite realizar pruebas desde un teléfono móvil conectado a la misma red Wi-Fi que la computadora donde se ejecuta Docker.

**No se requiere HTTPS, Cloudflare, ngrok ni ningún túnel externo para este entorno de desarrollo local.**

Sin embargo, Chrome Android restringe el acceso a la cámara cuando se accede mediante una dirección HTTP con una IP local. Para habilitarla durante las pruebas se puede utilizar una opción experimental de Chrome.

#### A. Iniciar Saturna en la computadora

Ejecutar:

```powershell
docker compose up --build -d
```

Comprobar los servicios:

```powershell
docker compose ps
```

La aplicación debe estar disponible en el puerto `8080`.

#### B. Obtener la dirección IP de la computadora

En Windows, abrir PowerShell y ejecutar:

```powershell
ipconfig
```

Buscar la sección del adaptador Wi-Fi y localizar la dirección IPv4.

Ejemplo de una dirección IP ficticia:

```text
192.168.1.50
```

La dirección IP puede ser diferente dependiendo de la red utilizada.

El teléfono y la computadora deben estar conectados a la misma red Wi-Fi.

Desde el teléfono se accederá a:

```text
http://192.168.1.50:8080
```

**Importante:** reemplazar `192.168.1.50` por la dirección IPv4 real de la computadora.

Si no se puede acceder, comprobar que Windows Firewall permita las conexiones entrantes al puerto `8080` y que la red Wi-Fi no tenga aislamiento entre dispositivos.

#### C. Habilitar el acceso a la cámara en Chrome Android

Chrome considera que las páginas HTTP con direcciones IP locales no son contextos seguros y, por defecto, restringe el acceso a dispositivos como la cámara.

Para permitir el acceso durante las pruebas:

1. Abrir Google Chrome en el teléfono Android.
2. Escribir en la barra de direcciones:

```text
chrome://flags/#unsafely-treat-insecure-origin-as-secure
```

3. Localizar la opción:

**Insecure origins treated as secure**

4. En el campo de texto introducir el origen completo de Saturna, incluyendo protocolo y puerto:

```text
http://192.168.1.50:8080
```

5. En el selector inferior elegir:

**Enabled (Habilitado)**

6. Pulsar el botón **Relaunch (Reiniciar)** para aplicar los cambios.

Chrome se cerrará y volverá a abrirse automáticamente.

Si se utiliza otra dirección IP o puerto, debe introducirse el origen correspondiente.

#### D. Conceder permisos de cámara

Después de reiniciar Chrome:

1. Volver a abrir Saturna utilizando la dirección IP de la computadora.
2. Iniciar sesión con un usuario válido.
3. Entrar en el módulo **Escanear QR**.
4. Cuando Chrome solicite acceso a la cámara, seleccionar **Permitir**.
5. Comprobar que se visualiza la imagen de la cámara trasera.

Si la cámara no aparece:

- Verificar que el permiso de cámara esté habilitado para el sitio.
- Comprobar que el teléfono y la computadora estén en la misma red Wi-Fi.
- Cerrar otras aplicaciones que puedan estar utilizando la cámara.
- Verificar que la IP y el puerto sean correctos.
- Comprobar que los contenedores de Docker estén funcionando.
- Recargar la página después de conceder los permisos.

#### E. Consideraciones importantes

- Esta configuración es exclusivamente para desarrollo y pruebas locales.
- La opción de Chrome utilizada es experimental y puede cambiar o desaparecer en futuras versiones.
- La excepción debe configurarse en cada teléfono que necesite utilizar el escáner.
- Si cambia la dirección IP de la computadora, debe actualizarse el origen configurado en Chrome.
- La configuración no convierte HTTP en HTTPS ni cifra las comunicaciones.
- No utilizar esta configuración para operar con información real o exponer Saturna a redes públicas.
- Para producción se debe implementar HTTPS mediante un dominio y un certificado válido.

**Resultado esperado:** Saturna puede ejecutarse en Docker en una computadora y utilizarse desde otros dispositivos de la misma red local, incluyendo el escáner QR con la cámara del teléfono Android.

### 6.2. Probar el flujo completo en 2 minutos

1. Ingresa como propietario → **Paquetes → Registrar paquete** (celular del comprador, ej. `71234567`). Se genera un código `SAT-XXXXXX`.

2. Sin credenciales de WhatsApp el aviso queda en **modo simulado** (aparece en el log de la API y el estado pasa a *Avisado*).

3. Abre **Agente IA**, escribe desde el celular `71234567`: «¿cómo va mi paquete SAT-XXXXXX?» y luego «quiero mi QR». Verás la imagen del QR.

   (También puedes emitirlo desde el detalle del paquete).

4. Abre **Escanear QR** y escanea con la cámara, o pega el código del QR. Elige efectivo/QR, confirma el cobro y la entrega.

5. Intenta usar el mismo QR otra vez: el sistema lo rechaza. Revisa el **Panel** y la bitácora del paquete.

6. Con el celular del propietario (`70000001`), pregunta al agente «¿cuánto cobré hoy?» (copiloto financiero, plan Premium).

## 7. Variables de entorno

| Variable | Para qué sirve |
|---|---|
| `DATABASE_URL` | Conexión a la base (PostgreSQL con `postgresql+psycopg://…`, o SQLite) |
| `JWT_SECRET` | Firma de tokens. **Cámbiala** en cualquier entorno real |
| `CORS_ORIGINS` | Dominios del frontend permitidos |
| `PUBLIC_BASE_URL` | URL pública de la API (WhatsApp descarga la imagen del QR desde ahí) |
| `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID` | Credenciales de la Cloud API. Vacías = modo simulado |
| `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET` | Verificación y firma del webhook. En producción define siempre el *app secret* |
| `WHATSAPP_TEMPLATE_ARRIVAL` | Nombre de la plantilla aprobada de aviso de llegada |
| `LLM_API_KEY`, `LLM_MODEL` | Modelo de lenguaje del agente. Vacío = agente por reglas |

## 8. WhatsApp y agente de IA

Guía paso a paso (cuenta de Meta, plantilla, webhook, costos):

`docs/WHATSAPP_Y_IA.md`

Herramientas del agente (el modelo solo puede llamar a estas):

| Herramienta | Quién | Qué hace |
|---|---|---|
| `consultar_estado_paquete(codigo)` | Comprador / personal | Estado, llegada, plazo y cobro estimado |
| `listar_mis_paquetes()` | Comprador / personal | Paquetes pendientes de ese número |
| `solicitar_qr_retiro(codigo)` | Comprador | Emite el QR y lo envía como imagen |
| `horario_de_atencion(codigo?)` | Comprador / personal | Horario y dirección configurados por la paquetería |
| `resumen_cobros(periodo)` | Propietario, Premium | «¿Cuánto cobré hoy?» (cobros registrados, **no** utilidad) |
| `paquetes_estancados()` | Propietario, Premium | Paquetes vencidos o por vencer |

## 9. Planes

Configurados en `backend/app/core/plans.py` (fáciles de cambiar):

| | Gratuito | Básico (Bs 99) | Premium (Bs 199) |
|---|---:|---:|---:|
| Paquetes/mes | 30 | 250 | Ilimitados |
| Avisos WhatsApp/mes | 30 | 250 | 700 |
| Consultas IA/mes | 10 | 50 | 500 |
| Operadores | 1 | 2 | Ilimitados |
| Gráficas de ingresos | — | Diaria | Diaria, semanal, mensual, anual |
| Copiloto financiero y alertas | — | — | ✔ |
| Export CSV | — | — | ✔ |

Los valores de Gratuito en IA (10) y los del documento no especificados son una propuesta de este proyecto; ajústalos tras el piloto.

## 10. API principal

Documentación interactiva completa en `/docs`.

| Método y ruta | Función |
|---|---|
| `POST /auth/register`, `/auth/login`, `/auth/refresh`; `GET /auth/me` | Autenticación |
| `GET/POST /packages`, `GET /packages/{id}` | Listar/registrar (valida el plan) y ver detalle con bitácora |
| `POST /packages/{id}/qr` | Emitir QR de retiro |
| `POST /packages/{id}/notify`, `/packages/{id}/state` | Reenviar aviso / cambios manuales (p. ej. devolver) |
| `POST /qr/validate` | Verifica el token escaneado (no lo consume) |
| `POST /qr/confirm` | Confirma entrega (+ cobro) y consume el token |
| `POST /payments`, `GET /payments` | Registrar y listar cobros |
| `GET /analytics/summary`, `/analytics/revenue?granularity=`, `/analytics/export.csv` | Panel |
| `GET/POST /users`, `PATCH /users/{id}/toggle` | Operadores (solo propietario) |
| `GET/PATCH /tenants/me`, `POST /tenants/me/plan`, `GET /tenants/me/usage` | Configuración de la paquetería |
| `GET/POST /webhooks/whatsapp` | Verificación y mensajes entrantes de Meta |
| `POST /agent/simulate`, `GET /agent/conversations` | Simulador y registro del agente |

## 11. Pruebas y calidad

```bash
cd backend
pytest -q
ruff check app tests

cd ../frontend
npm test
npm run lint
npm run build
```

Se incluyen 25 pruebas backend.

Cubren, entre otras: la máquina de estados, el uso único del QR (también con **8 confirmaciones simultáneas**), el token guardado solo como hash, expiración y reemisión, **aislamiento entre paqueterías**, límites de plan aplicados en el backend, permisos por rol, firma del webhook y el agente (el comprador no accede a herramientas financieras; un intento de *prompt injection* no cambia el tenant).

Las pruebas del backend corren sobre SQLite para ser rápidas y no requerir Docker.

## 12. Flujo de trabajo en equipo (Git)

- Ramas: `main` (estable), `develop` (integración), `feature/nombre-corto` por tarea.
- Pull Request obligatorio hacia `develop` con una revisión de otro integrante; el CI (Ruff, pytest, ESLint, Vitest, build) debe pasar.
- Commits claros: `feat(qr): valida token de un solo uso`.
- Reparto sugerido por áreas (del documento): backend/BD → Barrios; agente IA y prompts → Vargas; frontend/diseño → López; validación en campo y plantillas de WhatsApp → Roman; finanzas, planes y costos → Unzaga.

## 13. Notas y límites conocidos

- **Tareas en segundo plano:** el aviso se envía con `BackgroundTasks` de FastAPI (no bloquea el registro y reintenta). Si el volumen crece, la guía propone ARQ + Redis; la función `send_arrival_task` ya está aislada para migrarla.
- **Rate limiting** en memoria: suficiente para una instancia. Con varias réplicas usar Redis.
- **Analítica** agrupa en Python (portable entre SQLite y PostgreSQL). Con mucho volumen conviene `date_trunc` en SQL.
- **Sin internet:** la PWA carga sin conexión, pero registrar/cobrar requiere conexión. La cola offline con sincronización es una mejora posterior.
- **Costos de WhatsApp:** dependen de tarifas de Meta. Mídelos en el piloto (tabla `notifications` y `usage_counters`) y ajusta los topes por plan.
- **Privacidad:** se guardan solo nombre y teléfono; el propietario puede anonimizar un paquete cerrado (`POST /packages/{id}/anonymize`). Falta redactar el aviso de privacidad y el consentimiento del comprador para el piloto.
- **Plantilla de WhatsApp:** debe ser aprobada por Meta antes de operar con mensajes iniciados por la paquetería.
- **Observación del documento:** el plan Premium ofrece registro ilimitado con un tope de 700 avisos, igual al de Básico en la guía original; aquí se respeta el documento final (700) y está centralizado en `plans.py` por si deciden subirlo.

## 14. Créditos

Grupo **JAVA-Son** · Barrios Ferreira Nicolás Ignacio · López Stephanie Lorena · Roman Quispe Douglas Israel · Unzaga Roman Adriana Sara · Vargas Choque Félix Ariel.

Docente: M.Sc. Cayoja Cortez Juan.

UMSA, La Paz, Bolivia.