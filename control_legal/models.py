from django.db import models
from django.contrib.auth.models import User
import uuid

# ═══════════════════════════pyt═══════════════════
# 1. CLIENTE  (la raíz de todo)
# ══════════════════════════════════════════════
class Cliente(models.Model):
    # Datos personales
    ci              = models.CharField(max_length=20, unique=True, verbose_name="Cédula de identidad")
    nombre_completo = models.CharField(max_length=200, verbose_name="Nombre completo")
    telefono        = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    email           = models.EmailField(blank=True, verbose_name="Correo electrónico")
    direccion       = models.TextField(blank=True, verbose_name="Dirección")

    # Relación con el abogado responsable
    abogado_asignado = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='clientes',
        verbose_name="Abogado asignado"
    )
        
    codigo_acceso = models.CharField(
        max_length=12, unique=True, blank=True,null=True,
        verbose_name="Código de acceso del cliente"
    )

    notas_internas = models.TextField(blank=True, verbose_name="Notas internas")
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activo         = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.codigo_acceso:
            # Genera un código de 8 caracteres en mayúsculas
            self.codigo_acceso = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['nombre_completo']
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return f"{self.nombre_completo} (CI: {self.ci})"

    def total_expedientes(self):
        return self.expedientes.count()

    def expedientes_activos(self):
        return self.expedientes.filter(estado='activo').count()


# ══════════════════════════════════════════════
# 2. EXPEDIENTE  (pertenece a un Cliente)
# ══════════════════════════════════════════════
class Expediente(models.Model):
    ESTADO_ACTIVO    = 'activo'
    ESTADO_CONCLUIDO = 'concluido'
    ESTADO_ARCHIVADO = 'archivado'
    ESTADOS = [
        (ESTADO_ACTIVO,    'Activo'),
        (ESTADO_CONCLUIDO, 'Concluido'),
        (ESTADO_ARCHIVADO, 'Archivado'),
    ]

    MATERIAS = [
        ('Civil',           'Civil'),
        ('Penal',           'Penal'),
        ('Familia',         'Familia'),
        ('Laboral',         'Laboral'),
        ('Administrativo',  'Administrativo'),
        ('Constitucional',  'Constitucional'),
        ('Otro',            'Otro'),
    ]

    # Relación principal: el expediente pertenece a un cliente
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT,
        related_name='expedientes',
        verbose_name="Cliente"
    )
    abogado_asignado = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='expedientes',
        verbose_name="Abogado responsable"
    )

    # Datos del proceso judicial
    numero_expediente = models.CharField(max_length=50, blank=True, verbose_name="N° de expediente")
    nurej             = models.CharField(max_length=50, blank=True, verbose_name="NUREJ")
    juzgado           = models.CharField(max_length=200, blank=True, verbose_name="Juzgado")
    materia           = models.CharField(max_length=50, choices=MATERIAS, default='Civil', verbose_name="Materia")
    tipo_proceso      = models.CharField(max_length=100, blank=True, verbose_name="Tipo de proceso")
    descripcion       = models.TextField(blank=True, verbose_name="Descripción del caso")

    estado            = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_ACTIVO, verbose_name="Estado")
    fecha_inicio      = models.DateField(auto_now_add=True, verbose_name="Fecha de inicio")
    fecha_conclusion  = models.DateField(null=True, blank=True, verbose_name="Fecha de conclusión")

    # Para compatibilidad con tu código actual
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha_inicio']
        verbose_name = "Expediente"
        verbose_name_plural = "Expedientes"

    def __str__(self):
        return f"Exp. {self.numero_expediente or self.nurej} — {self.cliente.nombre_completo}"

    def total_documentos(self):
        return self.documentos.count()


# ══════════════════════════════════════════════
# 3. DOCUMENTO  (se agrega al expediente conforme avanza el proceso)
# ══════════════════════════════════════════════
class Documento(models.Model):
    TIPOS = [
        ('demanda',       'Demanda'),
        ('contestacion',  'Contestación'),
        ('resolucion',    'Resolución judicial'),
        ('memorial',      'Memorial'),
        ('contrato',      'Contrato'),
        ('poder',         'Poder notarial'),
        ('prueba',        'Prueba / evidencia'),
        ('notificacion',  'Notificación'),
        ('otro',          'Otro'),
    ]

    expediente   = models.ForeignKey(
        Expediente, on_delete=models.CASCADE,
        related_name='documentos',
        verbose_name="Expediente"
    )
    subido_por   = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='documentos_subidos',
        verbose_name="Subido por"
    )

    titulo        = models.CharField(max_length=200, verbose_name="Título del documento")
    tipo          = models.CharField(max_length=30, choices=TIPOS, default='otro', verbose_name="Tipo")
    archivo       = models.FileField(upload_to='expedientes/%Y/%m/', verbose_name="Archivo (PDF/imagen)")
    descripcion   = models.TextField(blank=True, verbose_name="Descripción")
    fecha_subida  = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de subida")

    class Meta:
        ordering = ['-fecha_subida']
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"

    def __str__(self):
        return f"{self.titulo} — {self.expediente}"

    def extension(self):
        return self.archivo.name.split('.')[-1].upper() if self.archivo else ''


# ══════════════════════════════════════════════
# 4. MOVIMIENTO  (historial del proceso)
# ══════════════════════════════════════════════
class Movimiento(models.Model):
    TIPOS = [
        ('audiencia',     'Audiencia'),
        ('resolucion',    'Resolución'),
        ('notificacion',  'Notificación'),
        ('memorial',      'Memorial presentado'),
        ('otro',          'Otro'),
    ]

    expediente  = models.ForeignKey(
        Expediente, on_delete=models.CASCADE,
        related_name='movimientos',
        verbose_name="Expediente"
    )
    registrado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='movimientos',
        verbose_name="Registrado por"
    )

    tipo        = models.CharField(max_length=30, choices=TIPOS, default='otro', verbose_name="Tipo")
    fecha       = models.DateField(verbose_name="Fecha del movimiento")
    descripcion = models.TextField(verbose_name="Descripción")
    creado_en   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = "Movimiento"
        verbose_name_plural = "Movimientos"

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.fecha} — {self.expediente}"

# ══════════════════════════════════════════════
# 5. EVENTO DE AGENDA
# ══════════════════════════════════════════════
class Evento(models.Model):
    TIPO_AUDIENCIA   = 'audiencia'
    TIPO_ENTREVISTA  = 'entrevista'
    TIPO_SEGUIMIENTO = 'seguimiento'
    TIPO_OTRO        = 'otro'
    TIPOS = [
        (TIPO_AUDIENCIA,   'Audiencia'),
        (TIPO_ENTREVISTA,  'Entrevista con cliente'),
        (TIPO_SEGUIMIENTO, 'Seguimiento de proceso'),
        (TIPO_OTRO,        'Otro'),
    ]

    MODALIDAD_PRESENCIAL = 'presencial'
    MODALIDAD_VIRTUAL    = 'virtual'
    MODALIDADES = [
        (MODALIDAD_PRESENCIAL, 'Presencial'),
        (MODALIDAD_VIRTUAL,    'Virtual'),
    ]

    titulo       = models.CharField(max_length=200, verbose_name="Título")
    tipo         = models.CharField(max_length=20, choices=TIPOS, default=TIPO_AUDIENCIA)
    expediente   = models.ForeignKey(
        Expediente, on_delete=models.CASCADE,
        related_name='eventos', null=True, blank=True,
        verbose_name="Expediente relacionado"
    )
    responsable  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='eventos', verbose_name="Responsable"
    )
    fecha_hora   = models.DateTimeField(verbose_name="Fecha y hora")
    modalidad    = models.CharField(max_length=20, choices=MODALIDADES, default=MODALIDAD_PRESENCIAL)
    lugar        = models.CharField(max_length=200, blank=True, verbose_name="Lugar / sala")
    enlace_virtual = models.URLField(blank=True, verbose_name="Enlace virtual (Meet/Zoom)")
    descripcion  = models.TextField(blank=True, verbose_name="Descripción / notas")
    recordatorio_enviado = models.BooleanField(default=False)
    creado_en    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha_hora']
        verbose_name = "Evento"
        verbose_name_plural = "Agenda"

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.titulo} ({self.fecha_hora.strftime('%d/%m/%Y %H:%M')})"

    def es_hoy(self):
        from django.utils import timezone
        return self.fecha_hora.date() == timezone.now().date()

    def es_urgente(self):
        from django.utils import timezone
        from datetime import timedelta
        return self.fecha_hora <= timezone.now() + timedelta(days=2)

# ══════════════════════════════════════════════
# 6. TAREA (control de pasantes/procuradores)
# ══════════════════════════════════════════════
class Tarea(models.Model):
    PRIORIDAD_ALTA   = 'alta'
    PRIORIDAD_MEDIA  = 'media'
    PRIORIDAD_BAJA   = 'baja'
    PRIORIDADES = [
        (PRIORIDAD_ALTA,  'Alta'),
        (PRIORIDAD_MEDIA, 'Media'),
        (PRIORIDAD_BAJA,  'Baja'),
    ]

    ESTADO_PENDIENTE   = 'pendiente'
    ESTADO_EN_PROCESO  = 'en_proceso'
    ESTADO_COMPLETADA  = 'completada'
    ESTADOS = [
        (ESTADO_PENDIENTE,  'Pendiente'),
        (ESTADO_EN_PROCESO, 'En proceso'),
        (ESTADO_COMPLETADA, 'Completada'),
    ]

    expediente   = models.ForeignKey(
        Expediente, on_delete=models.CASCADE,
        related_name='tareas', null=True, blank=True,
        verbose_name="Expediente relacionado"
    )
    asignada_a   = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='tareas_asignadas',
        verbose_name="Asignada a"
    )
    creada_por   = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='tareas_creadas',
        verbose_name="Creada por"
    )
    titulo       = models.CharField(max_length=200, verbose_name="Título de la tarea")
    descripcion  = models.TextField(verbose_name="Descripción")
    prioridad    = models.CharField(max_length=10, choices=PRIORIDADES, default=PRIORIDAD_MEDIA)
    estado       = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_PENDIENTE)
    fecha_limite = models.DateField(verbose_name="Fecha límite")
    fecha_completada = models.DateTimeField(null=True, blank=True)
    creada_en    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha_limite', '-prioridad']
        verbose_name = "Tarea"
        verbose_name_plural = "Tareas"

    def __str__(self):
        return f"{self.titulo} → {self.asignada_a.get_full_name()}"

    def esta_vencida(self):
        from django.utils import timezone
        return self.fecha_limite < timezone.now().date() and self.estado != self.ESTADO_COMPLETADA

# ══════════════════════════════════════════════
# 7. EVIDENCIA DE TAREA
# ══════════════════════════════════════════════
class EvidenciaTarea(models.Model):
    tarea       = models.ForeignKey(
        Tarea, on_delete=models.CASCADE,
        related_name='evidencias',
        verbose_name="Tarea"
    )
    subida_por  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        verbose_name="Subida por"
    )
    archivo     = models.FileField(
        upload_to='evidencias/%Y/%m/',
        verbose_name="Archivo (foto o documento)"
    )
    descripcion = models.CharField(max_length=200, blank=True, verbose_name="Descripción")
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_subida']
        verbose_name = "Evidencia"
        verbose_name_plural = "Evidencias"

    def __str__(self):
        return f"Evidencia de: {self.tarea.titulo}"

# ══════════════════════════════════════════════
# 8. PLANTILLA DE CONTRATO
# ══════════════════════════════════════════════
class PlantillaContrato(models.Model):
    TIPOS = [
        ('honorarios',      'Contrato de honorarios profesionales'),
        ('poder_notarial',  'Poder notarial'),
        ('arrendamiento',   'Contrato de arrendamiento'),
        ('compraventa',     'Contrato de compraventa'),
        ('confidencialidad','Acuerdo de confidencialidad'),
        ('otro',            'Otro'),
    ]

    nombre      = models.CharField(max_length=200, verbose_name="Nombre de la plantilla")
    tipo        = models.CharField(max_length=30, choices=TIPOS, default='honorarios')
    contenido   = models.TextField(
        verbose_name="Contenido de la plantilla",
        help_text=(
            "Usa estas variables: {{cliente_nombre}}, {{cliente_ci}}, "
            "{{cliente_direccion}}, {{abogado_nombre}}, {{fecha_hoy}}, "
            "{{expediente_nurej}}, {{monto}}, {{ciudad}}"
        )
    )
    activa      = models.BooleanField(default=True)
    creada_por  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='plantillas_creadas'
    )
    creada_en   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = "Plantilla de contrato"
        verbose_name_plural = "Plantillas de contratos"

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


# ══════════════════════════════════════════════
# 9. CONTRATO GENERADO
# ══════════════════════════════════════════════
class Contrato(models.Model):
    plantilla   = models.ForeignKey(
        PlantillaContrato, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='contratos_generados',
        verbose_name="Plantilla usada"
    )
    cliente     = models.ForeignKey(
        Cliente, on_delete=models.PROTECT,
        related_name='contratos',
        verbose_name="Cliente"
    )
    expediente  = models.ForeignKey(
        Expediente, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='contratos',
        verbose_name="Expediente relacionado"
    )
    generado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='contratos_generados'
    )
    titulo      = models.CharField(max_length=200, verbose_name="Título del contrato")
    contenido_final = models.TextField(verbose_name="Contenido final del contrato")
    monto       = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        verbose_name="Monto (Bs.)"
    )
    ciudad      = models.CharField(max_length=100, default="La Paz", verbose_name="Ciudad")
    fecha_generado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_generado']
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"

    def __str__(self):
        return f"{self.titulo} — {self.cliente.nombre_completo}"

# ══════════════════════════════════════════════
# 10. PLANTILLA DE MEMORIAL
# ══════════════════════════════════════════════
class PlantillaMemorial(models.Model):
    CATEGORIAS = [
        ('asistencia_familiar', 'Asistencia Familiar'),
        ('civil',              'Civil'),
        ('penal',              'Penal'),
        ('laboral',            'Laboral'),
        ('constitucional',     'Constitucional'),
        ('administrativo',     'Administrativo'),
        ('otro',               'Otro'),
    ]

    nombre      = models.CharField(
        max_length=200,
        verbose_name="Nombre del memorial",
        help_text="Ej: Demanda de Asistencia Familiar"
    )
    categoria   = models.CharField(
        max_length=30, choices=CATEGORIAS, default='civil',
        verbose_name="Categoría"
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name="Descripción breve",
        help_text="Explica cuándo se usa este memorial"
    )
    estructura  = models.TextField(
        verbose_name="Estructura / molde del memorial",
        help_text=(
            "Escribe aquí la estructura que la IA debe seguir. "
            "Puedes incluir las secciones obligatorias, el tono, "
            "las normas legales aplicables y los datos que debe pedir. "
            "Variables disponibles: {{cliente_nombre}}, {{cliente_ci}}, "
            "{{expediente_nurej}}, {{juzgado}}, {{abogado_nombre}}, {{ciudad}}, {{fecha_hoy}}"
        )
    )
    normas_aplicables = models.TextField(
        blank=True,
        verbose_name="Normas legales aplicables",
        help_text="Ej: Art. 109 Código de Familia, Art. 5 Ley 603"
    )
    activa      = models.BooleanField(default=True, verbose_name="Activa")
    creada_por  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='plantillas_memorial_creadas'
    )
    creada_en   = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['categoria', 'nombre']
        verbose_name = "Plantilla de memorial"
        verbose_name_plural = "Plantillas de memoriales"

    def __str__(self):
        return f"{self.nombre} ({self.get_categoria_display()})"


# ══════════════════════════════════════════════
# 11. MEMORIAL GENERADO
# ══════════════════════════════════════════════
class Memorial(models.Model):
    plantilla   = models.ForeignKey(
        PlantillaMemorial, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='memoriales_generados',
        verbose_name="Plantilla usada"
    )
    expediente  = models.ForeignKey(
        Expediente, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='memoriales',
        verbose_name="Expediente relacionado"
    )
    cliente     = models.ForeignKey(
        Cliente, on_delete=models.PROTECT,
        related_name='memoriales',
        verbose_name="Cliente"
    )
    generado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='memoriales_generados'
    )
    titulo          = models.CharField(max_length=200, verbose_name="Título del memorial")
    contenido_final = models.TextField(verbose_name="Contenido generado")
    fecha_generado  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_generado']
        verbose_name = "Memorial"
        verbose_name_plural = "Memoriales"

    def __str__(self):
        return f"{self.titulo} — {self.cliente.nombre_completo}"

# ══════════════════════════════════════════════
# 12. PRECEDENTE JURISPRUDENCIAL
# ══════════════════════════════════════════════
class PrecedenteJurisprudencial(models.Model):

    TRIBUNAL_TCP  = 'tcp'
    TRIBUNAL_TSJ  = 'tsj'
    TRIBUNAL_OTRO = 'otro'
    TRIBUNALES = [
        (TRIBUNAL_TCP,  'Tribunal Constitucional Plurinacional (TCP)'),
        (TRIBUNAL_TSJ,  'Tribunal Supremo de Justicia (TSJ)'),
        (TRIBUNAL_OTRO, 'Otro tribunal'),
    ]

    TIPO_SCP  = 'scp'    # Sentencia Constitucional Plurinacional
    TIPO_SC   = 'sc'     # Sentencia Constitucional
    TIPO_AS   = 'as'     # Auto Supremo
    TIPO_AC   = 'ac'     # Auto Constitucional
    TIPO_DCP  = 'dcp'    # Declaración Constitucional Plurinacional
    TIPO_OTRO = 'otro'
    TIPOS = [
        (TIPO_SCP,  'Sentencia Constitucional Plurinacional (SCP)'),
        (TIPO_SC,   'Sentencia Constitucional (SC)'),
        (TIPO_AS,   'Auto Supremo (AS)'),
        (TIPO_AC,   'Auto Constitucional (AC)'),
        (TIPO_DCP,  'Declaración Constitucional Plurinacional (DCP)'),
        (TIPO_OTRO, 'Otro'),
    ]

    MATERIAS = [
        ('civil',              'Civil'),
        ('penal',              'Penal'),
        ('familia',            'Familia'),
        ('laboral',            'Laboral'),
        ('constitucional',     'Constitucional'),
        ('administrativo',     'Administrativo'),
        ('tributario',         'Tributario'),
        ('asistencia_familiar','Asistencia Familiar'),
        ('derechos_humanos',   'Derechos Humanos'),
        ('otro',               'Otro'),
    ]

    ORIGEN_SCRAPER  = 'scraper'
    ORIGEN_MANUAL   = 'manual'
    ORIGEN_IA       = 'ia'
    ORIGENES = [
        (ORIGEN_SCRAPER, 'Extraído automáticamente (bot)'),
        (ORIGEN_MANUAL,  'Ingresado manualmente'),
        (ORIGEN_IA,      'Generado/completado por IA'),
    ]

    # ── Identificación ────────────────────────
    tribunal         = models.CharField(max_length=10, choices=TRIBUNALES,
                                        default=TRIBUNAL_TCP, verbose_name="Tribunal")
    tipo_resolucion  = models.CharField(max_length=10, choices=TIPOS,
                                        default=TIPO_SCP, verbose_name="Tipo de resolución")
    numero_sentencia = models.CharField(max_length=50, unique=True,
                                        verbose_name="Número de sentencia",
                                        help_text="Ej: 0732/2023-S2 o AS 234/2021")
    fecha_resolucion = models.DateField(null=True, blank=True,
                                        verbose_name="Fecha de resolución")
    materia          = models.CharField(max_length=30, choices=MATERIAS,
                                        default='civil', verbose_name="Materia")

    # ── Magistrados ───────────────────────────
    magistrado_relator = models.CharField(max_length=200, blank=True,
                                          verbose_name="Magistrado relator")
    sala               = models.CharField(max_length=100, blank=True,
                                          verbose_name="Sala / Comisión",
                                          help_text="Ej: Primera Sala, Sala Civil")

    # ── Contenido jurídico ────────────────────
    accion_origen    = models.CharField(max_length=200, blank=True,
                                        verbose_name="Acción de origen",
                                        help_text="Ej: Acción de Amparo Constitucional, Recurso de Casación")
    palabras_clave   = models.TextField(blank=True,
                                        verbose_name="Palabras clave",
                                        help_text="Separadas por coma. Ej: debido proceso, tutela, presunción de inocencia")
    ratio_decidendi  = models.TextField(blank=True,
                                        verbose_name="Ratio Decidendi",
                                        help_text="La regla jurídica central que establece la sentencia")
    resumen_ia       = models.TextField(blank=True,
                                        verbose_name="Resumen generado por IA",
                                        help_text="Resumen automático del holding y su aplicación práctica")
    texto_completo   = models.TextField(blank=True,
                                        verbose_name="Texto completo de la sentencia")

    # ── Referencia y trazabilidad ─────────────
    url_fuente       = models.URLField(blank=True,
                                       verbose_name="URL fuente (TCP/TSJ)",
                                       help_text="Link directo a la sentencia en el sitio oficial")
    origen           = models.CharField(max_length=10, choices=ORIGENES,
                                        default=ORIGEN_MANUAL, verbose_name="Origen del registro")
    ingresado_por    = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='precedentes_ingresados',
        verbose_name="Ingresado por"
    )
    verificado       = models.BooleanField(default=False,
                                           verbose_name="Verificado por abogado")
    fecha_ingreso    = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_resolucion', 'numero_sentencia']
        verbose_name = "Precedente jurisprudencial"
        verbose_name_plural = "Banco de jurisprudencia"
        indexes = [
            models.Index(fields=['numero_sentencia']),
            models.Index(fields=['materia']),
            models.Index(fields=['tribunal']),
            models.Index(fields=['fecha_resolucion']),
        ]

    def __str__(self):
        return f"{self.get_tipo_resolucion_display()} {self.numero_sentencia} — {self.get_materia_display()}"

    def get_palabras_lista(self):
        """Retorna las palabras clave como lista."""
        if self.palabras_clave:
            return [p.strip() for p in self.palabras_clave.split(',') if p.strip()]
        return [] 
