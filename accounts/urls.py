from django.urls import path
from . import views

urlpatterns = [
    # Login/Logout
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),

    # Password Reset
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Superadmin
    path('superadmin/', views.SuperadminDashboardView.as_view(), name='superadmin_dashboard'),
    path('superadmin/matriz-permisos/', views.MatrizPermisosView.as_view(), name='matriz_permisos'),
    path('superadmin/matriz-permisos/exportar-excel/', views.exportar_matriz_permisos_excel, name='exportar_matriz_permisos_excel'),
    path('superadmin/cargar-datos-demo/', views.cargar_datos_demo, name='cargar_datos_demo'),
]
