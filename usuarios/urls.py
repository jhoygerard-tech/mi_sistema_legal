from django.urls import path
from . import views

urlpatterns = [
    path('', views.vista_inicio, name='inicio'),
    path('dashboard/', views.vista_dashboard, name='dashboard'),
    path('sin-permiso/', views.vista_sin_permiso, name='sin_permiso'),
]