from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('',                          views.dashboard,         name='dashboard'),

    # Clientes
    path('clientes/',                 views.listar_clientes,   name='listar_clientes'),
    path('clientes/nuevo/',           views.registrar_cliente, name='registrar_cliente'),
    path('clientes/<int:pk>/',        views.detalle_cliente,   name='detalle_cliente'),
    path('clientes/<int:pk>/editar/', views.editar_cliente,    name='editar_cliente'),

    # Expedientes
    path('lista/',                    views.listar_casos,      name='listar_casos'),
    path('registrar/',                views.registrar_caso,    name='registrar_caso'),
    path('editar/<int:pk>/',          views.editar_caso,       name='editar_caso'),
    path('detalle/<int:pk>/',         views.detalle_caso,      name='detalle_caso'),
    path('eliminar/<int:pk>/',        views.eliminar_caso,     name='eliminar_caso'),

    # Papelera
    path('papelera/',                 views.papelera_casos,    name='papelera_casos'),
    path('restaurar/<int:pk>/',       views.restaurar_caso,    name='restaurar_caso'),

    # Reportes PDF
    path('exportar-pdf/',             views.exportar_pdf,      name='exportar_pdf'),
    path('reporte/<int:pk>/',         views.reporte_un_caso,   name='reporte_un_caso'),

    # Agenda
    path('agenda/',                   views.agenda,            name='agenda'),
    path('agenda/nuevo/',             views.registrar_evento,  name='registrar_evento'),
    path('agenda/<int:pk>/editar/',   views.editar_evento,     name='editar_evento'),
    path('agenda/<int:pk>/eliminar/', views.eliminar_evento,   name='eliminar_evento'),

    # Tareas
    path('tareas/',                       views.lista_tareas,         name='lista_tareas'),
    path('tareas/nueva/',                 views.crear_tarea,          name='crear_tarea'),
    path('tareas/<int:pk>/',              views.detalle_tarea,        name='detalle_tarea'),
    path('tareas/<int:pk>/editar/',       views.editar_tarea,         name='editar_tarea'),
    path('tareas/<int:pk>/estado/',       views.cambiar_estado_tarea, name='cambiar_estado_tarea'),
    
    # GEMINI
    path('contratos/',                  views.lista_contratos,       name='lista_contratos'),
    path('contratos/generar/',          views.generar_contrato,      name='generar_contrato'),
    path('contratos/<int:pk>/',         views.ver_contrato,          name='ver_contrato'),
    path('contratos/<int:pk>/pdf/',     views.exportar_contrato_pdf, name='exportar_contrato_pdf'),
    path('plantillas/',                 views.lista_plantillas,       name='lista_plantillas'),
    path('plantillas/nueva/',           views.crear_plantilla,        name='crear_plantilla'),
    path('plantillas/<int:pk>/editar/', views.editar_plantilla,       name='editar_plantilla'),
    path('contratos/ia/',               views.generar_contrato_ia,    name='generar_contrato_ia'),

    # Reportes
    path('reportes/',                         views.reportes,              name='reportes'),

    # Portal del cliente (público — sin login del bufete)
    path('portal/',                           views.portal_login,          name='portal_login'),
    path('portal/mi-caso/',                   views.portal_cliente,        name='portal_cliente'),
    path('portal/salir/',                     views.portal_logout,         name='portal_logout'),

    # Memoriales
    path('memoriales/',                       views.lista_memoriales,      name='lista_memoriales'),
    path('memoriales/generar/',               views.generar_memorial,      name='generar_memorial'),
    path('memoriales/<int:pk>/',              views.ver_memorial,          name='ver_memorial'),
    path('memoriales/<int:pk>/pdf/',          views.exportar_memorial_pdf, name='exportar_memorial_pdf'),

    # Jurisprudencia
    # 
    path('jurisprudencia/',                   views.jurisprudencia_asistente, name='jurisprudencia_asistente'),

    # Liquidación Asistencia Familiar (Ley 603)
    path('asistencia-familiar/',                        views.calculadora_asistencia, name='calculadora_asistencia'),
    path('expediente/<int:pk>/asistencia-familiar/',    views.calculadora_asistencia_expediente, name='calculadora_asistencia_expediente'),
    path('expediente/<int:pk>/asistencia-familiar/ia/', views.api_extraer_ia_liquidacion, name='api_extraer_ia_liquidacion'),
]