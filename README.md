# despacho-laboral
``` plain
despacho-laboral/
│
├── config/                          # Configuración central
│   ├── settings.py                  # Base de datos, apps, seguridad
│   ├── urls.py                      # Rutas principales
│   └── wsgi.py                      # Para producción
│
├── expedientes/                     # ✅ APP PRINCIPAL
│   ├── models.py                    # Cliente, Expediente, Documento, Movimiento
│   ├── admin.py                     # Panel administrativo
│   ├── views.py                     # 👈 AÑADIRÁS: dashboards, formularios, PDFs
│   ├── urls.py                      # 👈 AÑADIRÁS: rutas personalizadas
│   ├── forms.py                     # 👈 AÑADIRÁS: formularios de expedientes
│   ├── templates/                   # 👈 AÑADIRÁS: HTMLs
│   │   └── expedientes/
│   │       ├── dashboard.html
│   │       ├── expediente_list.html
│   │       ├── expediente_form.html
│   │       └── pdf_solicitud.html
│   └── management/                  # 👈 AÑADIRÁS: comandos automáticos
│       └── commands/
│           └── enviar_recordatorios.py
│
├── accounts/                        # 👈 APP AÑADIRÁS (Día 2)
│   ├── models.py                    # Perfil de usuario, roles
│   ├── views.py                     # Login personalizado, registro
│   └── templates/
│
├── notifications/                   # 👈 APP AÑADIRÁS (Día 4)
│   ├── whatsapp.py                  # Envío de mensajes
│   └── email.py                     # Correos automáticos
│
├── reports/                         # 👈 APP AÑADIRÁS (Día 3)
│   ├── pdf_generator.py             # WeasyPrint
│   ├── excel_reports.py             # OpenPyXL
│   └── templates/
│
├── static/                          # CSS, JS, imágenes
│   ├── css/
│   │   └── tailwind.css
│   └── js/
│       └── htmx.js
│
├── media/                           # Subidas de usuarios
│   └── documentos/                  # Screenshots, PDFs, Word
│
├── templates/                       # Templates globales
│   ├── base.html                    # Layout principal
│   └── 404.html
│
├── requirements.txt
├── manage.py
└── .env                             # Variables secretas (API keys)
