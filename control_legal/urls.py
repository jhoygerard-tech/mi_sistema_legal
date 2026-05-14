from django.urls import path
from . import views

urlpatterns = [
    path('registrar/', views.registrar_caso, name='registrar_caso'),
path('lista/', views.listar_casos, name='listar_casos'),
]

urlpatterns = [
    path('', views.dashboard, name='dashboard'), # Dashboard principal
    path('registrar/', views.registrar_caso, name='registrar_caso'),
    path('lista/', views.listar_casos, name='listar_casos'),
]

urlpatterns = [
    path('', views.dashboard, name='dashboard'), # Esto carga al entrar a /casos/
    path('registrar/', views.registrar_caso, name='registrar_caso'),
    path('lista/', views.listar_casos, name='listar_casos'),
]

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('registrar/', views.registrar_caso, name='registrar_caso'),
    path('lista/', views.listar_casos, name='listar_casos'),
    path('editar/<int:pk>/', views.editar_caso, name='editar_caso'), # Nueva ruta con ID
    path('eliminar/<int:pk>/', views.eliminar_caso_logico, name='eliminar_caso'),
    path('papelera/', views.papelera_casos, name='papelera_casos'),
    path('restaurar/<int:pk>/', views.restaurar_caso, name='restaurar_caso'),
    path('exportar-pdf/', views.exportar_casos_pdf, name='exportar_pdf'),
    path('reporte-caso/<int:pk>/', views.reporte_un_caso, name='reporte_un_caso'),
]