from django.shortcuts import render

# Create your v# En gestion/views.py (o cualquier otra app)
from usuarios.decoradores import login_requerido, rol_requerido
from control_legal.models import Tarea 

# Solo abogados y administradores pueden ver la lista de clientes
@rol_requerido('admin', 'abogado')
def lista_clientes(request):
    ...

# Solo el administrador puede crear nuevos usuarios
@rol_requerido('admin')
def crear_usuario(request):
    ...

# Los tres roles pueden ver tareas (pero el pasante solo verá las suyas)
@rol_requerido('admin', 'abogado', 'pasante')
def lista_tareas(request):
    if request.user.perfil.es_pasante():
        tareas = Tarea.objects.filter(asignada_a=request.user)
    else:
        tareas = Tarea.objects.all()
    
