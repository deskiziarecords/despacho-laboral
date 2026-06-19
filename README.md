# ⚖️ Despacho Laboral - Sistema de Gestión de Expedientes

Sistema web para la gestión de expedientes laborales de un despacho de abogados. Construido con Django 5.x, Tailwind CSS y HTMX.

## ✨ Características

- **Gestión de expedientes** con numeración automática (AAAA-####), estados controlados y validación de transiciones
- **Roles de usuario**: Superadmin, Administrativo (4), Asesor (15)
- **Dashboards diferenciados** por rol (asesor ve solo sus casos, admin ve todo)
- **CRUD completo** de expedientes y clientes
- **Subida de documentos** (PDF, imágenes) asociados a expedientes
- **Calendario de audiencias**
- **Búsqueda y filtros** avanzados
- **Historial de cambios** detallado (quién, cuándo, qué cambió)
- **Exportación a Excel** de expedientes
- **Generación de PDF** por expediente
- **Recordatorios automáticos** por comando de gestión
- **Interfaz responsive** con Tailwind CSS
- **Interactividad dinámica** con HTMX (sin React)

## 🚀 Inicio Rápido

### Requisitos

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (gestor de paquetes)

### Instalación

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd despacho-laboral

# 2. Instalar dependencias
uv sync

# 3. Ejecutar migraciones
uv run python manage.py migrate

# 4. Crear usuarios de prueba
uv run python manage.py crear_usuarios_prueba

# 5. Iniciar servidor
uv run python manage.py runserver
```

### Usuarios de Prueba

| Rol | Usuario | Contraseña | Cantidad |
|-----|---------|------------|----------|
| Superadmin | `superadmin` | `Admin123!` | 1 |
| Administrativo | `admin1` - `admin4` | `Admin1!` - `Admin4!` | 4 |
| Asesor | `asesor1` - `asesor15` | `Asesor1!` - `Asesor15!` | 15 |

### Probar los Diferentes Roles

1. **Superadmin** (`superadmin / Admin123!`): Acceso completo al panel de administración de Django y al dashboard administrativo.
2. **Administrativo** (`admin1 / Admin1!`): Ve todos los casos, reportes de productividad, montos totales, puede exportar a Excel. Accede al admin de Django.
3. **Asesor** (`asesor1 / Asesor1!`): Solo ve y edita sus propios casos. Tiene su dashboard personal con estadísticas.

Al iniciar sesión, cada usuario es redirigido automáticamente al dashboard correspondiente según su rol.

## 📁 Estructura del Proyecto

```
despacho-laboral/
├── accounts/                    # App de usuarios y roles
│   ├── models.py               # UserProfile (roles: superadmin, admin, asesor)
│   ├── views.py                # Login, dashboards
│   ├── forms.py                # Formulario de login
│   ├── admin.py                # Admin con perfil extendido
│   └── urls.py                 # Rutas de autenticación
├── config/                     # Configuración central
│   ├── settings.py             # Base de datos, apps, seguridad
│   ├── urls.py                 # Rutas principales
│   ├── wsgi.py                 # Para producción
│   └── asgi.py                 # Para producción
├── expedientes/                # App principal
│   ├── models.py               # Cliente, Expediente, Documento, Movimiento
│   ├── views.py                # Dashboards, CRUD, PDF, Excel
│   ├── forms.py                # Formularios de expedientes y clientes
│   ├── urls.py                 # Rutas de expedientes
│   ├── admin.py                # Panel administrativo
│   ├── signals.py              # Registro automático de movimientos
│   ├── apps.py                 # Configuración de la app
│   ├── templatetags/           # Filtros personalizados (intcomma)
│   └── management/commands/    # Comandos personalizados
│       ├── crear_usuarios_prueba.py
│       └── enviar_recordatorios.py
├── templates/                  # Templates globales
│   ├── base.html              # Layout principal con Tailwind + HTMX
│   ├── accounts/
│   │   └── login.html         # Página de inicio de sesión
│   └── expedientes/
│       ├── dashboard_asesor.html
│       ├── dashboard_admin.html
│       ├── expediente_list.html
│       ├── expediente_form.html
│       ├── expediente_detail.html
│       ├── cliente_list.html
│       ├── cliente_form.html
│       ├── calendario.html
│       └── pdf_expediente.html
├── media/                      # Archivos subidos
│   └── documentos/
├── static/                     # Archivos estáticos
│   ├── css/
│   └── js/
├── manage.py                   # Punto de entrada de Django
├── pyproject.toml              # Dependencias del proyecto
└── README.md
```

## 🗄️ Modelos de Datos

### UserProfile (accounts)
- **user**: OneToOne con User de Django
- **rol**: superadmin | admin | asesor
- **telefono**: Teléfono de contacto

### Cliente (expedientes)
- **nombre**, **rut** (único), **telefono**, **email**, **direccion**

### Expediente (expedientes)
- **numero**: Automático formato AAAA-####
- **estado**: nuevo → solicitud → audiencia → convenio/demanda → cerrado
- **Transiciones validadas**: No se puede saltar pasos
- **monto_reclamado**, **monto_convenio**: Montos del caso
- **fecha_audiencia**: Fecha de la audiencia programada
- **proxima_accion**: Fecha para recordatorio

### Movimiento (expedientes)
- Registro automático de: creación, cambio de estado, subida de documentos

## 🔄 Estados del Expediente y Transiciones

```
📄 Nuevo → 📨 Solicitud → ⚖️ Audiencia → 🤝 Convenio
                                       → ⚡ Demanda
                                     → 📨 Solicitud (reprogramación)
               → ✅ Cerrado (en cualquier etapa)
```

## 📋 Comandos Útiles

```bash
# Crear usuarios de prueba
uv run python manage.py crear_usuarios_prueba

# Enviar recordatorios (próximos 3 días)
uv run python manage.py enviar_recordatorios

# Enviar recordatorios (próximos 7 días, solo simular)
uv run python manage.py enviar_recordatorios --days=7 --dry-run

# Generar migraciones (si cambias modelos)
uv run python manage.py makemigrations

# Ejecutar migraciones
uv run python manage.py migrate

# Verificar el proyecto
uv run python manage.py check
```

## 🔧 Producción

Para desplegar en Railway o PythonAnywhere:

1. Cambiar `DEBUG = False` en `config/settings.py`
2. Configurar `ALLOWED_HOSTS` con tu dominio
3. Usar PostgreSQL en lugar de SQLite (descomentar configuración en settings.py)
4. Configurar variables de entorno para `SECRET_KEY`
5. Ejecutar `uv run python manage.py collectstatic`

### PostgreSQL (producción)

```python
# En config/settings.py, reemplazar DATABASES:
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'despacho_laboral',
        'USER': 'postgres',
        'PASSWORD': 'tu_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## 🎨 Tecnologías

- **Backend**: Django 5.x
- **Base de datos**: SQLite (desarrollo) / PostgreSQL (producción)
- **Frontend**: Tailwind CSS (vía CDN) + HTMX
- **PDFs**: WeasyPrint
- **Excel**: OpenPyXL
- **Imágenes**: Pillow
- **Paquetes**: uv

## 📄 Licencia

MIT
