from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('control_legal', '0007_precedentejurisprudencial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expediente',
            name='estado',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('activo',    'Activo'),
                    ('concluido', 'Concluido'),
                    ('archivado', 'Archivado'),
                    ('abandono',  'Abandono'),   # ← nuevo estado
                ],
                default='activo',
                verbose_name='Estado',
            ),
        ),
    ]