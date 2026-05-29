from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('control_legal', '0008_expediente_estado_abandono'),
    ]

    operations = [

        migrations.AddField(
            model_name='tarea',
            name='horas_estimadas',
            field=models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='Horas estimadas'),
        ),
        migrations.AddField(
            model_name='tarea',
            name='es_recurrente',
            field=models.BooleanField(default=False, verbose_name='¿Tarea recurrente?'),
        ),
        migrations.AddField(
            model_name='tarea',
            name='frecuencia_recurrencia',
            field=models.CharField(max_length=20, blank=True, choices=[('semanal','Semanal'),('quincenal','Quincenal'),('mensual','Mensual')], verbose_name='Frecuencia de recurrencia'),
        ),

        migrations.CreateModel(
            name='ComentarioTarea',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('texto', models.TextField(verbose_name='Comentario')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('tarea', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comentarios', to='control_legal.tarea', verbose_name='Tarea')),
                ('autor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='comentarios_tareas', to=settings.AUTH_USER_MODEL, verbose_name='Autor')),
            ],
            options={'verbose_name': 'Comentario de tarea', 'verbose_name_plural': 'Comentarios de tareas', 'ordering': ['creado_en']},
        ),

        migrations.CreateModel(
            name='NotificacionInterna',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('mensaje', models.CharField(max_length=300, verbose_name='Mensaje')),
                ('url_destino', models.CharField(max_length=200, blank=True)),
                ('leida', models.BooleanField(default=False, verbose_name='Leída')),
                ('creada_en', models.DateTimeField(auto_now_add=True)),
                ('destinatario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificaciones', to=settings.AUTH_USER_MODEL, verbose_name='Destinatario')),
                ('remitente', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notificaciones_enviadas', to=settings.AUTH_USER_MODEL, verbose_name='Remitente')),
            ],
            options={'verbose_name': 'Notificación interna', 'ordering': ['-creada_en']},
        ),
    ]