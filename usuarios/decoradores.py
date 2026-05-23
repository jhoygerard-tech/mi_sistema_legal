from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def login_requerido(func):
    """Redirige al login si el usuario no está autenticado."""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('usuarios:login')
        return func(request, *args, **kwargs)
    return wrapper

def rol_requerido(*roles_permitidos):
    """
    Uso: @rol_requerido('admin', 'abogado')
    Bloquea el acceso si el usuario no tiene uno de los roles indicados.
    """
    def decorador(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('usuarios:login')
            try:
                rol_actual = request.user.perfil.rol
            except Exception:
                return redirect('usuarios:login')
            if rol_actual not in roles_permitidos:
                messages.error(request, "No tienes permiso para acceder a esta sección.")
                return redirect('usuarios:sin_permiso')
            return func(request, *args, **kwargs)
        return wrapper
    return decorador