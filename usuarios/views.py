from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .decoradores import login_requerido

def vista_inicio(request):
    """Redirección a la página de inicio"""
    if request.user.is_authenticated:
        return redirect('listar_casos')
    return redirect('login')

def vista_login(request):
    if request.user.is_authenticated:
        return redirect('usuarios:dashboard')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        # Buscamos el usuario por email
        from django.contrib.auth.models import User
        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            messages.error(request, 'Credenciales incorrectas.')
            return render(request, 'usuarios/login.html')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            try:
                perfil_activo = user.perfil.activo
            except Exception:
                from .models import PerfilUsuario
                PerfilUsuario.objects.get_or_create(usuario=user)
                perfil_activo = True

            if perfil_activo:
                login(request, user)
                return redirect('usuarios:dashboard')

        messages.error(request, 'Credenciales incorrectas o cuenta desactivada.')

    return render(request, 'usuarios/login.html')


def vista_logout(request):
    logout(request)
    return redirect('usuarios:login')


@login_requerido
def vista_dashboard(request):
    return redirect('dashboard')


@login_requerido
def vista_sin_permiso(request):
    return render(request, 'usuarios/sin_permiso.html')
