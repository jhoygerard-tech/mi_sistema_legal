from django.db import models

class Caso(models.Model):
    MATERIAS = [('Civil', 'Civil'), ('Familiar', 'Familiar'), ('Laboral', 'Laboral'), ('Penal', 'Penal')]
    ESTADOS = [('Activo', 'Activo'), ('Trámite', 'Trámite'), ('Concluido', 'Concluido')]

    numero_caso = models.CharField(max_length=50, verbose_name="Número de Caso")
    cliente = models.CharField(max_length=200)
    materia = models.CharField(max_length=50, choices=MATERIAS, default='Civil')
    juzgado = models.CharField(max_length=100, blank=True, null=True)
    nurej = models.CharField(max_length=50, verbose_name="NUREJ" , blank=True, null=True) 
    abogado_asignado = models.CharField(max_length=200, verbose_name="Abogado Asignado")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    descripcion = models.TextField(verbose_name="Descripción del Caso")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Activo')

    activo = models.BooleanField(default=True) # <-- Añade esta línea
    
    def __str__(self):
        return f"{self.numero_caso} - {self.cliente}"

# Create your models here.
