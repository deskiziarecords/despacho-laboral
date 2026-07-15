from django.urls import path
from . import views

urlpatterns = [
    # Dashboards
    path('', views.dashboard_redirect, name='dashboard_redirect'),
    path('dashboard/asesor/', views.DashboardAsesorView.as_view(), name='dashboard_asesor'),
    path('dashboard/admin/', views.DashboardAdminView.as_view(), name='dashboard_admin'),

    # Búsqueda Global
    path('buscar/', views.busqueda_global, name='busqueda_global'),

    # CRUD Expedientes
    path('expedientes/', views.ExpedienteListView.as_view(), name='expediente_list'),
    path('expedientes/nuevo/', views.ExpedienteCreateView.as_view(), name='expediente_create'),
    path('expedientes/<int:pk>/', views.ExpedienteDetailView.as_view(), name='expediente_detail'),
    path('expedientes/<int:pk>/editar/', views.ExpedienteUpdateView.as_view(), name='expediente_update'),
    path('expedientes/<int:pk>/cambiar-estado/', views.cambiar_estado, name='cambiar_estado'),
    path('expedientes/<int:pk>/resultado-audiencia/', views.registrar_resultado_audiencia, name='resultado_audiencia'),

    # Notas
    path('expedientes/<int:pk>/notas/agregar/', views.agregar_nota, name='agregar_nota'),

    # CRUD Clientes
    path('clientes/', views.ClienteListView.as_view(), name='cliente_list'),
    path('clientes/nuevo/', views.ClienteCreateView.as_view(), name='cliente_create'),
    path('clientes/<int:pk>/editar/', views.ClienteUpdateView.as_view(), name='cliente_update'),

    # Documentos
    path('expedientes/<int:pk>/documentos/subir/', views.subir_documento, name='subir_documento'),
    path('documentos/<int:pk>/eliminar/', views.eliminar_documento, name='eliminar_documento'),

    # Calendario
    path('calendario/', views.calendario_audiencias, name='calendario_audiencias'),

    # WhatsApp
    path('expedientes/<int:pk>/whatsapp/', views.whatsapp_enviar, name='whatsapp_enviar'),
    path('expedientes/<int:pk>/whatsapp/historial/', views.whatsapp_historial, name='whatsapp_historial'),
    path('expedientes/<int:pk>/whatsapp/toggle-auto/', views.toggle_whatsapp_auto, name='toggle_whatsapp_auto'),
    path('whatsapp/plantilla/<str:tipo>/', views.whatsapp_plantilla, name='whatsapp_plantilla'),

    # Cálculos Laborales
    path('expedientes/<int:pk>/calculo-laboral/', views.calculo_laboral, name='calculo_laboral'),
    path('simulacion-rapida/', views.simulacion_rapida, name='simulacion_rapida'),

    # Solicitud de Conciliación
    path('expedientes/<int:pk>/solicitud/', views.solicitud_conciliacion, name='solicitud_conciliacion'),
    path('expedientes/<int:pk>/demanda/', views.demanda_editor, name='demanda_editor'),
    path('expedientes/<int:pk>/demanda/descargar/', views.demanda_descargar, name='demanda_descargar'),
    path('expedientes/<int:pk>/demanda/directa/', views.generar_demanda, name='generar_demanda'),

    # Machotes / Documentos desde plantillas
    path('machotes/<int:machote_id>/toggle-favorito/', views.toggle_machote_favorito, name='toggle_machote_favorito'),
    path('expedientes/<int:pk>/machotes/', views.machotes_listar, name='machotes_listar'),
    path('expedientes/<int:pk>/machotes/<int:machote_id>/preparar/', views.documento_preparar, name='documento_preparar'),
    path('expedientes/<int:pk>/machotes/<int:machote_id>/generar/', views.machotes_generar, name='machotes_generar'),
    path('expedientes/<int:pk>/machotes/<int:machote_id>/editor/', views.machotes_editor, name='machotes_editor'),
    path('expedientes/<int:pk>/machotes/<int:machote_id>/descargar/', views.machotes_descargar, name='machotes_descargar'),

    # Notificaciones
    path('notificaciones/<int:pk>/leer/', views.marcar_notificacion_leida, name='marcar_notificacion_leida'),
    path('notificaciones/leer-todas/', views.marcar_todas_leidas, name='marcar_todas_leidas'),

    # Transferencias de casos
    path('expedientes/<int:pk>/solicitar-transferencia/', views.solicitar_transferencia, name='solicitar_transferencia'),
    path('expedientes/<int:pk>/solicitar-transferencia/enviar/', views.enviar_solicitud_transferencia, name='enviar_solicitud_transferencia'),
    path('transferencias/', views.gestionar_transferencias, name='gestionar_transferencias'),
    path('transferencias/<int:pk>/aprobar/', views.aprobar_transferencia, name='aprobar_transferencia'),
    path('transferencias/<int:pk>/rechazar/', views.rechazar_transferencia, name='rechazar_transferencia'),
    path('transferencias/<int:pk>/cancelar/', views.cancelar_transferencia, name='cancelar_transferencia'),

    # Reportes
    path('reportes/excel/', views.exportar_excel, name='exportar_excel'),
    path('reportes/', views.reportes_admin, name='reportes_admin'),
    path('expedientes/<int:pk>/pdf/', views.generar_pdf_expediente, name='generar_pdf'),

    # Automatización de Conciliación (asíncrona con threading)
    path('expedientes/<int:pk>/conciliacion-automatica/', views.enviar_conciliacion_automation, name='enviar_conciliacion_automation'),
    path('conciliacion/<int:task_pk>/estado/', views.conciliacion_estado, name='conciliacion_estado'),
    path('conciliacion/<int:task_pk>/procesando/', views.conciliacion_procesando, name='conciliacion_procesando'),
]
