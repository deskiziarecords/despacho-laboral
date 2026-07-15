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

    # CRUD Socios
    path('socios/', views.PartnerListView.as_view(), name='partner_list'),
    path('socios/nuevo/', views.PartnerCreateView.as_view(), name='partner_create'),
    path('socios/<int:pk>/', views.PartnerDetailView.as_view(), name='partner_detail'),
    path('socios/<int:pk>/editar/', views.PartnerUpdateView.as_view(), name='partner_update'),

    # CRUD Semanas de Trabajo
    path('semanas/', views.WorkWeekListView.as_view(), name='workweek_list'),
    path('semanas/nuevo/', views.WorkWeekCreateView.as_view(), name='workweek_create'),
    path('semanas/<int:pk>/editar/', views.WorkWeekUpdateView.as_view(), name='workweek_update'),

    # CRUD Préstamos entre Socios
    path('prestamos/', views.PartnerLoanListView.as_view(), name='partnerloan_list'),
    path('prestamos/nuevo/', views.PartnerLoanCreateView.as_view(), name='partnerloan_create'),
    path('prestamos/<int:pk>/editar/', views.PartnerLoanUpdateView.as_view(), name='partnerloan_update'),
]
