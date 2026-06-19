from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/financiero/', views.DashboardFinancieroView.as_view(), name='dashboard_financiero'),
    path('dashboard/financiero/exportar-excel/', views.exportar_dashboard_financiero_excel, name='exportar_dashboard_financiero_excel'),
    path('api/flujo-mensual/', views.api_flujo_mensual, name='api_flujo_mensual'),

    # CRUD Movimientos de Caja
    path('caja/', views.CashMovementListView.as_view(), name='cashmovement_list'),
    path('caja/nuevo/', views.CashMovementCreateView.as_view(), name='cashmovement_create'),
    path('caja/<int:pk>/editar/', views.CashMovementUpdateView.as_view(), name='cashmovement_update'),
    path('caja/<int:pk>/eliminar/', views.CashMovementDeleteView.as_view(), name='cashmovement_delete'),
]
