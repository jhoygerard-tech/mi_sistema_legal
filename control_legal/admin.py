from django.contrib import admin
from .models import (Cliente, Expediente, Documento, Movimiento, Evento, PlantillaMemorial, Memorial, PrecedenteJurisprudencial)

# ── Título del panel admin ────────────────────
admin.site.site_header  = "LexNova Bolivia — Administración"
admin.site.site_title   = "LexNova Bolivia"
admin.site.index_title  = "Panel de administración"


# ── Documentos inline (dentro del expediente) ─
class DocumentoInline(admin.TabularInline):
    model        = Documento
    extra        = 0
    fields       = ('titulo', 'tipo', 'archivo', 'descripcion', 'fecha_subida')
    readonly_fields = ('fecha_subida',)
    verbose_name = "Documento"
    verbose_name_plural = "Documentos del expediente"


# ── Movimientos inline (dentro del expediente) ─
class MovimientoInline(admin.TabularInline):
    model        = Movimiento
    extra        = 0
    fields       = ('tipo', 'fecha', 'descripcion', 'registrado_por')
    verbose_name = "Movimiento"
    verbose_name_plural = "Historial de movimientos"


# ── Expedientes inline (dentro del cliente) ───
class ExpedienteInline(admin.StackedInline):
    model        = Expediente
    extra        = 0
    fields       = ('numero_expediente', 'nurej', 'materia', 'estado', 'juzgado', 'abogado_asignado')
    show_change_link = True   # botón "Ver/editar" desde el cliente
    verbose_name = "Expediente"
    verbose_name_plural = "Expedientes del cliente"


# ── Admin: Cliente ────────────────────────────
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    inlines          = [ExpedienteInline]
    list_display     = ('nombre_completo', 'ci', 'telefono', 'email', 'abogado_asignado', 'total_expedientes', 'activo', 'fecha_registro')
    list_filter      = ('activo', 'abogado_asignado')
    search_fields    = ('nombre_completo', 'ci', 'telefono', 'email')
    readonly_fields  = ('fecha_registro', 'codigo_acceso',)
    ordering         = ('nombre_completo',)
    list_per_page    = 20
    fieldsets = (
        ('Datos personales', {
            'fields': ('ci', 'nombre_completo', 'telefono', 'email', 'direccion')
        }),
        ('Asignación', {
            'fields': ('abogado_asignado', 'notas_internas')
        }),
        ('Estado', {
            'fields': ('activo', 'fecha_registro', 'codigo_acceso')
        }),
    )


# ── Admin: Expediente ─────────────────────────
@admin.register(Expediente)
class ExpedienteAdmin(admin.ModelAdmin):
    inlines       = [DocumentoInline, MovimientoInline]
    list_display  = ('numero_expediente', 'nurej', 'cliente', 'materia', 'estado', 'abogado_asignado', 'fecha_inicio', 'total_documentos')
    list_filter   = ('estado', 'materia', 'abogado_asignado')
    search_fields = ('numero_expediente', 'nurej', 'cliente__nombre_completo', 'juzgado')
    readonly_fields = ('fecha_inicio',)
    ordering      = ('-fecha_inicio',)
    list_per_page = 20
    fieldsets = (
        ('Datos del proceso', {
            'fields': ('cliente', 'numero_expediente', 'nurej', 'juzgado', 'materia', 'tipo_proceso', 'descripcion')
        }),
        ('Asignación y estado', {
            'fields': ('abogado_asignado', 'estado', 'fecha_inicio', 'fecha_conclusion')
        }),
    )


# ── Admin: Documento ──────────────────────────
@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display  = ('titulo', 'tipo', 'expediente', 'subido_por', 'fecha_subida', 'extension')
    list_filter   = ('tipo', 'fecha_subida')
    search_fields = ('titulo', 'expediente__numero_expediente', 'expediente__cliente__nombre_completo')
    readonly_fields = ('fecha_subida',)
    ordering      = ('-fecha_subida',)
    list_per_page = 20


# ── Admin: Movimiento ─────────────────────────
@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display  = ('tipo', 'fecha', 'expediente', 'registrado_por', 'creado_en')
    list_filter   = ('tipo', 'fecha')
    search_fields = ('descripcion', 'expediente__numero_expediente', 'expediente__cliente__nombre_completo')
    readonly_fields = ('creado_en',)
    ordering      = ('-fecha',)
    list_per_page = 20

# ── Admin: Evento (Agenda) ────────────────────
@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display  = ('titulo', 'tipo', 'fecha_hora', 'modalidad', 'responsable', 'expediente')
    list_filter   = ('tipo', 'modalidad', 'fecha_hora')
    search_fields = ('titulo', 'expediente__cliente__nombre_completo')
    ordering      = ('fecha_hora',)
    list_per_page = 20

# ── Admin: Plantilla de Memorial ──────────────
@admin.register(PlantillaMemorial)
class PlantillaMemorialAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'categoria', 'activa', 'creada_por', 'actualizada_en')
    list_filter   = ('categoria', 'activa')
    search_fields = ('nombre', 'descripcion')
    ordering      = ('categoria', 'nombre')
    list_per_page = 20
    fieldsets = (
        ('Identificación', {
            'fields': ('nombre', 'categoria', 'descripcion', 'activa')
        }),
        ('Contenido para la IA', {
            'fields': ('estructura', 'normas_aplicables'),
            'description': (
                'La IA usará la estructura como molde y las normas como referencia. '
                'Sé específico: incluye las secciones obligatorias, el tono y '
                'los datos que debe solicitar al abogado.'
            )
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.creada_por:
            obj.creada_por = request.user
        super().save_model(request, obj, form, change)


# ── Admin: Memorial generado ──────────────────
@admin.register(Memorial)
class MemorialAdmin(admin.ModelAdmin):
    list_display  = ('titulo', 'cliente', 'plantilla', 'generado_por', 'fecha_generado')
    list_filter   = ('plantilla__categoria', 'fecha_generado')
    search_fields = ('titulo', 'cliente__nombre_completo')
    readonly_fields = ('fecha_generado', 'generado_por', 'contenido_final')
    ordering      = ('-fecha_generado',)
    list_per_page = 20    

# ── Admin: Banco de Jurisprudencia ────────────
@admin.register(PrecedenteJurisprudencial)
class PrecedenteAdmin(admin.ModelAdmin):
    list_display  = ('numero_sentencia', 'tipo_resolucion', 'tribunal',
                     'materia', 'fecha_resolucion', 'magistrado_relator',
                     'verificado', 'origen')
    list_filter   = ('tribunal', 'tipo_resolucion', 'materia', 'verificado', 'origen')
    search_fields = ('numero_sentencia', 'magistrado_relator', 'palabras_clave',
                     'ratio_decidendi', 'resumen_ia', 'accion_origen')
    readonly_fields = ('fecha_ingreso', 'fecha_actualizacion', 'ingresado_por')
    ordering      = ('-fecha_resolucion',)
    list_per_page = 20
    list_editable = ('verificado',)

    fieldsets = (
        ('Identificación', {
            'fields': (
                'tribunal', 'tipo_resolucion', 'numero_sentencia',
                'fecha_resolucion', 'materia', 'sala', 'magistrado_relator',
                'accion_origen',
            )
        }),
        ('Análisis jurídico', {
            'fields': ('palabras_clave', 'ratio_decidendi', 'resumen_ia'),
            'description': (
                'El ratio decidendi es la regla jurídica central. '
                'El resumen de IA se genera automáticamente desde el buscador.'
            )
        }),
        ('Texto completo', {
            'fields': ('texto_completo',),
            'classes': ('collapse',),
        }),
        ('Trazabilidad', {
            'fields': ('url_fuente', 'origen', 'verificado',
                       'ingresado_por', 'fecha_ingreso', 'fecha_actualizacion'),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.ingresado_por:
            obj.ingresado_por = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ingresado_por')