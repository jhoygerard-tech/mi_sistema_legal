from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class PerfilUsuario(models.Model):

    ROL_ADMIN     = 'admin'
    ROL_ABOGADO   = 'abogado'
    ROL_PASANTE   = 'pasante'

    ROLES = [
        (ROL_ADMIN,   'Administrador'),
        (ROL_ABOGADO, 'Abogado'),
        (ROL_PASANTE, 'Pasante / Procurador'),
    ]

    usuario    = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol        = models.CharField(max_length=20, choices=ROLES, default=ROL_PASANTE)
    telefono   = models.CharField(max_length=20, blank=True)
    foto       = models.ImageField(upload_to='perfiles/', blank=True, null=True)
    activo     = models.BooleanField(default=True)
    creado_en  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.get_full_name()} ({self.get_rol_display()})"

    def es_admin(self):
        return self.rol == self.ROL_ADMIN

    def es_abogado(self):
        return self.rol == self.ROL_ABOGADO

    def es_pasante(self):
        return self.rol == self.ROL_PASANTE


# Esto crea el perfil automáticamente cuando se crea un usuario
@receiver(post_save, sender=User)
def crear_perfil(sender, instance, created, **kwargs):
    if created:
        PerfilUsuario.objects.create(usuario=instance)

@receiver(post_save, sender=User)
def guardar_perfil(sender, instance, **kwargs):
    try:
        instance.perfil.save()
    except PerfilUsuario.DoesNotExist:
        PerfilUsuario.objects.create(usuario=instance)
