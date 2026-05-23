from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Panel de administración
    path('admin/', admin.site.urls),

# Raíz → redirige al dashboard
    path('', RedirectView.as_view(url='/casos/', permanent=False)),

    # Autenticación (usa el sistema de Django, no el personalizado)
    path('login/',  auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'),         name='logout'),

    # Módulos del sistema
    path('casos/',    include('control_legal.urls')),
    path('usuarios/', include(('usuarios.urls', 'usuarios'), namespace='usuarios')),
]

# Servir archivos subidos en modo desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)